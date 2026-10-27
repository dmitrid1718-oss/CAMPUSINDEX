#!/usr/bin/env python3
"""Fetch audited BLS/FRED monthly observations for Campus Index.
Preserves prior dataset when upstream fails. No interpolated or synthetic observations.
"""
import csv, io, json, math, time, urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'history.json'
SERIES={
  'tuition_childcare_cpi':('CUSR0000SEEB','Tuition, other school fees AND childcare CPI (not tuition-only)'),
  'all_items_cpi':('CUSR0000SA0','All-items CPI'),
  'wage_hourly':('CES0500000003','Average hourly earnings, total private')
}

def get(sid):
  fred_id = {'CUSR0000SA0': 'CPIAUCSL'}.get(sid, sid)
  url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+fred_id
  for n in range(2):
    try:
      req=urllib.request.Request(url,headers={'User-Agent':'CampusIndex/1.0 (public federal series)','Accept':'text/csv'})
      with urllib.request.urlopen(req,timeout=20) as f: raw=f.read().decode('utf-8-sig')
      reader=csv.DictReader(io.StringIO(raw))
      data={}
      for row in reader:
        m=(row.get('DATE') or row.get('observation_date') or '')[:7]
        v=row.get(fred_id,'')
        if len(m)==7 and v not in ('','.','ND'):
          try:
            x=float(v)
            if math.isfinite(x) and x>0: data[m]=x
          except ValueError: pass
      if len(data)<12:raise ValueError('Insufficient observations')
      return data
    except (OSError,ValueError,TimeoutError) as e:
      print(sid,'attempt',n+1,'failed:',e,flush=True)
      if n==1:
        print(sid, 'trying original BLS source', flush=True)
        return get_bls(sid)
      time.sleep((n+1)*6)


def get_bls(sid):
  """Use the same seasonally adjusted BLS series, in unauthenticated 10-year windows."""
  data = {}
  current_year = datetime.now(timezone.utc).year
  for start in range(2006, current_year + 1, 10):
    end = min(start + 9, current_year)
    url = f'https://api.bls.gov/publicAPI/v2/timeseries/data/{sid}?startyear={start}&endyear={end}'
    req = urllib.request.Request(url, headers={'User-Agent': 'CampusIndex/1.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
      payload = json.load(response)
    if payload.get('status') != 'REQUEST_SUCCEEDED':
      raise ValueError(f'BLS failed for {sid}: {payload.get("message")}')
    entries = payload.get('Results', {}).get('series', [])
    if len(entries) != 1 or entries[0].get('seriesID') != sid:
      raise ValueError(f'Unexpected BLS series for {sid}')
    for row in entries[0].get('data', []):
      period = row.get('period', '')
      if period not in [f'M{i:02d}' for i in range(1, 13)]:
        continue
      year = int(row['year'])
      if not start <= year <= end:
        raise ValueError('BLS returned observations outside requested window')
      if row.get('value') in (None, '', '-', '.'):
        continue  # Missing observations are omitted, never filled.
      value = float(row['value'])
      if not math.isfinite(value) or value <= 0:
        raise ValueError('Invalid BLS observation')
      data[f'{year}-{period[1:]}'] = value
  if len(data) < 12 or '2006-03' not in data:
    raise ValueError(f'Incomplete BLS history for {sid}')
  return data

values={name:get(sid) for name,(sid,_) in SERIES.items()}
months=sorted(set.intersection(*(set(v.keys()) for v in values.values())))
months=[m for m in months if m>='2000-01']
if not months or len(months)<12:raise ValueError('No matched observations')
base='2006-03'
if base not in months:raise ValueError('Missing earliest common wage baseline 2006-03')
series={}
for name,(sid,label) in SERIES.items():
  series[name]={'id':sid,'label':label,'source':'https://fred.stlouisfed.org/series/'+{'CUSR0000SA0':'CPIAUCSL'}.get(sid,sid),
                'index_2006_03':[round(100*values[name][m]/values[name][base],3) for m in months],
                'raw':[round(values[name][m],3) for m in months]}
result={'updated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'latest_month':months[-1], 'base_month':base,'months':months,'series':series,
        'disclaimer':'Tuition/other fees/childcare CPI is a broad price proxy and is NOT tuition-only or room-and-board. Wage index is an average, not a household budget. Source publication schedules differ.'}
prior=json.loads(OUT.read_text()) if OUT.exists() else {}
if prior.get('months')==months and all(prior.get('series',{}).get(k,{}).get('raw')==series[k]['raw'] for k in series):
  print('No new or revised official readings; no change.')
else:
  OUT.parent.mkdir(parents=True, exist_ok=True)
  temporary = OUT.with_suffix('.tmp')
  temporary.write_text(json.dumps(result,indent=2)+'\n')
  temporary.replace(OUT)
  print('Updated matched monthly points:',len(months),'latest:',months[-1])

# Historical source data is collected only from published agency observations.

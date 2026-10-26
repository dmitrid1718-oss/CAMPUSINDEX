#!/usr/bin/env python3
"""Fetch audited BLS/FRED monthly observations for Campus Index.
Preserves prior dataset when upstream fails. No interpolated or synthetic observations.
"""
import csv, io, json, time, urllib.request
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
  url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+sid
  for n in range(4):
    try:
      req=urllib.request.Request(url,headers={'User-Agent':'CampusIndex/1.0 (public federal series)','Accept':'text/csv'})
      with urllib.request.urlopen(req,timeout=45) as f: raw=f.read().decode('utf-8-sig')
      reader=csv.DictReader(io.StringIO(raw))
      data={}
      for row in reader:
        m=(row.get('DATE') or row.get('observation_date') or '')[:7]
        v=row.get(sid,'')
        if len(m)==7 and v not in ('','.','ND'):
          try:
            x=float(v)
            if x>0: data[m]=x
          except ValueError: pass
      if len(data)<12:raise ValueError('Insufficient observations')
      return data
    except (OSError,ValueError,TimeoutError) as e:
      print(sid,'attempt',n+1,'failed:',e,flush=True)
      if n==3:raise
      time.sleep((n+1)*6)

values={name:get(sid) for name,(sid,_) in SERIES.items()}
months=sorted(set.intersection(*(set(v.keys()) for v in values.values())))
months=[m for m in months if m>='2000-01']
if not months or len(months)<12:raise ValueError('No matched observations')
base='2020-01'
if base not in months:raise ValueError('Missing 2020 baseline')
series={}
for name,(sid,label) in SERIES.items():
  series[name]={'id':sid,'label':label,'source':'https://fred.stlouisfed.org/series/'+sid,
                'index_2020_01':[round(100*values[name][m]/values[name][base],3) for m in months],
                'raw':[round(values[name][m],3) for m in months]}
result={'updated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'latest_month':months[-1], 'base_month':base,'months':months,'series':series,
        'disclaimer':'Tuition/other fees/childcare CPI is a broad price proxy and is NOT tuition-only or room-and-board. Wage index is an average, not a household budget. Source publication schedules differ.'}
prior=json.loads(OUT.read_text()) if OUT.exists() else {}
if prior.get('months')==months and all(prior.get('series',{}).get(k,{}).get('raw')==series[k]['raw'] for k in series):
  print('No new or revised official readings; no change.')
else:
  OUT.write_text(json.dumps(result,indent=2)+'\n')
  print('Updated matched monthly points:',len(months),'latest:',months[-1])

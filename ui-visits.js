/* UI visit sensor v2: anonymous IDs and event times only; never reads page content or URL parameters. */
(() => {
  'use strict';
  if (window.__uiVisitsStarted) return;
  window.__uiVisitsStarted = true;
  const project = 'campusindex';
  const endpoint = 'https://znzoepudtfpsxoglkyia.supabase.co/rest/v1/site_visit_events';
  const key = 'sb_publishable_XySCbewhCGiQXPGMui5peA_SiZz0VqA';
  const uuid = () => crypto.randomUUID();
  const validId = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  let visitor;
  try {
    visitor = localStorage.getItem('ui.visitor.v2');
    if (!validId(visitor)) { visitor = uuid(); localStorage.setItem('ui.visitor.v2', visitor); }
  } catch { visitor = uuid(); }
  const sessionKey = 'ui.session.v2.' + project;
  const expiry = 30 * 60 * 1000;
  let session;
  try { session = JSON.parse(sessionStorage.getItem(sessionKey) || 'null'); } catch {}
  if (!session || !validId(session.id) || !Number.isFinite(session.last) || Date.now() - session.last > expiry) {
    session = { id: uuid(), last: Date.now() };
  }
  const persist = () => { try { sessionStorage.setItem(sessionKey, JSON.stringify(session)); } catch {} };
  persist();
  let started = false, pending = false, lastSent = 0, timer;
  async function send(eventType) {
    if (pending) return;
    if (Date.now() - session.last > expiry) {
      session = { id: uuid(), last: Date.now() }; started = false;
    }
    // A failed first view must be retried before sending any heartbeat.
    const type = started ? eventType : 'view';
    if (type === 'heartbeat' && Date.now() - lastSent < 1000) return;
    pending = true;
    try {
      const response = await fetch(endpoint, {
        method: 'POST', keepalive: true, credentials: 'omit', referrerPolicy: 'no-referrer',
        headers: { apikey: key, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
        body: JSON.stringify({ visitor_id: visitor, session_id: session.id, event_type: type, project_slug: project })
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      started = true; lastSent = Date.now(); session.last = lastSent; persist();
    } catch (error) {
      console.warn('UI visit sensor could not record an event:', error instanceof Error ? error.message : 'network unavailable');
    } finally { pending = false; }
  }
  function resume() {
    clearInterval(timer);
    if (document.visibilityState !== 'visible') return;
    void send(started ? 'heartbeat' : 'view');
    timer = setInterval(() => { if (document.visibilityState === 'visible') void send('heartbeat'); }, 30000);
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') resume();
    else { clearInterval(timer); if (started) void send('heartbeat'); }
  });
  window.addEventListener('pagehide', () => { clearInterval(timer); if (started) void send('heartbeat'); });
  window.addEventListener('pageshow', event => { if (event.persisted) resume(); });
  window.addEventListener('online', resume);
  resume();
})();

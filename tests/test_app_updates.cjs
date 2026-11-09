const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

async function run() {
  const filename = path.join(__dirname, '..', 'app-updates.js');
  assert.ok(fs.existsSync(filename), 'Open-time update checking is not implemented');
  const { installOpenRefresh } = await import('data:text/javascript;base64,' + fs.readFileSync(filename).toString('base64'));
  const tick = () => new Promise(resolve => setImmediate(resolve));
  const storage = () => ({ values: new Map(), getItem(key) { return this.values.get(key) ?? null; }, setItem(key, value) { this.values.set(key, String(value)); } });
  function fixture({ saved = 'old', revision = 'new', key = 'vocabulary', store = storage(), beforeReload, fetch } = {}) {
    const host = new EventTarget();
    host.document = new EventTarget();
    host.document.visibilityState = 'visible';
    host.navigator = { onLine: true };
    host.sessionStorage = store;
    host.reloads = 0;
    host.location = { reload: () => host.reloads++ };
    host.requests = 0;
    host.revision = revision;
    host.fetch = fetch || (async (_url, options) => {
      host.requests++;
      assert.equal(options.cache, 'no-store');
      return { ok: true, json: async () => ({ schema_version: 1, revision: host.revision }) };
    });
    if (saved !== null) store.setItem(key, saved);
    const control = installOpenRefresh({ host, storageKey: key, beforeReload, timeoutMs: 15 });
    return { host, control, store };
  }
  function foreground(host) {
    host.document.visibilityState = 'hidden';
    host.document.dispatchEvent(new Event('visibilitychange'));
    host.document.visibilityState = 'visible';
    host.document.dispatchEvent(new Event('visibilitychange'));
  }

  let f = fixture({ saved: 'same', revision: 'same' });
  await f.control.check();
  assert.equal(f.host.reloads, 0);
  foreground(f.host);
  await f.control.check();
  assert.equal(f.host.reloads, 0, 'No new version must not interrupt practice');
  f.control.dispose();

  f = fixture();
  await Promise.all([f.control.check(), f.control.check()]);
  assert.equal(f.host.reloads, 1, 'Concurrent signals must reload only once');
  assert.equal(f.store.getItem('vocabulary'), 'new');
  foreground(f.host);
  await f.control.check();
  assert.equal(f.host.reloads, 1);
  const persisted = f.store;
  f.control.dispose();
  f = fixture({ saved: null, store: persisted });
  await f.control.check();
  assert.equal(f.host.reloads, 0, 'Reloaded document must not start a reload loop');
  f.host.revision = 'next';
  foreground(f.host);
  await f.control.check();
  assert.equal(f.host.reloads, 0, 'Rapid deployments must not cause a refresh loop');
  f.control.dispose();

  f = fixture({ saved: 'same', revision: 'same' });
  await f.control.check();
  f.host.navigator.onLine = false;
  f.host.revision = 'new';
  const requests = f.host.requests;
  foreground(f.host);
  await f.control.check();
  assert.equal(f.host.requests, requests);
  assert.equal(f.host.reloads, 0);
  f.host.navigator.onLine = true;
  f.host.dispatchEvent(new Event('online'));
  await f.control.check();
  assert.equal(f.host.reloads, 1);
  f.control.dispose();

  for (const fetch of [async () => { throw Error('offline'); }, async () => ({ ok: false }), async () => ({ ok: true, json: async () => ({ schema_version: 2, revision: 'bad' }) })]) {
    f = fixture({ fetch });
    await f.control.check();
    assert.equal(f.host.reloads, 0);
    assert.equal(f.store.getItem('vocabulary'), 'old');
    f.control.dispose();
  }

  f = fixture({ fetch: (_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(Error('timeout')))) });
  await f.control.check();
  assert.equal(f.host.reloads, 0);
  f.control.dispose();

  f = fixture({ saved: null, store: { getItem() { throw Error('storage blocked'); }, setItem() { throw Error('storage blocked'); } } });
  await f.control.check();
  assert.equal(f.host.reloads, 0, 'Blocked session storage must not create a reload loop');
  f.control.dispose();

  let finishSave;
  f = fixture({ beforeReload: () => new Promise(resolve => { finishSave = resolve; }) });
  await tick();
  assert.equal(f.host.reloads, 0, 'Pending progress writes must finish before refreshing');
  finishSave();
  await f.control.check();
  assert.equal(f.host.reloads, 1);
  f.control.dispose();

  f = fixture({ beforeReload: async () => { throw Error('save failed'); } });
  await f.control.check();
  assert.equal(f.host.reloads, 0);
  assert.equal(f.store.getItem('vocabulary'), 'old');
  f.control.dispose();
  console.log('Open-refresh tests passed: first open, unchanged version, foreground, coalescing, loop guard, offline, reconnect, timeout, storage failure, and progress-save protection.');
}

run().catch(error => { console.error(error); process.exitCode = 1; });

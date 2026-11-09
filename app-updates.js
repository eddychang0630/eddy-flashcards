export function installOpenRefresh({
  host = window,
  manifestUrl = './app-version.json',
  storageKey,
  beforeReload = async () => {},
  timeoutMs = 4000,
}) {
  let pending = null;
  let reloading = false;
  let disposed = false;
  let wasHidden = host.document.visibilityState === 'hidden';
  let controller = null;

  async function probe() {
    if (disposed || reloading || host.document.visibilityState === 'hidden' || host.navigator.onLine === false) return;
    let timer;
    try {
      controller = new AbortController();
      timer = setTimeout(() => controller?.abort(), timeoutMs);
      const response = await host.fetch(manifestUrl, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) return;
      const release = await response.json();
      if (release.schema_version !== 1 || typeof release.revision !== 'string' || !release.revision) return;
      const storage = host.sessionStorage;
      if (storage.getItem(storageKey) === release.revision) return;
      const lastReload = Number(storage.getItem(storageKey + ':reload') || 0);
      if (lastReload && Date.now() - lastReload < 10000) return;
      await beforeReload();
      if (disposed || host.document.visibilityState === 'hidden' || host.navigator.onLine === false) return;
      storage.setItem(storageKey, release.revision);
      storage.setItem(storageKey + ':reload', String(Date.now()));
      if (storage.getItem(storageKey) !== release.revision) return;
      reloading = true;
      host.location.reload();
    } catch {
      // Offline use, blocked storage, and unfinished saves must keep the current page.
    } finally {
      clearTimeout(timer);
      controller = null;
    }
  }

  function check() {
    if (!pending) pending = probe().finally(() => { pending = null; });
    return pending;
  }
  function visibility() {
    if (host.document.visibilityState === 'hidden') { wasHidden = true; return; }
    if (wasHidden) { wasHidden = false; check(); }
  }
  function restored(event) { if (event.persisted) check(); }
  host.document.addEventListener('visibilitychange', visibility);
  host.addEventListener('pageshow', restored);
  host.addEventListener('online', check);
  check();
  return {
    check,
    dispose() {
      disposed = true;
      controller?.abort();
      host.document.removeEventListener('visibilitychange', visibility);
      host.removeEventListener('pageshow', restored);
      host.removeEventListener('online', check);
    },
  };
}

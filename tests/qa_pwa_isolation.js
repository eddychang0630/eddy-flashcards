const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const origin = 'https://eddychang0630.github.io';
const root = path.join(__dirname, '..');

function loadWorker(file, scopePath, options = {}) {
  const handlers = {};
  const deleted = [];
  const location = new URL(scopePath, origin);
  const storage = options.storage || new Map();
  const lookup = (entries, key) => entries?.get(typeof key === 'string' ? key : key.url);
  const caches = {
    keys: async () => [...storage.keys()],
    delete: async name => deleted.push(name),
    match: async key => [...storage.values()].map(entries => lookup(entries, key)).find(Boolean),
    open: async name => ({match: async key => lookup(storage.get(name), key)}),
  };
  const self = {
    location,
    registration: {scope: location.href},
    clients: {claim: async () => {}},
    skipWaiting: async () => {},
    addEventListener: (type, handler) => { handlers[type] = handler; },
  };
  const context = {self, caches, URL, Request, Response, fetch: options.fetch || (async () => { throw Error('offline'); })};
  vm.runInNewContext(fs.readFileSync(path.join(root, file), 'utf8'), context);
  return {
    deleted,
    activate() {
      let ready;
      handlers.activate({waitUntil: promise => { ready = promise; }});
      return ready;
    },
    navigate(url) {
      let response;
      handlers.fetch({request: {method: 'GET', mode: 'navigate', url: new URL(url, origin).href}, respondWith: value => { response = value; }});
      return response;
    },
  };
}

test('vocabulary worker leaves sibling App navigation to the browser or its own worker', () => {
  const worker = loadWorker('sw.js', '/eddy-flashcards/');
  for (const route of ['/eddy-flashcards/sentences', '/eddy-flashcards/sentences/', '/eddy-flashcards/speaking/index.html', '/eddy-speaking/', 'https://example.org/']) {
    assert.equal(worker.navigate(route), undefined, route);
  }
});

test('vocabulary activation removes its own old cache only', async () => {
  const names = ['eddy-flashcard-v4', 'eddy-flashcard-v5', 'eddy-sentences-v2', 'eddy-chunks-v7', 'eddy-speaking-v1', 'another-app'];
  const worker = loadWorker('sw.js', '/eddy-flashcards/', {storage: new Map(names.map(name => [name, new Map()]))});
  await worker.activate();
  assert.deepEqual(worker.deleted, ['eddy-flashcard-v4']);
});

test('vocabulary navigation uses only its own cached page or a valid offline response', async () => {
  const cached = new Response('old vocabulary shell');
  const storage = new Map([
    ['eddy-speaking-v1', new Map([['./index.html', new Response('speaking shell')]])],
    ['eddy-flashcard-v5', new Map([['./index.html', cached]])],
  ]);
  const worker = loadWorker('sw.js', '/eddy-flashcards/', {storage});
  assert.equal(await worker.navigate('/eddy-flashcards/'), cached);
  storage.get('eddy-flashcard-v5').clear();
  const response = await worker.navigate('/eddy-flashcards/');
  assert.equal(response.status, 503);
  assert.match(await response.text(), /重新整理/);
});

test('an installed legacy speaking PWA redirects both start paths', async () => {
  const worker = loadWorker('speaking/sw.js', '/eddy-flashcards/speaking/');
  for (const route of ['/eddy-flashcards/speaking/', '/eddy-flashcards/speaking/index.html']) {
    const response = await worker.navigate(route);
    assert.equal(response.status, 302);
    assert.equal(response.headers.get('location'), origin + '/eddy-speaking/');
  }
  assert.equal(worker.navigate('/eddy-flashcards/sentences/'), undefined);
});

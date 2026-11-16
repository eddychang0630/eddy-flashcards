const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const playbackCode = html.slice(
  html.indexOf('let activeAudio=null'),
  html.indexOf('// Search always uses the complete vocabulary')
);

function testPlayer(navigator, webAudio = {}) {
  const played = [];
  const elements = new Map();
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, {
        dataset: { audioPath: 'test.mp3' },
        classList: { add() {}, remove() {} },
        setAttribute(name, value) { this[name] = value; },
        getAttribute() { return id; },
      });
      return elements.get(id);
    },
  };
  class Audio {
    constructor() {
      this.defaultPlaybackRate = 1;
      this.playbackRate = 1;
      this.preservesPitch = true;
    }
    play() {
      played.push({
        sessionType: navigator.audioSession?.type,
        defaultRate: this.defaultPlaybackRate,
        rate: this.playbackRate,
        preservesPitch: this.preservesPitch,
      });
      return Promise.resolve();
    }
    pause() {}
  }
  const context = vm.createContext({
    navigator, document, Audio, AbortController, setTimeout, clearTimeout, ...webAudio,
  });
  vm.runInContext(playbackCode, context);
  const event = { preventDefault() {}, stopPropagation() {} };
  return {
    played,
    play: id => context.playCardAudio(event, id),
    button: id => document.getElementById(id),
    setAudio: (id, path, slowPath) => context.setAudioButton(id, path, slowPath),
  };
}

test('study and quiz clips ask to mix, and only headwords play slower', () => {
  const player = testPlayer({ audioSession: { type: 'auto' } });
  for (const mode of ['s', 'q']) {
    player.play(`${mode}-word-audio`);
    player.play(`${mode}-example-audio`);
  }
  assert.deepEqual(player.played.map(clip => clip.sessionType), Array(4).fill('ambient'));
  for (const rate of ['defaultRate', 'rate']) {
    assert.deepEqual(player.played.map(clip => clip[rate]), [0.8, 1, 0.8, 1]);
  }
  assert(player.played.every(clip => clip.preservesPitch));
});

test('pronunciations still play when the browser does not allow audio session changes', () => {
  const unsupported = testPlayer({});
  unsupported.play('s-word-audio');
  assert.equal(unsupported.played.length, 1);

  const blocked = testPlayer({ audioSession: {
    get type() { return 'auto'; },
    set type(_) { throw new Error('Unsupported audio session type'); },
  } });
  blocked.play('q-word-audio');
  assert.equal(blocked.played[0].rate, 0.8);
});

test('opening the app does not access or write the system audio session', () => {
  let reads = 0;
  testPlayer({ userAgent: 'iPhone', get audioSession() { reads++; return { type: 'auto' }; } });
  assert.equal(reads, 0);
});

test('iPhone uses Web Audio for both speeds without opening a media element', async () => {
  const activity = [];
  const nodes = [];
  class AudioContext {
    async close() { activity.push('close'); }
    resume() {
      activity.push('resume');
      return Promise.resolve();
    }
    async decodeAudioData(bytes) { return bytes; }
    createBufferSource() {
      const node = {
        connect() {},
        disconnect() {},
        start() { activity.push('start'); },
        stop() { activity.push('stop'); },
      };
      nodes.push(node);
      return node;
    }
  }
  const session = { type: 'auto' };
  const player = testPlayer({ userAgent: 'iPhone', audioSession: session }, {
    window: { AudioContext },
    async fetch(url) {
      activity.push(url);
      return { ok: true, async arrayBuffer() { return new ArrayBuffer(4); } };
    },
  });
  player.setAudio('s-word-audio', 'word.mp3', 'word-slow08.mp3');
  player.setAudio('s-example-audio', 'example.mp3');
  await player.play('s-word-audio');
  await player.play('s-example-audio');
  nodes[1].onended();
  assert.deepEqual(activity, [
    'resume', 'word-slow08.mp3', 'start', 'stop', 'close',
    'resume', 'example.mp3', 'start', 'stop', 'close',
  ]);
  assert.equal(player.button('s-example-audio')['aria-pressed'], 'false');
  assert.equal(player.played.length, 0);
  assert.equal(session.type, 'auto');
});

test('canceled or failed iPhone requests never start regular media playback', async () => {
  let starts = 0;
  let finishFetch;
  let signal;
  let closed = 0;
  class AudioContext {
    state = 'running';
    async resume() {}
    async close() { closed++; }
    async decodeAudioData(bytes) { return bytes; }
    createBufferSource() { starts++; throw new Error('Unexpected source'); }
  }
  const player = testPlayer({ userAgent: 'iPhone' }, {
    window: { AudioContext },
    fetch(_url, options) {
      signal=options.signal;
      return new Promise(resolve => { finishFetch=resolve; });
    },
  });
  player.setAudio('q-word-audio', 'word.mp3', 'word-slow08.mp3');
  const pending = player.play('q-word-audio');
  player.play('q-word-audio');
  assert(signal.aborted);
  finishFetch({ ok: true, async arrayBuffer() { return new ArrayBuffer(4); } });
  await pending;
  const failed = player.play('q-word-audio');
  finishFetch({ ok: false });
  await failed;
  assert.equal(starts, 0);
  assert.equal(closed, 2);
  assert.equal(player.played.length, 0);
  assert.equal(player.button('q-word-audio')['aria-pressed'], 'false');
  assert.match(player.button('audio-status').textContent, /Safari/);
});

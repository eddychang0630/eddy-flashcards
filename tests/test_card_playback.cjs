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

function testPlayer(navigator) {
  const played = [];
  const audios = [];
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
    constructor(src) {
      this.src = src;
      this.defaultPlaybackRate = 1;
      this.playbackRate = 1;
      this.preservesPitch = true;
      audios.push(this);
    }
    play() {
      played.push({
        src: this.src,
        sessionType: navigator.audioSession?.type,
        defaultRate: this.defaultPlaybackRate,
        rate: this.playbackRate,
        preservesPitch: this.preservesPitch,
      });
      return Promise.resolve();
    }
    pause() { this.paused = true; }
  }
  const context = vm.createContext({
    navigator, document, Audio, AbortController, setTimeout: () => 0, clearTimeout() {},
  });
  vm.runInContext(playbackCode, context);
  const event = { preventDefault() {}, stopPropagation() {} };
  return {
    played,
    audios,
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
  const unsupported = testPlayer({ userAgent: 'iPhone' });
  unsupported.play('s-word-audio');
  assert.equal(unsupported.played.length, 1);

  const blocked = testPlayer({ userAgent: 'iPhone', audioSession: {
    get type() { return 'auto'; },
    set type(_) { throw new Error('Unsupported audio session type'); },
  } });
  blocked.play('q-word-audio');
  assert.equal(blocked.played[0].rate, 0.8);
});

test('opening the app does not access or write the system audio session', () => {
  let reads = 0;
  const player = testPlayer({ userAgent: 'iPhone', get audioSession() { reads++; return { type: 'auto' }; } });
  assert.equal(reads, 0);
  assert.equal(player.audios.length, 0);
});

test('iOS plays the slow word and original example as media on a tap', () => {
  for (const device of [
    { userAgent: 'iPhone', standalone: false },
    { userAgent: 'iPhone', standalone: true },
    { platform: 'MacIntel', maxTouchPoints: 5 },
  ]) {
    const session = { type: 'auto' };
    const player = testPlayer({ ...device, audioSession: session });
    for (const mode of ['s', 'q']) {
      player.setAudio(`${mode}-word-audio`, 'word.mp3', 'word-slow08.mp3');
      player.setAudio(`${mode}-example-audio`, 'example.mp3');
      player.play(`${mode}-word-audio`);
      player.play(`${mode}-example-audio`);
    }
    assert.deepEqual(player.played.map(clip => [clip.src, clip.sessionType, clip.rate]), [
      ['word-slow08.mp3', 'playback', 1],
      ['example.mp3', 'playback', 1],
      ['word-slow08.mp3', 'playback', 1],
      ['example.mp3', 'playback', 1],
    ]);
  }
});

test('stopping, finishing or failing a media clip clears its playing state', () => {
  const player = testPlayer({ userAgent: 'iPhone' });
  player.play('q-word-audio');
  assert.equal(player.button('q-word-audio')['aria-pressed'], 'true');
  player.play('q-word-audio');
  assert.equal(player.audios[0].paused, true);
  assert.equal(player.button('q-word-audio')['aria-pressed'], 'false');

  player.play('s-example-audio');
  player.audios[1].onended();
  assert.equal(player.button('s-example-audio')['aria-pressed'], 'false');
  player.play('s-example-audio');
  player.audios[2].onerror();
  assert.equal(player.button('s-example-audio')['aria-pressed'], 'false');
  assert.match(player.button('audio-status').textContent, /音檔載入失敗/);
});

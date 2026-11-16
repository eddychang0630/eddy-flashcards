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
  const document = {
    getElementById(id) {
      return {
        dataset: { audioPath: 'test.mp3' },
        classList: { add() {}, remove() {} },
        setAttribute() {},
        getAttribute() { return id; },
      };
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
  const context = vm.createContext({ navigator, document, Audio });
  vm.runInContext(playbackCode, context);
  const event = { preventDefault() {}, stopPropagation() {} };
  return { played, play: id => context.playCardAudio(event, id) };
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

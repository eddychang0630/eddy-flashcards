const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

test('the speaking guide entry is next to scenarios and starts hidden', () => {
  const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
  const views = [...html.matchAll(/data-view="([^"]+)"/g)].map(match => match[1]);
  assert.deepEqual(views, ['today', 'lessons', 'scenarios', 'guides']);
  assert.match(html, /<div id="speaking-guides"[^>]* hidden>/);
});

test('the questions guide has the six reference sections and bilingual corrections', async () => {
  const { speakingGuides } = await import('../src/speaking-guides.mjs');
  const guide = speakingGuides.find(topic => topic.id === 'asking-questions');
  assert.equal(guide.title, '英文問句');
  assert.deepEqual(guide.sections.map(section => section.id), [
    'question-words', 'how', 'tense', 'subject', 'negative', 'conversation',
  ]);
  assert.deepEqual(new Set(guide.shortcuts.map(item => item.section)), new Set(guide.sections.map(section => section.id)));
  const words = guide.sections[0].patterns.map(pattern => pattern.title.split('｜')[0]);
  assert.deepEqual(words, ['What', 'Where', 'When', 'Why', 'Who / Whom', 'Which', 'Whose', 'How']);
  for (const { patterns } of guide.sections) {
    assert(patterns.length >= 2);
    for (const { title, usage, structure, examples, mistake } of patterns) {
      assert(title && usage && structure);
      assert(examples.length >= 2 && examples.every(([english, chinese]) => english && chinese), title);
      assert(mistake.wrong && mistake.right && mistake.reason && mistake.wrong !== mistake.right, title);
    }
  }
});

test('a shortcut opens its matching section and moves focus to the heading', async () => {
  const { renderSpeakingGuides } = await import('../src/speaking-guide-view.mjs');
  function createElement(tagName) {
    return {
      tagName, children: [], ownerDocument: { createElement },
      append(...children) { this.children.push(...children); },
      replaceChildren(...children) { this.children = children; },
      setAttribute(name, value) { this[name] = value; },
      addEventListener(type, handler) { this[type] = handler; },
      focus() { this.focused = true; },
      scrollIntoView() { this.scrolled = true; },
    };
  }
  function descendants(element) {
    return [element, ...element.children.flatMap(descendants)];
  }
  const panel = createElement('div');
  renderSpeakingGuides(panel);
  const elements = descendants(panel);
  const shortcut = elements.find(element => element.tagName === 'button' && element['aria-controls'] === 'guide-asking-questions-negative');
  const destination = elements.find(element => element.id === shortcut['aria-controls']);
  assert.equal(Boolean(destination.open), false);
  shortcut.click();
  assert.equal(destination.open, true);
  assert.equal(destination.scrolled, true);
  assert.equal(destination.children[0].focused, true);
});

test('cancelled playback does not show a practice error after leaving the card', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/app.js'), 'utf8');
  const stop = source.slice(source.indexOf('function stopAudio()'), source.indexOf('function chooseQueue()'));
  const play = source.slice(source.indexOf('async function play(kind)'), source.indexOf('function exportProgress()'));
  let rejectPlayback;
  const messages = [];
  const audio = {
    paused: true,
    pause() {},
    play() { return new Promise((resolve, reject) => { rejectPlayback = reject; }); },
  };
  const context = vm.createContext({
    state: { audio, queue: [{ audio_answer: 'clip.mp3' }], index: 0, revealed: true },
    playbackSequence: 0,
    URL,
    location: { href: 'https://example.test/sentences/' },
    document: { querySelectorAll: () => [] },
    $: () => ({}),
    showMessage: message => messages.push(message),
  });
  vm.runInContext(stop + play, context);
  const pending = context.play('answer');
  context.stopAudio();
  rejectPlayback(new Error('Playback stopped'));
  await pending;
  assert.deepEqual(messages, []);

  const failed = context.play('answer');
  rejectPlayback(new Error('File unavailable'));
  await failed;
  assert.deepEqual(messages, ['音訊無法播放：File unavailable']);
});

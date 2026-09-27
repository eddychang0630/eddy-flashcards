import { createEmptyCard, fsrs, Rating } from 'ts-fsrs';
import { createIcons, RefreshCw, CalendarCheck, BookOpen, MessagesSquare, Volume2, Eye, Repeat2, RotateCcw, Download, Upload } from 'lucide';

const scheduler = fsrs();
const icons = { RefreshCw, CalendarCheck, BookOpen, MessagesSquare, Volume2, Eye, Repeat2, RotateCcw, Download, Upload };
const state = {
  cards: [], reviews: new Map(), view: 'today', selectedDate: '', selectedCategory: '',
  queue: [], index: 0, revealed: false, speed: 1, loop: false, audio: new Audio(), ratingBusy: false,
};
const $ = id => document.getElementById(id);
const setText = (id, value) => { $(id).textContent = value; };

function refreshIcons() {
  createIcons({ icons, attrs: { 'stroke-width': 1.9 } });
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('eddy-sentence-reviews', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('reviews', { keyPath: 'id' });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

let database;
function transaction(mode, action) {
  return new Promise((resolve, reject) => {
    const tx = database.transaction('reviews', mode);
    const store = tx.objectStore('reviews');
    const request = action(store);
    tx.oncomplete = () => resolve(request?.result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error('無法儲存複習進度'));
  });
}

function hydrateReview(record) {
  const card = { ...record.card, due: new Date(record.card.due) };
  if (card.last_review) card.last_review = new Date(card.last_review);
  if (Number.isNaN(card.due.getTime()) || (card.last_review && Number.isNaN(card.last_review.getTime()))) {
    throw new Error(`複習日期格式錯誤：${record.id}`);
  }
  return { id: record.id, card, reviewedAt: record.reviewedAt };
}

function isDue(item) {
  const review = state.reviews.get(item.id);
  return !review || new Date(review.card.due).getTime() <= Date.now();
}

function dueCards() {
  return state.cards.filter(isDue).sort((a, b) => {
    const left = state.reviews.get(a.id);
    const right = state.reviews.get(b.id);
    if (Boolean(left) !== Boolean(right)) return left ? -1 : 1;
    return left && right ? new Date(left.card.due) - new Date(right.card.due) : 0;
  });
}

function filteredCards() {
  if (state.view === 'today') return dueCards().slice(0, 20);
  if (state.view === 'lessons') return state.cards.filter(card => card.type === 'class' && card.date === state.selectedDate);
  return state.cards.filter(card => card.type === 'scenario' && (!state.selectedCategory || card.category === state.selectedCategory));
}

function stopAudio() {
  state.audio.pause();
  state.audio.currentTime = 0;
  document.querySelectorAll('.audio-button').forEach(button => button.classList.remove('playing'));
}

function chooseQueue() {
  stopAudio();
  state.queue = filteredCards();
  state.index = 0;
  state.revealed = false;
  render();
}

function renderFilters() {
  const box = $('filters');
  box.replaceChildren();
  box.hidden = state.view === 'today';
  if (box.hidden) return;
  const options = state.view === 'lessons'
    ? [...new Set(state.cards.filter(card => card.type === 'class').map(card => card.date))].sort().reverse().map(date => [date, date])
    : [['', '全部情境'], ...[...new Set(state.cards.filter(card => card.type === 'scenario').map(card => card.category))].map(category => [category, category])];
  for (const [value, label] of options) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `filter-button${(state.view === 'lessons' ? state.selectedDate : state.selectedCategory) === value ? ' active' : ''}`;
    button.textContent = label;
    button.addEventListener('click', () => {
      if (state.view === 'lessons') state.selectedDate = value;
      else state.selectedCategory = value;
      chooseQueue();
    });
    box.append(button);
  }
}

function showMessage(text, error = false) {
  $('message').hidden = false;
  $('message').classList.toggle('error', error);
  $('message').textContent = text;
}

function render() {
  const counts = { due: dueCards().length, seen: state.reviews.size, class: state.cards.filter(card => card.type === 'class').length };
  setText('due-count', counts.due);
  setText('seen-count', counts.seen);
  setText('class-count', counts.class);
  document.querySelectorAll('.tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.view === state.view);
    tab.setAttribute('aria-current', tab.dataset.view === state.view ? 'page' : 'false');
  });
  setText('view-kicker', { today: 'DAILY PRACTICE', lessons: 'CLASS NOTES', scenarios: 'REAL-LIFE ENGLISH' }[state.view]);
  setText('view-title', { today: '今日複習', lessons: '課堂句子', scenarios: '情境問答' }[state.view]);
  renderFilters();

  const item = state.queue[state.index];
  const total = state.queue.length;
  setText('session-count', total ? `${Math.min(state.index + 1, total)} / ${total}` : '');
  $('practice-card').hidden = !item;
  $('message').hidden = Boolean(item);
  $('restart').hidden = Boolean(item) || (state.view === 'today' && counts.due === 0);
  if (!item) {
    showMessage(state.view === 'today'
      ? counts.due ? `本輪完成。還有 ${counts.due} 句待複習。` : '今天的複習完成了。'
      : total ? '這組句子已練習完畢。' : '目前沒有句子。');
    $('restart').querySelector('span').textContent = state.view === 'today' ? '繼續複習' : '再練一次';
    return;
  }

  setText('card-type', item.type === 'class' ? `${item.date} · ${item.category}` : `情境練習 · ${item.category}`);
  setText('card-position', `${state.index + 1} / ${total}`);
  setText('prompt', item.prompt_zh);
  setText('question-en', item.question_en);
  setText('answer-en', item.answer_en);
  setText('answer-zh', item.answer_zh);
  setText('original', item.original);
  setText('grammar-explanation', item.grammar.explanation);
  setText('grammar-pattern', item.grammar.pattern);
  $('question-section').hidden = !item.question_en;
  $('original-section').hidden = !item.original;
  $('reveal-area').hidden = !state.revealed;
  $('reveal').hidden = state.revealed;
  $('ratings').hidden = !state.revealed;
  document.querySelectorAll('[data-speed]').forEach(button => button.classList.toggle('active', Number(button.dataset.speed) === state.speed));
  $('loop-audio').setAttribute('aria-pressed', String(state.loop));
}

function switchView(view) {
  if (!['today', 'lessons', 'scenarios'].includes(view)) return;
  state.view = view;
  chooseQueue();
}

async function rate(rating) {
  if (state.ratingBusy || !state.revealed || !state.queue[state.index] || ![Rating.Again, Rating.Hard, Rating.Good, Rating.Easy].includes(rating)) return;
  state.ratingBusy = true;
  try {
    const item = state.queue[state.index];
    const previous = state.reviews.get(item.id)?.card || createEmptyCard();
    const next = scheduler.next(previous, new Date(), rating).card;
    const record = { id: item.id, card: next, reviewedAt: new Date().toISOString() };
    await transaction('readwrite', store => store.put(record));
    state.reviews.set(item.id, record);
    stopAudio();
    state.index += 1;
    state.revealed = false;
    render();
  } finally {
    state.ratingBusy = false;
  }
}

async function play(kind) {
  const item = state.queue[state.index];
  const path = kind === 'question' ? item?.audio_question : item?.audio_answer;
  if (!item || !state.revealed || !path) return;
  const button = kind === 'question' ? $('play-question') : $('play-answer');
  const nextUrl = new URL(path, location.href).href;
  if (state.audio.src === nextUrl && !state.audio.paused) { stopAudio(); return; }
  stopAudio();
  state.audio.src = nextUrl;
  state.audio.playbackRate = state.speed;
  state.audio.loop = state.loop;
  try {
    await state.audio.play();
    button.classList.add('playing');
  } catch (error) {
    showMessage(`音訊無法播放：${error.message}`, true);
  }
}

function exportProgress() {
  const payload = { app: 'eddy-sentences', schema_version: 1, exported_at: new Date().toISOString(), reviews: [...state.reviews.values()] };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `eddy-sentence-progress-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function importProgress(file) {
  if (!file) return;
  try {
    const payload = JSON.parse(await file.text());
    if (payload.app !== 'eddy-sentences' || payload.schema_version !== 1 || !Array.isArray(payload.reviews)) throw new Error('不是句子 App 的進度備份');
    const known = new Set(state.cards.map(card => card.id));
    const records = payload.reviews.filter(record => known.has(record?.id)).map(hydrateReview);
    for (const record of records) {
      const current = state.reviews.get(record.id);
      if (!current || new Date(record.reviewedAt) > new Date(current.reviewedAt)) {
        await transaction('readwrite', store => store.put(record));
        state.reviews.set(record.id, record);
      }
    }
    chooseQueue();
    window.alert(`已匯入 ${records.length} 筆句子進度。`);
  } catch (error) {
    window.alert(`匯入失敗：${error.message}`);
  } finally {
    $('import-file').value = '';
  }
}

async function initialize() {
  refreshIcons();
  showMessage('載入句子資料中...');
  try {
    database = await openDatabase();
    const saved = await transaction('readonly', store => store.getAll());
    state.reviews = new Map(saved.map(record => [record.id, hydrateReview(record)]));
    const response = await fetch('data.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const dataset = await response.json();
    if (dataset.schema_version !== 1 || !Array.isArray(dataset.cards) || !dataset.cards.length) throw new Error('句子資料格式錯誤');
    state.cards = dataset.cards;
    state.selectedDate = [...new Set(state.cards.filter(card => card.type === 'class').map(card => card.date))].sort().at(-1) || '';
    setText('updated-at', `資料更新：${new Date(dataset.updated_at).toLocaleString('zh-TW')}`);
    chooseQueue();
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js', { scope: './' }).catch(() => {});
  } catch (error) {
    $('practice-card').hidden = true;
    showMessage(`無法載入句子資料：${error.message}`, true);
  }
}

document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => switchView(button.dataset.view)));
$('reveal').addEventListener('click', () => { state.revealed = true; render(); });
document.querySelectorAll('[data-rating]').forEach(button => button.addEventListener('click', () => rate(Number(button.dataset.rating)).catch(error => window.alert(`無法儲存：${error.message}`))));
$('play-question').addEventListener('click', () => play('question'));
$('play-answer').addEventListener('click', () => play('answer'));
state.audio.addEventListener('ended', () => document.querySelectorAll('.audio-button').forEach(button => button.classList.remove('playing')));
document.querySelectorAll('[data-speed]').forEach(button => button.addEventListener('click', () => {
  state.speed = Number(button.dataset.speed);
  state.audio.playbackRate = state.speed;
  render();
}));
$('loop-audio').addEventListener('click', () => { state.loop = !state.loop; state.audio.loop = state.loop; render(); });
$('restart').addEventListener('click', chooseQueue);
$('refresh').addEventListener('click', async () => { if ('serviceWorker' in navigator) await navigator.serviceWorker.getRegistration('./').then(registration => registration?.update()); location.reload(); });
$('export-progress').addEventListener('click', exportProgress);
$('import-progress').addEventListener('click', () => $('import-file').click());
$('import-file').addEventListener('change', event => importProgress(event.target.files[0]));
initialize();

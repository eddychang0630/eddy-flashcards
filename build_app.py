"""
build_app.py — 從 vocab_data.json 生成完整的 index.html
執行：python build_app.py
"""
import json
from pathlib import Path

APP_DIR   = Path(r"C:\Users\echang11\OneDrive - Lenovo\Desktop\英文\app")
JSON_FILE = APP_DIR / "vocab_data.json"
OUT_HTML  = APP_DIR / "index.html"

with open(JSON_FILE, encoding="utf-8") as f:
    cards = json.load(f)

# Gather unique dates in order
dates = []
for c in cards:
    # Pad to 12 elements to avoid index out of range if missing word forms
    while len(c) < 12:
        c.append("")
        
    d = c[10]
    if d and d not in dates:
        dates.append(d)

date_counts = {}
for c in cards:
    d = c[10]
    date_counts[d] = date_counts.get(d, 0) + 1

def fmt_date_label(d):
    # "2026-09-21" → "09/21"
    parts = d.split("-")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}"
    return d

# Build CARDS JS
cards_js_lines = ["const CARDS = ["]
for c in cards:
    cards_js_lines.append("  " + json.dumps(c, ensure_ascii=False) + ",")
cards_js_lines.append("];")
CARDS_JS = "\n".join(cards_js_lines)

# Build date pills HTML
date_pills_html = f'<button class="dpill active" onclick="setDateFilter(\'\')" id="dpill-all">全部 ({len(cards)})</button>\n'
for d in dates:
    label = fmt_date_label(d)
    cnt   = date_counts[d]
    date_pills_html += f'    <button class="dpill" onclick="setDateFilter(\'{d}\')" id="dpill-{d}">{label} ({cnt})</button>\n'

HTML = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="英文字卡">
  <meta name="theme-color" content="#6366f1">
  <link rel="manifest" href="manifest.json">
  <link rel="apple-touch-icon" href="icon.png">
  <title>英文字卡 App</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --primary: #6366f1; --bg: #0f0f13; --card-bg: #1a1a24;
      --text: #f1f1f5; --muted: #8b8b9e; --border: #2a2a3a;
      --green: #22c55e; --red: #ef4444;
      --radius: 20px;
      --safe-top: env(safe-area-inset-top, 0px);
      --safe-bottom: env(safe-area-inset-bottom, 16px);
    }}
    html, body {{
      height: 100%; width: 100%;
      background: var(--bg); color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans TC', sans-serif;
      overflow: hidden;
      -webkit-tap-highlight-color: transparent;
      -webkit-touch-callout: none;
      user-select: none;
    }}
    #app {{ display: flex; flex-direction: column; height: 100vh; height: 100dvh; }}

    /* Top Bar */
    #top-bar {{
      display: flex; align-items: center; justify-content: space-between;
      padding: calc(var(--safe-top) + 12px) 16px 10px;
      background: var(--bg); border-bottom: 1px solid var(--border); flex-shrink: 0;
    }}
    #top-bar h1 {{ font-size: 0.95rem; font-weight: 700; white-space: nowrap; }}
    .mode-toggle {{ display: flex; gap: 3px; background: var(--card-bg); border-radius: 12px; padding: 3px; }}
    .mode-btn {{
      padding: 5px 12px; border-radius: 9px; font-size: 0.72rem; font-weight: 700;
      border: none; cursor: pointer; background: transparent; color: var(--muted); white-space: nowrap;
    }}
    .mode-btn.active {{ background: var(--primary); color: #fff; }}

    /* Date Filter Bar */
    #date-bar {{
      display: flex; gap: 6px; padding: 8px 14px;
      overflow-x: auto; -webkit-overflow-scrolling: touch; flex-shrink: 0;
      border-bottom: 1px solid var(--border);
      scrollbar-width: none;
    }}
    #date-bar::-webkit-scrollbar {{ display: none; }}
    .dpill {{
      padding: 5px 12px; border-radius: 999px; font-size: 0.68rem; font-weight: 700;
      border: 1.5px solid var(--border); background: var(--card-bg); color: var(--muted);
      white-space: nowrap; cursor: pointer; transition: all 0.18s; flex-shrink: 0;
    }}
    .dpill.active {{ background: var(--primary); border-color: var(--primary); color: #fff; }}
    .dpill:active {{ opacity: 0.8; }}

    /* Progress */
    #progress-wrap {{ padding: 8px 16px 6px; flex-shrink: 0; }}
    .progress-row {{ display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--muted); margin-bottom: 4px; }}
    .progress-bar-bg {{ height: 3px; background: var(--border); border-radius: 999px; }}
    .progress-bar-fill {{ height: 100%; background: var(--primary); border-radius: 999px; transition: width 0.4s ease; }}

    /* Screens */
    .screen {{ display: none; flex: 1; flex-direction: column; overflow: hidden; min-height: 0; }}
    .screen.active {{ display: flex; }}

    /* ══ QUIZ ══ */
    #quiz-scores {{ display: flex; gap: 7px; padding: 0 16px 8px; flex-shrink: 0; }}
    .score-box {{
      flex: 1; background: var(--card-bg); border-radius: 13px;
      padding: 8px 5px; text-align: center; border: 1px solid var(--border);
    }}
    .score-box .s-label {{ font-size: 0.58rem; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }}
    .score-box .s-num {{ font-size: 1.5rem; font-weight: 800; margin-top: 1px; }}
    .score-box.green .s-num {{ color: var(--green); }}
    .score-box.red   .s-num {{ color: var(--red); }}

    #quiz-card-area {{
      flex: 1; display: flex; align-items: center; justify-content: center;
      padding: 0 16px; perspective: 1200px; min-height: 0;
    }}
    .flip-wrapper {{ width: 100%; max-width: 420px; height: 200px; position: relative; }}
    .flip-inner {{
      width: 100%; height: 100%; position: relative;
      transform-style: preserve-3d;
      transition: transform 0.5s cubic-bezier(.4,0,.2,1);
    }}
    .flip-inner.flipped {{ transform: rotateY(180deg); }}
    .flip-face {{
      position: absolute; width: 100%; height: 100%;
      backface-visibility: hidden; -webkit-backface-visibility: hidden;
      border-radius: var(--radius); padding: 18px;
      display: flex; flex-direction: column; justify-content: center;
    }}
    .flip-front {{ background: var(--card-bg); border: 1px solid var(--border); cursor: pointer; }}
    .flip-back {{ background: linear-gradient(135deg,#1e1b4b,#1a1a30); border: 1.5px solid rgba(99,102,241,0.5); transform: rotateY(180deg); }}

    .flip-badge {{
      font-size: 0.58rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase;
      padding: 2px 9px; border-radius: 999px;
      background: rgba(99,102,241,0.15); color: #818cf8;
      margin-bottom: 7px; align-self: flex-start;
    }}
    .flip-word {{
      font-weight: 800; line-height: 1.1; color: var(--text);
      white-space: nowrap; overflow: hidden;
    }}
    .flip-phonetic {{ font-size: 0.74rem; color: #818cf8; margin-top: 3px; font-family: monospace; }}
    .flip-hint {{ font-size: 0.63rem; color: var(--muted); margin-top: 8px; }}
    .flip-date-tag {{ font-size: 0.58rem; color: var(--muted); margin-top: 4px; }}

    .flip-back-content {{ display: flex; flex-direction: column; gap: 5px; }}
    .flip-pos-tag {{ font-size: 0.62rem; font-weight: 700; color: #818cf8; text-transform: uppercase; }}
    .flip-meaning {{ font-size: 0.92rem; font-weight: 600; line-height: 1.35; color: var(--text); }}
    .flip-ex {{ font-size: 0.7rem; color: var(--muted); font-style: italic; line-height: 1.4; margin-top: 3px; }}

    #swipe-hint {{ text-align: center; font-size: 0.64rem; color: var(--muted); padding: 4px 0; flex-shrink: 0; }}

    #quiz-actions {{
      padding: 8px 16px; flex-shrink: 0; display: flex; flex-direction: column; gap: 8px;
      padding-bottom: max(8px, var(--safe-bottom));
    }}
    #btn-flip {{
      width: 100%; padding: 14px; background: var(--primary); color: #fff;
      border: none; border-radius: 16px; font-size: 0.92rem; font-weight: 700; cursor: pointer;
    }}
    #btn-flip:active {{ opacity: 0.85; }}
    .judge-row {{ display: none; gap: 8px; }}
    .judge-row.show {{ display: flex; }}
    .judge-btn {{
      flex: 1; padding: 13px; border: 1.5px solid; border-radius: 16px;
      font-size: 0.85rem; font-weight: 700; cursor: pointer; background: transparent;
    }}
    .judge-btn.know  {{ border-color: var(--green); color: var(--green); }}
    .judge-btn.know:active  {{ background: rgba(34,197,94,0.12); }}
    .judge-btn.dunno {{ border-color: var(--red); color: var(--red); }}
    .judge-btn.dunno:active {{ background: rgba(239,68,68,0.12); }}

    /* ══ STUDY ══ */
    #study-scroll {{ flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; padding: 0 16px; }}
    .study-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; margin-bottom: 20px; }}

    /* Card Header */
    .s-header {{ padding: 16px 18px 12px; border-bottom: 1px solid var(--border); }}
    .s-word {{
      font-weight: 800; line-height: 1.15; color: var(--text);
      white-space: nowrap; overflow: hidden; display: block; width: 100%;
    }}
    .s-phonetic {{
      display: block; font-size: 0.8rem; color: #818cf8;
      font-family: 'Courier New', monospace; margin-top: 4px; margin-bottom: 10px;
    }}
    .s-meta-col {{
      display: flex; flex-direction: column; gap: 8px; margin-top: 6px;
    }}
    .s-pos {{
      font-size: 0.65rem; font-weight: 700; letter-spacing: 0.06em;
      padding: 4px 10px; border-radius: 6px; white-space: nowrap; align-self: flex-start; display: inline-block;
    }}
    .s-meaning-inline {{ font-size: 0.95rem; font-weight: 600; color: var(--text); line-height: 1.4; display: block; }}
    /* Date badge on study card */
    .s-date-badge {{
      font-size: 0.6rem; font-weight: 700; padding: 4px 8px; border-radius: 6px;
      background: rgba(99,102,241,0.12); color: #818cf8; white-space: nowrap; align-self: flex-start; display: inline-block;
    }}

    /* Word Forms */
    .s-forms {{ font-size: 0.82rem; color: var(--text); line-height: 1.5; background: rgba(255,255,255,0.04); padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 8px; }}

    /* Blocks */
    .s-block {{ padding: 11px 18px; border-bottom: 1px solid var(--border); }}
    .s-block:last-child {{ border-bottom: none; }}
    .s-section-label {{ font-size: 0.58rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }}
    .s-en {{ font-size: 0.82rem; font-style: italic; color: var(--text); line-height: 1.5; background: rgba(99,102,241,0.08); border-left: 3px solid var(--primary); padding: 8px 12px; border-radius: 0 10px 10px 0; margin-bottom: 6px; }}
    .s-zh {{ font-size: 0.77rem; color: var(--muted); padding-left: 4px; line-height: 1.5; }}

    /* Synonyms / Antonyms */
    .syn-ant-grid {{ display: flex; gap: 7px; }}
    .syn-box, .ant-box {{ flex: 1; border-radius: 11px; padding: 8px 10px; }}
    .syn-box {{ background: rgba(34,197,94,0.07); border: 1px solid rgba(34,197,94,0.25); }}
    .ant-box {{ background: rgba(239,68,68,0.07); border: 1px solid rgba(239,68,68,0.25); }}
    .syn-ant-title {{ font-size: 0.58rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 4px; }}
    .syn-box .syn-ant-title {{ color: var(--green); }}
    .ant-box .syn-ant-title {{ color: var(--red); }}
    .syn-ant-en {{ font-size: 0.73rem; color: var(--text); font-weight: 600; line-height: 1.4; }}
    .syn-ant-zh {{ font-size: 0.68rem; color: var(--muted); margin-top: 2px; line-height: 1.4; }}
    .no-data {{ font-size: 0.7rem; color: var(--muted); font-style: italic; }}

    /* Study Nav */
    #study-nav {{
      display: flex; gap: 8px; padding: 8px 16px; flex-shrink: 0;
      padding-bottom: max(8px, var(--safe-bottom)); border-top: 1px solid var(--border);
    }}
    .nav-btn {{
      padding: 13px 14px; border-radius: 14px; font-weight: 700; border: 1.5px solid var(--border);
      background: var(--card-bg); color: var(--text); font-size: 0.85rem; cursor: pointer; white-space: nowrap;
    }}
    .nav-btn.primary {{ flex: 1; background: var(--primary); border-color: var(--primary); color: #fff; }}
    .nav-btn:disabled {{ opacity: 0.3; cursor: not-allowed; }}
    .nav-btn:not(:disabled):active {{ opacity: 0.8; transform: scale(0.97); }}

    /* Tab Bar */
    #tab-bar {{
      display: flex; background: var(--card-bg); border-top: 1px solid var(--border);
      padding-bottom: var(--safe-bottom); flex-shrink: 0;
    }}
    .tab-btn {{
      flex: 1; display: flex; flex-direction: column; align-items: center;
      padding: 8px 0 5px; gap: 2px; background: none; border: none; cursor: pointer;
      color: var(--muted); font-size: 0.58rem; font-weight: 700; transition: color 0.2s;
    }}
    .tab-icon {{ font-size: 1.3rem; }}
    .tab-btn.active {{ color: var(--primary); }}

    /* Finish */
    #finish-overlay {{
      display: none; position: fixed; inset: 0; background: rgba(15,15,19,0.97);
      flex-direction: column; align-items: center; justify-content: center;
      z-index: 100; padding: 32px; text-align: center;
    }}
    #finish-overlay.show {{ display: flex; }}
    .fin-emoji {{ font-size: 4rem; margin-bottom: 12px; }}
    .fin-title {{ font-size: 1.5rem; font-weight: 800; margin-bottom: 6px; }}
    .fin-msg {{ color: var(--muted); font-size: 0.86rem; margin-bottom: 24px; line-height: 1.7; white-space: pre-line; }}
    .fin-btns {{ display: flex; flex-direction: column; gap: 9px; width: 100%; max-width: 300px; }}
    .fin-btn {{ padding: 14px; border-radius: 14px; font-weight: 700; font-size: 0.92rem; cursor: pointer; border: none; }}
    .fin-btn.primary {{ background: var(--primary); color: #fff; }}
    .fin-btn.secondary {{ background: var(--card-bg); color: var(--text); border: 1.5px solid var(--border); }}

    /* Animations */
    @keyframes cardIn {{ from {{ opacity: 0; transform: translateX(18px); }} to {{ opacity: 1; transform: translateX(0); }} }}
    @keyframes popAnim {{ 0%,100%{{transform:scale(1)}} 50%{{transform:scale(1.04)}} }}
    @keyframes shakeAnim {{ 0%,100%{{transform:translateX(0)}} 25%{{transform:translateX(-8px)}} 75%{{transform:translateX(8px)}} }}
    .anim-in    {{ animation: cardIn   0.25s ease; }}
    .anim-pop   {{ animation: popAnim  0.25s ease; }}
    .anim-shake {{ animation: shakeAnim 0.3s ease; }}
  </style>
</head>
<body>
<div id="app">
  <div id="top-bar">
    <h1>📚 Eddy 英文字卡</h1>
    <div class="mode-toggle">
      <button class="mode-btn active" id="mode-quiz-btn" onclick="switchMode('quiz')">🃏 抽考</button>
      <button class="mode-btn" id="mode-study-btn" onclick="switchMode('study')">📖 背誦</button>
    </div>
  </div>

  <!-- Date Filter Bar -->
  <div id="date-bar">
    {date_pills_html.strip()}
  </div>

  <!-- Progress -->
  <div id="progress-wrap">
    <div class="progress-row">
      <span id="prog-label">第 1 張，共 {len(cards)} 張</span>
      <span id="prog-pct">1%</span>
    </div>
    <div class="progress-bar-bg"><div class="progress-bar-fill" id="prog-fill" style="width:1%"></div></div>
  </div>

  <!-- QUIZ SCREEN -->
  <div class="screen active" id="screen-quiz">
    <div id="quiz-scores">
      <div class="score-box green"><div class="s-label">✅ 認識</div><div class="s-num" id="q-know">0</div></div>
      <div class="score-box red">  <div class="s-label">❌ 不熟</div><div class="s-num" id="q-dunno">0</div></div>
      <div class="score-box">      <div class="s-label">🔀 剩餘</div><div class="s-num" id="q-remain">{len(cards)}</div></div>
    </div>
    <div id="quiz-card-area">
      <div class="flip-wrapper" id="flip-wrapper">
        <div class="flip-inner" id="flip-inner">
          <div class="flip-face flip-front" onclick="doFlip()">
            <div class="flip-badge" id="q-badge">字彙</div>
            <div class="flip-word" id="q-word"></div>
            <div class="flip-phonetic" id="q-phonetic"></div>
            <div class="flip-hint">輕觸翻面 👆 翻後左滑不熟 / 右滑認識</div>
            <div class="flip-date-tag" id="q-date-tag"></div>
          </div>
          <div class="flip-face flip-back">
            <div class="flip-back-content">
              <div class="flip-pos-tag" id="q-pos-tag"></div>
              <div class="flip-meaning" id="q-meaning"></div>
              <div class="flip-ex" id="q-ex"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div id="swipe-hint">← 左滑「不熟」&nbsp;｜&nbsp;「認識」右滑 →</div>
    <div id="quiz-actions">
      <button id="btn-flip" onclick="doFlip()">翻面看答案</button>
      <div class="judge-row" id="judge-row">
        <button class="judge-btn dunno" onclick="judge(false)">← 還不熟</button>
        <button class="judge-btn know" onclick="judge(true)">認識！→</button>
      </div>
    </div>
  </div>

  <!-- STUDY SCREEN -->
  <div class="screen" id="screen-study">
    <div id="study-scroll">
      <div class="study-card" id="study-card">
        <div class="s-header">
          <span class="s-word" id="s-word"></span>
          <span class="s-phonetic" id="s-phonetic"></span>
          <div class="s-meta-col">
            <span class="s-pos" id="s-pos"></span>
            <span class="s-meaning-inline" id="s-meaning"></span>
            <span class="s-date-badge" id="s-date-badge">📅 —</span>
          </div>
        </div>
        <div class="s-block" id="s-forms-block" style="display:none;">
          <div class="s-section-label">🔄 字形變化 (Word Forms)</div>
          <div class="s-forms" id="s-forms"></div>
        </div>
        <div class="s-block">
          <div class="s-section-label">💬 例句</div>
          <div class="s-en" id="s-en"></div>
          <div class="s-zh" id="s-zh"></div>
        </div>
        <div class="s-block">
          <div class="s-section-label">🔗 近義詞 / 反義詞</div>
          <div class="syn-ant-grid">
            <div class="syn-box">
              <div class="syn-ant-title">近義詞 Synonyms</div>
              <div class="syn-ant-en" id="s-syn-en"></div>
              <div class="syn-ant-zh" id="s-syn-zh"></div>
            </div>
            <div class="ant-box">
              <div class="syn-ant-title">反義詞 Antonyms</div>
              <div class="syn-ant-en" id="s-ant-en"></div>
              <div class="syn-ant-zh" id="s-ant-zh"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div id="study-nav">
      <button class="nav-btn" id="s-prev" onclick="studyNav(-1)">← 上一張</button>
      <button class="nav-btn primary" id="s-next" onclick="studyNav(1)">下一張 →</button>
    </div>
  </div>

  <div id="tab-bar">
    <button class="tab-btn active" id="tab-quiz" onclick="switchMode('quiz')">
      <span class="tab-icon">🃏</span>隨機抽考
    </button>
    <button class="tab-btn" id="tab-study" onclick="switchMode('study')">
      <span class="tab-icon">📖</span>完整背誦
    </button>
    <button class="tab-btn" onclick="onShuffle()">
      <span class="tab-icon">🔀</span>重新洗牌
    </button>
  </div>
</div>

<div id="finish-overlay">
  <div class="fin-emoji" id="fin-emoji">🎉</div>
  <div class="fin-title">完成！</div>
  <div class="fin-msg" id="fin-msg"></div>
  <div class="fin-btns">
    <button class="fin-btn secondary" id="fin-retry" onclick="retryWrong()">再練不熟的</button>
    <button class="fin-btn primary" onclick="restartAll()">重新開始</button>
  </div>
</div>

<script>
// ─── CARDS Data ───────────────────────────────────────────────────────────────
// Format: [word, phonetic, pos, meaning, enEx, zhEx, synEn, synZh, antEn, antZh, classDate]
//           0       1       2     3       4     5     6      7      8      9        10
{CARDS_JS}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const shuffle = a => {{ const b=[...a]; for(let i=b.length-1;i>0;i--){{ const j=Math.floor(Math.random()*(i+1));[b[i],b[j]]=[b[j],b[i]]; }} return b; }};

function fitWordFont(el, word) {{
  const n = word.length;
  el.style.fontSize = n<=6?'2.1rem':n<=9?'1.85rem':n<=12?'1.55rem':n<=16?'1.25rem':n<=22?'1.05rem':n<=30?'0.88rem':'0.75rem';
}}

function posStyle(pos) {{
  const p = (pos||'').toLowerCase();
  if(p.startsWith('n.'))    return {{bg:'rgba(59,130,246,0.15)',color:'#60a5fa'}};
  if(p.startsWith('v.'))    return {{bg:'rgba(34,197,94,0.15)', color:'#4ade80'}};
  if(p.startsWith('adj.'))  return {{bg:'rgba(234,179,8,0.15)', color:'#fbbf24'}};
  if(p.includes('phrasal')||p.includes('片語動詞')) return {{bg:'rgba(168,85,247,0.15)',color:'#c084fc'}};
  if(p.includes('noun phrase')||p.includes('名詞片語')) return {{bg:'rgba(59,130,246,0.12)',color:'#93c5fd'}};
  if(p.includes('verb phrase')||p.includes('動詞片語')) return {{bg:'rgba(34,197,94,0.12)',color:'#86efac'}};
  if(p.includes('口語')||p.includes('expression')) return {{bg:'rgba(236,72,153,0.15)',color:'#f472b6'}};
  if(p.includes('諺語')||p.includes('proverb'))    return {{bg:'rgba(20,184,166,0.15)',color:'#2dd4bf'}};
  if(p.includes('adverb')||p.includes('副詞'))     return {{bg:'rgba(251,146,60,0.15)',color:'#fb923c'}};
  return {{bg:'rgba(148,163,184,0.15)',color:'#94a3b8'}};
}}

function fmtDate(d) {{
  if(!d) return '';
  const p = d.split('-');
  return p.length===3 ? `${{p[1]}}/${{p[2]}}` : d;
}}

// ─── State ────────────────────────────────────────────────────────────────────
let activeDate = '';   // '' = all dates
let filteredCards = [...CARDS];

let qDeck=[], qIdx=0, qKnow=0, qDunno=0, qFlipped=false, wrongCards=[];
let sIdx=0;
let mode='quiz';

// ─── Date Filter ──────────────────────────────────────────────────────────────
function setDateFilter(date) {{
  activeDate = date;
  filteredCards = date ? CARDS.filter(c => c[10]===date) : [...CARDS];

  // Update pill styles
  document.querySelectorAll('.dpill').forEach(el => el.classList.remove('active'));
  const target = date ? document.getElementById(`dpill-${{date}}`) : document.getElementById('dpill-all');
  if(target) target.classList.add('active');
  // Scroll the pill into view
  if(target) target.scrollIntoView({{behavior:'smooth', block:'nearest', inline:'center'}});

  // Restart current mode with filtered deck
  if(mode==='quiz') initQuiz(filteredCards);
  else {{ sIdx=0; showSCard(); }}
}}

// ─── Progress ─────────────────────────────────────────────────────────────────
function setProgress(idx, total) {{
  const pct = total ? Math.round(((idx+1)/total)*100) : 0;
  document.getElementById('prog-label').textContent = `第 ${{idx+1}} 張，共 ${{total}} 張`;
  document.getElementById('prog-pct').textContent = `${{pct}}%`;
  document.getElementById('prog-fill').style.width = `${{Math.max(pct,1)}}%`;
}}

// ─── Quiz ─────────────────────────────────────────────────────────────────────
function initQuiz(cards) {{
  qDeck=shuffle(cards); qIdx=0; qKnow=0; qDunno=0; wrongCards=[];
  document.getElementById('finish-overlay').classList.remove('show');
  updateScores(); showQCard();
}}
function showQCard() {{
  if(qIdx>=qDeck.length){{showFinish();return;}}
  const c=qDeck[qIdx];
  const wordEl=document.getElementById('q-word');
  wordEl.textContent=c[0]; fitWordFont(wordEl,c[0]);

  const phonEl=document.getElementById('q-phonetic');
  phonEl.textContent=c[1]||''; phonEl.style.display=c[1]?'block':'none';

  document.getElementById('q-badge').textContent=c[2]||'字彙';
  document.getElementById('q-pos-tag').textContent=c[2]||'';
  document.getElementById('q-meaning').textContent=c[3]||'';
  document.getElementById('q-ex').textContent=c[4]?`"${{c[4]}}"` :'';
  document.getElementById('q-date-tag').textContent=c[10]?`📅 ${{c[10]}}` :'';

  qFlipped=false;
  document.getElementById('flip-inner').classList.remove('flipped');
  document.getElementById('btn-flip').style.display='';
  document.getElementById('judge-row').classList.remove('show');
  setProgress(qIdx,qDeck.length);

  const w=document.getElementById('flip-wrapper');
  w.classList.remove('anim-in','anim-pop','anim-shake'); void w.offsetWidth; w.classList.add('anim-in');
}}
function doFlip() {{
  if(qFlipped)return;
  qFlipped=true;
  document.getElementById('flip-inner').classList.add('flipped');
  setTimeout(()=>{{
    document.getElementById('btn-flip').style.display='none';
    document.getElementById('judge-row').classList.add('show');
  }},280);
}}
function judge(knew) {{
  const w=document.getElementById('flip-wrapper');
  if(knew){{ qKnow++; w.classList.remove('anim-pop'); void w.offsetWidth; w.classList.add('anim-pop'); }}
  else    {{ qDunno++; wrongCards.push(qDeck[qIdx]); w.classList.remove('anim-shake'); void w.offsetWidth; w.classList.add('anim-shake'); }}
  updateScores(); qIdx++;
  setTimeout(showQCard,320);
}}
function updateScores() {{
  document.getElementById('q-know').textContent=qKnow;
  document.getElementById('q-dunno').textContent=qDunno;
  document.getElementById('q-remain').textContent=Math.max(0,qDeck.length-qIdx);
}}
function showFinish() {{
  const total=qKnow+qDunno, pct=total?Math.round(qKnow/total*100):0;
  const emoji=pct>=90?'🏆':pct>=70?'🎯':pct>=50?'💪':'📚';
  document.getElementById('fin-emoji').textContent=emoji;
  document.getElementById('fin-msg').textContent=`認識 ${{qKnow}} / ${{total}} 個（${{pct}}%）\\n${{wrongCards.length?`還有 ${{wrongCards.length}} 個需要加強！`:'全部掌握 🎉'}}`;
  document.getElementById('fin-retry').style.display=wrongCards.length?'':'none';
  document.getElementById('finish-overlay').classList.add('show');
}}
function retryWrong(){{ document.getElementById('finish-overlay').classList.remove('show'); initQuiz(wrongCards.length?wrongCards:filteredCards); }}
function restartAll() {{ document.getElementById('finish-overlay').classList.remove('show'); initQuiz(filteredCards); }}

// ─── Study ────────────────────────────────────────────────────────────────────
function showSCard() {{
  const c=filteredCards[sIdx];
  const wordEl=document.getElementById('s-word');
  wordEl.textContent=c[0]; fitWordFont(wordEl,c[0]);

  const phonEl=document.getElementById('s-phonetic');
  phonEl.textContent=c[1]||''; phonEl.style.display=c[1]?'block':'none';

  const posEl=document.getElementById('s-pos');
  posEl.textContent=c[2]||'';
  const st=posStyle(c[2]);
  posEl.style.background=st.bg; posEl.style.color=st.color;

  document.getElementById('s-meaning').textContent=c[3]||'';
  document.getElementById('s-en').textContent=c[4]?`"${{c[4]}}"` :'';
  document.getElementById('s-zh').textContent=c[5]?`→ ${{c[5]}}` :'';

  // Date badge
  document.getElementById('s-date-badge').textContent=c[10]?`📅 ${{c[10]}}` :'';

  // Word Forms
  const formsBlock = document.getElementById('s-forms-block');
  if(c[11] && c[11] !== '—') {{
    formsBlock.style.display = 'block';
    document.getElementById('s-forms').textContent = c[11];
  }} else {{
    formsBlock.style.display = 'none';
  }}

  // Synonyms
  const setField=(id,val)=>{{
    const el=document.getElementById(id);
    if(val&&val!=='—'){{ el.textContent=val; }}
    else{{ el.innerHTML='<span class="no-data">—</span>'; }}
  }};
  setField('s-syn-en',c[6]); document.getElementById('s-syn-zh').textContent=c[7]&&c[7]!=='—'?c[7]:'';
  setField('s-ant-en',c[8]); document.getElementById('s-ant-zh').textContent=c[9]&&c[9]!=='—'?c[9]:'';

  document.getElementById('s-prev').disabled=sIdx===0;
  document.getElementById('s-next').textContent=sIdx===filteredCards.length-1?'回到第一張 ↩':'下一張 →';
  setProgress(sIdx,filteredCards.length);
  document.getElementById('study-scroll').scrollTop=0;

  const card=document.getElementById('study-card');
  card.classList.remove('anim-in'); void card.offsetWidth; card.classList.add('anim-in');
}}
function studyNav(d) {{
  const n=sIdx+d;
  sIdx=n<0?0:n>=filteredCards.length?0:n;
  showSCard();
}}

// ─── Mode / Shuffle ───────────────────────────────────────────────────────────
function switchMode(m) {{
  mode=m;
  ['quiz','study'].forEach(x=>{{
    document.getElementById(`screen-${{x}}`).classList.toggle('active',x===m);
    document.getElementById(`mode-${{x}}-btn`).classList.toggle('active',x===m);
    document.getElementById(`tab-${{x}}`).classList.toggle('active',x===m);
  }});
  if(m==='study'){{ sIdx=0; showSCard(); }}
  else setProgress(qIdx,qDeck.length);
}}
function onShuffle() {{
  if(mode==='quiz') initQuiz(filteredCards);
  else{{ sIdx=0; showSCard(); }}
}}

// ─── Swipe ────────────────────────────────────────────────────────────────────
let tx=0;
document.getElementById('quiz-card-area').addEventListener('touchstart',e=>{{tx=e.touches[0].clientX;}},{{passive:true}});
document.getElementById('quiz-card-area').addEventListener('touchend',e=>{{
  if(!qFlipped)return;
  if(Math.abs(e.changedTouches[0].clientX-tx)>55) judge(e.changedTouches[0].clientX-tx>0);
}},{{passive:true}});
document.getElementById('study-scroll').addEventListener('touchstart',e=>{{tx=e.touches[0].clientX;}},{{passive:true}});
document.getElementById('study-scroll').addEventListener('touchend',e=>{{
  if(Math.abs(e.changedTouches[0].clientX-tx)>65) studyNav(e.changedTouches[0].clientX-tx>0?-1:1);
}},{{passive:true}});

// ─── Keyboard ────────────────────────────────────────────────────────────────
document.addEventListener('keydown',e=>{{
  if(mode==='quiz'){{
    if(e.key===' ')doFlip();
    if(e.key==='ArrowRight'&&qFlipped)judge(true);
    if(e.key==='ArrowLeft'&&qFlipped)judge(false);
  }}
  if(mode==='study'){{
    if(e.key==='ArrowRight')studyNav(1);
    if(e.key==='ArrowLeft')studyNav(-1);
  }}
}});

// ─── Service Worker ───────────────────────────────────────────────────────────
if('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');

// ─── Init ─────────────────────────────────────────────────────────────────────
initQuiz(filteredCards);
showSCard();
</script>
</body>
</html>"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"✅ Generated index.html with {len(cards)} cards and {len(dates)} date filters")
print(f"   Output: {OUT_HTML}")

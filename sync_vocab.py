"""
英文字卡同步腳本 sync_vocab.py
====================================
用途：從 Excel 讀取最新單字資料，自動更新 App 並推送到 GitHub

使用方式：
  python sync_vocab.py

每次在 Excel 更新完單字後，執行這個腳本就會自動：
1. 讀取 Excel 所有單字（去重複）
2. 更新 App 的 index.html
3. 自動 git commit + push 到 GitHub Pages
"""

import argparse
import os
import sys

import openpyxl
import json
import re
import subprocess
from pathlib import Path
from collections import defaultdict

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

# ── 路徑設定 ──────────────────────────────────────────────────────────────────
DEFAULT_EXCEL_PATH = Path(
    os.environ.get(
        "ENGLISH_CLASS_EXCEL",
        r"G:\我的雲端硬碟\2026 English class 整理重點\Master_Vocabulary_Tracker.xlsx",
    )
)
APP_DIR = Path(__file__).resolve().parent
INDEX_HTML = APP_DIR / "index.html"

# ── 讀取 Excel ────────────────────────────────────────────────────────────────
def read_vocab(excel_path=DEFAULT_EXCEL_PATH):
    print("📖 讀取 Excel 單字庫...")
    wb = openpyxl.load_workbook(Path(excel_path))
    ws = wb.active

    cards = []
    seen = set()       # 去重用（小寫比對）
    date_counts = defaultdict(int)

    for row in ws.iter_rows(min_row=2, values_only=True):
        cols = (list(row) + [None] * 16)[:16]
        date, no, word, meaning, pos, syn_en, syn_zh, ant_en, ant_zh, ex_en, ex_zh, _, _, _, _, forms = cols

        # 驗證日期格式
        if not date or not word:
            continue
        date_str = str(date).strip()
        if not date_str.startswith("20"):
            continue

        word_str = str(word).strip()
        if not word_str:
            continue

        # 去重複（大小寫不敏感）
        word_key = word_str.lower()
        if word_key in seen:
            print(f"  ⚠️  跳過重複單字：{word_str}")
            continue
        seen.add(word_key)

        def clean(v):
            return str(v).strip() if v and str(v).strip() not in ("None", "") else ""

        card = [
            word_str,           # 0  英文單字
            "",                 # 1  音標（Excel 無此欄，留空）
            clean(pos),         # 2  詞性
            clean(meaning),     # 3  中文意思
            clean(ex_en),       # 4  英文例句
            clean(ex_zh),       # 5  中文翻譯
            clean(syn_en),      # 6  近義詞（英）
            clean(syn_zh),      # 7  近義詞（中）
            clean(ant_en),      # 8  反義詞（英）
            clean(ant_zh),      # 9  反義詞（中）
            date_str[:10],      # 10 課程日期 YYYY-MM-DD
            clean(forms),       # 11 字形變化 (Excel P 欄)
        ]
        cards.append(card)
        date_counts[date_str[:10]] += 1

    print(f"✅ 讀取完成：{len(cards)} 個唯一單字")
    print("\n📅 按課程日期分布：")
    for d in sorted(date_counts):
        print(f"   {d}：{date_counts[d]} 個單字")

    wb.close()
    return cards, dict(date_counts)

# ── 生成 JavaScript CARDS 陣列字串 ────────────────────────────────────────────
def generate_cards_js(cards):
    lines = ["const CARDS = ["]
    for c in cards:
        lines.append("  " + json.dumps(c, ensure_ascii=False) + ",")
    lines.append("];")
    return "\n".join(lines)

# ── 更新 index.html ───────────────────────────────────────────────────────────
def update_html(cards, index_html=INDEX_HTML):
    print("\n✏️  更新 index.html...")
    with open(index_html, "r", encoding="utf-8") as f:
        html = f.read()

    cards_js = generate_cards_js(cards)

    # 替換 const CARDS = [...] 區塊
    pattern = r"const CARDS = \[.*?\];"
    if re.search(pattern, html, flags=re.DOTALL):
        html = re.sub(pattern, cards_js, html, flags=re.DOTALL)
        print(f"✅ 成功替換 CARDS 陣列（{len(cards)} 筆）")
    else:
        print("❌ 找不到 CARDS 陣列，請確認 index.html 格式")
        return False

    with open(index_html, "w", encoding="utf-8") as f:
        f.write(html)
    return True

# ── Git Push ──────────────────────────────────────────────────────────────────
def git_push(cards, date_counts):
    print("\n🚀 推送到 GitHub Pages...")
    total  = len(cards)
    dates  = len(date_counts)
    msg    = f"Sync vocab: {total} words across {dates} class dates"

    subprocess.run(["git", "add", "index.html"], cwd=APP_DIR, check=True)
    result = subprocess.run(["git", "diff", "--cached", "--stat"], cwd=APP_DIR, capture_output=True, text=True)
    if "nothing to commit" in result.stdout or not result.stdout.strip():
        print("ℹ️  index.html 沒有變更，無需 push")
        return
    subprocess.run(["git", "commit", "-m", msg], cwd=APP_DIR, check=True)
    subprocess.run(["git", "push"], cwd=APP_DIR, check=True)
    print(f"✅ 已推送！網站約 1 分鐘後更新：")
    print(f"   https://eddychang0630.github.io/eddy-flashcards/")

# ── 主程式 ────────────────────────────────────────────────────────────────────
def build_parser():
    parser = argparse.ArgumentParser(description="同步 Excel 單字到英文字卡 App")
    parser.add_argument(
        "--excel",
        type=Path,
        default=DEFAULT_EXCEL_PATH,
        help="Master_Vocabulary_Tracker.xlsx 路徑",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    print("=" * 50)
    print("  英文字卡同步工具 v1.0")
    print("=" * 50)

    try:
        cards, date_counts = read_vocab(args.excel)
        if not cards:
            print("❌ 沒有讀到任何單字，請確認 Excel 路徑正確")
            return 1

        if update_html(cards):
            git_push(cards, date_counts)
            print("\n🎉 同步完成！")
            return 0
        else:
            print("\n❌ 同步失敗，請確認 index.html 格式")
            return 1

    except FileNotFoundError as e:
        print(f"\n❌ 找不到檔案：{e}")
        print("   請確認 Excel 路徑是否正確，且 Google Drive 已同步")
        return 1
    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())

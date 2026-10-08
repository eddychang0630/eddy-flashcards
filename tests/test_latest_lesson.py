from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import sync_vocab


ROOT = Path(__file__).resolve().parents[1]


def card(word, date):
    return [word, "", "Noun", "meaning", "Example.", "translation", "", "", "", "", date, "", "", ""]


class DatePills(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.pills = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "dpill" in attrs.get("class", "").split():
            self.pills.append(attrs)


class LatestLessonTest(unittest.TestCase):
    def initial_state(self, html, cards):
        match = re.search(r"// \u2500+ State .*?\n(.*?)\nfunction stopCardAudio", html, re.S)
        self.assertIsNotNone(match)
        helpers = re.search(r"function cardSource\(card\).*?(?=// \u2500+ State)", html, re.S)
        script = (
            "const CARDS=" + json.dumps(cards) + ";\n" + (helpers[0] if helpers else "") + match[1]
            + "\nJSON.stringify({activeDate, words:filteredCards.map(c=>c[0]), mode});"
        )
        runner = "console.log(require('node:vm').runInNewContext(process.argv[1]));"
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", runner, script],
            check=True, capture_output=True, text=True,
        )
        return json.loads(result.stdout)

    def assert_date_pills(self, html, dates):
        pills = DatePills(html).pills
        self.assertEqual(["dpill-all"] + ["dpill-" + date for date in dates], [p["id"] for p in pills])
        self.assertEqual(["dpill-" + dates[0]], [p["id"] for p in pills if "active" in p["class"].split()])

    def build(self, directory, cards):
        shutil.copyfile(ROOT / "build_app.py", directory / "build_app.py")
        (directory / "vocab_data.json").write_text(json.dumps(cards), encoding="utf-8")
        subprocess.run([sys.executable, str(directory / "build_app.py")], check=True, capture_output=True)
        return (directory / "index.html").read_text(encoding="utf-8")

    def test_initial_study_deck_uses_latest_date_not_card_order(self):
        cards = [card("old", "2026-06-25"), card("new", "2027-01-05"), card("middle", "2026-10-05"), card("newer", "2027-01-05")]
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(
            {"activeDate": "2027-01-05", "words": ["new", "newer"], "mode": "study"},
            self.initial_state(html, cards),
        )

    def test_rebuild_selects_latest_date_and_orders_pills_descending(self):
        cards = [card("old", "2026-06-25"), card("new", "2027-01-05"), card("middle", "2026-10-05")]
        with tempfile.TemporaryDirectory() as temp:
            html = self.build(Path(temp), cards)
        self.assert_date_pills(html, ["2027-01-05", "2026-10-05", "2026-06-25"])

    def test_daily_sync_new_lesson_automatically_becomes_default(self):
        cards = [card("old", "2026-06-25"), card("middle", "2026-10-05")]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.build(directory, cards)
            cards.insert(1, card("new", "2027-01-05"))
            self.assertTrue(sync_vocab.update_html(cards, directory / "index.html"))
            html = (directory / "index.html").read_text(encoding="utf-8")
        self.assert_date_pills(html, ["2027-01-05", "2026-10-05", "2026-06-25"])
        self.assertEqual(
            {"activeDate": "2027-01-05", "words": ["new"], "mode": "study"},
            self.initial_state(html, cards),
        )


if __name__ == "__main__":
    unittest.main()

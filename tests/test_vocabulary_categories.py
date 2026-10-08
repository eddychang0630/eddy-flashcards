import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


def card(word, date, source=None):
    value = [word, "", "Noun", "meaning", "Example.", "translation", "", "", "", "", date, "", "", ""]
    return value + [source] if source else value


class VocabularyCategoriesTest(unittest.TestCase):
    def run_state(self, cards, expression):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        match = re.search(r"function cardSource\(card\).*?\nfunction stopCardAudio", html, re.S)
        self.assertIsNotNone(match, "Vocabulary categories have not been implemented")
        script = "const CARDS=" + json.dumps(cards) + ";\n" + match[0].rsplit("\nfunction stopCardAudio", 1)[0]
        script += "\nJSON.stringify(" + expression + ");"
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", "console.log(require('node:vm').runInNewContext(process.argv[1]));", script],
            check=True, capture_output=True, text=True,
        )
        return json.loads(result.stdout)

    def test_newer_life_date_does_not_replace_latest_class_homepage(self):
        cards = [card("old", "2026-07-06"), card("lesson", "2026-10-05", "class"), card("life", "2026-10-08", "life")]
        self.assertEqual(
            {"source": "class", "date": "2026-10-05", "words": ["lesson"], "mode": "study"},
            self.run_state(cards, "{source:activeSource,date:activeDate,words:filteredCards.map(c=>c[0]),mode}"),
        )

    def test_category_and_date_filter_keep_repeated_phrase_in_each_category(self):
        cards = [card("from the get-go", "2026-07-06"), card("from the get-go", "2026-10-08", "life"), card("another", "2026-10-09", "life")]
        self.assertEqual(
            {"class": ["2026-07-06"], "life": ["2026-10-08", "2026-10-09"], "day": ["from the get-go"], "latest": "2026-10-09", "empty": []},
            self.run_state(cards, "{class:filterVocabulary(CARDS,'class','').map(c=>c[10]),life:filterVocabulary(CARDS,'life','').map(c=>c[10]),day:filterVocabulary(CARDS,'life','2026-10-08').map(c=>c[0]),latest:latestVocabularyDate(CARDS,'life'),empty:filterVocabulary(CARDS,'life','2026-10-10')}"),
        )


if __name__ == "__main__":
    unittest.main()

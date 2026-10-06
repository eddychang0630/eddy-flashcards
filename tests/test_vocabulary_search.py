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


def card(word, date="2026-09-10"):
    return [word, "", "Noun", "中文", "Example.", "例句。", "", "", "", "", date, "", "", ""]


class VocabularySearchTest(unittest.TestCase):
    def search(self, html, cards, queries):
        match = re.search(
            r"function searchVocabulary\(cards, query\) \{(.*?)\n\}\n\nfunction renderVocabularySearch",
            html,
            re.S,
        )
        self.assertIsNotNone(match, "Vocabulary search has not been implemented")
        function = "function searchVocabulary(cards, query) {" + match[1] + "\n}"
        runner = (
            "const vm=require('node:vm'); const ctx={};"
            "vm.runInNewContext(process.argv[1],ctx);"
            "const cards=JSON.parse(process.argv[2]);"
            "console.log(JSON.stringify(JSON.parse(process.argv[3]).map(q=>ctx.searchVocabulary(cards,q))));"
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", runner, function, json.dumps(cards), json.dumps(queries)],
            check=True, capture_output=True, text=True,
        )
        return json.loads(result.stdout)

    def test_global_search_normalization_ranking_and_empty_results(self):
        cards = [card("action"), card("act"), card("procrastination"), card("ahead of time"), card("react")]
        queries = [" PROCRASTINATION ", "procr", "ＡＣＴ", "ahead  of", "act", "", "   ", "[.*", "notfound"]
        actual = self.search((ROOT / "index.html").read_text(encoding="utf-8"), cards, queries)
        self.assertEqual([[2], [2], [1, 0, 4], [3], [1, 0, 4], [], [], [], []], actual)

    def test_rebuilding_and_daily_sync_preserve_working_search(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            shutil.copyfile(ROOT / "build_app.py", directory / "build_app.py")
            (directory / "vocab_data.json").write_text(json.dumps([card("act")]), encoding="utf-8")
            subprocess.run([sys.executable, str(directory / "build_app.py")], check=True, capture_output=True)
            cards = [card("procrastination"), card("beforehand", "2026-10-05")]
            self.assertTrue(sync_vocab.update_html(cards, directory / "index.html"))
            actual = self.search((directory / "index.html").read_text(encoding="utf-8"), cards, ["PROCR", "before"])
            self.assertEqual([[0], [1]], actual)


if __name__ == "__main__":
    unittest.main()

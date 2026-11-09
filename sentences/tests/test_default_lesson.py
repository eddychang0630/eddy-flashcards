import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DefaultLessonTest(unittest.TestCase):
    def test_homepage_opens_latest_actual_class_date(self):
        source = (ROOT / "src" / "app.js").read_text(encoding="utf-8")
        state = re.search(r"const state = \{.*?\n\};", source, re.S)[0]
        selection = re.search(r"state.selectedDate = \[\.\.\.new Set.*?;", source)[0]
        cards = [{"type": "class", "date": "2026-09-01"}, {"type": "class", "date": "2027-01-12"}, {"type": "class", "date": "2026-11-05"}, {"type": "scenario", "date": "2028-01-01"}]
        script = state + "\nstate.cards=" + json.dumps(cards) + ";" + selection + ";JSON.stringify({view:state.view,date:state.selectedDate});"
        result = subprocess.run(["node", "-e", "console.log(require('node:vm').runInNewContext(process.argv[1],{Audio:function(){}}));", script], check=True, capture_output=True, text=True)
        self.assertEqual({"view": "lessons", "date": "2027-01-12"}, json.loads(result.stdout))

    def test_static_shell_agrees_with_latest_lesson_startup(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertTrue('class="tab active" data-view="lessons"' in html, "Class lessons must be the initial selected tab")
        self.assertTrue('id="view-title">課堂句子' in html, "Initial heading must match class lessons")
        self.assertFalse('class="tab active" data-view="today"' in html)


if __name__ == "__main__":
    unittest.main()

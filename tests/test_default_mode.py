from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DefaultModeTest(unittest.TestCase):
    def test_app_opens_in_study_mode(self):
        for name in ("build_app.py", "index.html"):
            with self.subTest(name=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                for expected in (
                    'class="mode-btn active" id="mode-study-btn"',
                    'class="screen active" id="screen-study"',
                    'class="tab-btn active" id="tab-study"',
                    "let mode='study';",
                    'class="mode-btn" id="mode-quiz-btn"',
                    'class="screen" id="screen-quiz"',
                    'class="tab-btn" id="tab-quiz"',
                ):
                    self.assertTrue(expected in source, f"{name}: missing {expected}")


if __name__ == "__main__":
    unittest.main()

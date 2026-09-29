import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NavigationShellTest(unittest.TestCase):
    def test_navigation_styles_are_preloaded_for_offline_use(self):
        worker = (ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertIn("'./navigation.css'", worker)
        self.assertIn("eddy-sentences-v2", worker)
        self.assertIn("fetch(new Request(request, { cache: 'no-store' }))", worker)


if __name__ == "__main__":
    unittest.main()

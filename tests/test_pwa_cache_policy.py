from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PwaCachePolicyTest(unittest.TestCase):
    def test_new_deployments_replace_cached_html_immediately(self):
        worker = (ROOT / "sw.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        builder = (ROOT / "build_app.py").read_text(encoding="utf-8")

        self.assertIn("eddy-flashcard-v2", worker)
        self.assertIn("self.skipWaiting()", worker)
        self.assertIn("self.clients.claim()", worker)
        self.assertIn("request.mode === 'navigate'", worker)
        self.assertIn("updateViaCache: 'none'", index)
        self.assertIn("registration.update()", index)
        self.assertIn("updateViaCache: 'none'", builder)
        self.assertIn("registration.update()", builder)


if __name__ == "__main__":
    unittest.main()

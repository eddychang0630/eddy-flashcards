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

    def test_manual_refresh_button_updates_worker_before_reloading(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        builder = (ROOT / "build_app.py").read_text(encoding="utf-8")

        for source in (index, builder):
            self.assertIn('id="app-refresh-btn"', source)
            self.assertIn('aria-label="重新整理 App"', source)
            self.assertIn("async function refreshApp()", source)
            self.assertIn("await registration.update()", source)
            self.assertIn("window.location.reload()", source)
            self.assertIn("is-refreshing", source)


if __name__ == "__main__":
    unittest.main()

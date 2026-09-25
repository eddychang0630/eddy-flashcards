import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AudioUiTest(unittest.TestCase):
    def test_study_and_quiz_have_word_and_example_playback(self):
        for name in ("build_app.py", "index.html"):
            source = (ROOT / name).read_text(encoding="utf-8")
            for expected in (
                'id="s-word-audio"',
                'id="s-example-audio"',
                'id="q-word-audio"',
                'id="q-example-audio"',
                "function playCardAudio(",
                "c[12]",
                "c[13]",
            ):
                self.assertTrue(expected in source, f"{name}: missing {expected}")

    def test_service_worker_caches_audio_after_first_play(self):
        source = (ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertIn("/audio/", source)
        self.assertIn("cache.put(cacheKey", source)


if __name__ == "__main__":
    unittest.main()

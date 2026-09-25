import tempfile
import unittest
from pathlib import Path

from audio_assets import attach_audio_paths, audio_relative_path, ensure_complete, generate_missing


def card(word, example):
    return [word, "", "Noun", "中文", example, "翻譯", "", "", "", "", "2026-09-25", ""]


class AudioAssetsTest(unittest.TestCase):
    def test_paths_are_stable_and_voice_specific(self):
        first = audio_relative_path("Ample time")
        self.assertEqual(first, audio_relative_path("Ample time"))
        self.assertNotEqual(first, audio_relative_path("ample time"))
        self.assertNotEqual(first, audio_relative_path("Ample time", voice="am_echo"))
        self.assertTrue(first.startswith("audio/"))
        self.assertTrue(first.endswith(".mp3"))
        self.assertEqual("", audio_relative_path(""))

    def test_attaches_word_and_example_audio_without_extra_columns_on_retry(self):
        cards = [card("ample time", "We have ample time to prepare.")]
        enriched = attach_audio_paths(cards)

        self.assertEqual(14, len(enriched[0]))
        self.assertEqual(audio_relative_path("ample time"), enriched[0][12])
        self.assertEqual(audio_relative_path("We have ample time to prepare."), enriched[0][13])
        self.assertEqual(enriched, attach_audio_paths(enriched))
        self.assertEqual(12, len(cards[0]))

    def test_generates_each_unique_clip_once_and_resumes(self):
        cards = attach_audio_paths([card("same", "same"), card("other", "same")])
        with tempfile.TemporaryDirectory() as temp:
            audio_dir = Path(temp) / "audio"
            calls = []

            def fake_render(text, path):
                calls.append(text)
                path.write_bytes(b"mp3")

            self.assertEqual(2, generate_missing(cards, audio_dir, fake_render))
            self.assertEqual(["same", "other"], calls)
            self.assertEqual(0, generate_missing(cards, audio_dir, fake_render))
            ensure_complete(cards, audio_dir)

            (audio_dir / audio_relative_path("same").split("/", 1)[1]).write_bytes(b"")
            with self.assertRaisesRegex(RuntimeError, "missing or empty"):
                ensure_complete(cards, audio_dir)


if __name__ == "__main__":
    unittest.main()

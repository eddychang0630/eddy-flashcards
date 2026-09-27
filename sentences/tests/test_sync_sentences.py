import json
import tempfile
import unittest
from pathlib import Path

from sentences.sync_sentences import build_dataset, load_lesson, parse_better_table


NOTE = """# 2026-09-27 English Class Notes
## Better Expressions / 換個說法更好聽
> Source: lesson.Eddy_only.txt
<table class="better"><thead><tr><th>#</th><th>Original Sentence</th><th>Improved Sentence / 中文</th><th>修正重點</th></tr></thead>
<tbody><tr><td>1</td><td>I go yesterday.<br><span class="time">01:23</span></td>
<td>I went yesterday.<br><span class="zh">我昨天去了。</span></td><td>過去時間用過去式。</td></tr></tbody></table>
## Speaking Feedback / 課堂英文表達評語
"""


class SentenceSyncTest(unittest.TestCase):
    def test_july_waiting_card_uses_complete_chinese_translation(self):
        data_path = Path(__file__).resolve().parents[1] / "data.json"
        cards = json.loads(data_path.read_text(encoding="utf-8"))["cards"]
        card = next(card for card in cards if card["id"] == "class-20260706-01")
        self.assertEqual("請等我一下。", card["prompt_zh"])
        self.assertEqual("請等我一下。", card["answer_zh"])

    def test_parse_separates_spoken_text_translation_time_and_correction(self):
        rows = parse_better_table(NOTE)
        self.assertEqual(1, len(rows))
        self.assertEqual("I go yesterday.", rows[0]["original"])
        self.assertEqual("I went yesterday.", rows[0]["improved"])
        self.assertEqual("我昨天去了。", rows[0]["translation"])
        self.assertEqual("01:23", rows[0]["timecode"])
        self.assertEqual("過去時間用過去式。", rows[0]["correction"])

    def test_lesson_rejects_unverified_or_incomplete_tables(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "20260927"
            root.mkdir()
            note = root / "english_class_notes.md"
            note.write_text(NOTE, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly 10"):
                load_lesson(note)
            note.write_text(NOTE.replace("Eddy_only.txt", "unknown.txt"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Eddy"):
                load_lesson(note)

    def test_dataset_requires_grammar_and_keeps_stable_ids(self):
        row = {
            "number": 1, "original": "I go yesterday.", "improved": "I went yesterday.",
            "translation": "我昨天去了。", "timecode": "01:23", "correction": "過去時間用過去式。",
        }
        with self.assertRaisesRegex(ValueError, "grammar"):
            build_dataset({"20260927": [row]}, {}, [])

        guides = {"20260927": [{"pattern": "I went to ... yesterday."}]}
        dataset = build_dataset({"20260927": [row]}, guides, [])
        card = dataset["cards"][0]
        self.assertEqual("class-20260927-01", card["id"])
        self.assertEqual("2026-09-27", card["date"])
        self.assertEqual("過去時間用過去式。", card["grammar"]["explanation"])
        self.assertEqual("I went to ... yesterday.", card["grammar"]["pattern"])
        self.assertTrue(card["audio_answer"].startswith("audio/"))
        self.assertFalse(card["audio_question"])

    def test_scenario_question_and_answer_have_audio_without_teacher_attribution(self):
        scenario = [{
            "id": "clarify-01", "category": "課堂溝通", "prompt_zh": "請老師再說一次",
            "question_en": "Could you say that again?", "answer_en": "Of course.",
            "answer_zh": "當然可以。", "grammar": {"explanation": "Could you... 是禮貌請求。", "pattern": "Could you + 原形動詞...?"},
        }]
        dataset = build_dataset({}, {}, scenario)
        card = dataset["cards"][0]
        self.assertEqual("scenario", card["type"])
        self.assertTrue(card["audio_question"].startswith("audio/"))
        self.assertTrue(card["audio_answer"].startswith("audio/"))
        self.assertEqual("", card["original"])


if __name__ == "__main__":
    unittest.main()

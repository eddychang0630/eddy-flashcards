import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

import sync_vocab


ROOT = Path(__file__).resolve().parents[1]


class SyncVocabularyTest(unittest.TestCase):
    def test_audio_failure_blocks_html_update_and_deployment(self):
        cards = [["word", "", "Noun", "中文", "Example sentence.", "翻譯", "", "", "", "", "2026-09-25", ""]]
        with patch.object(sync_vocab, "read_vocab", return_value=(cards, {"2026-09-25": 1})), \
             patch.object(sync_vocab, "prepare_audio", side_effect=RuntimeError("audio failed")), \
             patch.object(sync_vocab, "update_html") as update, \
             patch.object(sync_vocab, "git_push") as push:
            with self.assertRaisesRegex(RuntimeError, "audio failed"):
                sync_vocab.main(["--excel", "unused.xlsx"])
        update.assert_not_called()
        push.assert_not_called()

    def test_uses_portable_app_path_and_accepts_excel_argument(self):
        self.assertEqual(ROOT, Path(sync_vocab.APP_DIR))
        args = sync_vocab.build_parser().parse_args(["--excel", "custom.xlsx"])
        self.assertEqual(Path("custom.xlsx"), args.excel)

        builder = (ROOT / "build_app.py").read_text(encoding="utf-8")
        sync_source = (ROOT / "sync_vocab.py").read_text(encoding="utf-8")
        self.assertNotIn("echang11", builder)
        self.assertNotIn("echang11", sync_source)
        self.assertIn("Path(__file__).resolve().parent", builder)

    def test_reads_word_forms_from_column_p(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "vocabulary.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append([f"Column {column}" for column in range(1, 17)])
            row = [None] * 16
            row[0] = "2026-09-23"
            row[2] = "literate"
            row[3] = "識字的"
            row[4] = "Adjective"
            row[15] = "Noun: literacy; Adverb: literately"
            sheet.append(row)
            workbook.save(workbook_path)

            cards, date_counts = sync_vocab.read_vocab(workbook_path)

        self.assertEqual("Noun: literacy; Adverb: literately", cards[0][11])
        self.assertEqual({"2026-09-23": 1}, date_counts)

    def test_read_vocab_skips_embedded_header_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "vocabulary.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append([f"Column {column}" for column in range(1, 17)])
            sheet.append(
                [
                    "2026-06-22",
                    "序號 (No.)",
                    "英文單字 (English Word)",
                    "中文解釋 (Meaning)",
                    "單字詞性\n(POS)",
                ]
            )
            row = [None] * 16
            row[0] = "2026-09-23"
            row[2] = "literate"
            row[3] = "識字的"
            row[4] = "Adjective"
            sheet.append(row)
            workbook.save(workbook_path)

            cards, date_counts = sync_vocab.read_vocab(workbook_path)

        self.assertEqual(["literate"], [card[0] for card in cards])
        self.assertEqual({"2026-09-23": 1}, date_counts)

    def test_update_html_preserves_escaped_newlines_in_card_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "index.html"
            index_path.write_text(
                '<div id="date-bar"></div>\n'
                "<script>\nconst CARDS = [];\n</script>\n",
                encoding="utf-8",
            )
            card = [
                "header-like entry",
                "",
                "Noun\nphrase",
                "meaning",
                "example",
                "translation",
                "synonym",
                "Syn\nMeaning",
                "antonym",
                "Ant\nMeaning",
                "2026-09-23",
                "",
            ]

            updated = sync_vocab.update_html([card], index_path)
            html = index_path.read_text(encoding="utf-8")

        self.assertTrue(updated)
        self.assertIn('"Noun\\nphrase"', html)
        self.assertIn('"Syn\\nMeaning"', html)
        self.assertNotIn('"Noun\nphrase"', html)

    def test_update_html_rebuilds_date_filters_and_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "index.html"
            index_path.write_text(
                """      <div id="date-bar">
    <button id="dpill-all">全部 (999)</button>
  </div>
<script>
const CARDS = [];
</script>
""",
                encoding="utf-8",
            )
            cards = [
                ["one", "", "n.", "一", "", "", "", "", "", "", "2026-09-23", ""],
                ["two", "", "n.", "二", "", "", "", "", "", "", "2026-09-23", ""],
                ["three", "", "n.", "三", "", "", "", "", "", "", "2026-09-24", ""],
            ]

            updated = sync_vocab.update_html(cards, index_path)
            html = index_path.read_text(encoding="utf-8")

        self.assertTrue(updated)
        self.assertIn("全部 (3)", html)
        self.assertIn("09/23 (2)", html)
        self.assertIn("09/24 (1)", html)
        self.assertIn('id="dpill-2026-09-24"', html)
        self.assertNotIn("全部 (999)", html)
        self.assertIn('\n  <div id="date-bar">\n', "\n" + html)


if __name__ == "__main__":
    unittest.main()

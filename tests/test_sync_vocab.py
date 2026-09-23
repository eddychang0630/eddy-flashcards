import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

import sync_vocab


ROOT = Path(__file__).resolve().parents[1]


class SyncVocabularyTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

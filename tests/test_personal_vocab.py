import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from audio_assets import attach_audio_paths
import sync_vocab


ROOT = Path(__file__).resolve().parents[1]


def entry(word="from the get-go"):
    return {
        "word": word, "pos": "Idiom", "meaning": "從一開始；打從最初",
        "synonyms": "from the beginning; from the outset", "synonym_meaning": "從一開始；打從最初",
        "antonyms": "—", "antonym_meaning": "—",
        "example": "From the get-go, I knew this would be a challenge.",
        "translation": "我從一開始就知道這會是個挑戰。", "word_forms": "",
    }


class PersonalVocabularyTest(unittest.TestCase):
    def module(self):
        path = ROOT / "personal_vocab.py"
        self.assertTrue(path.is_file(), "Personal vocabulary workflow is not implemented")
        spec = importlib.util.spec_from_file_location("personal_vocab", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_source_is_not_required_and_audio_preserves_category(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "personal.json"
            self.assertEqual(1, module.add_entries(path, [entry()], "2026-10-08", Path(temp) / "backups"))
            cards = module.load_personal_cards(path)
        self.assertEqual("2026-10-08", cards[0][10])
        self.assertEqual("", cards[0][11])
        self.assertEqual("life", cards[0][14])
        self.assertEqual("life", attach_audio_paths(cards)[0][14])
        self.assertEqual(attach_audio_paths(cards), attach_audio_paths(attach_audio_paths(cards)))

    def test_retry_does_not_duplicate_but_new_date_preserves_occurrence(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "personal.json"
            backup = Path(temp) / "backups"
            self.assertEqual(1, module.add_entries(path, [entry()], "2026-10-08", backup))
            duplicate = entry(" FROM   THE GET-GO ")
            self.assertEqual(0, module.add_entries(path, [duplicate], "2026-10-08", backup))
            self.assertEqual(1, module.add_entries(path, [entry()], "2026-10-09", backup))
            self.assertEqual(2, len(module.load_personal_cards(path)))
            self.assertEqual(1, len(list(backup.glob("*.json"))))

    def test_invalid_fields_dates_and_phrase_forms_are_rejected_before_write(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "personal.json"
            for changes, date in [({"translation": ""}, "2026-10-08"),
                                  ({"word_forms": "Verb: get"}, "2026-10-08"),
                                  ({"antonym_meaning": "相反"}, "2026-10-08"),
                                  ({}, "2026-02-30")]:
                with self.subTest(changes=changes, date=date):
                    with self.assertRaises(ValueError):
                        module.add_entries(path, [entry() | changes], date, Path(temp) / "backups")
                    self.assertFalse(path.exists())

    def test_daily_sync_keeps_personal_card_even_if_it_is_in_excel(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "personal.json"
            module.add_entries(path, [entry()], "2026-10-08", Path(temp) / "backups")
            old = module.load_personal_cards(path)[0][:12]
            old[10] = "2026-07-06"
            with patch.object(sync_vocab, "read_vocab", return_value=([old], {old[10]: 1})), \
                 patch.object(sync_vocab, "PERSONAL_FILE", path), \
                 patch.object(sync_vocab, "prepare_audio", side_effect=attach_audio_paths), \
                 patch.object(sync_vocab, "update_html", return_value=True) as update, \
                 patch.object(sync_vocab, "update_json"), patch.object(sync_vocab, "git_push") as push:
                self.assertEqual(0, sync_vocab.main(["--excel", "unused.xlsx", "--local-only"]))
            cards = update.call_args.args[0]
            self.assertEqual(["class", "life"], [card[14] for card in cards])
            self.assertEqual(["2026-07-06", "2026-10-08"], [card[10] for card in cards])
            push.assert_not_called()

    def test_class_date_bar_does_not_include_life_dates_or_counts(self):
        card = ["lesson", "", "Noun", "meaning", "Example.", "translation", "", "", "", "", "2026-10-05", "", "", "", "class"]
        life = card[:]
        life[10], life[14] = "2026-10-08", "life"
        html = sync_vocab.generate_date_bar_html([card, life])
        self.assertIn("全部 (1)", html)
        self.assertNotIn("10/08", html)
        self.assertIn('class="dpill active"', html)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AppVersionTest(unittest.TestCase):
    def module(self):
        path = ROOT / "app_version.py"
        self.assertTrue(path.is_file(), "Automatic release versions are not implemented")
        spec = importlib.util.spec_from_file_location("app_version", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_release_changes_only_when_its_app_files_change(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in module.APP_FILES["vocabulary"]:
                (root / name).write_text(name, encoding="utf-8")
            first = module.write_app_version(root, "vocabulary")
            stamp = (root / "app-version.json").stat().st_mtime_ns
            self.assertEqual(first, module.write_app_version(root, "vocabulary"))
            self.assertEqual(stamp, (root / "app-version.json").stat().st_mtime_ns)
            (root / "sentences").mkdir()
            (root / "sentences" / "data.json").write_text("changed", encoding="utf-8")
            self.assertEqual(first, module.write_app_version(root, "vocabulary"))
            (root / "vocab_data.json").write_text("new vocabulary", encoding="utf-8")
            self.assertNotEqual(first["revision"], module.write_app_version(root, "vocabulary")["revision"])

    def test_sentence_release_tracks_bundle_and_data_without_touching_reviews(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in module.APP_FILES["sentences"]:
                (root / name).write_text(name, encoding="utf-8")
            first = module.write_app_version(root, "sentences")
            (root / "app.js").write_text("new interface", encoding="utf-8")
            second = module.write_app_version(root, "sentences")
            self.assertNotEqual(first["revision"], second["revision"])
            self.assertEqual(second, json.loads((root / "app-version.json").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()

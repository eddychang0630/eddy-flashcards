import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICONS = {
    "icon-192-v2.png": (192, 192),
    "icon-512-v2.png": (512, 512),
    "apple-touch-icon-v2.png": (180, 180),
}


class AppIconTest(unittest.TestCase):
    def test_icon_assets_have_expected_dimensions(self):
        self.assertTrue((ROOT / "app-icon.svg").is_file())
        self.assertTrue((ROOT / "render_app_icon.py").is_file())
        for name, expected in ICONS.items():
            with self.subTest(name=name):
                raw = (ROOT / name).read_bytes()
                self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", raw[16:24]), expected)
        self.assertEqual((ROOT / "favicon-v2.ico").read_bytes()[:4], b"\x00\x00\x01\x00")

    def test_manifest_and_pages_reference_new_icons(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {(icon["src"], icon["sizes"]) for icon in manifest["icons"]},
            {("icon-192-v2.png", "192x192"), ("icon-512-v2.png", "512x512")},
        )
        for name in ("build_app.py", "index.html"):
            with self.subTest(name=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn('href="apple-touch-icon-v2.png"', source)
                self.assertIn('href="icon-192-v2.png"', source)
                self.assertIn('href="favicon-v2.ico"', source)

    def test_worker_preloads_current_icon_assets(self):
        worker = (ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertIn("eddy-flashcard-v4", worker)
        for name in (*ICONS, "favicon-v2.ico"):
            self.assertIn(name, worker)


if __name__ == "__main__":
    unittest.main()

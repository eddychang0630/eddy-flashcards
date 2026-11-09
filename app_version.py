"""Create per-App release fingerprints immediately before publication."""

import argparse
import hashlib
import json
from pathlib import Path

APP_FILES = {
    "vocabulary": ("index.html", "vocab_data.json", "app-updates.js", "sw.js", "manifest.json"),
    "sentences": ("index.html", "app.js", "data.json", "style.css", "navigation.css", "sw.js", "manifest.json"),
}


def write_app_version(directory, kind):
    directory = Path(directory)
    digest = hashlib.sha256()
    for name in APP_FILES[kind]:
        content = (directory / name).read_bytes().replace(b"\r\n", b"\n")
        digest.update(name.encode("utf-8") + b"\0" + hashlib.sha256(content).digest())
    release = {"schema_version": 1, "revision": digest.hexdigest()[:20]}
    path = directory / "app-version.json"
    if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != release:
        path.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    return release


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("kind", choices=APP_FILES)
    args = parser.parse_args()
    print(json.dumps(write_app_version(args.directory, args.kind)))

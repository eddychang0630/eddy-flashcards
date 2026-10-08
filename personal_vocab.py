"""Validate and append agent-reviewed everyday vocabulary without a source field."""

import argparse
from datetime import date as calendar_date, datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import unicodedata


APP_DIR = Path(__file__).resolve().parent
PERSONAL_FILE = APP_DIR / "personal_vocabulary.json"
FIELDS = ("word", "pos", "meaning", "example", "translation", "synonyms",
          "synonym_meaning", "antonyms", "antonym_meaning", "word_forms")
PHRASE_MARKERS = ("phrase", "phrasal verb", "idiom", "expression", "sentence",
                  "question", "collocation", "proverb")


def word_key(word):
    return " ".join(unicodedata.normalize("NFKC", word).casefold().split())


def validate_entry(entry, date=None):
    if not isinstance(entry, dict):
        raise ValueError("Each vocabulary entry must be an object")
    result = {}
    for field in FIELDS:
        value = entry.get(field, "")
        if not isinstance(value, str):
            raise ValueError(f"{field} must be text")
        result[field] = value.strip()
        if field != "word_forms" and not result[field]:
            raise ValueError(f"Missing {field}")
    result["word"] = " ".join(result["word"].split())
    label = date or entry.get("date", "")
    try:
        if calendar_date.fromisoformat(label).isoformat() != label:
            raise ValueError("Date must be YYYY-MM-DD")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid vocabulary date: {label}") from exc
    if date and entry.get("date", date) != date:
        raise ValueError("Entry date does not match the requested date")
    result["date"] = label
    for english, chinese in (("synonyms", "synonym_meaning"), ("antonyms", "antonym_meaning")):
        if (result[english] == "—") != (result[chinese] == "—"):
            raise ValueError(f"Use the same no-data marker in {english} and {chinese}")
    phrase = " " in result["word"] or any(marker in result["pos"].lower() for marker in PHRASE_MARKERS)
    if phrase and result["word_forms"]:
        raise ValueError("Phrases and expressions must not have word_forms")
    if not phrase and not result["word_forms"]:
        raise ValueError("Single words require reviewed word_forms or a no-family marker")
    return result


def read_entries(path):
    path = Path(path)
    if not path.exists():
        return []
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Personal vocabulary must be an array")
    return [validate_entry(entry) for entry in entries]


def load_personal_cards(path=PERSONAL_FILE):
    return [
        [entry["word"], "", entry["pos"], entry["meaning"], entry["example"],
         entry["translation"], entry["synonyms"], entry["synonym_meaning"],
         entry["antonyms"], entry["antonym_meaning"], entry["date"],
         entry["word_forms"], "", "", "life"]
        for entry in read_entries(path)
    ]


def add_entries(path, entries, date, backup_dir):
    path = Path(path)
    if not isinstance(entries, list) or not entries:
        raise ValueError("Supply a nonempty array of reviewed vocabulary entries")
    additions = [validate_entry(entry, date) for entry in entries]
    existing = read_entries(path)
    seen = {(entry["date"], word_key(entry["word"])) for entry in existing}
    added = []
    for entry in additions:
        key = (entry["date"], word_key(entry["word"]))
        if key not in seen:
            seen.add(key)
            added.append(entry)
    if not added:
        return 0
    if path.exists():
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        shutil.copy2(path, backup_dir / f"personal_vocabulary_{stamp}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".personal-", suffix=".json", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(existing + added, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return len(added)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--date", required=True, help="User's local date, YYYY-MM-DD")
    parser.add_argument("--database", type=Path, default=PERSONAL_FILE)
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    entries = json.loads(args.input.read_text(encoding="utf-8"))
    count = add_entries(args.database, entries, args.date, args.backup_dir)
    print(json.dumps({"added": count, "date": args.date, "database": str(args.database)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

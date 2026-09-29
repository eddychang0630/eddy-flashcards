"""Publish source-checked class sentences and curated scenario practice."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
SITE_ROOT = APP_DIR.parent
sys.path.insert(0, str(SITE_ROOT))
from audio_assets import attach_audio_paths, audio_relative_path, ensure_complete, missing_clips  # noqa: E402
from sentences.translation_audit import approve_reviews, build_request, require_reviewed  # noqa: E402


class BetterTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.in_table = False
        self.in_row = False
        self.row = []
        self.cell = None
        self.span_roles = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and not self.rows and not self.in_table:
            self.in_table = True
        elif not self.in_table:
            return
        elif tag == "tr":
            self.in_row = True
            self.row = []
        elif tag in ("td", "th") and self.in_row:
            self.cell = {"main": [], "zh": [], "time": []}
        elif tag == "span" and self.cell is not None:
            classes = attrs.get("class", "").split()
            role = "zh" if "zh" in classes else "time" if "time" in classes else None
            self.span_roles.append(role)
        elif tag == "br" and self.cell is not None:
            self.cell[self._role()].append(" ")

    def _role(self):
        return next((role for role in reversed(self.span_roles) if role), "main")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell[self._role()].append(data)

    def handle_endtag(self, tag):
        if not self.in_table:
            return
        if tag == "span" and self.span_roles:
            self.span_roles.pop()
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append({key: " ".join("".join(value).split()) for key, value in self.cell.items()})
            self.cell = None
        elif tag == "tr" and self.in_row:
            self.rows.append(self.row)
            self.in_row = False
        elif tag == "table":
            self.in_table = False


def better_section(markdown):
    start = markdown.find("Better Expressions")
    if start < 0:
        raise ValueError("Missing Better Expressions section")
    end = markdown.find("## Speaking Feedback", start)
    return markdown[start:end if end >= 0 else None]


def parse_better_table(markdown):
    section = better_section(markdown)
    parser = BetterTableParser()
    parser.feed(section)
    records = []
    for cells in parser.rows:
        if len(cells) < 4 or not cells[0]["main"].isdigit():
            continue
        improved = cells[2]["main"]
        translation = cells[2]["zh"] or cells[3]["zh"] or cells[3]["main"]
        correction = cells[3]["main"] if cells[2]["zh"] else ""
        records.append({
            "number": int(cells[0]["main"]),
            "original": cells[1]["main"],
            "improved": improved,
            "translation": translation,
            "timecode": cells[1]["time"],
            "correction": correction,
        })
    return records


def load_lesson(note_path):
    note_path = Path(note_path)
    markdown = note_path.read_text(encoding="utf-8")
    section = better_section(markdown)
    rows = parse_better_table(markdown)
    intro = section.split("<table", 1)[0]
    identified = any(marker in intro for marker in ("Eddy_only", "辨識為 Eddy", "Eddy-labeled"))
    if not identified and not ("BETTER_START" in intro and rows and all(row["timecode"] for row in rows)):
        raise ValueError(f"Eddy speech provenance missing: {note_path}")
    if len(rows) != 10 or [row["number"] for row in rows] != list(range(1, 11)):
        raise ValueError(f"Expected exactly 10 ordered Eddy sentences: {note_path}")
    for row in rows:
        if not all(row[field] for field in ("original", "improved", "translation")):
            raise ValueError(f"Incomplete sentence in {note_path}: {row['number']}")
    return rows


def load_lessons(notes_root):
    lessons = {}
    for folder in sorted(Path(notes_root).iterdir()):
        if not folder.is_dir() or not re.fullmatch(r"20\d{6}", folder.name):
            continue
        note = folder / "english_class_notes.md"
        if note.is_file():
            lessons[folder.name] = load_lesson(note)
    if not lessons:
        raise ValueError(f"No verified lesson notes found under {notes_root}")
    return lessons


def build_dataset(lessons, guides, scenarios, topics=None, overrides=None):
    topics = topics or {}
    overrides = overrides or {}
    cards = []
    for date, rows in sorted(lessons.items()):
        if len(guides.get(date, [])) != len(rows):
            raise ValueError(f"Missing grammar guides for {date}")
        for row, guide in zip(rows, guides[date]):
            card_id = f"class-{date}-{row['number']:02d}"
            correction = overrides.get(card_id, {})
            if not isinstance(correction, dict) or set(correction) - {"answer_en", "answer_zh"}:
                raise ValueError(f"Invalid override: {card_id}")
            if any(not value or not isinstance(value, str) for value in correction.values()):
                raise ValueError(f"Empty override: {card_id}")
            improved = correction.get("answer_en", row["improved"])
            translation = correction.get("answer_zh", row["translation"])
            explanation = guide.get("explanation") or row.get("correction", "")
            pattern = guide.get("pattern", "")
            if not explanation or not pattern:
                raise ValueError(f"Missing grammar explanation/pattern: {date} #{row['number']}")
            cards.append({
                "id": card_id,
                "type": "class",
                "date": f"{date[:4]}-{date[4:6]}-{date[6:]}",
                "category": topics.get(date, "課堂表達"),
                "prompt_zh": translation,
                "question_en": "",
                "answer_en": improved,
                "answer_zh": translation,
                "original": row["original"],
                "timecode": row.get("timecode", ""),
                "source": f"{date}/english_class_notes.md",
                "grammar": {
                    "title": guide.get("title", "句型重點"),
                    "explanation": explanation,
                    "pattern": pattern,
                },
                "audio_question": "",
                "audio_answer": audio_relative_path(improved),
            })

    unknown = set(overrides) - {card["id"] for card in cards}
    if unknown:
        raise ValueError(f"Unknown override: {sorted(unknown)[0]}")

    seen_ids = {card["id"] for card in cards}
    for scenario in scenarios:
        ident = f"scenario-{scenario['id']}"
        if ident in seen_ids:
            raise ValueError(f"Duplicate sentence ID: {ident}")
        seen_ids.add(ident)
        needed = ("category", "prompt_zh", "question_en", "answer_en", "answer_zh")
        if not all(scenario.get(key) for key in needed):
            raise ValueError(f"Incomplete scenario: {ident}")
        grammar = scenario.get("grammar", {})
        if not grammar.get("explanation") or not grammar.get("pattern"):
            raise ValueError(f"Missing grammar guide: {ident}")
        cards.append({
            "id": ident,
            "type": "scenario",
            "date": "",
            "category": scenario["category"],
            "prompt_zh": scenario["prompt_zh"],
            "question_en": scenario["question_en"],
            "answer_en": scenario["answer_en"],
            "answer_zh": scenario["answer_zh"],
            "original": "",
            "timecode": "",
            "source": "curated scenario practice",
            "grammar": grammar,
            "audio_question": audio_relative_path(scenario["question_en"]),
            "audio_answer": audio_relative_path(scenario["answer_en"]),
        })
    return {"schema_version": 1, "cards": cards}


def audio_jobs(cards):
    jobs = []
    for card in cards:
        row = [""] * 12
        row[0] = card["question_en"] or card["answer_en"]
        row[4] = card["answer_en"] if card["question_en"] else ""
        jobs.append(row)
    return attach_audio_paths(jobs)


def generate_audio(cards):
    jobs = audio_jobs(cards)
    audio_dir = APP_DIR / "audio"
    if missing_clips(jobs, audio_dir):
        kokoro_python = Path(os.environ.get(
            "KOKORO_PYTHON",
            Path.home() / "Desktop/English class 整理重點/.models/kokoro/venv/Scripts/python.exe",
        ))
        if not kokoro_python.is_file():
            raise FileNotFoundError(f"Kokoro Python not found: {kokoro_python}")
        with tempfile.TemporaryDirectory() as temp_dir:
            cards_file = Path(temp_dir) / "audio_jobs.json"
            cards_file.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
            subprocess.run([
                str(kokoro_python), str(SITE_ROOT / "audio_assets.py"),
                "--cards-file", str(cards_file), "--audio-dir", str(audio_dir),
            ], check=True, cwd=SITE_ROOT)
    ensure_complete(jobs, audio_dir)


def write_dataset(dataset):
    target = APP_DIR / "data.json"
    payload = json.dumps(dataset["cards"], ensure_ascii=False, sort_keys=True)
    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    previous = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
    dataset["revision"] = fingerprint
    dataset["updated_at"] = (
        previous.get("updated_at") if previous.get("revision") == fingerprint
        else datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    target.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sync sentence practice PWA")
    parser.add_argument("--notes-root", type=Path, default=Path.home() / "Desktop/English class 整理重點")
    parser.add_argument("--local-only", action="store_true")
    audit = parser.add_mutually_exclusive_group()
    audit.add_argument("--audit-request", type=Path, help="Export changed bilingual cards for semantic review")
    audit.add_argument("--audit-approve", type=Path, help="Apply explicit approvals for current card fingerprints")
    args = parser.parse_args(argv)
    lessons = load_lessons(args.notes_root)
    guides = json.loads((APP_DIR / "grammar_guides.json").read_text(encoding="utf-8"))
    scenarios = json.loads((APP_DIR / "scenarios.json").read_text(encoding="utf-8"))
    topics = json.loads((APP_DIR / "lesson_topics.json").read_text(encoding="utf-8"))
    overrides_path = APP_DIR / "translation_overrides.json"
    overrides = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.is_file() else {}
    dataset = build_dataset(lessons, guides, scenarios, topics, overrides)
    audit_path = APP_DIR / "translation_audit.json"
    ledger = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else {"schema_version": 1, "cards": {}}
    if args.audit_request:
        request = build_request(dataset["cards"], ledger)
        args.audit_request.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Translation review request: {len(request['cards'])} card(s) -> {args.audit_request}")
        return 0
    if args.audit_approve:
        response = json.loads(args.audit_approve.read_text(encoding="utf-8"))
        ledger = approve_reviews(dataset["cards"], ledger, response)
        require_reviewed(dataset["cards"], ledger)
        audit_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Translation review current for {len(dataset['cards'])} card(s)")
        return 0
    require_reviewed(dataset["cards"], ledger)
    generate_audio(dataset["cards"])
    write_dataset(dataset)
    print(f"Sentence cards: {len(dataset['cards'])}, lessons: {len(lessons)}, revision: {dataset['revision']}")
    if not args.local_only:
        paths = ["sentences/data.json", "sentences/audio", "sentences/grammar_guides.json", "sentences/lesson_topics.json", "sentences/scenarios.json", "sentences/translation_overrides.json", "sentences/translation_audit.json"]
        subprocess.run(["git", "add", "--", *paths], cwd=SITE_ROOT, check=True)
        changes = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=SITE_ROOT)
        if changes.returncode == 1:
            subprocess.run(["git", "commit", "-m", f"Sync sentence practice {dataset['revision']}", "--", *paths], cwd=SITE_ROOT, check=True)
            subprocess.run(["git", "push"], cwd=SITE_ROOT, check=True)
        elif changes.returncode != 0:
            raise RuntimeError("Cannot inspect staged sentence changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

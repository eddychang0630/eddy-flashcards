"""Build reusable Kokoro MP3 clips for flashcard words and examples."""

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
from pathlib import Path


VOICE = "am_puck"
APP_DIR = Path(__file__).resolve().parent


def audio_relative_path(text, voice=VOICE):
    text = str(text).strip()
    if not text:
        return ""
    digest = hashlib.sha256(f"{voice}\0{text}".encode("utf-8")).hexdigest()[:20]
    return f"audio/{digest}.mp3"


def attach_audio_paths(cards):
    return [
        list(card[:12]) + [audio_relative_path(card[0]), audio_relative_path(card[4])]
        for card in cards
    ]


def clip_texts(cards):
    clips = {}
    for card in cards:
        for text, relative_path in ((card[0], card[12]), (card[4], card[13])):
            if relative_path:
                clips.setdefault(relative_path, str(text).strip())
    return clips


def missing_clips(cards, audio_dir):
    audio_dir = Path(audio_dir)
    return {
        relative_path: text
        for relative_path, text in clip_texts(cards).items()
        if not (audio_dir / Path(relative_path).name).is_file()
        or (audio_dir / Path(relative_path).name).stat().st_size == 0
    }


def generate_missing(cards, audio_dir, render_one):
    audio_dir = Path(audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    pending = missing_clips(cards, audio_dir)
    for index, (relative_path, text) in enumerate(pending.items(), start=1):
        target = audio_dir / Path(relative_path).name
        render_one(text, target)
        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError(f"audio generation failed: {relative_path}")
        if index % 20 == 0 or index == len(pending):
            print(f"Generated {index}/{len(pending)} {VOICE} clips", flush=True)
    return len(pending)


def ensure_complete(cards, audio_dir):
    pending = missing_clips(cards, audio_dir)
    if pending:
        raise RuntimeError(f"missing or empty audio: {len(pending)} clips, first: {next(iter(pending))}")


def _short_path(path):
    path = str(Path(path).resolve())
    if os.name != "nt":
        return path
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(path, buffer, len(buffer))
    if not length or length >= len(buffer):
        raise RuntimeError(f"Windows short path unavailable for eSpeak data: {path}")
    return buffer.value.replace("\\", "/")


def make_renderer(kokoro_home):
    kokoro_home = Path(kokoro_home)
    data_path = kokoro_home / "venv/Lib/site-packages/espeakng_loader/espeak-ng-data"
    if not data_path.is_dir():
        raise FileNotFoundError(f"eSpeak data not found: {data_path}")

    os.environ["HF_HOME"] = str(kokoro_home / "hf-cache")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["ESPEAK_DATA_PATH"] = _short_path(data_path)

    import misaki.espeak  # noqa: F401 - initialize bundled eSpeak library
    from phonemizer.backend.espeak.wrapper import EspeakWrapper
    import torch
    from kokoro import KPipeline

    EspeakWrapper.set_data_path(None)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Kokoro {VOICE} on {device}", flush=True)
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device=device)

    def render_one(text, target):
        target = Path(target)
        temporary = target.with_suffix(".tmp.mp3")
        try:
            chunks = [result.audio for result in pipeline(text, voice=VOICE)]
            if not chunks:
                raise RuntimeError(f"Kokoro produced no audio for: {text}")
            samples = torch.cat(chunks).detach().cpu().numpy().astype("float32")
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "f32le", "-ar", "24000", "-ac", "1", "-i", "pipe:0",
                    "-codec:a", "libmp3lame", "-q:a", "4", "-f", "mp3", str(temporary),
                ],
                input=samples.tobytes(),
                check=True,
            )
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    return render_one


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate offline Kokoro flashcard MP3s")
    parser.add_argument("--cards-file", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, default=APP_DIR / "audio")
    parser.add_argument(
        "--kokoro-home", type=Path,
        default=Path(os.environ.get("KOKORO_HOME", Path.home() / "Desktop/English class 整理重點/.models/kokoro")),
    )
    args = parser.parse_args(argv)
    cards = attach_audio_paths(json.loads(args.cards_file.read_text(encoding="utf-8")))
    pending = missing_clips(cards, args.audio_dir)
    print(f"Audio clips: {len(clip_texts(cards))} needed, {len(pending)} missing", flush=True)
    if pending:
        generate_missing(cards, args.audio_dir, make_renderer(args.kokoro_home))
    ensure_complete(cards, args.audio_dir)
    print("All audio clips verified", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

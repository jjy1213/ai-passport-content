"""Generate a versioned 16 kHz PCM voice pack for the four v2 courses.

Requires DASHSCOPE_API_KEY and the official dashscope Python package.
Run --dry-run first. The script never prints or writes the API key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEMES = ("good-morning", "animal-friends", "snack-time", "story-trip")
MODEL = "qwen-audio-3.1-tts-flash"
VOICE = "Abby_v3.1"


def text_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_pcm(text: str, key: str) -> bytes:
    from dashscope.audio.http_tts.http_speech_synthesizer import HttpSpeechSynthesizer

    chunks = []
    result = HttpSpeechSynthesizer.call(
        model=MODEL,
        text=text,
        voice=VOICE,
        format="pcm",
        sample_rate=16000,
        language_hints=["en"],
        stream=True,
        api_key=key,
    )
    for chunk in result:
        # The final event can also advertise the full audio URL; do not append
        # that event again or the spoken text may play twice.
        if not chunk.audio_url and chunk.audio_data:
            chunks.append(chunk.audio_data)
    audio = b"".join(chunks)
    if len(audio) < 3200 or len(audio) % 2:
        raise RuntimeError("Qwen returned empty or invalid 16-bit PCM audio")
    return audio


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    key = os.environ.get("DASHSCOPE_API_KEY")
    if not args.dry_run and not key:
        raise SystemExit("Set DASHSCOPE_API_KEY in your local environment first")

    catalog = json.loads((ROOT / "themes.json").read_text(encoding="utf-8"))
    device = json.loads((ROOT / "device-catalog.json").read_text(encoding="utf-8"))
    catalog_by_id = {theme["id"]: theme for theme in catalog["themes"]}
    device_by_id = {theme["id"]: theme for theme in device["themes"]}
    jobs = []

    for theme_id in THEMES:
        course = json.loads((ROOT / "courses" / "v2" / f"{theme_id}.json").read_text(encoding="utf-8"))
        if len(course["items"]) != 20:
            raise SystemExit(f"Expected 20 items in {theme_id}")
        for item in course["items"]:
            word = item["word"]
            if not word.isascii() or not word.replace("-", "").isalpha():
                raise SystemExit(f"Unsafe filename from word: {word}")
            for kind, spoken in (("word", word), ("example", item["example"])):
                rel = f"audio/v3/{theme_id}/{word}-{kind}.pcm"
                item[f"{kind}Audio"] = rel
                jobs.append((spoken, ROOT / rel))
        course["schemaVersion"] = 2
        course["version"] = 3
        raw = (json.dumps(course, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        catalog_by_id[theme_id].update(
            version=3,
            download=f"courses/v3/{theme_id}.json",
            estimatedBytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
        )
        device_by_id[theme_id].update(
            download=f"courses/v3/{theme_id}.json",
            sha256=hashlib.sha256(raw).hexdigest(),
        )
        if not args.dry_run:
            path = ROOT / "courses" / "v3" / f"{theme_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    print(f"Qwen model={MODEL}, voice={VOICE}, 16 kHz mono PCM, clips={len(jobs)}")
    if args.dry_run:
        return

    for index, (spoken, path) in enumerate(jobs, 1):
        if path.exists():
            size = path.stat().st_size
            if 3200 <= size <= 512000 and size % 2 == 0:
                print(f"[{index}/{len(jobs)}] existing {path.relative_to(ROOT)}")
                continue
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_suffix(".pcm.partial")
        pending.write_bytes(generate_pcm(spoken, key))
        pending.replace(path)
        print(f"[{index}/{len(jobs)}] generated {path.relative_to(ROOT)}")

    text_file(ROOT / "themes.json", catalog)
    text_file(ROOT / "device-catalog.json", device)
    for theme_id in THEMES:
        path = ROOT / "themes" / theme_id / "theme.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["version"] = 3
        metadata["course"] = f"courses/v3/{theme_id}.json"
        text_file(path, metadata)


if __name__ == "__main__":
    main()

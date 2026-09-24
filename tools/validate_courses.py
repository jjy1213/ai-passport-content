"""Validate the published device catalogue against bounded firmware fields."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"id": 24, "title": 36, "titleZh": 36, "download": 64,
          "word": 24, "meaningZh": 48, "example": 96,
          "exampleZh": 128, "wordAudio": 64, "exampleAudio": 64}


def check_text(label: str, value: str, limit: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: missing text")
    if len(value.encode("utf-8")) >= limit:
        raise ValueError(f"{label}: exceeds firmware field size {limit - 1} bytes")


def main() -> None:
    web = json.loads((ROOT / "themes.json").read_text(encoding="utf-8"))
    device = json.loads((ROOT / "device-catalog.json").read_text(encoding="utf-8"))
    if web.get("schemaVersion") != 2 or device.get("schemaVersion") != 2:
        raise ValueError("Catalogue schema must be v2")
    web_themes = {entry["id"]: entry for entry in web["themes"]}
    device_themes = {entry["id"]: entry for entry in device["themes"]}
    if not web_themes or len(web_themes) > 80 or web_themes.keys() != device_themes.keys():
        raise ValueError("Catalogue IDs differ or exceed 80 themes")

    words = set()
    for theme_id, entry in web_themes.items():
        compact = device_themes[theme_id]
        for field in ("id", "title", "titleZh", "download"):
            check_text(f"{theme_id}.{field}", compact[field], LIMITS[field])
            if compact[field] != entry[field]:
                raise ValueError(f"Catalogue mismatch: {theme_id}.{field}")
        if compact["sha256"] != entry["sha256"]:
            raise ValueError(f"Catalogue hash mismatch: {theme_id}")
        if not re.fullmatch(r"courses/v\d+/[a-z0-9-]+\.json", entry["download"]):
            raise ValueError(f"Unsafe course path: {theme_id}")
        raw = (ROOT / entry["download"]).read_bytes()
        if len(raw) != entry["estimatedBytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"Course size or SHA mismatch: {theme_id}")
        course = json.loads(raw)
        if course.get("format") != "ai-passport-course" or course.get("schemaVersion") != 2:
            raise ValueError(f"Unsupported course: {theme_id}")
        if course["theme"] != theme_id or course["version"] != entry["version"]:
            raise ValueError(f"Course identity mismatch: {theme_id}")
        items = course["items"]
        if len(items) != 20 or entry["itemCount"] != 20:
            raise ValueError(f"Expected 20 items: {theme_id}")
        for item in items:
            word = item["word"]
            if word in words:
                raise ValueError(f"Duplicate word across courses: {word}")
            words.add(word)
            for field in ("word", "meaningZh", "example", "exampleZh"):
                check_text(f"{theme_id}/{word}.{field}", item[field], LIMITS[field])
            if not re.search(r"\b" + re.escape(word) + r"\b", item["example"], re.I):
                raise ValueError(f"Example does not use its word: {theme_id}/{word}")
            for field in ("wordAudio", "exampleAudio"):
                if field not in item:
                    continue
                rel = item[field]
                check_text(f"{theme_id}/{word}.{field}", rel, LIMITS[field])
                if not re.fullmatch(r"audio/v\d+/[a-z0-9-]+/[a-z0-9-]+-(word|example)\.pcm", rel):
                    raise ValueError(f"Unsafe audio path: {rel}")
                audio = (ROOT / rel).read_bytes()
                if len(audio) < 3200 or len(audio) > 512000 or len(audio) % 2:
                    raise ValueError(f"Invalid PCM size: {rel}")
    print(f"PASS: {len(web_themes)} themes, {len(words)} unique words, matching SHA-256")


if __name__ == "__main__":
    main()

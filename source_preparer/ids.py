from __future__ import annotations

import re


SEGMENT_ID_PATTERN = re.compile(r"^v\d{2}_ch\d{3}_s\d{3}$")


def normalize_ordinal(value: str | int, width: int = 3) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("Ordinal value is required")
    if text.isdigit():
        return f"{int(text):0{width}d}"
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return f"{int(digits):0{width}d}"
    raise ValueError(f"Ordinal value must contain digits: {value}")


def normalize_volume(value: str | int) -> int:
    volume = int(str(value).strip())
    if volume < 1:
        raise ValueError("Volume number must be at least 1")
    return volume


def volume_label(volume_number: str | int) -> str:
    return f"v{normalize_volume(volume_number):02d}"


def make_segment_id(volume_number: str | int, chapter: str | int, segment: str | int) -> str:
    return f"{volume_label(volume_number)}_ch{normalize_ordinal(chapter)}_s{normalize_ordinal(segment)}"

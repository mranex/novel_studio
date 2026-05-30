from __future__ import annotations

import re
from pathlib import Path

from .ids import normalize_ordinal
from .models import Chapter


CHAPTER_MARKER = re.compile(r"^\*\*\*Chapter_(?P<number>[^*]+)\*\*\*\s*$")


def parse_txt(text: str) -> list[Chapter]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chapters: list[Chapter] = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        match = CHAPTER_MARKER.match(line)
        if not match:
            raise ValueError(f"Expected chapter marker at line {index + 1}: {lines[index]}")

        chapter = normalize_ordinal(match.group("number"))
        if index + 1 >= len(lines):
            raise ValueError(f"Missing chapter name after marker at line {index + 1}")
        name = lines[index + 1].strip()

        separator_index = index + 2
        if separator_index >= len(lines) or lines[separator_index].strip() != "**":
            raise ValueError(f"Missing ** separator after chapter name for chapter {chapter}")

        content_start = separator_index + 1
        content_end = content_start
        while content_end < len(lines) and not CHAPTER_MARKER.match(lines[content_end].strip()):
            content_end += 1

        content = "\n".join(lines[content_start:content_end]).strip()
        chapters.append(Chapter(chapter=chapter, name=name, content=content))
        index = content_end

    if not chapters:
        raise ValueError("No chapters found")
    return chapters


def parse_txt_file(path: str | Path) -> list[Chapter]:
    return parse_txt(Path(path).read_text(encoding="utf-8-sig"))


def chapter_from_paste(chapter_number: str | int, name: str, content: str) -> Chapter:
    return Chapter(chapter=normalize_ordinal(chapter_number), name=name.strip(), content=content.strip())

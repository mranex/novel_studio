from __future__ import annotations

import json
import re

from .ids import make_segment_id, normalize_volume
from .models import Chapter, Segment


def renumber_segments(segments: list[Segment], volume_number: str | int) -> list[Segment]:
    normalize_volume(volume_number)
    counters: dict[str, int] = {}
    renumbered: list[Segment] = []
    for segment in segments:
        counters[segment.chapter] = counters.get(segment.chapter, 0) + 1
        segment_number = f"{counters[segment.chapter]:03d}"
        renumbered.append(
            Segment(
                chapter=segment.chapter,
                name=segment.name,
                segment=segment_number,
                segment_ID=make_segment_id(volume_number, segment.chapter, segment_number),
                content=segment.content.strip(),
            )
        )
    return renumbered


def make_single_segments(chapters: list[Chapter], volume_number: str | int) -> list[Segment]:
    segments = [
        Segment(
            chapter=chapter.chapter,
            name=chapter.name,
            segment="001",
            segment_ID=make_segment_id(volume_number, chapter.chapter, 1),
            content=chapter.content.strip(),
        )
        for chapter in chapters
    ]
    return renumber_segments(segments, volume_number)


def split_segment_at(
    segments: list[Segment],
    selected_index: int,
    split_offset: int,
    volume_number: str | int,
) -> list[Segment]:
    if selected_index < 0 or selected_index >= len(segments):
        raise IndexError("Selected segment index is out of range")
    selected = segments[selected_index]
    content = selected.content
    if split_offset <= 0 or split_offset >= len(content):
        raise ValueError("Split point must be inside the segment content")

    left = content[:split_offset].strip()
    right = content[split_offset:].strip()
    if not left or not right:
        raise ValueError("Split would create an empty segment")

    replacement = [
        Segment(selected.chapter, selected.name, selected.segment, selected.segment_ID, left),
        Segment(selected.chapter, selected.name, selected.segment, selected.segment_ID, right),
    ]
    return renumber_segments(segments[:selected_index] + replacement + segments[selected_index + 1 :], volume_number)


def merge_segments(segments: list[Segment], selected_indices: list[int], volume_number: str | int) -> list[Segment]:
    if len(selected_indices) < 2:
        raise ValueError("Select at least two adjacent segments to merge")
    selected = sorted(selected_indices)
    if selected != list(range(selected[0], selected[-1] + 1)):
        raise ValueError("Selected segments must be adjacent")
    chapters = {segments[index].chapter for index in selected}
    if len(chapters) != 1:
        raise ValueError("Can only merge segments in the same chapter")

    first = segments[selected[0]]
    merged_content = "\n\n".join(segments[index].content.strip() for index in selected if segments[index].content.strip())
    merged = Segment(first.chapter, first.name, first.segment, first.segment_ID, merged_content)
    updated = segments[: selected[0]] + [merged] + segments[selected[-1] + 1 :]
    return renumber_segments(updated, volume_number)


def extract_segments_from_llm_json(raw_text: str, chapter: Chapter, volume_number: str | int) -> list[Segment]:
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()

    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("segments")
    if not isinstance(data, list):
        raise ValueError("LLM result must be a JSON array or an object with a segments array")

    segments: list[Segment] = []
    for index, item in enumerate(data, start=1):
        if isinstance(item, str):
            content = item
        elif isinstance(item, dict):
            content = str(item.get("content", ""))
        else:
            raise ValueError(f"Invalid segment result at index {index}")
        segments.append(
            Segment(
                chapter=chapter.chapter,
                name=chapter.name,
                segment=f"{index:03d}",
                segment_ID=make_segment_id(volume_number, chapter.chapter, index),
                content=content.strip(),
            )
        )
    return renumber_segments(segments, volume_number)

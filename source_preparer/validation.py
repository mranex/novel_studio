from __future__ import annotations

import re

from .ids import SEGMENT_ID_PATTERN, make_segment_id, normalize_volume
from .models import Chapter, Segment, ValidationResult


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def validate_chapters(chapters: list[Chapter]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()

    if not chapters:
        errors.append("At least one chapter is required.")

    for chapter in chapters:
        if chapter.chapter in seen:
            errors.append(f"Duplicate chapter number: {chapter.chapter}.")
        seen.add(chapter.chapter)
        if not chapter.content.strip():
            errors.append(f"Chapter {chapter.chapter} has empty content.")
        if not chapter.name.strip():
            warnings.append(f"Chapter {chapter.chapter} has no name.")

    return ValidationResult(errors=errors, warnings=warnings)


def validate_segments(chapters: list[Chapter], segments: list[Segment], volume_number: str | int) -> ValidationResult:
    errors = validate_chapters(chapters).errors
    warnings = validate_chapters(chapters).warnings
    chapter_map = {chapter.chapter: chapter for chapter in chapters}

    volume_is_valid = True
    try:
        normalize_volume(volume_number)
    except ValueError as exc:
        volume_is_valid = False
        errors.append(str(exc))

    if chapters and not segments:
        errors.append("At least one segment is required.")

    seen_ids: set[str] = set()
    segments_by_chapter: dict[str, list[Segment]] = {}

    for segment in segments:
        if not segment.content.strip():
            errors.append(f"Segment {segment.segment_ID or '<missing>'} has empty content.")
        if segment.segment_ID in seen_ids:
            errors.append(f"Duplicate segment_ID: {segment.segment_ID}.")
        seen_ids.add(segment.segment_ID)
        if not SEGMENT_ID_PATTERN.match(segment.segment_ID):
            errors.append(f"Invalid segment_ID format: {segment.segment_ID}.")
        if volume_is_valid:
            expected_id = make_segment_id(volume_number, segment.chapter, segment.segment)
            if segment.segment_ID != expected_id:
                errors.append(f"Segment {segment.segment_ID} should be {expected_id}.")
        if segment.chapter not in chapter_map:
            errors.append(f"Segment {segment.segment_ID} references missing chapter {segment.chapter}.")
        segments_by_chapter.setdefault(segment.chapter, []).append(segment)

    for chapter in chapters:
        chapter_segments = segments_by_chapter.get(chapter.chapter, [])
        if not chapter_segments:
            errors.append(f"Chapter {chapter.chapter} has no segments.")
            continue

        expected_numbers = [f"{index:03d}" for index in range(1, len(chapter_segments) + 1)]
        actual_numbers = [segment.segment for segment in chapter_segments]
        if actual_numbers != expected_numbers:
            errors.append(
                f"Chapter {chapter.chapter} segment order should be {', '.join(expected_numbers)}."
            )

        combined = "\n".join(segment.content for segment in chapter_segments)
        if _normalized_text(combined) != _normalized_text(chapter.content):
            warnings.append(f"Segments for chapter {chapter.chapter} do not exactly match chapter content.")

    return ValidationResult(errors=errors, warnings=warnings)

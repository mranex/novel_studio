from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter

from app.projects import load_project_metadata, load_project_settings
from app.schemas import (
    PipelineItem,
    PipelineRunResponse,
    PipelineStepState,
    PipelineSubItem,
    SegmentSkeleton,
    SourceSegment,
    utc_now,
)
from app.storage import read_json, resolve_project_path, write_json_atomic
from app.storage.helpers import volume_dir
from app.pipeline.state import load_pipeline_state, save_pipeline_state, upsert_pipeline_step


segment_adapter = TypeAdapter(list[SourceSegment])
item_adapter = TypeAdapter(list[PipelineItem])
skeleton_adapter = TypeAdapter(list[SegmentSkeleton])
subitem_adapter = TypeAdapter(list[PipelineSubItem])

OPEN_QUOTES = ["「", "『", "“", "\"", "‘", "'", "—", "-"]
QUOTE_PAIRS = {
    "「": "」",
    "『": "』",
    "“": "”",
    "\"": "\"",
    "‘": "’",
    "'": "'",
}
SENTENCE_END_RE = re.compile(r"[。！？.!?；;]\s*$")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")
LATIN_WORD_RE = re.compile(r"[A-Za-z0-9_]+")

def _load_segments(project_root: str | Path, volume: int) -> list[SourceSegment]:
    path = resolve_project_path(project_root, "segment", f"volume.{volume:02d}.segment.json")
    return read_json(path, segment_adapter)


def split_paragraphs(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]


def classify_paragraph(text: str, source_language: str) -> tuple[str, bool, str, list[str]]:
    stripped = text.strip()
    warnings: list[str] = []
    starts_with_dialogue = any(stripped.startswith(marker) for marker in OPEN_QUOTES)
    contains_quote = any(open_quote in stripped and close_quote in stripped for open_quote, close_quote in QUOTE_PAIRS.items())
    balanced = True
    for open_quote, close_quote in QUOTE_PAIRS.items():
        if open_quote in stripped or close_quote in stripped:
            if open_quote == close_quote:
                balanced = stripped.count(open_quote) % 2 == 0
            else:
                balanced = stripped.count(open_quote) == stripped.count(close_quote)
            if not balanced:
                break

    is_dialogue = starts_with_dialogue or (contains_quote and source_language in {"zh", "ja", "ko", "en", "other"})
    needs_review = False
    confidence = "high"
    if is_dialogue and not balanced:
        needs_review = True
        confidence = "low"
        warnings.append("unbalanced_dialogue_markers")
    if is_dialogue and contains_quote and not starts_with_dialogue:
        needs_review = True
        confidence = "low"
        warnings.append("mixed_narration_dialogue")
    if is_dialogue and (stripped.endswith("。") or stripped.endswith(".") or stripped.endswith("!")) and contains_quote:
        outside_quote = re.sub(r"[「『“\"‘'].*?[」』”\"’']", "", stripped).strip()
        if outside_quote:
            needs_review = True
            confidence = "low"
            if "mixed_narration_dialogue" not in warnings:
                warnings.append("mixed_narration_dialogue")

    return ("dialogue" if is_dialogue else "narration", needs_review, confidence, warnings)


def _item_id(segment_id: str, item_type: str, counter: int) -> str:
    affix = "diag" if item_type == "dialogue" else "nar"
    return f"{segment_id}_{affix}_{counter:03d}"


def build_items_from_segments(segments: list[SourceSegment], source_language: str) -> tuple[list[SegmentSkeleton], list[PipelineItem]]:
    skeletons: list[SegmentSkeleton] = []
    items: list[PipelineItem] = []
    for segment in segments:
        counters = {"narration": 0, "dialogue": 0}
        item_ids: list[str] = []
        for paragraph in split_paragraphs(segment.content):
            item_type, needs_review, confidence, warnings = classify_paragraph(paragraph, source_language)
            counters[item_type] += 1
            item_id = _item_id(segment.segment_ID, item_type, counters[item_type])
            item_ids.append(item_id)
            items.append(
                PipelineItem(
                    item_ID=item_id,
                    segment_ID=segment.segment_ID,
                    chapter=segment.chapter,
                    type=item_type,
                    text=paragraph,
                    needs_review=needs_review,
                    confidence=confidence,
                    warnings=warnings,
                )
            )
        skeletons.append(SegmentSkeleton(segment_ID=segment.segment_ID, items=item_ids))
    return skeletons, items


def _estimate_tokens_heuristic(text: str) -> int:
    cjk_count = len(CJK_RE.findall(text))
    latin_count = len(LATIN_WORD_RE.findall(text))
    punctuation_buffer = max(1, len(text) // 40)
    return int(cjk_count * 1.5 + latin_count * 1.3 + punctuation_buffer)


def estimate_tokens(text: str) -> int:
    try:
        import tiktoken  # type: ignore

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return _estimate_tokens_heuristic(text)


def _split_long_text(text: str, max_tokens: int) -> list[str]:
    if estimate_tokens(text) <= max_tokens:
        return [text]

    chunks: list[str] = []
    remaining = text.strip()
    while remaining:
        if estimate_tokens(remaining) <= max_tokens:
            chunks.append(remaining)
            break

        ratio = max_tokens / max(estimate_tokens(remaining), 1)
        cut = max(1, min(len(remaining) - 1, int(len(remaining) * ratio * 0.9)))
        search_start = max(0, int(cut * 0.55))
        punctuation_cut = -1
        for index in range(cut, search_start, -1):
            if SENTENCE_END_RE.search(remaining[:index]):
                punctuation_cut = index
                break
        if punctuation_cut > 0:
            cut = punctuation_cut

        chunk = remaining[:cut].strip()
        if not chunk:
            chunk = remaining[:cut]
        chunks.append(chunk)
        remaining = remaining[cut:].strip()
    return chunks


def build_subitems_from_items(items: list[PipelineItem], max_tokens: int) -> list[PipelineSubItem]:
    subitems: list[PipelineSubItem] = []
    for item in items:
        chunks = [item.text] if item.type == "dialogue" else _split_long_text(item.text, max_tokens)
        for index, chunk in enumerate(chunks, start=1):
            subitems.append(
                PipelineSubItem(
                    item_ID=item.item_ID,
                    sub_item_ID=f"{item.item_ID}_sub_{index:03d}",
                    text=chunk,
                )
            )
    return subitems


def build_skeleton(project_root: str | Path, volume: int) -> PipelineRunResponse:
    metadata = load_project_metadata(project_root)
    segments = _load_segments(project_root, volume)
    skeletons, items = build_items_from_segments(segments, metadata.source_language)
    work_dir = resolve_project_path(project_root, "work", volume_dir(volume))
    work_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(work_dir / "segment_skeleton.json", skeletons, skeleton_adapter)
    write_json_atomic(work_dir / "segment_flesh.json", items, item_adapter)

    warnings = sorted({warning for item in items for warning in item.warnings})
    counts = {
        "segments": len(skeletons),
        "items": len(items),
        "narration_items": sum(1 for item in items if item.type == "narration"),
        "dialogue_items": sum(1 for item in items if item.type == "dialogue"),
        "needs_review": sum(1 for item in items if item.needs_review),
    }
    state = load_pipeline_state(project_root, volume)
    upsert_pipeline_step(
        state,
        PipelineStepState(
            name="skeleton",
            status="completed",
            message=f"{counts['items']} items built",
            updated_at=utc_now(),
            metrics=counts,
        ),
    )
    upsert_pipeline_step(
        state,
        PipelineStepState(
            name="sub_items",
            status="ready",
            message="Ready to split sub-items",
            updated_at=utc_now(),
            metrics={},
        ),
    )
    saved_state = save_pipeline_state(project_root, volume, state)
    return PipelineRunResponse(volume=volume, pipeline_state=saved_state, counts=counts, warnings=warnings)


def load_items(project_root: str | Path, volume: int) -> list[PipelineItem]:
    path = resolve_project_path(project_root, "work", volume_dir(volume), "segment_flesh.json")
    return read_json(path, item_adapter)


def load_subitems(project_root: str | Path, volume: int) -> list[PipelineSubItem]:
    path = resolve_project_path(project_root, "work", volume_dir(volume), "sub_items.json")
    return read_json(path, subitem_adapter)


def build_subitems(project_root: str | Path, volume: int) -> PipelineRunResponse:
    settings = load_project_settings(project_root)
    items = load_items(project_root, volume)
    subitems = build_subitems_from_items(items, settings.max_subitem_tokens)
    work_dir = resolve_project_path(project_root, "work", volume_dir(volume))
    write_json_atomic(work_dir / "sub_items.json", subitems, subitem_adapter)
    subitem_counts = Counter(subitem.item_ID for subitem in subitems)

    counts = {
        "items": len(items),
        "sub_items": len(subitems),
        "split_narration_items": sum(1 for count in subitem_counts.values() if count > 1),
    }
    warnings = []
    for item in items:
        if item.type == "dialogue" and estimate_tokens(item.text) > settings.max_subitem_tokens:
            warnings.append(f"very_long_dialogue:{item.item_ID}")

    state = load_pipeline_state(project_root, volume)
    upsert_pipeline_step(
        state,
        PipelineStepState(
            name="sub_items",
            status="completed",
            message=f"{counts['sub_items']} sub-items built",
            updated_at=utc_now(),
            metrics=counts,
        ),
    )
    saved_state = save_pipeline_state(project_root, volume, state)
    return PipelineRunResponse(volume=volume, pipeline_state=saved_state, counts=counts, warnings=warnings)

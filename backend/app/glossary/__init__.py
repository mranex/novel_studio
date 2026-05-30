from __future__ import annotations

__all__ = [
    "extract_draft_glossary",
    "get_volume_table",
    "merge_draft_glossary",
    "scan_item_glossary",
    "scan_segment_glossary",
    "update_glossary_entry",
]


def __getattr__(name: str):
    if name in __all__:
        from . import service

        return getattr(service, name)
    raise AttributeError(name)


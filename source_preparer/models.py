from __future__ import annotations

from dataclasses import dataclass


SEGMENT_WARNING = (
    "Segment boundaries affect relationship extraction, dialogue labels, pronouns, "
    "and translation context.\n"
    "Avoid cutting in the middle of a dialogue or event."
)


@dataclass(slots=True)
class Chapter:
    chapter: str
    name: str
    content: str

    def to_json(self) -> dict[str, str]:
        return {
            "chapter": self.chapter,
            "name": self.name,
            "content": self.content,
        }


@dataclass(slots=True)
class Segment:
    chapter: str
    name: str
    segment: str
    segment_ID: str
    content: str

    def to_json(self) -> dict[str, str]:
        return {
            "chapter": self.chapter,
            "name": self.name,
            "segment": self.segment,
            "segment_ID": self.segment_ID,
            "content": self.content,
        }


@dataclass(slots=True)
class LLMConfig:
    base_url: str
    api_key: str = ""
    model: str = ""
    batch_count: int = 1


@dataclass(slots=True)
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors

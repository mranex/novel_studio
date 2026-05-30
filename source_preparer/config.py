from __future__ import annotations

import json
from pathlib import Path

from .models import LLMConfig


DEFAULT_CONFIG = LLMConfig(base_url="https://api.openai.com/v1", api_key="", model="", batch_count=1)


def _config_from_dict(data: dict) -> LLMConfig:
    if "big_llm" in data and isinstance(data["big_llm"], dict):
        provider = data["big_llm"]
        return LLMConfig(
            base_url=str(provider.get("base_url", DEFAULT_CONFIG.base_url)),
            api_key=str(provider.get("api_key", "")),
            model=str(provider.get("model", "")),
            batch_count=int(data.get("batch_count", 1) or 1),
        )
    return LLMConfig(
        base_url=str(data.get("base_url", DEFAULT_CONFIG.base_url)),
        api_key=str(data.get("api_key", "")),
        model=str(data.get("model", "")),
        batch_count=int(data.get("batch_count", 1) or 1),
    )


def load_config_file(path: str | Path) -> LLMConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Config JSON must be an object")
    return _config_from_dict(data)


def load_default_config() -> LLMConfig:
    app_settings = Path.home() / ".novel-studio" / "settings.json"
    if app_settings.exists():
        return load_config_file(app_settings)
    return DEFAULT_CONFIG


def load_prompt(path: str | Path | None = None) -> str:
    if path:
        prompt_path = Path(path)
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8-sig")

    default_prompt = Path("prompt") / "segment_source.md"
    if default_prompt.exists():
        return default_prompt.read_text(encoding="utf-8-sig")

    return DEFAULT_SEGMENT_PROMPT


DEFAULT_SEGMENT_PROMPT = """# Task
Split the chapter into coherent novel translation segments.

# Segmentation Criteria
A segment should end at one of these natural boundaries:
- End of an event, scene beat, timeskip, or point that does not affect the next event.
- POV change.
- End of a large dialogue exchange without cutting through the dialogue.

# Hard Rules
- Do not rewrite the source.
- Do not omit content.
- Do not split inside a sentence.
- Avoid splitting in the middle of a dialogue exchange.
- Preserve paragraph order.

# Output Schema
[
  {
    "chapter": "[CHAPTER]",
    "name": "[CHAPTER_NAME]",
    "segment": "001",
    "content": "segment source text"
  }
]

# Source
[SOURCE_TEXT]
"""

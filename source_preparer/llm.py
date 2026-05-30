from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import load_prompt
from .models import Chapter, LLMConfig
from .segmentation import extract_segments_from_llm_json


def build_segmentation_prompt(chapter: Chapter, prompt_template: str | None = None) -> str:
    template = prompt_template or load_prompt()
    values = {
        "CHAPTER": chapter.chapter,
        "CHAPTER_NAME": chapter.name,
        "SOURCE_TEXT": chapter.content,
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"[{key}]", value)
    if rendered != template:
        return rendered.rstrip() + "\n"

    return (
        f"{template.rstrip()}\n\n"
        f"Chapter: {chapter.chapter}\n"
        f"Name: {chapter.name}\n\n"
        "[SOURCE_TEXT]\n"
        f"{chapter.content}\n"
        "[/SOURCE_TEXT]\n"
    )


def call_openai_compatible(config: LLMConfig, prompt: str, timeout: int = 120) -> str:
    if not config.base_url.strip():
        raise ValueError("Base URL is required")
    if not config.model.strip():
        raise ValueError("Model is required")

    endpoint = config.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0,
    }
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8-sig"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("LLM response did not contain choices[0].message.content") from exc


def auto_segment_chapter(chapter: Chapter, volume_number: str | int, config: LLMConfig):
    prompt = build_segmentation_prompt(chapter)
    raw_result = call_openai_compatible(config, prompt)
    return extract_segments_from_llm_json(raw_result, chapter, volume_number)

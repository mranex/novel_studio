from __future__ import annotations

__all__ = [
    "call_llm",
    "ensure_prompt_files",
    "list_prompt_files",
    "read_prompt_file",
    "render_prompt",
    "run_llm",
    "save_prompt_result",
    "update_prompt_file",
    "validate_prompt_result",
]


def __getattr__(name: str):
    if name in __all__:
        from . import service

        return getattr(service, name)
    raise AttributeError(name)

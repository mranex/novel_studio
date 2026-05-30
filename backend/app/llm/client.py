from __future__ import annotations

import logging

import httpx

from app.schemas import AppSettings, ProviderSlot


logger = logging.getLogger(__name__)


def call_llm(settings: AppSettings, provider_slot: ProviderSlot, prompt: str) -> str:
    provider = getattr(settings, provider_slot)
    if not provider.base_url.strip():
        raise ValueError(f"{provider_slot} base_url is required.")
    if not provider.model.strip():
        raise ValueError(f"{provider_slot} model is required.")

    headers = {"Content-Type": "application/json"}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"
    payload = {
        "model": provider.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    url = provider.base_url.rstrip("/") + "/chat/completions"
    logger.info("Calling LLM provider_slot=%s model=%s url=%s", provider_slot, provider.model, url)
    response = httpx.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]

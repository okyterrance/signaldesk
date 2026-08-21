"""Minimal TokenRouter client with ordered cross-family fallback.

TokenRouter exposes an OpenAI-compatible /chat/completions surface, so
this is a plain httpx call rather than a heavyweight SDK -- easier to
read, and the whole request is visible in one screen.

Providers are tried in order and the first to return parseable output
wins. The chain is deliberately cross-family (Anthropic then OpenAI):
chaining two models from one vendor gives you a retry, not a fallback,
because a vendor outage takes out both links at once.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import httpx

from src.config import settings

log = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass
class LLMResult:
    data: dict
    model: str
    ok: bool


def _extract_json(text: str) -> dict:
    """Parse a JSON object out of raw or markdown-fenced model output.

    Models fence their JSON unpredictably even when told not to, so strip
    fences first and fall back to scanning for the outermost braces.
    """
    cleaned = _FENCE.sub("", (text or "").strip()).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        parsed = json.loads(cleaned[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("no JSON object in model output")


async def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int | None = None,
) -> LLMResult:
    """Call the chain until one provider returns a JSON object.

    Never raises for provider failure -- callers get `ok=False` and are
    expected to render a template-only fallback. A briefing that arrives
    without its LLM summary is far better than one that never arrives.
    """
    if not settings.tokenrouter_api_key:
        log.warning("TOKENROUTER_API_KEY unset; skipping LLM")
        return LLMResult(data={}, model="", ok=False)

    headers = {
        "Authorization": f"Bearer {settings.tokenrouter_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.tokenrouter_base_url.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=settings.llm_timeout_s) as client:
        for model in settings.llm_model_chain:
            payload = {
                "model": model,
                "max_tokens": max_tokens or settings.llm_max_tokens,
                # Low but not zero. Zero makes the summaries read like a
                # template; high makes them invent connective tissue the
                # source material does not support.
                "temperature": 0.3,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return LLMResult(data=_extract_json(content), model=model, ok=True)
            except Exception as exc:
                log.warning(
                    "llm provider failed: %s (%s)", model, type(exc).__name__
                )
                continue

    log.error("all llm providers failed; falling back to template output")
    return LLMResult(data={}, model="", ok=False)

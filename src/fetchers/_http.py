"""Shared HTTP client with retry, backoff, and a rotating user agent.

Several of the feeds we read rate-limit or soft-block clients that look
automated, so requests go out behind a small UA pool. Retries are capped
tight: this runs on a schedule, and a feed that is down now will be
polled again in fifteen minutes anyway.
"""
from __future__ import annotations

import random
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


@asynccontextmanager
async def make_session(timeout: float = 20.0) -> AsyncIterator[httpx.AsyncClient]:
    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "application/rss+xml, application/xml, text/xml, application/json;q=0.9, */*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(
        timeout=timeout, headers=headers, follow_redirects=True
    ) as client:
        yield client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    reraise=True,
)
async def get_with_retry(
    client: httpx.AsyncClient, url: str, **kwargs: object
) -> httpx.Response:
    response = await client.get(url, **kwargs)  # type: ignore[arg-type]
    response.raise_for_status()
    return response

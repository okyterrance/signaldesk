"""Twelve RSS feeds, two buckets, zero API keys.

Crypto and macro are fetched into separate buckets and scored separately.
Mixing them would be a mistake: macro headlines lose on the asset factor
by construction, so a single pool would quietly crowd out the Fed in
favour of whatever token moved overnight.

Every source is independently try/except'd and independently timed out. A
hanging feed must not zero out the whole run -- an early version of the
upstream system lost entire digests to one RSS host that took 66 seconds
to not respond.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import feedparser

from src.config import settings
from src.fetchers._http import get_with_retry, make_session
from src.models import NewsItem
from src.scoring.filters import reject_reason

log = logging.getLogger(__name__)

# (label, url, bucket, window_hours_override)
FEEDS: list[tuple[str, str, str, int | None]] = [
    # --- crypto ---
    ("CoinDesk",     "https://www.coindesk.com/arc/outboundfeeds/rss/", "crypto", None),
    ("The Block",    "https://www.theblock.co/rss.xml",                 "crypto", None),
    ("Decrypt",      "https://decrypt.co/feed",                         "crypto", None),
    ("The Defiant",  "https://thedefiant.io/api/feed",                  "crypto", None),
    ("DL News",      "https://dlnews.com/arc/outboundfeeds/rss/",       "crypto", None),
    ("Unchained",    "https://unchainedcrypto.com/feed/",               "crypto", None),
    # --- macro ---
    ("CNBC",         "https://www.cnbc.com/id/100003114/device/rss/rss.html", "macro", None),
    ("FT Markets",   "https://www.ft.com/markets?format=rss",           "macro", None),
    ("Bloomberg",    "https://feeds.bloomberg.com/markets/news.rss",    "macro", None),
    ("SCMP Business", "https://www.scmp.com/rss/2/feed",                "macro", None),
    ("Channel News Asia", "https://www.channelnewsasia.com/rssfeeds/8395986", "macro", None),
    # Official statements come roughly twice a week, so a 24h window would
    # usually see nothing. 72h keeps the last one in range.
    ("ECB Press",    "https://www.ecb.europa.eu/rss/press.html",        "macro", 72),
]

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", text or "")).strip()


def _parse_time(entry: dict) -> datetime:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    # An entry with no usable timestamp is treated as "just now" rather
    # than dropped. Some feeds omit dates on their newest items.
    return datetime.now(timezone.utc)


def parse_feed(
    xml: str | None, label: str, bucket: str, cutoff: datetime, cap: int
) -> tuple[list[NewsItem], dict[str, int]]:
    """Parse one feed. Returns (kept items, reject counts by reason)."""
    items: list[NewsItem] = []
    rejects: dict[str, int] = {}
    if not xml:
        return items, rejects

    for entry in feedparser.parse(xml).entries:
        if len(items) >= cap:
            break
        title = (entry.get("title") or "").strip()
        url = entry.get("link") or ""
        if not title or not url.startswith("http"):
            continue

        published_at = _parse_time(entry)
        if published_at < cutoff:
            continue

        reason = reject_reason(title, bucket)
        if reason:
            rejects[reason] = rejects.get(reason, 0) + 1
            continue

        items.append(
            NewsItem(
                title=title,
                url=url,
                source=label,
                published_at=published_at,
                bucket=bucket,
                tags=[
                    t.get("term", "").lower()
                    for t in (entry.get("tags") or [])
                    if t.get("term")
                ],
                summary=_strip_html(entry.get("summary", ""))[:400],
            )
        )
    return items, rejects


async def fetch_all() -> tuple[list[NewsItem], dict[str, object]]:
    """Fetch every feed concurrently.

    Returns the items plus a stats dict, which `/status` renders so a
    quietly-degraded feed is visible instead of just producing a thinner
    digest for no apparent reason.
    """
    now = datetime.now(timezone.utc)
    raw: dict[str, str | None] = {}
    failed: list[str] = []

    async with make_session(timeout=20.0) as client:

        async def _one(label: str, url: str) -> None:
            try:
                response = await asyncio.wait_for(
                    get_with_retry(client, url),
                    timeout=settings.source_timeout_s,
                )
                raw[label] = response.text
            except (Exception, asyncio.TimeoutError) as exc:
                failed.append(label)
                log.warning("feed failed: %s (%s)", label, type(exc).__name__)

        await asyncio.gather(*(_one(label, url) for label, url, _, _ in FEEDS))

    items: list[NewsItem] = []
    rejects: dict[str, int] = {}
    per_source: dict[str, int] = {}

    for label, _url, bucket, window_override in FEEDS:
        window = window_override or settings.news_window_h
        cutoff = now - timedelta(hours=window)
        parsed, feed_rejects = parse_feed(
            raw.get(label), label, bucket, cutoff, settings.news_max_per_source
        )
        items.extend(parsed)
        per_source[label] = len(parsed)
        for reason, count in feed_rejects.items():
            rejects[reason] = rejects.get(reason, 0) + count

    stats = {
        "feeds_total": len(FEEDS),
        "feeds_ok": len(FEEDS) - len(failed),
        "feeds_failed": failed,
        "items_kept": len(items),
        "rejected": rejects,
        "per_source": per_source,
        "fetched_at": now,
    }
    return items, stats

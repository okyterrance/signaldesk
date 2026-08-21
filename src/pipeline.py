"""The pipeline: feeds in, ranked stories out.

    fetch (12 feeds, concurrent)
      -> hard filters      [in the fetcher, so rejects never reach scoring]
      -> dedupe            [per bucket]
      -> 7-factor score    [per bucket]
      -> adaptive top-N    [per bucket]
      -> merge, re-sort

Buckets stay separate until the final merge. Crypto and macro headlines
are not comparable on the asset factor -- a Fed decision names no token
and would lose slots to any coin story if they competed directly -- so
each bucket gets its own quota and they only meet again at the end.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.config import settings
from src.fetchers import market as market_fetcher
from src.fetchers import rss
from src.models import MarketSnapshot, NewsItem
from src.scoring import categories
from src.scoring.dedup import dedupe
from src.scoring.weights import score_all, select_top, weights_for

log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    items: list[NewsItem]
    market: MarketSnapshot
    stats: dict[str, object] = field(default_factory=dict)
    ran_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


async def run(
    *,
    with_market: bool = True,
    enabled_categories: set[str] | None = None,
    depth: str = "balanced",
) -> PipelineResult:
    """Fetch, rank and select, against one reader's preferences.

    Category filtering runs *after* dedupe and *before* scoring. After
    dedupe, so corroboration counts are computed over the whole feed
    rather than over one reader's slice — a story carried by four outlets
    is corroborated whether or not this reader subscribes to all four
    categories. Before scoring, so the adaptive top-N thresholds apply to
    the pool the reader will actually see.
    """
    raw_items, stats = await (
        _gather(with_market) if with_market else _gather_news_only()
    )
    market = stats.pop("_market", MarketSnapshot())  # type: ignore[assignment]

    categories.annotate(raw_items)
    table = weights_for(depth)

    by_bucket: dict[str, list[NewsItem]] = {"crypto": [], "macro": []}
    for item in raw_items:
        by_bucket.setdefault(item.bucket, []).append(item)

    selected: list[NewsItem] = []
    bucket_stats: dict[str, dict[str, int]] = {}
    filtered_out = 0

    for bucket, bucket_items in by_bucket.items():
        before = len(bucket_items)
        deduped = dedupe(bucket_items, threshold=settings.dedupe_threshold)

        if enabled_categories is not None:
            kept = categories.filter_by_categories(deduped, enabled_categories)
            filtered_out += len(deduped) - len(kept)
            deduped = kept

        scored = score_all(deduped, weights=table)

        if bucket == "crypto":
            min_n, max_n = settings.crypto_min_n, settings.crypto_max_n
        else:
            min_n, max_n = settings.macro_min_n, settings.macro_max_n

        top = select_top(scored, min_n, max_n, settings.select_threshold)
        selected.extend(top)
        bucket_stats[bucket] = {
            "fetched": before,
            "after_dedupe": len(deduped),
            "selected": len(top),
        }

    selected.sort(key=lambda i: -i.score)
    stats["buckets"] = bucket_stats
    stats["selected_total"] = len(selected)
    stats["filtered_by_category"] = filtered_out
    stats["depth"] = depth
    stats["categories"] = sorted(enabled_categories) if enabled_categories else "all"

    log.info(
        "pipeline: %s kept -> %s selected (%s)",
        stats.get("items_kept"),
        len(selected),
        bucket_stats,
    )
    return PipelineResult(items=selected, market=market, stats=stats)


async def _gather(with_market: bool) -> tuple[list[NewsItem], dict[str, object]]:
    """News and market data concurrently; market failure must not block news."""
    news_task = rss.fetch_all()
    market_task = market_fetcher.fetch_market()
    (items, stats), market = await asyncio.gather(news_task, market_task)
    stats["_market"] = market
    return items, stats


async def _gather_news_only() -> tuple[list[NewsItem], dict[str, object]]:
    items, stats = await rss.fetch_all()
    stats["_market"] = MarketSnapshot()
    return items, stats

"""Shared in-memory state between commands and scheduled jobs.

Two things need to persist across handler calls:

  1. The last ranked result, so `/why 3` refers to the same story `/top`
     just printed. Without it, `/why` would have to re-run the pipeline
     and could easily answer about a different story than the one the
     user is looking at.

  2. Which stories have already been alerted on, so a story sitting above
     threshold does not re-fire every polling cycle for as long as it
     stays in the 24h window.

The alerted set is capped and time-pruned rather than growing forever;
a long-running process should not leak memory over a URL set.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.models import MarketSnapshot, NewsItem


@dataclass
class BotState:
    last_items: list[NewsItem] = field(default_factory=list)
    last_market: MarketSnapshot = field(default_factory=MarketSnapshot)
    last_stats: dict = field(default_factory=dict)
    last_run: datetime | None = None

    alert_threshold: float | None = None      # None -> use the configured default
    _alerted: dict[str, datetime] = field(default_factory=dict)

    def remember(
        self, items: list[NewsItem], market: MarketSnapshot, stats: dict
    ) -> None:
        self.last_items = items
        self.last_market = market
        self.last_stats = stats
        self.last_run = datetime.now(timezone.utc)

    def is_fresh(self, max_age_minutes: int = 20) -> bool:
        if not self.last_run or not self.last_items:
            return False
        age = datetime.now(timezone.utc) - self.last_run
        return age < timedelta(minutes=max_age_minutes)

    # --- alert de-duplication ---

    def should_alert(self, item: NewsItem) -> bool:
        return item.key not in self._alerted

    def mark_alerted(self, item: NewsItem) -> None:
        self._alerted[item.key] = datetime.now(timezone.utc)
        self._prune()

    def _prune(self, ttl_hours: int = 48) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
        self._alerted = {k: v for k, v in self._alerted.items() if v > cutoff}


state = BotState()

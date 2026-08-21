"""In-memory state shared between commands and scheduled jobs.

Two things need to survive between handler calls:

  1. The last ranked result *per chat*, so `/why 3` refers to the same
     story `/top` just printed. It is keyed by chat because rankings are
     now per-chat — serving one reader's security-only ranking to another
     who asked for everything would be worse than no cache at all.

     The cache also records the preferences it was computed under, so a
     settings change invalidates it implicitly as well as explicitly.

  2. Which stories have already been alerted on, so a story sitting above
     threshold does not re-fire every polling cycle for as long as it
     stays inside the 24h window. That set is time-pruned rather than
     growing forever; a long-running process should not leak memory over
     a set of URLs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.models import MarketSnapshot, NewsItem

CACHE_TTL_MINUTES = 20


@dataclass
class ChatCache:
    items: list[NewsItem]
    market: MarketSnapshot
    stats: dict
    signature: tuple
    ran_at: datetime

    def is_fresh(self, signature: tuple) -> bool:
        if signature != self.signature:
            return False
        age = datetime.now(timezone.utc) - self.ran_at
        return age < timedelta(minutes=CACHE_TTL_MINUTES)


def _signature(prefs) -> tuple:
    """What the ranking depended on. Any change here invalidates the cache."""
    return (tuple(sorted(prefs.categories)), prefs.depth)


@dataclass
class BotState:
    _chats: dict[str, ChatCache] = field(default_factory=dict)
    _alerted: dict[str, datetime] = field(default_factory=dict)

    alert_threshold: float | None = None   # None -> use the configured default

    # --- per-chat ranking cache ---

    def remember(
        self,
        chat_id: str | int,
        prefs,
        items: list[NewsItem],
        market: MarketSnapshot,
        stats: dict,
    ) -> None:
        self._chats[str(chat_id)] = ChatCache(
            items=items,
            market=market,
            stats=stats,
            signature=_signature(prefs),
            ran_at=datetime.now(timezone.utc),
        )

    def get_cached(self, chat_id: str | int, prefs) -> list[NewsItem] | None:
        cached = self._chats.get(str(chat_id))
        if cached and cached.is_fresh(_signature(prefs)):
            return cached.items
        return None

    def market_for(self, chat_id: str | int) -> MarketSnapshot:
        cached = self._chats.get(str(chat_id))
        return cached.market if cached else MarketSnapshot()

    def stats_for(self, chat_id: str | int) -> dict:
        cached = self._chats.get(str(chat_id))
        return cached.stats if cached else {}

    def invalidate(self, chat_id: str | int) -> None:
        self._chats.pop(str(chat_id), None)

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

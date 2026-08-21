"""Core data shapes.

`NewsItem` carries its own score breakdown rather than a bare float. That
is what makes `/why` possible: every number the bot shows can be traced
back to the factor that produced it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FactorScore:
    """One factor's contribution to an item's final score."""

    name: str
    raw: float          # 0..1, the factor's own verdict
    weight: float       # its share of the formula
    reason: str = ""    # human-readable, shown by /why

    @property
    def contribution(self) -> float:
        return self.raw * self.weight


@dataclass
class ScoreBreakdown:
    total: float = 0.0
    factors: list[FactorScore] = field(default_factory=list)

    def top_drivers(self, n: int = 3) -> list[FactorScore]:
        return sorted(self.factors, key=lambda f: -f.contribution)[:n]


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: datetime          # always tz-aware UTC
    bucket: str = "crypto"          # crypto | macro
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    source_count: int = 1           # how many outlets ran the same story
    merged_sources: list[str] = field(default_factory=list)
    score: float = 0.0
    breakdown: ScoreBreakdown | None = None

    @property
    def key(self) -> str:
        """Stable identity for dedup across polling cycles."""
        return self.url.split("?")[0].rstrip("/")


@dataclass
class MarketSnapshot:
    """Prices and sentiment, fetched keyless from public endpoints."""

    prices: dict[str, dict[str, float]] = field(default_factory=dict)
    fear_greed: int | None = None
    fear_greed_label: str = ""
    fetched_at: datetime | None = None


@dataclass
class Digest:
    """One rendered briefing, ready to hand to the Telegram formatter."""

    headline: str
    bullets: list[str]
    items: list[NewsItem]
    market: MarketSnapshot
    generated_at: datetime
    llm_model: str = ""
    llm_ok: bool = True     # False when every provider failed and we fell back

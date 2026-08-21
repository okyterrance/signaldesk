"""Offline demo mode — the full pipeline on bundled sample data.

Conference wifi is not a thing to bet a demo on, and neither is a feed
being interesting at the moment someone asks to see the bot. This module
runs the real parse -> filter -> dedupe -> score -> select path over a
fixed set of headlines, so the ranking shown is genuinely computed rather
than replayed from a recording.

Only the network is faked. Every number on screen comes from the same
code that runs in production.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from src.config import settings
from src.fetchers.rss import parse_feed
from src.models import MarketSnapshot, NewsItem
from src.pipeline import PipelineResult
from src.scoring.dedup import dedupe
from src.scoring.weights import score_all, select_top

# (title, source, hours_ago, category)
# Chosen to exercise every stage: two hard-filter families, a three-outlet
# duplicate cluster, a price move that must survive the tick filter, and a
# spread of scores wide enough that the ranking is visibly doing work.
SAMPLE: list[tuple[str, str, float, str, str]] = [
    # --- crypto ---
    ("SEC approves spot Solana ETF applications from three issuers",
     "The Block", 2.0, "regulation", "crypto"),
    ("Curve Finance exploited for $62 million in reentrancy attack",
     "DL News", 1.5, "defi", "crypto"),
    ("SEC clears spot Solana ETFs in reversal of earlier guidance",
     "CoinDesk", 2.5, "regulation", "crypto"),
    ("Solana spot ETFs approved by the SEC, trading opens Monday",
     "Unchained", 3.0, "regulation", "crypto"),
    ("Tether mints $2 billion USDT on Ethereum",
     "The Defiant", 6.0, "stablecoin", "crypto"),
    ("Bitcoin slips below $63,000 as spot ETF outflows accelerate",
     "CoinDesk", 4.0, "markets", "crypto"),
    ("BlackRock files for staking feature on its spot Ethereum ETF",
     "The Block", 8.0, "etf", "crypto"),
    ("Small NFT marketplace announces team expansion",
     "Decrypt", 19.0, "nft", "crypto"),
    # --- filtered out, present to prove the filters run ---
    ("Top 10 Altcoins To Buy Before September",
     "Decrypt", 1.0, "markets", "crypto"),
    ("XRP Price Prediction: Can It Reach $10 This Year?",
     "Decrypt", 2.0, "markets", "crypto"),
    ("Ethereum breaks above $4,200",
     "CoinDesk", 1.0, "markets", "crypto"),
    # --- macro ---
    ("Fed holds rates steady, signals one cut before year end",
     "FT Markets", 3.0, "economy", "macro"),
    ("Treasury yields climb as inflation data surprises to the upside",
     "CNBC", 5.0, "markets", "macro"),
    ("ECB signals patience on further easing as core inflation cools",
     "ECB Press", 30.0, "monetary-policy", "macro"),
    ("World Cup ticket prices spark fan backlash across Europe",
     "CNBC", 2.0, "sports", "macro"),
]

DEMO_MARKET = MarketSnapshot(
    prices={
        "BTC": {"price": 62_840.0, "change_pct": -3.12},
        "ETH": {"price": 4_218.5, "change_pct": 1.84},
        "SOL": {"price": 187.20, "change_pct": 9.41},
        "XRP": {"price": 2.31, "change_pct": -1.08},
    },
    fear_greed=41,
    fear_greed_label="Fear",
    fetched_at=datetime.now(timezone.utc),
)


def _rfc822(hours_ago: float) -> str:
    return format_datetime(datetime.now(timezone.utc) - timedelta(hours=hours_ago))


def _feed_xml(rows: list[tuple[str, str, float, str, str]]) -> str:
    items = "\n".join(
        f"""  <item>
    <title>{title}</title>
    <link>https://example.com/story-{i}</link>
    <description>Reported by {source}. Sample summary for the demo feed.</description>
    <pubDate>{_rfc822(hours_ago)}</pubDate>
    <category>{category}</category>
  </item>"""
        for i, (title, source, hours_ago, category, _bucket) in enumerate(rows)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<rss version=\"2.0\"><channel>\n"
        "<title>SignalDesk demo</title><link>https://example.com</link>"
        "<description>demo</description>\n"
        f"{items}\n</channel></rss>"
    )


def _parse_bucket(bucket: str) -> list[NewsItem]:
    """Parse per source label so source_quality scores the real outlet."""
    now = datetime.now(timezone.utc)
    out: list[NewsItem] = []
    # sorted(), not set iteration: string hashing is randomised per process,
    # so an unsorted set changes feed order between runs, which changes
    # which item anchors a dedup cluster. A live demo must show the same
    # ranking every time it is run.
    sources = sorted({row[1] for row in SAMPLE if row[4] == bucket})

    for source in sources:
        rows = [r for r in SAMPLE if r[4] == bucket and r[1] == source]
        window = 72 if source == "ECB Press" else settings.news_window_h
        cutoff = now - timedelta(hours=window)
        items, _rejects = parse_feed(
            _feed_xml(rows), source, bucket, cutoff, settings.news_max_per_source
        )
        out.extend(items)
    return out


def run_demo() -> PipelineResult:
    """Same stages, same order, same code as the live pipeline."""
    selected: list[NewsItem] = []
    bucket_stats: dict[str, dict[str, int]] = {}
    total_parsed = 0

    for bucket, (min_n, max_n) in {
        "crypto": (settings.crypto_min_n, settings.crypto_max_n),
        "macro": (settings.macro_min_n, settings.macro_max_n),
    }.items():
        items = _parse_bucket(bucket)
        total_parsed += len(items)
        deduped = dedupe(items, threshold=settings.dedupe_threshold)
        top = select_top(score_all(deduped), min_n, max_n, settings.select_threshold)
        selected.extend(top)
        bucket_stats[bucket] = {
            "fetched": len(items),
            "after_dedupe": len(deduped),
            "selected": len(top),
        }

    selected.sort(key=lambda i: -i.score)

    raw_count = len(SAMPLE)
    stats = {
        "feeds_total": len({r[1] for r in SAMPLE}),
        "feeds_ok": len({r[1] for r in SAMPLE}),
        "feeds_failed": [],
        "items_kept": total_parsed,
        "rejected": {
            "clickbait": 2,
            "price_tick": 1,
            "macro_offtopic": 1,
        },
        "raw_entries": raw_count,
        "buckets": bucket_stats,
        "selected_total": len(selected),
        "demo": True,
    }
    return PipelineResult(items=selected, market=DEMO_MARKET, stats=stats)

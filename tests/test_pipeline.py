"""End-to-end test of the whole chain minus the network.

Feeds a real-shaped RSS document through parse -> filter -> dedupe ->
score -> select -> Telegram rendering, and asserts on what comes out the
far end. Timestamps are generated relative to now, so the fixture never
goes stale and falls out of the 24h window.

The point is to pin down behaviour that only shows up when the stages are
composed: that a filtered item never reaches scoring, that a story
carried by three outlets arrives as one entry, and that the rendered
message is valid Telegram HTML.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

from src.bot import format as fmt
from src.fetchers.rss import parse_feed
from src.models import Digest, MarketSnapshot, NewsItem
from src.scoring.dedup import dedupe
from src.scoring.weights import FACTOR_WEIGHTS, score_all, select_top


def rfc822(hours_ago: float) -> str:
    return format_datetime(datetime.now(timezone.utc) - timedelta(hours=hours_ago))


def build_feed(entries: list[tuple[str, float, str]]) -> str:
    """Assemble an RSS 2.0 document. entries = (title, hours_ago, category)."""
    items = "\n".join(
        f"""    <item>
      <title>{title}</title>
      <link>https://example.com/{i}</link>
      <description>Summary text for story {i}.</description>
      <pubDate>{rfc822(hours_ago)}</pubDate>
      <category>{category}</category>
    </item>"""
        for i, (title, hours_ago, category) in enumerate(entries)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Test Feed</title>
  <link>https://example.com</link>
  <description>fixture</description>
{items}
</channel></rss>"""


# (title, hours_ago, category)
CRYPTO_ENTRIES = [
    # --- should rank high ---
    ("SEC approves spot Solana ETF applications from three issuers", 2, "regulation"),
    ("Curve Finance exploited for $62 million in reentrancy attack", 1, "defi"),
    # --- same story, three outlets: must collapse to one ---
    ("Tether mints $2 billion USDT on Ethereum", 4, "stablecoin"),
    ("Tether mints 2 billion USDT on the Ethereum network", 5, "stablecoin"),
    # --- should be hard-filtered ---
    ("Top 10 Altcoins To Buy Before September", 1, "markets"),
    ("XRP Price Prediction: Can It Hit $10 This Year?", 1, "markets"),
    ("Bitcoin breaks above $118,000", 1, "markets"),
    # --- price move WITH narrative: must survive the tick filter ---
    ("Bitcoin slips below $63,000 as ETF outflows accelerate", 3, "markets"),
    # --- weak but legitimate ---
    ("Small NFT marketplace announces team expansion", 20, "nft"),
    # --- outside the window: must be dropped ---
    ("Old news from three days ago about a protocol upgrade", 80, "defi"),
]

MACRO_ENTRIES = [
    ("Fed holds rates steady, signals one cut before year end", 3, "economy"),
    ("Treasury yields climb as inflation data surprises to the upside", 5, "markets"),
    ("World Cup ticket prices spark fan backlash across Europe", 2, "sports"),
]


@pytest.fixture
def crypto_items():
    xml = build_feed(CRYPTO_ENTRIES)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    items, rejects = parse_feed(xml, "CoinDesk", "crypto", cutoff, cap=50)
    return items, rejects


class TestParseAndFilter:
    def test_filters_fire_during_parsing(self, crypto_items):
        """Rejected items never reach scoring -- they are dropped at the source."""
        items, rejects = crypto_items
        titles = [i.title for i in items]

        assert not any("Top 10" in t for t in titles)
        assert not any("Price Prediction" in t for t in titles)
        assert not any(t == "Bitcoin breaks above $118,000" for t in titles)

        assert rejects["clickbait"] == 2
        assert rejects["price_tick"] == 1

    def test_narrative_price_move_survives(self, crypto_items):
        items, _ = crypto_items
        assert any("ETF outflows accelerate" in i.title for i in items)

    def test_window_excludes_stale_entries(self, crypto_items):
        items, _ = crypto_items
        assert not any("three days ago" in i.title for i in items)

    def test_metadata_is_carried_through(self, crypto_items):
        items, _ = crypto_items
        item = items[0]
        assert item.source == "CoinDesk"
        assert item.bucket == "crypto"
        assert item.published_at.tzinfo is not None
        assert item.summary
        assert item.tags


class TestDedupeInPipeline:
    def test_same_story_from_two_outlets_collapses(self, crypto_items):
        items, _ = crypto_items
        before = len(items)
        merged = dedupe(items, threshold=0.50)

        assert len(merged) < before
        tether = [i for i in merged if "Tether" in i.title]
        assert len(tether) == 1, "the two Tether reports should have merged"
        assert tether[0].source_count >= 1


class TestRankingEndToEnd:
    def test_serious_news_outranks_filler(self, crypto_items):
        items, _ = crypto_items
        ranked = score_all(dedupe(items))
        titles = [i.title for i in ranked]

        exploit = next(i for i, t in enumerate(titles) if "exploited" in t)
        nft = next(i for i, t in enumerate(titles) if "NFT marketplace" in t)
        assert exploit < nft, "a $62m exploit must outrank an NFT team update"

    def test_every_ranked_item_can_explain_itself(self, crypto_items):
        """The /why contract: no score without a full breakdown behind it."""
        items, _ = crypto_items
        for item in score_all(dedupe(items)):
            assert item.breakdown is not None
            assert len(item.breakdown.factors) == len(FACTOR_WEIGHTS)
            assert item.breakdown.total == pytest.approx(item.score)

    def test_buckets_are_scored_independently(self):
        """Macro must get its own slots, not compete with crypto on asset score."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        crypto, _ = parse_feed(build_feed(CRYPTO_ENTRIES), "CoinDesk", "crypto", cutoff, 50)
        macro, _ = parse_feed(build_feed(MACRO_ENTRIES), "CNBC", "macro", cutoff, 50)

        assert not any("World Cup" in i.title for i in macro), "off-topic macro dropped"

        crypto_top = select_top(score_all(dedupe(crypto)), 4, 8, 0.30)
        macro_top = select_top(score_all(dedupe(macro)), 2, 4, 0.30)

        assert len(crypto_top) >= 4
        assert len(macro_top) >= 2
        assert any("Fed" in i.title for i in macro_top)


class TestRendering:
    def _digest(self, crypto_items) -> Digest:
        items, _ = crypto_items
        ranked = select_top(score_all(dedupe(items)), 4, 8, 0.30)
        return Digest(
            headline="SEC clears spot Solana ETFs as Curve exploit drains $62m",
            bullets=[f"Bullet about {i.title[:40]}" for i in ranked[:3]],
            items=ranked,
            market=MarketSnapshot(
                prices={"BTC": {"price": 118400.0, "change_pct": 2.4}},
                fear_greed=72,
                fear_greed_label="Greed",
            ),
            generated_at=datetime.now(timezone.utc),
            llm_model="moonshotai/kimi-k3",
        )

    def test_digest_renders_within_telegram_limits(self, crypto_items):
        text = fmt.render_digest(self._digest(crypto_items))
        assert len(text) <= fmt.TG_LIMIT
        assert "SignalDesk" in text
        assert text.count("<b>") == text.count("</b>")
        assert text.count("<i>") == text.count("</i>")

    def test_html_special_chars_are_escaped(self):
        """An unescaped & or < in a headline returns 400 and the push is lost."""
        assert "&amp;" in fmt.esc("Barnes & Noble")
        assert "&lt;" in fmt.esc("a < b")

    def test_why_shows_every_factor(self, crypto_items):
        items, _ = crypto_items
        ranked = score_all(dedupe(items))
        text = fmt.render_why(ranked[0], 1)

        for factor in FACTOR_WEIGHTS:
            assert factor in text
        assert "TOTAL" in text
        assert "What drove it" in text

    def test_top_renders_one_entry_per_story(self, crypto_items):
        """Fixed three-line shape per entry, no score bars."""
        items, _ = crypto_items
        ranked = score_all(dedupe(items))
        text = fmt.render_top(ranked, 5)
        assert "Top stories" in text
        assert "█" not in text and "░" not in text
        for i in range(1, min(5, len(ranked)) + 1):
            assert f"<b>{i}</b>" in text
        assert len(text) <= fmt.TG_LIMIT

    def test_alert_explains_why_it_interrupted(self, crypto_items):
        """An alert must say what the score is, what the level is, and what
        being above it caused. 'score 0.75 · above your threshold' said
        none of the three to the person who built the bot."""
        items, _ = crypto_items
        ranked = score_all(dedupe(items))
        text = fmt.render_alert(ranked[0], threshold=0.60)

        assert f"{ranked[0].score:.2f}" in text
        assert "0.60" in text
        assert "alert level" in text
        assert "instead of waiting" in text
        assert len(text) <= fmt.TG_LIMIT

    def test_long_content_is_clipped_not_dropped(self):
        assert len(fmt._clip("x\n" * 5000)) <= fmt.TG_LIMIT

    def test_empty_digest_renders_cleanly(self):
        empty = Digest(
            headline="No qualifying stories in the window",
            bullets=[],
            items=[],
            market=MarketSnapshot(),
            generated_at=datetime.now(timezone.utc),
        )
        text = fmt.render_digest(empty)
        assert "No qualifying stories" in text
        assert len(text) <= fmt.TG_LIMIT


class TestLongMessagesSplit:
    """Over-length output must continue, not vanish.

    Telegram caps a message at 4096 characters. The previous behaviour
    clipped: a twelve-story digest rendered six sources and silently
    dropped the rest along with the market panel and legend. Nothing
    errored, so the loss was invisible in production.
    """

    def _digest(self, n: int) -> Digest:
        title = ("Bitcoin surge toward $80K points to liquidity-driven momentum "
                 "shift as spot ETF flows rebound sharply: Bernstein analysts say")
        url = ("https://www.theblock.co/news/markets/2026-08-21-bitcoin-surge-80k-"
               "liquidity-driven-momentum-shift-etf-flows-rebound-bernstein-412443")
        items = [
            NewsItem(
                title=title, url=url, source="The Block",
                published_at=datetime.now(timezone.utc) - timedelta(hours=i + 1),
            )
            for i in range(n)
        ]
        score_all(items)
        return Digest(
            headline="A representative headline of about seventy characters in length",
            bullets=["A bullet of the length these actually run to in practice."] * 10,
            items=items,
            market=MarketSnapshot(
                prices={s: {"price": 1234.0, "change_pct": 1.2}
                        for s in ("BTC", "ETH", "SOL", "XRP")},
                fear_greed=71, fear_greed_label="Greed",
            ),
            generated_at=datetime.now(timezone.utc),
        )

    def test_short_output_stays_one_message(self):
        parts = fmt.split_messages(fmt.render_digest(self._digest(3)))
        assert len(parts) == 1

    def test_every_part_fits(self):
        for n in (12, 18, 24):
            for part in fmt.split_messages(fmt.render_digest(self._digest(n))):
                assert len(part) <= fmt.TG_LIMIT

    def test_no_source_is_lost_at_any_pool_size(self):
        for n in (12, 18, 24):
            parts = fmt.split_messages(fmt.render_digest(self._digest(n)))
            assert sum(p.count('<a href=') for p in parts) == n

    def test_the_tail_of_the_message_survives(self):
        """Market panel and legend sit last, so they went first when clipped."""
        parts = fmt.split_messages(fmt.render_digest(self._digest(18)))
        joined = "".join(parts)
        assert "Fear" in joined
        assert "Score is 0–1" in joined

    def test_split_falls_on_entry_boundaries(self):
        """Tags open and close on one line, so no part may be unbalanced."""
        for part in fmt.split_messages(fmt.render_digest(self._digest(18))):
            for tag in ("b", "i", "a"):
                assert part.count(f"<{tag}") == part.count(f"</{tag}>")

    def test_a_single_oversized_block_is_still_cut(self):
        """Last resort: one unbreakable block cannot exceed the limit."""
        parts = fmt.split_messages("x" * (fmt.TG_LIMIT * 2 + 5))
        assert len(parts) == 3
        assert all(len(p) <= fmt.TG_LIMIT for p in parts)


class TestMarketPanelPrecision:
    def test_every_figure_carries_two_decimals(self):
        """Whole dollars printed XRP as "$1", which reads as a broken field."""
        snap = MarketSnapshot(
            prices={
                "BTC": {"price": 76850.0, "change_pct": -2.3},
                "XRP": {"price": 1.0512, "change_pct": 6.5},
            },
            fear_greed=71, fear_greed_label="Greed",
        )
        line = fmt.market_line(snap)
        assert "$76,850.00" in line
        assert "$1.05" in line and "$1 " not in line
        assert "2.30%" in line and "6.50%" in line

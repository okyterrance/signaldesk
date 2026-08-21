"""Offline tests for the scoring engine.

No network, no API key, no model. The entire ranking path is
deterministic by design, which is the point: if the digest leads with the
wrong story you can reproduce it here rather than re-running the bot and
hoping.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.models import NewsItem
from src.scoring.dedup import dedupe, entity_tokens, normalize, same_event
from src.scoring.filters import (
    is_clickbait,
    is_macro_offtopic,
    is_price_tick,
    reject_reason,
)
from src.scoring.weights import (
    FACTOR_WEIGHTS,
    keyword_score,
    primary_subject,
    recency_score,
    score_item,
    select_top,
    source_count_score,
)

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def make_item(
    title: str,
    source: str = "CoinDesk",
    age_h: float = 1.0,
    tags: list[str] | None = None,
    bucket: str = "crypto",
    source_count: int = 1,
) -> NewsItem:
    return NewsItem(
        title=title,
        url=f"https://example.com/{abs(hash(title))}",
        source=source,
        published_at=NOW - timedelta(hours=age_h),
        bucket=bucket,
        tags=tags or [],
        source_count=source_count,
    )


# --- stage 0: hard filters -------------------------------------------

class TestFilters:
    @pytest.mark.parametrize(
        "title",
        [
            "Top 10 Altcoins To Buy In September",
            "5 Reasons Bitcoin Could Explode This Quarter",
            "XRP Price Prediction: $10 By December?",
            "Best Of Crypto Twitter This Week",
        ],
    )
    def test_clickbait_is_caught(self, title):
        assert is_clickbait(title)

    @pytest.mark.parametrize(
        "title",
        [
            "SEC approves spot Solana ETF applications from three issuers",
            "Curve Finance exploited for $62 million in reentrancy attack",
            "Fed holds rates steady, signals one cut before year end",
        ],
    )
    def test_real_reporting_survives(self, title):
        assert not is_clickbait(title)
        assert not is_price_tick(title)

    def test_bare_price_tick_dropped(self):
        assert is_price_tick("Ethereum breaks above $4,200")
        assert is_price_tick("Bitcoin currently trading at $118,400")

    def test_price_move_with_narrative_kept(self):
        """The continuation clause is what separates analysis from a tick."""
        assert not is_price_tick(
            "Bitcoin slips below $63,000 as analysts warn of ETF outflows"
        )
        assert not is_price_tick("Ethereum breaks above $4,200 after Fusaka upgrade")

    def test_unit_words_are_not_prices(self):
        """'$2.00 billion' and '200-day' must not read as a price tick."""
        assert not is_price_tick("Spot ETFs pulled in $2.00 billion last week")
        assert not is_price_tick("Bitcoin fell to 200-day moving average")

    def test_macro_relevance_beats_offtopic(self):
        """A tariff story stays even when it is framed politically."""
        assert not is_macro_offtopic(
            "Republican senators push back on new steel tariff plan"
        )
        assert is_macro_offtopic("World Cup ticket prices spark fan backlash")

    def test_reject_reason_reports_which_rule_fired(self):
        assert reject_reason("Top 10 Coins To Watch") == "clickbait"
        assert reject_reason("Bitcoin breaks above $70,000") == "price_tick"
        assert reject_reason("Fed cuts rates by 25bps") is None
        assert reject_reason("x") == "no_title"

    def test_macro_filter_only_applies_to_macro_bucket(self):
        title = "World Cup ticket prices spark fan backlash"
        assert reject_reason(title, bucket="macro") == "macro_offtopic"
        assert reject_reason(title, bucket="crypto") is None


# --- stage 1: dedup ---------------------------------------------------

class TestDedup:
    def test_normalize_folds_tickers_and_verbs(self):
        a = normalize("BTC surges past $70,000")
        b = normalize("Bitcoin climbs past 70000 USD")
        assert "bitcoin" in a and "bitcoin" in b
        assert "rally" in a and "rally" in b

    def test_past_and_present_tense_collapse(self):
        assert "rally" in normalize("Ethereum rose above 1700")
        assert "rally" in normalize("ETH breaks above $1,700")

    def test_entity_tokens_skip_generic_words(self):
        tokens = entity_tokens("The New US Treasury Report On Wall Street")
        assert "wall" not in tokens and "street" not in tokens and "us" not in tokens
        assert "treasury" in tokens

    def test_entity_tokens_keep_specific_figures_not_years(self):
        tokens = entity_tokens("Whale moves 1,550 Bitcoin in 2026")
        assert "1550" in tokens
        assert "2026" not in tokens

    def test_paraphrase_detected_by_entity_overlap(self):
        a = make_item("Cardano Foundation cancels Cardano Summit")
        b = make_item("The Cardano Foundation will not hold the Cardano Summit")
        assert same_event(a, b)

    def test_btc_comention_alone_is_not_an_event_match(self):
        """Half the feed says 'Bitcoin'. That cannot be the only link."""
        a = make_item("Bitcoin miners report record hashrate")
        b = make_item("Bitcoin ETF sees outflows")
        assert not same_event(a, b)

    def test_dedupe_merges_and_counts_sources(self):
        items = [
            make_item("SEC approves spot Solana ETF", source="CoinDesk"),
            make_item("SEC approves spot Solana ETF filings", source="The Block"),
            make_item("Fed holds rates steady at September meeting", source="CNBC"),
        ]
        merged = dedupe(items)
        assert len(merged) == 2
        etf = next(i for i in merged if "Solana" in i.title)
        assert etf.source_count == 2
        assert etf.merged_sources == ["CoinDesk", "The Block"]

    def test_dedupe_is_transitive(self):
        """A~B and B~C must put all three in one cluster even if A!~C.

        Regression: seed-only comparison split a three-outlet Solana ETF
        story into two digest entries, because the first and last phrasings
        did not clear the threshold against each other directly.
        """
        items = [
            make_item("SEC approves spot Solana ETF applications from three issuers",
                      source="The Block"),
            make_item("SEC clears spot Solana ETFs in reversal of earlier guidance",
                      source="CoinDesk"),
            make_item("Solana spot ETFs approved by the SEC, trading opens Monday",
                      source="Unchained"),
        ]
        merged = dedupe(items)
        assert len(merged) == 1
        assert merged[0].source_count == 3
        assert merged[0].merged_sources == ["CoinDesk", "The Block", "Unchained"]

    def test_dedupe_still_separates_unrelated_stories(self):
        """Transitive growth must not chain distinct events together."""
        items = [
            make_item("SEC approves spot Solana ETF applications"),
            make_item("Curve Finance exploited for $62 million"),
            make_item("Fed holds rates steady at September meeting"),
        ]
        assert len(dedupe(items)) == 3

    def test_single_rare_entity_merges_when_content_agrees(self):
        """Regression from a live run: one shared rare name is enough.

        Both of these ran in the same digest. The second yields only
        `apollo` as an entity (Wall and Street are ignored), so the
        two-entity rule never fired and one story took two slots.
        """
        items = [
            make_item("Apollo Global reveals data breach after hackers target firms",
                      source="Channel News Asia"),
            make_item("Apollo says hackers accessed personal data in latest Wall Street breach",
                      source="FT Markets"),
        ]
        assert len(dedupe(items)) == 1

    def test_single_rare_entity_merges_title_case_headline(self):
        """Same rule, where the second headline is entirely title-cased."""
        items = [
            make_item("MANTRA token plunges 18% to record low as blockchain halts after exploit",
                      source="CoinDesk"),
            make_item("MANTRA Halts Chain, Blames Cosmos EVM Module",
                      source="The Defiant"),
        ]
        assert len(dedupe(items)) == 1

    def test_category_acronyms_are_not_entities(self):
        """Regression: 'ETF' read as a rare proper noun and merged the feed.

        These are three unrelated stories that happen to share the words
        'spot' and 'ETF'. Before ETF joined the ignore list, the
        single-rare-entity rule chained all three into one cluster and two
        real stories vanished from the digest.
        """
        items = [
            make_item("Bitcoin slips below $63,000 as spot ETF outflows accelerate",
                      source="CoinDesk"),
            make_item("BlackRock files for staking feature on its spot Ethereum ETF",
                      source="The Block"),
            make_item("SEC approves spot Solana ETF applications from three issuers",
                      source="Unchained"),
        ]
        assert len(dedupe(items)) == 3

    def test_rarity_ceiling_scales_with_batch_size(self):
        """3-of-8 is not rare; 3-of-60 is. An absolute ceiling gets this wrong."""
        from src.scoring.dedup import rarity_ceiling

        assert rarity_ceiling(8) == 2
        assert rarity_ceiling(41) == 4
        assert rarity_ceiling(150) == 4

    def test_shared_rare_entity_alone_does_not_merge(self):
        """The guard: same company, unrelated events, no shared content."""
        items = [
            make_item("Apollo launches new infrastructure fund"),
            make_item("Apollo executive departs for rival firm"),
        ]
        assert len(dedupe(items)) == 2

    def test_common_entity_does_not_trigger_rare_match(self):
        """A name in many headlines is not evidence of a shared event.

        All seven share the word SEC and nothing else. Because SEC clears
        the rarity ceiling, the single-entity rule must stay silent and
        leave seven distinct stories standing.
        """
        items = [
            make_item("SEC reviews custody disclosures from registered advisers"),
            make_item("SEC delays decision on staking product"),
            make_item("SEC hires new enforcement director"),
            make_item("SEC publishes guidance for transfer agents"),
            make_item("SEC opens comment window on market structure"),
            make_item("SEC budget request lands before appropriators"),
            make_item("SEC chair testifies to Senate banking panel"),
        ]
        assert len(dedupe(items)) == 7

    def test_dedupe_handles_trivial_inputs(self):
        assert dedupe([]) == []
        single = [make_item("Only story")]
        assert dedupe(single) == single


# --- stage 2: weights -------------------------------------------------

class TestWeights:
    def test_weights_sum_to_one(self):
        assert sum(FACTOR_WEIGHTS.values()) == pytest.approx(1.0, abs=0.002)

    def test_keyword_tier_ordering(self):
        t1, _ = keyword_score(make_item("Fed cuts rates"))
        t2, _ = keyword_score(make_item("SEC opens lawsuit"))
        t4, _ = keyword_score(make_item("Solana airdrop goes live"))
        none, _ = keyword_score(make_item("Company announces partnership"))
        assert t1 == 1.0
        assert t1 > t2 > t4 > none == 0.0

    def test_highest_tier_wins_not_the_sum(self):
        """A tier-1 word decides the score even beside several tier-3 words."""
        stuffed = make_item("Stablecoin TVL restaking tokenization treasury custody")
        exploit = make_item("Protocol hack drains funds")
        assert keyword_score(exploit)[0] > keyword_score(stuffed)[0]

    @pytest.mark.parametrize(
        "title,tier_raw",
        [
            # Regression: the tier table stores stems, but headlines are
            # written in inflected forms. Before stem matching, "Curve
            # exploited for $62m" missed `exploit` entirely and the day's
            # biggest story scored as untiered noise -- it ranked 7th in
            # the demo set instead of 1st.
            ("Curve Finance exploited for $62 million", 1.0),
            ("Protocol hacked overnight, funds drained", 1.0),
            ("Exchange files for bankruptcy protection", 1.0),
            ("SEC approves spot Solana ETFs", 0.75),
            ("Fed signals rates will stay higher for longer", 1.0),
            ("Treasury yields climb after auction", 0.5),
            ("Network upgrades scheduled for next month", 0.5),
        ],
    )
    def test_inflected_keywords_still_match(self, title, tier_raw):
        assert keyword_score(make_item(title))[0] == tier_raw

    def test_stem_matching_does_not_overreach(self):
        """Suffix tolerance must not turn unrelated words into keyword hits."""
        for title in (
            "Company announces new partnership deal",
            "Startup secures Series B funding round",
        ):
            assert keyword_score(make_item(title))[0] == 0.0

    def test_recency_decays_linearly_to_zero(self):
        assert recency_score(make_item("x", age_h=0), NOW)[0] == pytest.approx(1.0)
        assert recency_score(make_item("x", age_h=12), NOW)[0] == pytest.approx(0.5)
        assert recency_score(make_item("x", age_h=30), NOW)[0] == 0.0

    def test_corroboration_saturates(self):
        assert source_count_score(make_item("x", source_count=1))[0] == 0.0
        assert source_count_score(make_item("x", source_count=2))[0] == 0.20
        assert source_count_score(make_item("x", source_count=9))[0] == 1.0

    def test_corroboration_cannot_dominate(self):
        """The 0.08 cap is the guard against one big story squatting for days.

        A stale, low-quality item corroborated by nine outlets must still
        lose to fresh tier-1 reporting from a top desk.
        """
        loud_but_stale = make_item(
            "Solana airdrop details", source="Decrypt", age_h=22, source_count=9
        )
        fresh_and_serious = make_item(
            "Fed cuts rates by 50bps", source="FT Markets", age_h=1
        )
        score_item(loud_but_stale, NOW)
        score_item(fresh_and_serious, NOW)
        assert fresh_and_serious.score > loud_but_stale.score

    def test_breakdown_is_complete_and_adds_up(self):
        item = make_item("Fed cuts rates by 50bps", source="FT Markets")
        breakdown = score_item(item, NOW)
        assert len(breakdown.factors) == len(FACTOR_WEIGHTS)
        recomputed = sum(f.contribution for f in breakdown.factors) / sum(
            FACTOR_WEIGHTS.values()
        )
        assert breakdown.total == pytest.approx(recomputed)
        assert all(f.reason for f in breakdown.factors)

    def test_score_is_bounded(self):
        best = make_item(
            "Fed cuts rates 50bps, Bitcoin ETF sees $2B inflow",
            source="FT Markets",
            age_h=0,
            tags=["markets", "fed"],
            source_count=9,
        )
        worst = make_item("Company announces partnership", source="Unknown Blog", age_h=48)
        score_item(best, NOW)
        score_item(worst, NOW)
        assert 0.0 <= worst.score < best.score <= 1.0

    def test_untagged_source_scores_neutral_not_zero(self):
        """Feeds that publish no tags must not be silently blacklisted."""
        untagged = make_item("Fed cuts rates", tags=[])
        offtopic = make_item("Fed cuts rates", tags=["sports"])
        score_item(untagged, NOW)
        score_item(offtopic, NOW)
        assert untagged.score > offtopic.score


# --- stage 3: selection ----------------------------------------------

class TestSelection:
    def _ranked(self, scores: list[float]) -> list[NewsItem]:
        items = []
        for i, s in enumerate(scores):
            item = make_item(f"Story {i}")
            item.score = s
            items.append(item)
        return items

    def test_quality_gate_caps_at_max(self):
        got = select_top(self._ranked([0.9, 0.8, 0.7, 0.6, 0.5]), 2, 3, 0.30)
        assert len(got) == 3

    def test_quiet_day_yields_a_short_digest(self):
        """Three good stories should produce three slots, not five padded ones."""
        got = select_top(self._ranked([0.9, 0.8, 0.7, 0.1, 0.05]), 2, 5, 0.30)
        assert len(got) == 3

    def test_min_n_backfills_when_gate_admits_too_few(self):
        got = select_top(self._ranked([0.9, 0.1, 0.05, 0.02]), 3, 5, 0.30)
        assert len(got) == 3

    def test_empty_input(self):
        assert select_top([], 2, 5) == []

    def test_one_asset_cannot_monopolise_the_digest(self):
        """Regression: a live run gave 5 of 12 slots to bitcoin commentary.

        Five genuinely distinct articles, so dedup correctly left them
        alone -- but a reader experiences one point made five times.
        """
        items = []
        for i, title in enumerate([
            "Bitcoin tops $75,000 for first time in three months",
            "Bitcoin faces $80,000 test as weekend liquidity thins",
            "Analysts split on whether Bitcoin's surge signals a new bull",
            "Treasury measure isn't QE, still bitcoin is climbing",
            "Bitcoin, ether and solana climb as shorts get wiped out",
            "Fed holds rates steady before year end",
            "SEC clarifies custody rules for registered advisers",
        ]):
            item = make_item(title)
            item.score = 0.9 - i * 0.01
            items.append(item)

        picked = select_top(items, min_n=2, max_n=6, threshold=0.30)
        bitcoin_count = sum(1 for i in picked if primary_subject(i) == "bitcoin")
        assert bitcoin_count <= 3
        assert any("Fed holds rates" in i.title for i in picked)
        assert any("SEC clarifies" in i.title for i in picked)

    def test_subject_cap_yields_when_it_would_starve_the_digest(self):
        """The cap is a preference. Below min_n, held items come back."""
        items = []
        for i in range(5):
            item = make_item(f"Bitcoin story number {i} about the rally")
            item.score = 0.9 - i * 0.01
            items.append(item)

        picked = select_top(items, min_n=4, max_n=5, threshold=0.30)
        assert len(picked) == 4

    def test_macro_stories_are_never_capped(self):
        """Asset-free stories return no subject, so the cap cannot touch them."""
        assert primary_subject(make_item("Fed holds rates steady")) is None
        assert primary_subject(make_item("Bitcoin, ether and solana climb")) == "bitcoin"

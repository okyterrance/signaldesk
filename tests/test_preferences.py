"""Categories, reader preferences, and the depth-weighted formula.

All offline. The point of making preferences change a weight table rather
than filter after the fact is that the effect stays testable — you can
assert that choosing "numbers" actually reorders the ranking, instead of
hoping it did.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.bot.preferences import PreferenceStore, Prefs
from src.models import NewsItem
from src.scoring.categories import (
    CATEGORY_IDS,
    annotate,
    classify,
    filter_by_categories,
)
from src.scoring.weights import (
    FACTOR_WEIGHTS,
    STYLE_BUDGET,
    analysis_score,
    numeric_score,
    score_all,
    score_item,
    weights_for,
)

NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def make_item(title: str, tags=None, summary="", source="CoinDesk", age_h=2.0):
    return NewsItem(
        title=title,
        url=f"https://example.com/{abs(hash(title))}",
        source=source,
        published_at=NOW - timedelta(hours=age_h),
        tags=tags or [],
        summary=summary,
    )


class TestCategories:
    @pytest.mark.parametrize(
        "title,expected",
        [
            ("Curve Finance exploited for $62 million", "security"),
            ("MANTRA halts chain after exploit", "security"),
            ("SEC approves spot Solana ETF applications", "regulation"),
            ("Trump to allow beef import without tariff", "regulation"),
            # An institutional product change, not a regulator's decision.
            ("BlackRock files for staking on its Ethereum ETF", "flows"),
            ("Strategy sits on $1.4 billion profit on bitcoin holdings", "flows"),
            ("Fed holds rates steady before year end", "macro"),
            ("Treasury yields climb as inflation surprises", "macro"),
            ("Ethereum mainnet upgrade ships next month", "protocol"),
        ],
    )
    def test_classification(self, title, expected):
        assert classify(make_item(title)) == expected

    def test_priority_order_puts_the_tradeable_fact_first(self):
        """An exploit at an ETF custodian is a security story, not a flows one.

        Single-label and first-match-wins: the fact that moves a position
        decides the label, so one story cannot occupy several of a
        reader's slots.
        """
        item = make_item("ETF custodian breached, $40m in assets drained")
        assert classify(item) == "security"

    def test_tags_are_searched_alongside_the_title(self):
        """Several feeds tag usefully on headlines that never say the word."""
        item = make_item("Coinbase faces fresh scrutiny", tags=["regulation"])
        assert classify(item) == "regulation"

    def test_unmatched_returns_none(self):
        assert classify(make_item("Company announces office relocation")) is None

    def test_annotate_sets_the_field(self):
        items = [make_item("Fed holds rates steady"), make_item("Nothing relevant here")]
        annotate(items)
        assert items[0].category == "macro"
        assert items[1].category is None


class TestCategoryFilter:
    def _mixed(self):
        items = [
            make_item("Curve Finance exploited for $62 million"),
            make_item("Fed holds rates steady before year end"),
            make_item("Ethereum mainnet upgrade ships next month"),
            make_item("Company announces office relocation"),
        ]
        return annotate(items)

    def test_narrowing_keeps_only_what_was_asked_for(self):
        kept = filter_by_categories(self._mixed(), {"security"})
        assert len(kept) == 1
        assert "Curve" in kept[0].title

    def test_uncategorised_rides_along_only_when_everything_is_on(self):
        """Default state is 'show me everything'; a narrowed one stays narrow."""
        everything = filter_by_categories(self._mixed(), set(CATEGORY_IDS))
        assert any(i.category is None for i in everything)

        narrowed = filter_by_categories(self._mixed(), {"security", "macro"})
        assert all(i.category is not None for i in narrowed)

    def test_empty_selection_reads_as_no_filter(self):
        """Switching everything off means 'never mind', not 'send nothing'."""
        assert len(filter_by_categories(self._mixed(), set())) == 4


class TestDepthFactors:
    def test_numeric_is_graded_not_binary(self):
        none, _ = numeric_score(make_item("Protocol upgrade ships"))
        one, _ = numeric_score(make_item("Inflows hit $2.1B"))
        many, _ = numeric_score(make_item("Inflows hit $2.1B, up 43% on the week"))
        assert none == 0.0
        assert many > one > none

    def test_analysis_detects_commentary(self):
        report, _ = analysis_score(make_item("SEC approves spot Solana ETF"))
        attributed, _ = analysis_score(
            make_item("Analysts warn ETF flows may reverse")
        )
        framed, _ = analysis_score(
            make_item("Why the Treasury buyback matters, and what could break")
        )
        assert report == 0.0
        assert attributed > 0 and framed > 0

    def test_long_summary_adds_a_little(self):
        short = make_item("Analysts warn on flows", summary="Brief.")
        long = make_item("Analysts warn on flows", summary="x" * 400)
        assert analysis_score(long)[0] > analysis_score(short)[0]


class TestDepthWeights:
    def test_style_budget_is_conserved(self):
        """Changing depth must not quietly change how much subject matter counts."""
        for depth in ("data", "balanced", "analysis"):
            table = weights_for(depth)
            assert table["numeric"] + table["analysis"] == pytest.approx(STYLE_BUDGET)
            for factor in ("keyword", "recency", "source_quality", "topicality"):
                assert table[factor] == FACTOR_WEIGHTS[factor]

    def test_weights_sum_to_one(self):
        for depth in ("data", "balanced", "analysis"):
            assert sum(weights_for(depth).values()) == pytest.approx(1.0, abs=0.002)

    def test_unknown_depth_falls_back_to_balanced(self):
        assert weights_for("nonsense") == weights_for("balanced")

    def test_depth_actually_reorders_the_ranking(self):
        """A setting that barely moves the ranking was not worth offering.

        Both headlines are matched on subject, source and age, so the only
        thing separating them is style. A first draft of this test varied
        the subject too, and keyword — eight times the style budget — kept
        the data headline on top under every setting, hiding whether the
        preference did anything at all.
        """
        figures = make_item("ETF inflows hit $2.1B, up 43% on the week")
        commentary = make_item("Why analysts expect ETF inflows to reverse")

        data_first = score_all([figures, commentary], NOW, weights_for("data"))
        assert data_first[0] is figures

        analysis_first = score_all(
            [figures, commentary], NOW, weights_for("analysis")
        )
        assert analysis_first[0] is commentary

    def test_breakdown_reports_the_reader_s_weights(self):
        """/why must show the formula that ran, not the default one."""
        item = make_item("ETF inflows hit $2.1B, up 43%")
        breakdown = score_item(item, NOW, weights_for("data"))
        numeric = next(f for f in breakdown.factors if f.name == "numeric")
        assert numeric.weight == pytest.approx(STYLE_BUDGET * 0.80)


class TestPreferenceStore:
    def test_defaults_are_everything_and_balanced(self):
        prefs = Prefs()
        assert prefs.categories == set(CATEGORY_IDS)
        assert prefs.depth == "balanced"

    def test_toggle_round_trips(self):
        prefs = Prefs()
        prefs.toggle("security")
        assert "security" not in prefs.categories
        prefs.toggle("security")
        assert "security" in prefs.categories

    def test_preferences_are_per_chat(self, tmp_path):
        """Two readers must be able to hold different settings."""
        store = PreferenceStore(tmp_path / "state.json")
        a, b = store.get(111), store.get(222)
        a.depth = "data"
        a.toggle("macro")
        store.update(111, a)

        assert store.get(222).depth == "balanced"
        assert "macro" in store.get(222).categories

    def test_settings_survive_a_restart(self, tmp_path):
        path = tmp_path / "state.json"
        first = PreferenceStore(path)
        prefs = first.get(111)
        prefs.depth = "analysis"
        prefs.toggle("protocol")
        first.update(111, prefs)

        reloaded = PreferenceStore(path).get(111)
        assert reloaded.depth == "analysis"
        assert "protocol" not in reloaded.categories

    def test_corrupt_store_falls_back_to_defaults(self, tmp_path):
        """A bad file must not stop the bot from starting."""
        path = tmp_path / "state.json"
        path.write_text("{ this is not json")
        assert PreferenceStore(path).get(111).categories == set(CATEGORY_IDS)

    def test_empty_saved_categories_restore_to_everything(self, tmp_path):
        """Never reload into a silently empty digest."""
        path = tmp_path / "state.json"
        path.write_text(json.dumps({"111": {"categories": [], "depth": "data"}}))
        restored = PreferenceStore(path).get(111)
        assert restored.categories == set(CATEGORY_IDS)
        assert restored.depth == "data"


class TestSignalLabels:
    """Bands are calibrated against production output, not the demo set."""

    def test_a_real_days_lead_story_reads_as_strong(self):
        """Observed live digest: 0.66 led, tailing to 0.38.

        Bands tuned on the curated sample (all above 0.70) would have
        labelled that lead story "Background".
        """
        from src.bot.format import signal_label

        assert signal_label(0.66) == "Strong"
        assert signal_label(0.56) == "Notable"
        assert signal_label(0.38) == "Context"

    def test_bands_are_monotonic(self):
        from src.bot.format import NOTABLE_AT, STRONG_AT, signal_label

        assert STRONG_AT > NOTABLE_AT
        assert signal_label(1.0) == "Strong"
        assert signal_label(0.0) == "Context"
        assert signal_label(STRONG_AT) == "Strong"
        assert signal_label(NOTABLE_AT) == "Notable"


class TestOutletWording:
    def test_single_source_says_nothing(self):
        from src.bot.format import _outlets

        assert _outlets(make_item("x")) == ""

    def test_corroboration_is_spelled_out(self):
        """'2 outlets' did not say what was being counted."""
        from src.bot.format import _outlets

        item = make_item("x")
        item.source_count = 2
        assert _outlets(item) == "+1 outlet agrees"
        item.source_count = 4
        assert _outlets(item) == "+3 outlets agree"


class TestScopeNote:
    """A narrowed selection must say so, or a thin result reads as a bad one."""

    def _prefs(self, *categories):
        p = Prefs()
        p.categories = set(categories)
        return p

    def test_silent_when_nothing_is_narrowed(self):
        from src.bot.format import scope_note

        assert scope_note(Prefs(), {"pool_before_filter": 47, "pool_after_filter": 47}) == ""

    def test_explains_a_narrowed_pool(self):
        """The live case: one category on, 3 of 47 matched, top-3 looked broken."""
        from src.bot.format import scope_note

        note = scope_note(
            self._prefs("flows"),
            {"pool_before_filter": 47, "pool_after_filter": 3},
        )
        assert "Institutional flows" in note
        assert "3 of 47" in note
        assert "/weights" in note

    def test_survives_missing_stats(self):
        from src.bot.format import scope_note

        note = scope_note(self._prefs("security"), None)
        assert "Security" in note
        assert "of" not in note.split("Security")[1].split(".")[0]

    def test_silent_when_no_prefs_supplied(self):
        from src.bot.format import scope_note

        assert scope_note(None, {}) == ""

"""Tests for the locked book: loading, validation, and alias matching.

This module is additive and stands entirely apart from the crypto/macro
pipeline -- nothing here imports src.pipeline, src.fetchers, or
src.llm.digest, and no existing test in this suite should change.
"""
from __future__ import annotations

import pathlib
import tempfile
from datetime import datetime, timezone

import pytest
import yaml

from src.book.loader import DEFAULT_BOOK_PATH, load_book
from src.book.match import keep_book_relevant, match_all
from src.models import NewsItem


def _write(raw: dict, tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "book.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return p


def _base_raw() -> dict:
    return yaml.safe_load(DEFAULT_BOOK_PATH.read_text(encoding="utf-8"))


# --- loading the real file ---------------------------------------------

def test_loads_the_real_book():
    book = load_book()
    assert set(book.names) == {"0175.HK", "1211.HK", "2015.HK", "VOW3.DE"}


def test_two_long_two_short():
    book = load_book()
    assert {n.ticker for n in book.longs} == {"0175.HK", "1211.HK"}
    assert {n.ticker for n in book.shorts} == {"2015.HK", "VOW3.DE"}


def test_every_name_has_thesis_kill_and_aliases():
    book = load_book()
    for name in book.names.values():
        assert name.thesis
        assert name.kill
        assert name.aliases


def test_sleeve_is_locked():
    book = load_book()
    assert book.sleeve.locked is True
    assert book.sleeve.theme_watch  # the shared trigger must be non-empty


# --- validation: a missing kill condition must not load silently -------

def test_missing_kill_raises(tmp_path):
    raw = _base_raw()
    del raw["names"]["2015.HK"]["kill"]
    with pytest.raises(ValueError, match="kill"):
        load_book(_write(raw, tmp_path))


def test_missing_thesis_raises(tmp_path):
    raw = _base_raw()
    del raw["names"]["0175.HK"]["thesis"]
    with pytest.raises(ValueError, match="thesis"):
        load_book(_write(raw, tmp_path))


# --- validation: exactly 4 names, no more, no fewer --------------------

def test_fifth_name_raises(tmp_path):
    raw = _base_raw()
    raw["names"]["9999.HK"] = dict(raw["names"]["2015.HK"])
    with pytest.raises(ValueError, match="4 names"):
        load_book(_write(raw, tmp_path))


def test_missing_name_raises(tmp_path):
    raw = _base_raw()
    del raw["names"]["VOW3.DE"]
    with pytest.raises(ValueError, match="4 names"):
        load_book(_write(raw, tmp_path))


# --- validation: role mix must be exactly 2 LONG / 2 SHORT -------------

def test_role_imbalance_raises(tmp_path):
    raw = _base_raw()
    raw["names"]["2015.HK"]["role"] = "LONG"  # now 3 LONG, 1 SHORT
    with pytest.raises(ValueError, match="2 LONG and 2 SHORT"):
        load_book(_write(raw, tmp_path))


def test_invalid_role_raises(tmp_path):
    raw = _base_raw()
    raw["names"]["2015.HK"]["role"] = "PAIR"
    with pytest.raises(ValueError, match="LONG or SHORT"):
        load_book(_write(raw, tmp_path))


def test_unlocked_sleeve_raises(tmp_path):
    raw = _base_raw()
    raw["sleeve"]["locked"] = False
    with pytest.raises(ValueError, match="locked"):
        load_book(_write(raw, tmp_path))


def test_missing_file_raises(tmp_path):
    with pytest.raises(ValueError, match="no file"):
        load_book(tmp_path / "does_not_exist.yaml")


# --- alias matching ------------------------------------------------------

def _item(title: str, summary: str = "") -> NewsItem:
    return NewsItem(
        title=title, url=f"https://x/{hash(title)}", source="test",
        published_at=datetime.now(timezone.utc), summary=summary,
    )


def test_matches_english_company_name():
    book = load_book()
    item = _item("Li Auto vehicle margin falls to 9.4% in Q2")
    match_all([item], book)
    assert item.matched_tickers == ["2015.HK"]


def test_matches_specific_cjk_company_name():
    book = load_book()
    item = _item("吉利汽車8月出口佔比升至41%")
    match_all([item], book)
    assert item.matched_tickers == ["0175.HK"]


def test_generic_two_char_cjk_word_does_not_match():
    """'理想' alone means 'ideal' and must not fire Li Auto's ticker."""
    book = load_book()
    item = _item("理想的追求：一個人的理想主義")
    match_all([item], book)
    assert item.matched_tickers == []


def test_generic_two_char_cjk_word_geely_does_not_match():
    """'吉利' alone means 'auspicious' and must not fire Geely's ticker."""
    book = load_book()
    item = _item("開業大吉利是市不錯的意頭")
    match_all([item], book)
    assert item.matched_tickers == []


def test_bare_ticker_number_does_not_match():
    """'2015' is also a year -- must not fire on its own."""
    book = load_book()
    item = _item("Looking back at the industry in 2015")
    match_all([item], book)
    assert item.matched_tickers == []


def test_vw_shorthand_matches_volkswagen():
    book = load_book()
    item = _item("VW China JV equity profit falls again")
    match_all([item], book)
    assert item.matched_tickers == ["VOW3.DE"]


def test_bare_vow_english_word_does_not_match():
    """'vow' is a real English word and is denylisted even though it
    passes the length rule."""
    book = load_book()
    item = _item("Mayor renews vow to cut city spending")
    match_all([item], book)
    assert item.matched_tickers == []


def test_theme_trigger_matches_without_naming_a_company():
    book = load_book()
    item = _item("EU proposes anti-dumping tariff on Chinese EV imports")
    match_all([item], book)
    assert item.matched_tickers == []
    assert item.theme_hit is True


def test_off_book_company_matches_nothing():
    book = load_book()
    item = _item("Volvo posts record quarterly deliveries")
    match_all([item], book)
    assert item.matched_tickers == []
    assert item.theme_hit is False


def test_keep_book_relevant_drops_unmatched_items():
    book = load_book()
    items = [
        _item("Li Auto vehicle margin falls to 9.4%"),
        _item("Volvo posts record quarterly deliveries"),
        _item("EU proposes anti-dumping tariff on Chinese EV imports"),
    ]
    match_all(items, book)
    kept = keep_book_relevant(items)
    assert [i.title for i in kept] == [
        "Li Auto vehicle margin falls to 9.4%",
        "EU proposes anti-dumping tariff on Chinese EV imports",
    ]


def test_matches_against_summary_too():
    book = load_book()
    item = _item(
        "Chinese automaker posts record exports",
        summary="BYD said overseas shipments rose 40% year on year.",
    )
    match_all([item], book)
    assert item.matched_tickers == ["1211.HK"]

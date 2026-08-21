"""Stage 0 — hard filters.

These run *before* the weighted formula, and they are binary: an item that
trips one is dropped outright, not merely penalised. The distinction
matters. A soft penalty lets a listicle with a strong source and a fresh
timestamp still out-rank real reporting; a hard filter cannot be
out-voted by other factors.

Three families:
  1. clickbait   — listicles, price predictions, horoscopes
  2. price ticks — bare "X breaks above $Y" with no narrative
  3. macro noise — general-news items with no market/policy relevance
"""
from __future__ import annotations

import re

# --- 1. clickbait -----------------------------------------------------

_CLICKBAIT = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\btop\s*\d+\b",
        r"\b\d+\s+(things|ways|reasons|coins?|tokens?)\b",
        r"\bwatch(?:list|\s+list)\b",
        r"\b(celebrity|celeb|obituary|wedding|horoscope)\b",
        r"\b(lifestyle|fashion|recipe)\b",
        r"\bbest\s+of\b",
        r"\bprice\s+(prediction|forecast|target)\b",
        r"\b(could|will|might)\s+(hit|reach|explode|moon)\b",
        r"^\d+\s+altcoins?\s+to\b",
        r"\bhere'?s\s+(why|what|how)\b.*\bnext\b",
    ]
]


def is_clickbait(title: str) -> bool:
    return any(p.search(title) for p in _CLICKBAIT)


# --- 2. bare price ticks ----------------------------------------------

# A quoted price is $-prefixed, USD(T)-suffixed, or a bare number that is
# NOT followed by a unit word. Without those negative lookaheads,
# "200-day moving average" and "$2.00 billion in inflows" read as ticks.
_PRICE_NUM = (
    r"(?:\$[\d,.]+|[\d,.]+\s*(?:USDT|USD)\b|[\d,.]+\b)(?![\d,.])"
    r"(?!\s*(?:billion|million|trillion|years?)\b)(?![MBK]\b)(?!-day\b)"
)

_PRICE_TICK = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(break|breaks|broke|rose|rises|fell|falls|slips?|slid|surged?|"
        r"climbed?|jumped?|dropped?|plunged?|tumbled?)\s+"
        r"(above|below|through|past|to)\s+" + _PRICE_NUM,
        r"\bcurrently trading at\b",
        r"\b(up|down)\s+[\d.]+%\s+(on the day|intraday|in 24 hours)\b",
        r"\b(rose|fell|gained|lost|surged|dropped)\s+[\d.]+%\s+(to|intraday)\b",
    ]
]

# The escape hatch. "Bitcoin slips below $63,000 as analysts warn of ..."
# is analysis, not a tick — the continuation clause is what carries the
# story. Only kill a tick headline when nothing follows the number.
_CONTINUATION = re.compile(
    r"\b(as|after|amid|while|despite|because|following|warns?|says?|said|"
    r"analysts?|setting|hits? record|all-time high|ath|if|could|what|since)\b",
    re.IGNORECASE,
)


def is_price_tick(title: str) -> bool:
    """True for bare price moves the market panel already shows."""
    if not any(p.search(title) for p in _PRICE_TICK):
        return False
    return not _CONTINUATION.search(title)


# --- 3. macro off-topic ----------------------------------------------

_MACRO_RELEVANT = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(fed|fomc|central bank|rate|rates|inflation|cpi|ppi|pce)\b",
        r"\b(treasur(?:y|ies)|yield|bond|dxy|dollar|fx|liquidity)\b",
        r"\b(gdp|pmi|jobs?|payrolls?|unemployment|retail sales)\b",
        r"\b(oil|wti|brent|energy|gas|shipping|hormuz)\b",
        r"\b(tariff|sanction|geopolitical|war|ceasefire)\b",
        r"\b(sec|crypto|bitcoin|stablecoin|token|exchange)\b",
        r"\b(global markets?|risk assets?|stocks?|nasdaq|s&p|volatility|vix)\b",
    ]
]

_MACRO_OFFTOPIC = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(beauty|fashion|style|lifestyle|recipe|travel|dining)\b",
        r"\b(world cup|olympics?|ticket prices?|fans?|pope)\b",
        r"\b(celebrity|entertainment|box office|streaming series)\b",
        r"\b(murder|trial|court case)\b",
        r"\b(gop|democrat|republican|midterm|campaign cash|polls?)\b",
        r"\b(earnings beat|shares jump|analyst upgrade)\b",
    ]
]


def is_macro_offtopic(title: str) -> bool:
    """Drop general-news items that carry no market or policy signal.

    Relevance wins ties: a headline naming both a tariff and an election is
    kept, because the tariff is tradeable and the election framing is not
    what makes it noise.
    """
    if any(p.search(title) for p in _MACRO_RELEVANT):
        return False
    return any(p.search(title) for p in _MACRO_OFFTOPIC)


# --- entry point ------------------------------------------------------

REJECT_REASONS = {
    "clickbait": "listicle / price-prediction pattern",
    "price_tick": "bare price move, already in the market panel",
    "macro_offtopic": "general news with no market or policy relevance",
    "no_title": "empty or malformed title",
}


def reject_reason(title: str, bucket: str = "crypto") -> str | None:
    """Return the reason this item is dropped, or None to keep it."""
    if not title or len(title.strip()) < 8:
        return "no_title"
    if is_clickbait(title):
        return "clickbait"
    if is_price_tick(title):
        return "price_tick"
    if bucket == "macro" and is_macro_offtopic(title):
        return "macro_offtopic"
    return None

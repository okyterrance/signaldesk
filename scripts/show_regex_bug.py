"""Reproduce the keyword-matching bug on demand, beside the fix.

The bug: tier-1 keywords were matched with `\\b(exploit)\\b`, which cannot
match the word *"exploited"* — the trailing word boundary fails against
the following "e". Headlines are written in inflected forms, so a $62m
protocol hack matched nothing and scored as untiered noise. It ranked 7th.
`ETFs` missed an `etf` entry for the same reason.

Tests were green throughout. It was found by printing the factor table
beside a ranking and asking why that story's keyword score was 0.25.

    python scripts/show_regex_bug.py

Prints both rankings side by side over the same headlines, so the effect
is visible rather than remembered. Nothing is mutated: the broken matcher
is rebuilt locally from the same tier table the fixed one uses, so this
cannot drift away from the shipped code.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models import NewsItem                        # noqa: E402
from src.scoring import weights                        # noqa: E402
from src.scoring.weights import KEYWORD_TIERS, score_all, weights_for  # noqa: E402

NOW = datetime.now(timezone.utc)

# The same headlines that exposed it, verbatim.
HEADLINES = [
    ("Curve Finance exploited for $62 million in reentrancy attack", "DL News", 1.5),
    ("SEC approves spot Solana ETFs in reversal of earlier guidance", "CoinDesk", 2.5),
    ("Fed holds rates steady, signals one cut before year end", "FT Markets", 3.0),
    ("Bitcoin slips below $63,000 as spot ETF outflows accelerate", "CoinDesk", 4.0),
    ("BlackRock files for staking feature on its spot Ethereum ETF", "The Block", 8.0),
    ("Tether mints $2 billion USDT on Ethereum", "The Defiant", 6.0),
    ("Treasury yields climb as inflation data surprises", "CNBC", 5.0),
    ("Small NFT marketplace announces team expansion", "Decrypt", 19.0),
]

# What the tier matcher used to be: the stem alone, no inflections.
BROKEN_PATTERNS = {
    tier: re.compile(rf"\b({'|'.join(re.escape(w) for w in sorted(words))})\b")
    for tier, words in KEYWORD_TIERS.items()
}


def items() -> list[NewsItem]:
    return [
        NewsItem(title=t, url=f"https://example.com/{i}", source=s,
                 published_at=NOW - timedelta(hours=h))
        for i, (t, s, h) in enumerate(HEADLINES)
    ]


def rank(broken: bool) -> list[NewsItem]:
    original = weights._TIER_PATTERNS
    if broken:
        weights._TIER_PATTERNS = BROKEN_PATTERNS
    try:
        return score_all(items(), NOW, weights_for("balanced"))
    finally:
        weights._TIER_PATTERNS = original


def keyword_of(item: NewsItem) -> float:
    return next(f.raw for f in item.breakdown.factors if f.name == "keyword")


def show(title: str, ranked: list[NewsItem], mark: str) -> None:
    print(f"\n  {title}")
    print("  " + "─" * 74)
    print(f"  {'#':<3}{'score':>7}{'keyword':>9}   headline")
    for i, it in enumerate(ranked, 1):
        flag = "  <<<" if mark in it.title else ""
        print(f"  {i:<3}{it.score:>7.3f}{keyword_of(it):>9.2f}   {it.title[:46]}{flag}")


def main() -> int:
    marker = "Curve"
    before, after = rank(broken=True), rank(broken=False)

    print("\n" + "=" * 78)
    print("  KEYWORD MATCHING — the same 8 headlines, two matchers")
    print("=" * 78)

    show(r"BEFORE   \b(exploit)\b   cannot match “exploited”", before, marker)
    show(r"AFTER    \b(exploit)(?:s|ed|ing|…)?\b   matches inflections", after, marker)

    b = next(i for i, x in enumerate(before, 1) if marker in x.title)
    a = next(i for i, x in enumerate(after, 1) if marker in x.title)
    print("\n  " + "─" * 74)
    print(f"  The $62m exploit moved from rank {b} to rank {a}.")
    print(f"  Its keyword factor went {keyword_of(before[b-1]):.2f} → "
          f"{keyword_of(after[a-1]):.2f} — untiered noise to tier 1.\n")
    print("  Every test was green before and after. This was found by reading")
    print("  the factor table next to the ranking, not by a test.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

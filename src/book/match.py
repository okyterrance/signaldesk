"""Stage: which headlines are even about this book.

Twelve equity/policy feeds cover an entire industry; the book holds four
names. Everything that isn't about one of those four names, or about the
one shared trade-policy trigger the sleeve is watching for, is dropped
before it ever reaches scoring.

Alias matching is deliberately conservative. Several natural aliases are
excluded on purpose:

  - Bare ticker numbers ("0175", "1211", "2015") are display-only. "2015"
    is a year; a numeric ticker floating in free text is not evidence.
  - Short CJK aliases ("吉利", "大眾", "理想") are common words in their
    own right -- "吉利" means "auspicious", "理想" means "ideal", "大眾"
    means "the public". Only aliases of 3+ CJK characters are used to
    match ("比亞迪", "理想汽車", "大眾集團"), because at that length they
    stop being generic vocabulary.
  - A short denylist catches ASCII aliases that pass the length rule but
    are still real English words ("vow").

None of this is configurable per name on purpose: one rule, applied
uniformly, is auditable. A per-name exception list would need the same
scrutiny as the aliases themselves.
"""
from __future__ import annotations

import re

from src.book.models import Book, Name
from src.models import NewsItem

_ASCII_DENYLIST = {"vow"}

# "VW" fails the length>=3 rule but is the standard journalistic shorthand
# for Volkswagen, and this book's feed pool is scoped to the auto industry
# -- unlike a two-letter alias in a general-news pool, it will not collide
# with unrelated coverage here. A narrow, explicit exception, not a lower
# length threshold that would also let back in ambiguous tokens like "LI".
_ASCII_ALLOWLIST_SHORT = {"vw"}


def _is_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


def _usable_aliases(name: Name) -> list[str]:
    """The subset of `name.aliases` (plus the ticker's bare company name)
    specific enough to match on. See module docstring for the rule."""
    candidates = [*name.aliases, name.name]
    out: list[str] = []
    for alias in candidates:
        alias = alias.strip()
        if not alias:
            continue
        if alias.isdigit():
            continue
        if _is_cjk(alias):
            if len(alias) >= 3:
                out.append(alias)
            continue
        lowered = alias.lower()
        if lowered in _ASCII_ALLOWLIST_SHORT:
            out.append(alias)
        elif len(alias) >= 3 and lowered not in _ASCII_DENYLIST:
            out.append(alias)
    return out


def _build_index(book: Book) -> dict[str, list[re.Pattern[str]]]:
    """ticker -> compiled patterns, one per usable alias."""
    index: dict[str, list[re.Pattern[str]]] = {}
    for ticker, name in book.names.items():
        patterns = []
        for alias in _usable_aliases(name):
            if _is_cjk(alias):
                patterns.append(re.compile(re.escape(alias)))
            else:
                patterns.append(re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE))
        index[ticker] = patterns
    return index


# The sleeve's one shared trigger: a tariff/anti-dumping/export-restriction
# move against the destination markets the theme depends on. Hits here set
# `theme_hit` on the item regardless of which (if any) name it also matches.
_THEME_PATTERN = re.compile(
    r"\b(anti-?dumping|tariff\w*|export\s+(?:ban|controls?|curbs?|restrict\w*)|"
    r"trade\s+war|countervailing\s+dut\w*)\b",
    re.IGNORECASE,
)
_THEME_CJK_TRIGGERS = ("反傾銷", "反倾销", "關稅", "关税", "出口管制", "出口禁令", "內捲", "内卷")


def _theme_hit(text: str) -> bool:
    if _THEME_PATTERN.search(text):
        return True
    return any(trigger in text for trigger in _THEME_CJK_TRIGGERS)


def match_all(items: list[NewsItem], book: Book) -> None:
    """Annotate each item with `matched_tickers` and `theme_hit`, in place."""
    index = _build_index(book)
    for item in items:
        text = f"{item.title} {item.summary}"
        matched = [
            ticker
            for ticker, patterns in index.items()
            if any(p.search(text) for p in patterns)
        ]
        item.matched_tickers = sorted(matched)
        item.theme_hit = _theme_hit(text)


def keep_book_relevant(items: list[NewsItem]) -> list[NewsItem]:
    """Drop anything that names none of the book and isn't the shared trigger.

    Call this *after* `match_all`.
    """
    return [i for i in items if i.matched_tickers or i.theme_hit]

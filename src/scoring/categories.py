"""Five reader-facing categories, and the classifier that assigns them.

These are not the same thing as the crypto/macro buckets. Buckets exist so
macro stories are not crowded out on the asset factor; categories exist so
a reader can say "I only care about security and flows" and get that.

The set is deliberately small and non-overlapping. Twenty tags would be
more precise and nobody would configure them. Five fit on one screen of
buttons and each maps onto something a desk actually cares about.

Classification is single-label and first-match-wins, in priority order.
A story about an exploit at an ETF custodian is a security story: that is
the fact that moves a position. Multi-label would let one story occupy
several of a reader's slots, which is the opposite of what filtering is
for.
"""
from __future__ import annotations

import re

from src.models import NewsItem

# Ordered by priority. The first pattern to match decides the category, so
# the sharper, more consequential subjects are tested first.
CATEGORIES: list[tuple[str, str, str, re.Pattern[str]]] = [
    (
        "security",
        "Security & risk",
        "hacks, exploits, depegs, insolvency, liquidations",
        re.compile(
            r"\b(hack|hacks|hacked|hacker|hackers|hacking|exploit|exploits|"
            r"exploited|breach|breached|drain|drained|stolen|theft|scam|"
            r"rug\s?pull|depeg|depegged|insolven\w+|bankrupt\w*|liquidat\w+|"
            r"attack|attacked|vulnerab\w+|halts?|halted|freeze|frozen)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "regulation",
        "Regulation & policy",
        "SEC, lawsuits, legislation, sanctions, tariffs",
        re.compile(
            r"\b(sec|cftc|regulat\w+|lawsuit|sued|sues|court|judge|ruling|"
            r"settlement|subpoena|enforcement|legislat\w+|bill|act|congress|"
            r"senate|sanction\w*|tariff\w*|ban|banned|licence|license|"
            r"compliance|mica|ofac|probe|investigat\w+)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "flows",
        "Institutional flows",
        "ETFs, treasuries, custody, corporate holdings",
        re.compile(
            # Generic finance nouns are deliberately absent. Flows is
            # tested before macro, so anything matched here is taken out
            # of macro's reach -- and two bare words did exactly that in
            # production. `treasur\w+` swallowed "Treasury yields climb as
            # inflation surprises"; `fund|funds` then swallowed "hedge
            # funds' top energy plays", "Goldman says hedge funds
            # underperformed the S&P 500" and "how money-market funds are
            # fuelling stocks" -- three equity-market stories filed as
            # crypto institutional flows, in one digest.
            #
            # This category means capital moving into or out of digital
            # assets. A fund that is merely mentioned is not that, so
            # `fund` only counts when qualified as a crypto vehicle.
            r"\b(etf|etfs|inflow\w*|outflow\w*|custody|custodian|blackrock|"
            r"fidelity|grayscale|vanguard|microstrategy|"
            # One intervening word allowed, so "RLUSD credit fund" and
            # "crypto index fund" match while a distant co-mention does not.
            r"(?:crypto|bitcoin|digital[- ]asset|token(?:ized)?|rlusd|stablecoin)"
            r"\s+(?:\w+\s+)?fund\w*|"
            r"corporate treasur\w+|treasury (?:holdings?|company|reserves?)|"
            r"aum|holdings?|accumulat\w+|whale\w*)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "macro",
        "Macro & rates",
        "Fed, CPI, central banks, yields, broad markets",
        re.compile(
            r"\b(fed|fomc|federal reserve|ecb|boj|central bank\w*|cpi|ppi|pce|"
            r"inflation|deflation|rate|rates|yield\w*|bond\w*|dxy|dollar|"
            r"currency|gdp|payroll\w*|unemployment|recession|stimulus|"
            r"qe|liquidity|jobs report|"
            # Broad-market conditions belong here too. Without these, a
            # story about hedge funds and the S&P 500 matches nothing at
            # all once it stops (correctly) matching crypto flows.
            r"s&p|nasdaq|dow|equit\w+|stocks?|vix|volatility|"
            r"hedge fund\w*|money[- ]market fund\w*|money[- ]market|"
            r"commercial paper|oil|wti|brent|energy sector)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "protocol",
        "Protocol & tech",
        "upgrades, forks, L2s, DeFi mechanics, airdrops",
        re.compile(
            r"\b(upgrade\w*|fork\w*|mainnet|testnet|layer\s?2|l2|rollup\w*|"
            r"staking|stake\w*|validator\w*|airdrop\w*|unlock\w*|tvl|"
            r"protocol\w*|defi|dex|bridge\w*|token\w*|smart contract\w*|"
            r"consensus|throughput|node\w*)\b",
            re.IGNORECASE,
        ),
    ),
]

CATEGORY_IDS: list[str] = [c[0] for c in CATEGORIES]
CATEGORY_LABELS: dict[str, str] = {c[0]: c[1] for c in CATEGORIES}
CATEGORY_BLURBS: dict[str, str] = {c[0]: c[2] for c in CATEGORIES}

# Shown beside each category in the settings keyboard.
CATEGORY_EMOJI: dict[str, str] = {
    "security": "🔓",
    "regulation": "⚖️",
    "flows": "🏦",
    "macro": "📉",
    "protocol": "⚙️",
}


def classify(item: NewsItem) -> str | None:
    """Assign one category, or None when nothing matches.

    Tags are searched alongside the title: several feeds carry a useful
    `regulation` or `defi` tag on stories whose headline never says the
    word.
    """
    text = f"{item.title} {' '.join(item.tags)}"
    for cid, _label, _blurb, pattern in CATEGORIES:
        if pattern.search(text):
            return cid
    return None


def annotate(items: list[NewsItem]) -> list[NewsItem]:
    """Attach `category` to each item in place."""
    for item in items:
        item.category = classify(item)
    return items


def filter_by_categories(
    items: list[NewsItem], enabled: set[str]
) -> list[NewsItem]:
    """Keep only items in the enabled categories.

    Two deliberate behaviours:

    Unclassified items ride along only when every category is enabled.
    That makes the default state "show me everything" while a narrowed
    selection stays honestly narrow — a reader who asked for security news
    should not receive an uncategorised story as filler.

    An empty selection is treated as no filter rather than as a request
    for an empty digest, since the only way to reach it is by switching
    everything off, which reads as "never mind".
    """
    if not enabled or set(enabled) >= set(CATEGORY_IDS):
        return items
    return [i for i in items if i.category in enabled]

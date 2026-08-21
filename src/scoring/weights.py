"""Stage 2 — the seven-factor weighted score.

Every surviving item gets one number in [0, 1]. The number is a weighted
sum of seven independent factors, each normalised to [0, 1] first so the
weights mean what they look like they mean.

    score = sum(weight_i * factor_i) / sum(weight_i)

Unlike a bare float, every score here comes back with its own breakdown:
which factor contributed what, and why. That is what `/why` prints, and
it is the difference between a ranking you trust and one you don't.

--- Why these weights ---

keyword (0.222) and recency (0.222) lead because they answer the two
questions that dominate whether a story matters this morning: is the
subject consequential, and did it happen recently enough to still be
tradeable.

source_quality (0.220) is nearly as heavy. A claim in the FT and the same
claim on an SEO farm are not the same claim.

category (0.145) is a coarse topical gate from feed tags.

source_count (0.080) is deliberately *light*, and this is the least
obvious choice in the table. Corroboration across outlets is genuine
evidence, so the factor earns its place -- but weight it heavily and a
big story wins every slot for three days running, because every outlet
keeps re-reporting it. Capping its influence at 8% buys corroboration
signal without letting yesterday's news squat on today's digest.

numeric (0.056) and asset (0.056) are tie-breakers. A headline carrying a
concrete figure is more actionable than one that doesn't; a headline
about BTC is more relevant to this audience than one about a microcap.
Neither should ever outrank subject matter, hence the small weights.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from src.models import FactorScore, NewsItem, ScoreBreakdown

# ---------------------------------------------------------------------
# Weights. Must be treated as a single tuned set -- changing one in
# isolation shifts the meaning of all the others.
# ---------------------------------------------------------------------

FACTOR_WEIGHTS: dict[str, float] = {
    "keyword": 0.200,
    "recency": 0.200,
    "source_quality": 0.200,
    "topicality": 0.140,
    "source_count": 0.080,
    # numeric + analysis share a fixed 0.130 budget, split by the reader's
    # depth preference. Keeping the pair's total constant means changing
    # the preference re-weights style without quietly changing how much
    # subject matter, freshness or source reputation count.
    "numeric": 0.065,
    "analysis": 0.065,
    "asset": 0.050,
}

STYLE_BUDGET = FACTOR_WEIGHTS["numeric"] + FACTOR_WEIGHTS["analysis"]

# How the style budget splits, per reader preference. The swing is large
# on purpose: a setting that barely moves the ranking is a setting that
# was not worth offering.
DEPTH_SPLITS: dict[str, tuple[float, float]] = {
    #            numeric              analysis
    "data":     (STYLE_BUDGET * 0.80, STYLE_BUDGET * 0.20),
    "balanced": (STYLE_BUDGET * 0.50, STYLE_BUDGET * 0.50),
    "analysis": (STYLE_BUDGET * 0.20, STYLE_BUDGET * 0.80),
}


def weights_for(depth: str = "balanced") -> dict[str, float]:
    """The factor table as this reader has it configured."""
    numeric, analysis = DEPTH_SPLITS.get(depth, DEPTH_SPLITS["balanced"])
    table = dict(FACTOR_WEIGHTS)
    table["numeric"] = numeric
    table["analysis"] = analysis
    return table

# --- factor 1: keyword tiers -----------------------------------------

# Tier 1 moves every asset class. Tier 4 is table stakes in a crypto feed
# and therefore says almost nothing on its own.
KEYWORD_TIERS: dict[int, set[str]] = {
    1: {"fed", "fomc", "cpi", "hack", "exploit", "bankrupt", "insolvency"},
    2: {"rate", "inflation", "etf", "sec", "war", "sanction", "tariff",
        "lawsuit", "fraud", "depeg", "liquidation", "halt", "default"},
    3: {"tvl", "stablecoin", "restaking", "blackrock", "fidelity",
        "grayscale", "microstrategy", "ofac", "mica", "treasury", "yield",
        "custody", "rwa", "tokenization", "upgrade", "fork", "unlock"},
    4: {"btc", "bitcoin", "eth", "ethereum", "sol", "solana", "defi",
        "halving", "merge", "airdrop", "nft", "layer2"},
}

# Entries above are stems, and the pattern matches common inflections.
# Without this, the tier table silently misses the form headlines actually
# use: "Curve exploited for $62m" never matched `\bexploit\b`, so the
# biggest story of the day scored as an untiered item, and "ETFs" missed
# an `etf` entry that only matched the singular.
_SUFFIX = r"(?:s|es|ed|d|ing|er|ers|cy)?"
_TIER_PATTERNS = {
    tier: re.compile(
        rf"\b({'|'.join(re.escape(w) for w in sorted(words))}){_SUFFIX}\b"
    )
    for tier, words in KEYWORD_TIERS.items()
}


def keyword_score(item: NewsItem) -> tuple[float, str]:
    """Highest tier hit wins; T1 -> 1.0, T2 -> 0.75, T3 -> 0.5, T4 -> 0.25.

    Highest-tier-wins rather than summing: a story about an exploit at a
    stablecoin issuer is an exploit story. Counting both would let a
    headline stuffed with mid-tier terms beat a plain one about the Fed.
    """
    text = f"{item.title} {' '.join(item.tags)}".lower()
    for tier in (1, 2, 3, 4):
        match = _TIER_PATTERNS[tier].search(text)
        if match:
            return (5 - tier) / 4.0, f"tier-{tier} keyword '{match.group(1)}'"
    return 0.0, "no tiered keyword"


# --- factor 2: recency -----------------------------------------------

def recency_score(item: NewsItem, now: datetime | None = None) -> tuple[float, str]:
    """Linear decay to zero across 24h.

    Linear, not exponential: exponential decay makes anything older than a
    few hours effectively unrankable, which is wrong for a once-a-day
    digest that must still surface a 20-hour-old policy decision.
    """
    now = now or datetime.now(timezone.utc)
    pub = item.published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    age_h = max(0.0, (now - pub).total_seconds() / 3600)
    return max(0.0, 1.0 - age_h / 24.0), f"{age_h:.1f}h old"


# --- factor 3: source quality ----------------------------------------

SOURCE_QUALITY: dict[str, float] = {
    # Wire-grade / primary
    "FT Markets": 1.00,
    "Bloomberg": 1.00,
    "ECB Press": 1.00,
    "The Block": 1.00,
    # Strong crypto desks
    "DL News": 0.95,
    "Unchained": 0.95,
    "CNBC": 0.90,
    "CoinDesk": 0.85,
    "The Defiant": 0.85,
    "SCMP Business": 0.85,
    # Reliable but lighter editing
    "Decrypt": 0.75,
    "Channel News Asia": 0.75,
}
_DEFAULT_QUALITY = 0.60


def source_quality_score(item: NewsItem) -> tuple[float, str]:
    q = SOURCE_QUALITY.get(item.source, _DEFAULT_QUALITY)
    note = item.source if item.source in SOURCE_QUALITY else f"{item.source} (unrated)"
    return q, note


# --- factor 4: category relevance ------------------------------------

RELEVANT_TAGS = {
    "bitcoin", "ethereum", "crypto", "cryptocurrency", "defi", "blockchain",
    "stablecoin", "regulation", "sec", "etf", "markets", "economy", "fed",
    "central-banks", "monetary-policy", "inflation", "trade", "geopolitics",
    "policy", "business", "finance",
}
OFFTOPIC_TAGS = {"sports", "entertainment", "lifestyle", "travel", "food", "arts"}


def category_score(item: NewsItem) -> tuple[float, str]:
    """Untagged feeds score neutral rather than zero.

    Several sources publish no tags at all. Scoring those 0 would silently
    blacklist whole outlets for a metadata habit that has nothing to do
    with the story's importance.
    """
    tags = {t.lower().replace("_", "-") for t in item.tags if t}
    if not tags:
        return 0.5, "no tags (neutral)"
    hit = tags & RELEVANT_TAGS
    if hit:
        return 1.0, f"relevant tag '{sorted(hit)[0]}'"
    if tags & OFFTOPIC_TAGS:
        return 0.0, f"off-topic tag '{sorted(tags & OFFTOPIC_TAGS)[0]}'"
    return 0.5, "tags present but unmapped"


# --- factor 5: corroboration -----------------------------------------

def source_count_score(item: NewsItem) -> tuple[float, str]:
    """Step function, saturating at 5 outlets.

    Steps not a ratio: the jump from one outlet to two is the meaningful
    one (it went from a claim to a corroborated claim). Going from five to
    nine tells you the story is loud, which recency and keyword already
    capture.
    """
    n = item.source_count
    if n == 1:
        return 0.0, "single source"
    if n == 2:
        return 0.20, "2 sources"
    if n <= 4:
        return 0.55, f"{n} sources"
    return 1.0, f"{n} sources (saturated)"


# --- factors 6 & 7: specificity tie-breakers -------------------------

_NUMERIC = re.compile(r"\$\d|\d+%|\d{3,}")
_ASSET_T1 = re.compile(r"\b(btc|bitcoin|eth|ethereum)\b", re.IGNORECASE)
_ASSET_T2 = re.compile(r"\b(sol|solana|xrp|ripple|bnb|sui|hyperliquid)\b", re.IGNORECASE)
_ASSET_T3 = re.compile(r"\b(doge|shib|pepe|altcoin|memecoin)\b", re.IGNORECASE)


def numeric_score(item: NewsItem) -> tuple[float, str]:
    """Concrete figures in the headline, and how many.

    Graded rather than binary: "ETF inflows hit $2.1B, up 43% on the week"
    carries more for a numbers-first reader than a headline with one
    incidental figure in it.
    """
    hits = _NUMERIC.findall(item.title)
    if not hits:
        return 0.0, "no figure in headline"
    if len(hits) == 1:
        return 0.7, f"one figure ({hits[0]})"
    return 1.0, f"{len(hits)} figures"


# Markers of a piece that explains rather than reports. Two families:
# framing words that announce analysis, and attribution verbs that mean
# somebody is being quoted making an argument.
_ANALYSIS_FRAMING = re.compile(
    r"\b(why|what|how|explainer|analysis|opinion|outlook|forecast|"
    r"takeaways?|deep\s?dive|breaking\s?down|inside|behind|"
    r"could|would|should|whether|if)\b",
    re.IGNORECASE,
)
_ANALYSIS_ATTRIBUTION = re.compile(
    r"\b(analysts?|strategists?|economists?|researchers?|says?|said|argues?|"
    r"warns?|warned|expects?|predicts?|sees|flags?|points? to|weighs?)\b",
    re.IGNORECASE,
)


def analysis_score(item: NewsItem) -> tuple[float, str]:
    """How much this reads as commentary rather than a bare event report.

    Headline signals carry most of it; a long summary adds a little,
    because explainers run longer than wire copy. Deliberately not an
    LLM call — this factor has to stay cheap and reproducible like every
    other one, and a regex that is right most of the time and inspectable
    all of the time is the better trade here.
    """
    framing = bool(_ANALYSIS_FRAMING.search(item.title))
    attribution = bool(_ANALYSIS_ATTRIBUTION.search(item.title))
    long_form = len(item.summary or "") > 220

    score = 0.0
    reasons: list[str] = []
    if framing:
        score += 0.45
        reasons.append("framing")
    if attribution:
        score += 0.40
        reasons.append("attributed view")
    if long_form:
        score += 0.15
        reasons.append("long summary")

    if not reasons:
        return 0.0, "straight report"
    return min(1.0, score), ", ".join(reasons)


def asset_score(item: NewsItem) -> tuple[float, str]:
    """Majors 1.0, large alts 0.7, memecoins 0.3, no asset named 0.5.

    'No asset named' sits *above* memecoins on purpose: an untagged
    regulatory or macro story is more consequential to this audience than
    a confirmed memecoin story.
    """
    t = item.title
    if _ASSET_T1.search(t):
        return 1.0, "major asset (BTC/ETH)"
    if _ASSET_T2.search(t):
        return 0.7, "large alt"
    if _ASSET_T3.search(t):
        return 0.3, "memecoin / long tail"
    return 0.5, "no specific asset"


# ---------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------

_FACTOR_FNS = {
    "keyword": keyword_score,
    "recency": recency_score,
    "source_quality": source_quality_score,
    "topicality": category_score,
    "source_count": source_count_score,
    "numeric": numeric_score,
    "analysis": analysis_score,
    "asset": asset_score,
}


def score_item(
    item: NewsItem,
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
) -> ScoreBreakdown:
    """Score one item and attach the full factor breakdown.

    `weights` defaults to the balanced table; pass `weights_for(depth)` to
    score against a reader's own preference.
    """
    table = weights or FACTOR_WEIGHTS
    total_weight = sum(table.values())

    factors: list[FactorScore] = []
    for name, weight in table.items():
        fn = _FACTOR_FNS[name]
        raw, reason = fn(item, now) if name == "recency" else fn(item)
        factors.append(FactorScore(name=name, raw=raw, weight=weight, reason=reason))

    total = sum(f.contribution for f in factors) / total_weight
    breakdown = ScoreBreakdown(total=total, factors=factors)
    item.score = total
    item.breakdown = breakdown
    return breakdown


def score_all(
    items: list[NewsItem],
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
) -> list[NewsItem]:
    """Score in place and return sorted best-first."""
    now = now or datetime.now(timezone.utc)
    for item in items:
        score_item(item, now, weights)
    items.sort(key=lambda i: -i.score)
    return items


# --- subject diversity --------------------------------------------------

# Deduping collapses the same *story*. It cannot collapse the same
# *narrative*: five separate, genuinely distinct articles about bitcoin's
# move are five different stories that a reader experiences as one point
# made five times. A live run filled 5 of 12 slots that way.
_SUBJECTS: list[tuple[str, re.Pattern[str]]] = [
    ("bitcoin", re.compile(r"\b(btc|bitcoin)\b", re.IGNORECASE)),
    ("ethereum", re.compile(r"\b(eth|ethereum|ether)\b", re.IGNORECASE)),
    ("solana", re.compile(r"\b(sol|solana)\b", re.IGNORECASE)),
    ("xrp", re.compile(r"\b(xrp|ripple)\b", re.IGNORECASE)),
]


def primary_subject(item: NewsItem) -> str | None:
    """First asset named in the headline, or None for asset-free stories.

    Order matters and is deliberate: "Bitcoin, ether and solana climb"
    counts as bitcoin, because that is the subject a reader files it
    under. Macro and regulatory stories return None and are never capped
    -- they are already the scarce half of the digest.
    """
    for name, pattern in _SUBJECTS:
        if pattern.search(item.title):
            return name
    return None


def select_top(
    scored: list[NewsItem],
    min_n: int,
    max_n: int,
    threshold: float = 0.30,
    max_per_subject: int = 3,
) -> list[NewsItem]:
    """Adaptive top-N: quality gate, subject cap, fixed count as a floor.

    A quiet news day should produce a short digest, not `max_n` slots
    padded with whatever ranked highest among the noise. But an empty
    digest is a broken-looking bot, so `min_n` backfills by rank when the
    gate admits too few.

    The subject cap is a preference, not a quota. If enforcing it would
    push the digest below `min_n`, held-back items are let back in: a
    repetitive digest beats a thin one.
    """
    if not scored:
        return []

    pool = [i for i in scored if i.score >= threshold]
    if len(pool) < min_n:
        pool = scored[:min_n]

    picked: list[NewsItem] = []
    held: list[NewsItem] = []
    seen: dict[str, int] = {}

    for item in pool:
        if len(picked) >= max_n:
            break
        subject = primary_subject(item)
        if subject and seen.get(subject, 0) >= max_per_subject:
            held.append(item)
            continue
        picked.append(item)
        if subject:
            seen[subject] = seen.get(subject, 0) + 1

    for item in held:
        if len(picked) >= min_n:
            break
        picked.append(item)

    picked.sort(key=lambda i: -i.score)
    return picked[:max_n]

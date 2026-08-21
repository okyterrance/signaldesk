"""Stage 1 — collapse the same story reported by different outlets.

Twelve feeds covering one market means the same event arrives up to six
times with six different headlines. Left alone, a single story would fill
the whole digest.

Two detectors run in parallel, and either one firing merges the pair:

  A. TF-IDF cosine over normalised titles. Catches near-identical
     wording. Normalisation folds ticker aliases (btc -> bitcoin) and
     verb families (surges/climbs/jumps -> rally) so that lexical
     variation of the same claim collapses to the same vector.

  B. Proper-noun overlap. Catches cross-outlet paraphrases that share no
     phrasing at all -- "Cardano Foundation cancels summit" vs "The
     Cardano Foundation will not be holding the Cardano Summit". TF-IDF
     scores that pair well below threshold; entity overlap does not.

Detector B is deliberately hard to trigger (>=2 shared entities AND
Jaccard >= 0.5, and the shared set cannot be only BTC/ETH) because
over-merging is the worse failure: a missed merge costs one slot, a bad
merge silently deletes a real story.
"""
from __future__ import annotations

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.models import NewsItem

# --- normalisation tables --------------------------------------------

TICKER_SYNONYMS = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana", "xrp": "ripple",
    "doge": "dogecoin", "ada": "cardano", "avax": "avalanche",
    "dot": "polkadot", "link": "chainlink", "bnb": "binancecoin",
}

# Present and past tense both fold to the same root: "Ethereum rose above
# 1700" and "ETH breaks above $1,700" must produce the same token.
VERB_SYNONYMS = {
    "tops": "rally", "breaks": "rally", "hits": "rally", "rallies": "rally",
    "surges": "rally", "climbs": "rally", "jumps": "rally", "pumps": "rally",
    "soars": "rally", "spikes": "rally", "rises": "rally", "gains": "rally",
    "topped": "rally", "broke": "rally", "hit": "rally", "rallied": "rally",
    "surged": "rally", "climbed": "rally", "jumped": "rally", "pumped": "rally",
    "soared": "rally", "spiked": "rally", "rose": "rally", "gained": "rally",
    "drops": "fall", "falls": "fall", "slides": "fall", "crashes": "fall",
    "plunges": "fall", "tumbles": "fall", "dumps": "fall", "sinks": "fall",
    "slumps": "fall", "dives": "fall",
    "dropped": "fall", "fell": "fall", "slid": "fall", "crashed": "fall",
    "plunged": "fall", "tumbled": "fall", "dumped": "fall", "sank": "fall",
    "slumped": "fall", "dived": "fall", "dove": "fall",
}

STOPWORDS = {
    "on", "in", "at", "amid", "for", "the", "a", "an", "of", "and", "or",
    "to", "by", "with", "from", "as", "is", "are", "was", "were", "be",
    "been", "has", "have", "had", "will", "would", "can", "could", "may",
    "might", "near", "this", "that", "these", "those", "it", "its", "new",
    "says", "said", "reports", "report", "after", "before", "over", "under",
}


def normalize(text: str) -> str:
    """Lowercase, fold synonyms, drop stopwords -- but keep digits.

    Digits are the strongest shared token between two reports of the same
    move, so "1700" survives; thousands separators and a trailing ".00"
    are stripped first so $1,700 and 1700.00 collapse together.
    """
    lowered = text.lower().replace(",", "")
    lowered = re.sub(r"(\d)\.0+\b", r"\1", lowered)
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    out: list[str] = []
    for tok in cleaned.split():
        if len(tok) < 2:
            continue
        tok = TICKER_SYNONYMS.get(tok, tok)
        tok = VERB_SYNONYMS.get(tok, tok)
        if tok in STOPWORDS:
            continue
        out.append(tok)
    return " ".join(out)


# --- entity detector --------------------------------------------------

_PROPER_NOUN = re.compile(r"\b([A-Z][a-zA-Z]+|[A-Z]{2,})\b")
_NUMBER = re.compile(r"\d[\d,]*")

# Words that pass the capitalisation test but say nothing about *which*
# event this is. Currency units and compound place names are the usual
# false-merge culprits ("Wall Street", "South Korean", "USDT").
_ENTITY_IGNORE = frozenset({
    "the", "a", "an", "this", "that", "new", "here", "how", "why", "what",
    "after", "before", "amid", "as", "while", "data", "analysis", "report",
    "us", "usd", "usdt", "wall", "street", "south", "north", "korean",
    "korea", "japanese", "japan", "index", "live", "breaking", "update",
})

# Half the crypto feed mentions BTC or ETH; co-mention alone identifies
# nothing. They still count toward the Jaccard ratio, they just cannot be
# the *only* thing two headlines share.
_GENERIC_ENTITIES = frozenset({"bitcoin", "ethereum"})


def entity_tokens(title: str) -> frozenset[str]:
    out: set[str] = set()
    for tok in _PROPER_NOUN.findall(title):
        low = tok.lower()
        if low in _ENTITY_IGNORE:
            continue
        out.add(TICKER_SYNONYMS.get(low, low))
    # Specific figures are strong event fingerprints ("1,550 bitcoin").
    # Skip short numbers (24h, top-5) and anything that looks like a year.
    for num in _NUMBER.findall(title):
        digits = num.replace(",", "")
        if len(digits) >= 3 and not re.fullmatch(r"(19|20)\d\d", digits):
            out.add(digits)
    return frozenset(out)


def same_event(a: NewsItem, b: NewsItem) -> bool:
    ta, tb = entity_tokens(a.title), entity_tokens(b.title)
    if not ta or not tb:
        return False
    shared = ta & tb
    if len(shared) < 2 or not (shared - _GENERIC_ENTITIES):
        return False
    return len(shared) / len(ta | tb) >= 0.5


# --- merge ------------------------------------------------------------

def dedupe(items: list[NewsItem], threshold: float = 0.50) -> list[NewsItem]:
    """Collapse duplicate reports; the survivor records how many outlets ran it.

    Clusters are grown to their transitive closure: a candidate joins if it
    matches *any* member, not just the first one. Comparing only against
    the seed is not enough -- with three outlets on one story it is common
    for A~B and B~C to clear the threshold while A~C does not, because the
    two ends phrase it differently. Seed-only comparison leaves C out, and
    the story appears twice in a digest whose entire job is to not do that.

    Transitive growth trades that for a chain-merge risk, which the strict
    entity guard in `same_event` (>=2 shared non-generic entities AND
    Jaccard >= 0.5) is there to contain.

    The earliest item of each cluster anchors it. Callers pass feed order
    rather than scored order, so no outlet is systematically favoured.
    """
    if len(items) <= 1:
        return items

    corpus = [normalize(f"{i.title} {' '.join(i.tags)}") for i in items]
    matrix = TfidfVectorizer(max_features=1000, ngram_range=(1, 2)).fit_transform(corpus)
    sim = cosine_similarity(matrix)

    def matches(a: int, b: int) -> bool:
        return bool(sim[a, b] >= threshold or same_event(items[a], items[b]))

    merged: list[NewsItem] = []
    claimed: set[int] = set()

    for i in range(len(items)):
        if i in claimed:
            continue

        cluster = [i]
        claimed.add(i)
        frontier = [i]
        while frontier:
            member = frontier.pop()
            for j in range(len(items)):
                if j in claimed or not matches(member, j):
                    continue
                claimed.add(j)
                cluster.append(j)
                frontier.append(j)

        anchor = items[cluster[0]]
        if len(cluster) > 1:
            sources = {items[k].source for k in cluster}
            anchor.source_count = len(sources)
            anchor.merged_sources = sorted(sources)
            anchor.tags = sorted({t for k in cluster for t in items[k].tags})
        merged.append(anchor)
    return merged

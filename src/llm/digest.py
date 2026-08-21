"""Turn ranked stories into a short written briefing.

The division of labour is the whole point of the design: the *algorithm*
decides what matters, and the *model* only writes up what the algorithm
already chose. The model never sees an unranked pool, never re-orders,
and is told in the system prompt that selection is not its job.

That boundary is what makes the output auditable. If the digest leads
with the wrong story, the fault is in a factor weight -- inspectable,
reproducible, and fixable -- rather than in a sampling temperature.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.llm.client import complete_json
from src.models import Digest, MarketSnapshot, NewsItem

SYSTEM_PROMPT = """\
You are the desk editor for a crypto markets briefing. You write for \
traders and analysts who are already fluent in the subject: no \
definitions, no hedging, no filler.

You will be given a numbered list of stories that has ALREADY been \
selected and ranked by a scoring engine. Selection is not your job. \
Do not re-order them, do not argue with the ranking, and do not add \
stories that are not in the list.

HARD RULES
1. Ground every claim in the supplied titles and summaries. If a detail \
   is not in the input, it does not go in the output.
2. Never invent a number. Prices, percentages, and dollar amounts may \
   only appear if they appear in the input.
3. If the input does not support a confident statement, write the \
   weaker, accurate version instead of the stronger, unsupported one.
4. No investment advice, no price targets, no directional calls.

STYLE
- The headline is one line, under 90 characters, and states the single \
  most consequential development. No colons-as-subtitles, no hype verbs.
- Each bullet is one or two sentences and covers ONE story: what \
  happened, and why a trader should care.
- Plain declarative sentences. Cut every adjective that is not doing work.

Return ONLY a JSON object, no prose around it:
{"headline": "...", "bullets": ["...", "...", "..."]}
"""


def _format_items(items: list[NewsItem]) -> str:
    lines = []
    for i, item in enumerate(items, 1):
        corroboration = (
            f" [corroborated by {item.source_count} outlets]"
            if item.source_count > 1
            else ""
        )
        lines.append(
            f"{i}. [{item.bucket}] [{item.source}]{corroboration} "
            f"(score {item.score:.2f})\n"
            f"   TITLE: {item.title}\n"
            f"   SUMMARY: {item.summary[:320] or '(none provided)'}"
        )
    return "\n\n".join(lines)


def _format_market(market: MarketSnapshot) -> str:
    if not market.prices and market.fear_greed is None:
        return "(market data unavailable this run)"
    parts = [
        f"{sym} ${row['price']:,.2f} ({row['change_pct']:+.2f}% 24h)"
        for sym, row in market.prices.items()
    ]
    if market.fear_greed is not None:
        parts.append(f"Fear & Greed {market.fear_greed} ({market.fear_greed_label})")
    return " | ".join(parts)


def _fallback(items: list[NewsItem]) -> tuple[str, list[str]]:
    """Template-only output for when every LLM provider is down.

    Uses the top-ranked headline verbatim. Degraded, but honest and
    still correctly ordered -- the ranking never depended on the model.
    """
    headline = items[0].title if items else "No qualifying stories in the window"
    bullets = [f"{i.title} ({i.source})" for i in items[:6]]
    return headline, bullets


async def build_digest(items: list[NewsItem], market: MarketSnapshot) -> Digest:
    now = datetime.now(timezone.utc)

    if not items:
        return Digest(
            headline="No qualifying stories in the window",
            bullets=[],
            items=[],
            market=market,
            generated_at=now,
            llm_ok=True,
        )

    user_prompt = (
        f"MARKET CONTEXT (for tone only, do not restate verbatim):\n"
        f"{_format_market(market)}\n\n"
        f"RANKED STORIES ({len(items)}):\n\n{_format_items(items)}\n\n"
        f"Write the briefing. One bullet per story, in the order given, "
        f"maximum {len(items)} bullets."
    )

    result = await complete_json(SYSTEM_PROMPT, user_prompt)

    headline = str(result.data.get("headline") or "").strip()
    bullets = [
        str(b).strip()
        for b in (result.data.get("bullets") or [])
        if str(b).strip()
    ]

    # A provider can answer 200 OK with valid JSON and still give us
    # nothing usable. Treat empty output as a failure, not as a digest.
    if not result.ok or not headline or not bullets:
        headline, bullets = _fallback(items)
        return Digest(
            headline=headline,
            bullets=bullets,
            items=items,
            market=market,
            generated_at=now,
            llm_model=result.model,
            llm_ok=False,
        )

    return Digest(
        headline=headline,
        bullets=bullets,
        items=items,
        market=market,
        generated_at=now,
        llm_model=result.model,
        llm_ok=True,
    )

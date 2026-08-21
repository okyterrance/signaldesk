"""Telegram message rendering.

Everything uses HTML parse mode rather than MarkdownV2. MarkdownV2
requires escaping eighteen characters including `.` `-` `!` and `(`, which
appear constantly in news headlines and price figures; a single missed
escape returns a 400 and the message is simply never delivered. HTML mode
needs three escapes and fails loudly.

Layout rules, since Telegram gives no CSS and a wall of text is the
default failure mode:

  - One idea per line. Never pack score, source, category and age into
    one run of text.
  - A blank line between entries. It is the only paragraph break there is.
  - A fixed shape per entry — rank line, headline, attribution — so the
    eye learns it once and can then skim.
  - Rules (────) only between sections, never between entries; used too
    often they stop separating anything.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.config import settings
from src.models import Digest, MarketSnapshot, NewsItem
from src.scoring.categories import CATEGORY_EMOJI, CATEGORY_LABELS

TG_LIMIT = 4096  # Telegram's hard per-message ceiling

RULE = "━━━━━━━━━━━━━━━━"


def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def _local(dt: datetime) -> str:
    try:
        return dt.astimezone(ZoneInfo(settings.digest_tz)).strftime("%d %b · %H:%M")
    except Exception:
        return dt.strftime("%d %b · %H:%M UTC")


def _age(item: NewsItem) -> str:
    published = item.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
    if hours < 1:
        return f"{int(hours * 60)}m ago"
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours / 24)}d ago"


def _badge(item: NewsItem) -> str:
    if not item.category:
        return ""
    emoji = CATEGORY_EMOJI.get(item.category, "")
    label = CATEGORY_LABELS.get(item.category, item.category).split(" &")[0]
    return f"{emoji} {esc(label)}"


def _attribution(item: NewsItem) -> str:
    parts = [esc(item.source)]
    if item.source_count > 1:
        parts.append(f"{item.source_count} outlets")
    parts.append(_age(item))
    return " · ".join(parts)


def _entry(item: NewsItem, index: int) -> str:
    """One story, in the fixed three-line shape used everywhere."""
    head = f"<b>{index}</b>  <code>{item.score:.2f}</code>"
    badge = _badge(item)
    if badge:
        head += f"  {badge}"
    return (
        f"{head}\n"
        f"<a href=\"{esc(item.url)}\">{esc(item.title)}</a>\n"
        f"<i>{_attribution(item)}</i>"
    )


# --- market -----------------------------------------------------------

def market_line(market: MarketSnapshot) -> str:
    if not market.prices and market.fear_greed is None:
        return "<i>market data unavailable</i>"
    rows = []
    for sym, row in market.prices.items():
        arrow = "▲" if row["change_pct"] >= 0 else "▼"
        rows.append(
            f"<b>{esc(sym)}</b>  ${row['price']:,.0f}  "
            f"{arrow} {abs(row['change_pct']):.1f}%"
        )
    out = "\n".join(rows)
    if market.fear_greed is not None:
        out += f"\n\n<i>Fear &amp; Greed {market.fear_greed} · {esc(market.fear_greed_label)}</i>"
    return out


# --- primary views ----------------------------------------------------

def render_top(items: list[NewsItem], limit: int, depth: str = "balanced") -> str:
    if not items:
        return (
            "🏆 <b>Top stories</b>\n\n"
            "Nothing matched your categories in the last 24 hours.\n\n"
            "<i>Widen them with /weights.</i>"
        )

    from src.bot.preferences import DEPTH_LABELS

    lines = [
        "🏆 <b>Top stories</b>",
        f"<i>your weights · {esc(DEPTH_LABELS.get(depth, depth)).lower()}</i>",
        "",
        RULE,
        "",
    ]
    for i, item in enumerate(items[:limit], 1):
        lines.append(_entry(item, i))
        lines.append("")

    lines += [RULE, "", "<i>/digest for the written briefing</i>"]
    return _clip("\n".join(lines))


def render_digest(digest: Digest, depth: str = "balanced") -> str:
    lines = [
        "📊 <b>SignalDesk</b>",
        f"<i>{_local(digest.generated_at)}</i>",
        "",
        RULE,
        "",
        f"<b>{esc(digest.headline)}</b>",
        "",
    ]

    for bullet in digest.bullets:
        lines.append(f"▸ {esc(bullet)}")
        lines.append("")

    if digest.items:
        lines += [RULE, "", "<b>Sources</b>", ""]
        for i, item in enumerate(digest.items, 1):
            badge = _badge(item)
            lines.append(
                f"<b>{i}</b>  <code>{item.score:.2f}</code>"
                + (f"  {badge}" if badge else "")
            )
            lines.append(f"<a href=\"{esc(item.url)}\">{esc(item.title)}</a>")
            lines.append(f"<i>{_attribution(item)}</i>")
            lines.append("")

    lines += [RULE, "", market_line(digest.market)]

    if not digest.llm_ok:
        lines += ["", "<i>⚠️ Model unavailable — showing ranked headlines only</i>"]

    return _clip("\n".join(lines))


def render_alert(item: NewsItem) -> str:
    lines = [
        "🚨 <b>Alert</b>",
        f"<i>score {item.score:.2f} · above your threshold</i>",
        "",
        RULE,
        "",
    ]
    badge = _badge(item)
    if badge:
        lines.append(badge)
    lines += [
        f"<a href=\"{esc(item.url)}\">{esc(item.title)}</a>",
        "",
        f"<i>{_attribution(item)}</i>",
    ]
    if item.breakdown:
        drivers = " · ".join(f.name for f in item.breakdown.top_drivers(2))
        lines.append(f"<i>driven by {esc(drivers)}</i>")
    return _clip("\n".join(lines))


# --- settings ---------------------------------------------------------

def render_settings(prefs, weights: dict[str, float]) -> str:
    """The /weights screen: what you chose, and what it does to the formula.

    Showing the resulting weight table beside the toggles is the point.
    A settings screen that only says "Numbers-first: on" asks you to trust
    that it did something; this one shows the two numbers that moved.
    """
    from src.bot.preferences import DEPTH_BLURBS, DEPTH_LABELS
    from src.scoring.categories import CATEGORIES

    lines = [
        "⚖️ <b>Your settings</b>",
        "",
        RULE,
        "",
        "<b>Categories</b>",
        "<i>which subjects reach your digest</i>",
        "",
    ]
    for cid, label, blurb, _pattern in CATEGORIES:
        mark = "🟢" if cid in prefs.categories else "⚪️"
        lines.append(f"{mark}  {CATEGORY_EMOJI[cid]} <b>{esc(label)}</b>")
        lines.append(f"      <i>{esc(blurb)}</i>")
    lines.append("")

    lines += [
        RULE,
        "",
        "<b>Depth</b>",
        f"<i>{esc(DEPTH_BLURBS[prefs.depth])}</i>",
        "",
        f"▸ <b>{esc(DEPTH_LABELS[prefs.depth])}</b>",
        "",
        RULE,
        "",
        "<b>Your formula</b>",
        "<i>every story scores against this</i>",
        "",
        "<pre>",
    ]
    for name, weight in sorted(weights.items(), key=lambda kv: -kv[1]):
        marker = "  ←" if name in ("numeric", "analysis") else ""
        lines.append(f"{name:<15}{weight:.3f}{marker}")
    lines += [
        "</pre>",
        "<i>← set by your depth choice</i>",
        "",
        "<i>Tap below to change.</i>",
    ]
    return _clip("\n".join(lines))


def render_help() -> str:
    return (
        "🤖 <b>SignalDesk</b>\n"
        "<i>Ranks crypto and macro news by a transparent, configurable "
        "score — then writes the briefing.</i>\n\n"
        f"{RULE}\n\n"
        "<b>/top</b>\n"
        "<i>highest-ranked stories right now</i>\n\n"
        "<b>/digest</b>\n"
        "<i>the written briefing</i>\n\n"
        "<b>/weights</b>\n"
        "<i>choose your subjects and depth</i>\n\n"
        f"{RULE}\n\n"
        "<b>Automatic</b>\n"
        f"<i>Daily briefing at {esc(settings.digest_time)} "
        f"{esc(settings.digest_tz.split('/')[-1].replace('_', ' '))}</i>\n"
        "<i>Anything scoring above your threshold arrives immediately</i>"
    )


def render_why(item: NewsItem, index: int) -> str:
    """The transparency view: every factor, its weight, and its verdict.

    Kept out of /help to keep the command surface small, but still the
    thing to reach for when a ranking looks wrong.
    """
    if not item.breakdown:
        return "No breakdown recorded for that item."

    lines = [
        f"🔍 <b>Why #{index} scored {item.score:.3f}</b>",
        "",
        f"<a href=\"{esc(item.url)}\">{esc(item.title)}</a>",
        f"<i>{_attribution(item)}</i>",
        "",
        RULE,
        "",
        "<pre>",
        f"{'factor':<15}{'raw':>6}{'wt':>7}{'adds':>7}",
        "─" * 35,
    ]
    for factor in sorted(item.breakdown.factors, key=lambda f: -f.contribution):
        lines.append(
            f"{factor.name:<15}{factor.raw:>6.2f}{factor.weight:>7.3f}"
            f"{factor.contribution:>7.3f}"
        )
    lines += ["─" * 35, f"{'TOTAL':<15}{'':>6}{'':>7}{item.score:>7.3f}", "</pre>", ""]

    lines.append("<b>What drove it</b>")
    for factor in item.breakdown.top_drivers(3):
        lines.append(f"▸ <b>{esc(factor.name)}</b> — {esc(factor.reason)}")

    weakest = min(item.breakdown.factors, key=lambda f: f.contribution)
    lines += [
        "",
        "<b>What held it back</b>",
        f"▸ <b>{esc(weakest.name)}</b> — {esc(weakest.reason)}",
    ]
    return _clip("\n".join(lines))


def _clip(text: str) -> str:
    if len(text) <= TG_LIMIT:
        return text
    return text[: TG_LIMIT - 24].rsplit("\n", 1)[0] + "\n\n<i>…truncated</i>"

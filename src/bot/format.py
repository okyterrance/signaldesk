"""Telegram message rendering.

Everything uses HTML parse mode rather than MarkdownV2. MarkdownV2
requires escaping eighteen characters including `.` `-` `!` and `(`,
which appear constantly in news headlines and price figures; a single
missed escape returns a 400 and the message is simply never delivered.
HTML mode needs three escapes and fails loudly.
"""
from __future__ import annotations

import html
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import settings
from src.models import Digest, MarketSnapshot, NewsItem

TG_LIMIT = 4096  # Telegram's hard per-message ceiling


def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def _local(dt: datetime) -> str:
    try:
        return dt.astimezone(ZoneInfo(settings.digest_tz)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M UTC")


def _bar(value: float, width: int = 10) -> str:
    """Unicode meter. Telegram has no inline charts, so the bar is the chart."""
    filled = max(0, min(width, round(value * width)))
    return "█" * filled + "░" * (width - filled)


def market_line(market: MarketSnapshot) -> str:
    if not market.prices and market.fear_greed is None:
        return "<i>market data unavailable</i>"
    parts = []
    for sym, row in market.prices.items():
        arrow = "▲" if row["change_pct"] >= 0 else "▼"
        parts.append(
            f"<b>{esc(sym)}</b> ${row['price']:,.0f} {arrow}{abs(row['change_pct']):.1f}%"
        )
    line = "  ".join(parts)
    if market.fear_greed is not None:
        line += f"\nFear &amp; Greed <b>{market.fear_greed}</b> ({esc(market.fear_greed_label)})"
    return line


def render_digest(digest: Digest) -> str:
    head = [
        "📊 <b>SignalDesk Daily</b>",
        f"<i>{_local(digest.generated_at)} · {len(digest.items)} stories ranked</i>",
        "",
        f"<b>{esc(digest.headline)}</b>",
        "",
    ]
    body = [f"• {esc(b)}" for b in digest.bullets]

    sources = ["", "───────────", "<b>Sources</b>"]
    for i, item in enumerate(digest.items, 1):
        corroboration = f" ×{item.source_count}" if item.source_count > 1 else ""
        sources.append(
            f"{i}. <a href=\"{esc(item.url)}\">{esc(item.title[:80])}</a>\n"
            f"   <code>{item.score:.2f}</code> · {esc(item.source)}{corroboration}"
        )

    footer = [
        "",
        "───────────",
        market_line(digest.market),
        "",
        f"<i>/why 1 to see why story 1 ranked where it did</i>",
    ]
    if not digest.llm_ok:
        footer.append("<i>⚠️ LLM unavailable — showing raw ranked headlines</i>")

    return _clip("\n".join(head + body + sources + footer))


def render_top(items: list[NewsItem], limit: int) -> str:
    if not items:
        return "Nothing cleared the filters in the current window."
    lines = [
        f"🏆 <b>Top {min(limit, len(items))} right now</b>",
        "<i>ranked by the 7-factor score, highest first</i>",
        "",
    ]
    for i, item in enumerate(items[:limit], 1):
        corroboration = f" · ×{item.source_count} outlets" if item.source_count > 1 else ""
        lines.append(
            f"<b>{i}.</b> <a href=\"{esc(item.url)}\">{esc(item.title[:100])}</a>\n"
            f"<code>{_bar(item.score)} {item.score:.2f}</code>\n"
            f"<i>{esc(item.source)} · {esc(item.bucket)}{corroboration}</i>\n"
        )
    lines.append("<i>/why &lt;n&gt; for the factor breakdown</i>")
    return _clip("\n".join(lines))


def render_why(item: NewsItem, index: int) -> str:
    """The transparency view: every factor, its weight, and its verdict.

    This is the answer to "why is this at the top" -- not a model's
    self-explanation, but the actual arithmetic that produced the rank.
    """
    if not item.breakdown:
        return "No breakdown recorded for that item."

    lines = [
        f"🔍 <b>Why #{index} scored {item.score:.3f}</b>",
        "",
        f"<a href=\"{esc(item.url)}\">{esc(item.title[:110])}</a>",
        f"<i>{esc(item.source)} · {esc(item.bucket)}</i>",
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
        lines.append(f"• <b>{esc(factor.name)}</b> — {esc(factor.reason)}")

    weakest = min(item.breakdown.factors, key=lambda f: f.contribution)
    lines.append(f"\n<b>What held it back</b>\n• <b>{esc(weakest.name)}</b> — {esc(weakest.reason)}")
    return _clip("\n".join(lines))


def render_alert(item: NewsItem) -> str:
    drivers = ""
    if item.breakdown:
        drivers = " · ".join(f.name for f in item.breakdown.top_drivers(2))
    return _clip(
        f"🚨 <b>Threshold alert</b> — score <code>{item.score:.2f}</code>\n\n"
        f"<a href=\"{esc(item.url)}\">{esc(item.title[:150])}</a>\n\n"
        f"<i>{esc(item.source)}"
        + (f" · ×{item.source_count} outlets" if item.source_count > 1 else "")
        + (f"\ndriven by: {esc(drivers)}" if drivers else "")
        + "</i>"
    )


def render_status(stats: dict, market: MarketSnapshot, threshold: float) -> str:
    failed = stats.get("feeds_failed") or []
    rejected = stats.get("rejected") or {}
    buckets = stats.get("buckets") or {}

    lines = [
        "⚙️ <b>Pipeline status</b>",
        "",
        f"Feeds: <b>{stats.get('feeds_ok', 0)}/{stats.get('feeds_total', 0)}</b> responding",
    ]
    if failed:
        lines.append(f"  <i>down: {esc(', '.join(failed))}</i>")

    lines += ["", f"Items passing hard filters: <b>{stats.get('items_kept', 0)}</b>"]
    if rejected:
        lines.append("Rejected before scoring:")
        for reason, count in sorted(rejected.items(), key=lambda kv: -kv[1]):
            lines.append(f"  • {esc(reason)}: {count}")

    if buckets:
        lines.append("")
        for bucket, bstats in buckets.items():
            lines.append(
                f"<b>{esc(bucket)}</b>: {bstats['fetched']} fetched → "
                f"{bstats['after_dedupe']} after dedupe → "
                f"<b>{bstats['selected']}</b> selected"
            )

    lines += [
        "",
        f"Alert threshold: <code>{threshold:.2f}</code>",
        f"Digest time: <code>{esc(settings.digest_time)} {esc(settings.digest_tz)}</code>",
        "",
        market_line(market),
    ]
    return _clip("\n".join(lines))


def render_help() -> str:
    return (
        "🤖 <b>SignalDesk</b>\n"
        "<i>Ranks crypto and macro news by a transparent 7-factor score, "
        "then writes the briefing.</i>\n\n"
        "<b>Commands</b>\n"
        "/top [n] — top ranked stories right now (default 5)\n"
        "/why &lt;n&gt; — full factor breakdown for story n\n"
        "/digest — generate and send the briefing now\n"
        "/market — prices and sentiment\n"
        "/weights — the scoring formula\n"
        "/threshold [0-1] — view or set the alert threshold\n"
        "/status — pipeline health and reject counts\n\n"
        "<b>Automatic</b>\n"
        f"• Daily briefing at {esc(settings.digest_time)} {esc(settings.digest_tz)}\n"
        f"• Any story scoring ≥ threshold is pushed immediately\n"
    )


def render_weights(weights: dict[str, float]) -> str:
    lines = [
        "⚖️ <b>Scoring formula</b>",
        "<i>score = Σ(weight × factor) / Σ(weight), all factors normalised to 0–1</i>",
        "",
        "<pre>",
    ]
    for name, weight in sorted(weights.items(), key=lambda kv: -kv[1]):
        lines.append(f"{name:<15}{weight:.3f}  {_bar(weight / 0.222, 8)}")
    lines += [
        "</pre>",
        "",
        "<b>keyword</b> — 4 tiers, highest hit wins (fed/cpi/hack → 1.0)",
        "<b>recency</b> — linear decay to zero over 24h",
        "<b>source_quality</b> — per-outlet, FT/Bloomberg 1.0 → unrated 0.60",
        "<b>category</b> — topical gate from feed tags",
        "<b>source_count</b> — corroboration, capped low on purpose so one "
        "big story cannot hold the digest for days",
        "<b>numeric</b> — headline carries a concrete figure",
        "<b>asset</b> — BTC/ETH 1.0, large alts 0.7, memecoins 0.3",
    ]
    return _clip("\n".join(lines))


def _clip(text: str) -> str:
    if len(text) <= TG_LIMIT:
        return text
    return text[: TG_LIMIT - 20].rsplit("\n", 1)[0] + "\n<i>…truncated</i>"

"""Telegram command handlers.

Every handler that needs ranked data goes through `_ensure_items`, which
serves the cached run when it is recent and only re-runs the pipeline
when it is stale. Twelve HTTP fetches per keystroke would be both slow
and rude to the feeds.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from src import pipeline
from src.bot import format as fmt
from src.bot.state import state
from src.config import settings
from src.llm.digest import build_digest
from src.models import NewsItem
from src.scoring.weights import FACTOR_WEIGHTS

log = logging.getLogger(__name__)

_SEND = {"parse_mode": ParseMode.HTML, "disable_web_page_preview": True}


async def _ensure_items(update: Update, force: bool = False) -> list[NewsItem]:
    """Return ranked items, re-running the pipeline only when stale."""
    if not force and state.is_fresh():
        return state.last_items

    if update.effective_chat:
        await update.effective_chat.send_action(ChatAction.TYPING)

    result = await pipeline.run()
    state.remember(result.items, result.market, result.stats)
    return result.items


# --- commands ---------------------------------------------------------

async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(fmt.render_help(), **_SEND)


async def top(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    limit = 5
    if ctx.args:
        try:
            limit = max(1, min(10, int(ctx.args[0])))
        except ValueError:
            await update.message.reply_text("Usage: /top [1-10]")
            return

    items = await _ensure_items(update)
    await update.message.reply_text(fmt.render_top(items, limit), **_SEND)


async def why(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not ctx.args:
        await update.message.reply_text(
            "Usage: <code>/why 1</code> — the number from /top or the digest.",
            **_SEND,
        )
        return
    try:
        index = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("That is not a number. Try <code>/why 1</code>.", **_SEND)
        return

    items = await _ensure_items(update)
    if not 1 <= index <= len(items):
        await update.message.reply_text(
            f"Pick a number between 1 and {len(items)}."
        )
        return

    await update.message.reply_text(fmt.render_why(items[index - 1], index), **_SEND)


async def digest(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat:
        await update.effective_chat.send_action(ChatAction.TYPING)

    result = await pipeline.run()
    state.remember(result.items, result.market, result.stats)
    built = await build_digest(result.items, result.market)
    await update.message.reply_text(fmt.render_digest(built), **_SEND)


async def market(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from src.fetchers.market import fetch_market

    snapshot = await fetch_market()
    state.last_market = snapshot
    await update.message.reply_text(fmt.market_line(snapshot), **_SEND)


async def weights(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(fmt.render_weights(FACTOR_WEIGHTS), **_SEND)


async def threshold(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    current = state.alert_threshold or settings.alert_threshold
    if not ctx.args:
        await update.message.reply_text(
            f"Alert threshold is <code>{current:.2f}</code>.\n"
            f"Set it with <code>/threshold 0.75</code> — higher means fewer, "
            f"more selective alerts.",
            **_SEND,
        )
        return
    try:
        value = float(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Usage: /threshold 0.75")
        return
    if not 0.0 < value <= 1.0:
        await update.message.reply_text("Threshold must be between 0 and 1.")
        return

    state.alert_threshold = value
    await update.message.reply_text(
        f"Alert threshold set to <code>{value:.2f}</code>.", **_SEND
    )


async def status(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _ensure_items(update, force=True)
    await update.message.reply_text(
        fmt.render_status(
            state.last_stats,
            state.last_market,
            state.alert_threshold or settings.alert_threshold,
        ),
        **_SEND,
    )


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the traceback, tell the user something plain.

    Handlers reach the network on nearly every call, so failures are
    expected rather than exceptional. What must not happen is silence.
    """
    log.error("handler error", exc_info=ctx.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Something broke on my side. It is logged — try again in a moment."
        )

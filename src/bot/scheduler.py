"""The two automatic jobs: the daily digest, and the threshold alert loop.

The alert loop is where the scoring engine earns its keep. It re-runs the
pipeline on a short interval and pushes anything at or above the threshold
*immediately*, instead of holding it for the morning. A digest answers
"what happened yesterday"; an alert answers "this cannot wait".

Both run against the destination chat's own preferences, so the scheduled
briefing is filtered and weighted exactly like the one that chat gets from
/digest. A push that ignored the reader's settings would be the one place
the whole configuration silently did not apply.

Both are registered on python-telegram-bot's JobQueue, so they share the
bot's event loop and no separate scheduler process is needed.
"""
from __future__ import annotations

import logging
from datetime import time as dt_time
from zoneinfo import ZoneInfo

from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from src import pipeline
from src.bot import format as fmt
from src.bot.preferences import store
from src.bot.state import state
from src.config import settings
from src.llm.digest import build_digest

log = logging.getLogger(__name__)

_SEND = {"parse_mode": ParseMode.HTML, "disable_web_page_preview": True}


async def daily_digest_job(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = settings.telegram_chat_id
    prefs = store.get(chat_id)
    log.info("running scheduled digest (depth=%s, %s categories)",
             prefs.depth, len(prefs.categories))
    try:
        result = await pipeline.run(
            enabled_categories=prefs.categories, depth=prefs.depth
        )
        state.remember(chat_id, prefs, result.items, result.market, result.stats)

        built = await build_digest(result.items, result.market)
        await ctx.bot.send_message(
            chat_id=chat_id, text=fmt.render_digest(built, prefs.depth), **_SEND
        )
        # Anything in the digest should not also fire as an alert minutes
        # later. The reader has already seen it.
        for item in result.items:
            state.mark_alerted(item)
        log.info("digest sent: %s stories", len(result.items))
    except Exception:
        log.exception("scheduled digest failed")


async def alert_job(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = settings.telegram_chat_id
    prefs = store.get(chat_id)
    threshold = state.alert_threshold or settings.alert_threshold
    try:
        result = await pipeline.run(
            with_market=False,
            enabled_categories=prefs.categories,
            depth=prefs.depth,
        )

        fired = 0
        for item in result.items:
            if item.score < threshold:
                break  # sorted, so nothing below here qualifies
            if not state.should_alert(item):
                continue
            await ctx.bot.send_message(
                chat_id=chat_id, text=fmt.render_alert(item, threshold), **_SEND
            )
            state.mark_alerted(item)
            fired += 1

        if fired:
            log.info("alerts fired: %s (threshold %.2f)", fired, threshold)
    except Exception:
        log.exception("alert poll failed")


def register_jobs(app: Application) -> None:
    hour, minute = (int(x) for x in settings.digest_time.split(":"))
    tz = ZoneInfo(settings.digest_tz)

    app.job_queue.run_daily(
        daily_digest_job,
        time=dt_time(hour=hour, minute=minute, tzinfo=tz),
        name="daily_digest",
    )

    # first=60 rather than 0: let the process finish starting before the
    # first twelve-feed fetch goes out.
    app.job_queue.run_repeating(
        alert_job,
        interval=settings.alert_poll_minutes * 60,
        first=60,
        name="alert_poll",
    )

    log.info(
        "jobs registered: digest %s %s, alerts every %smin",
        settings.digest_time,
        settings.digest_tz,
        settings.alert_poll_minutes,
    )

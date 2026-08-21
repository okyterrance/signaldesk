"""SignalDesk entry point.

    python main.py            run the bot (commands + scheduled jobs)
    python main.py --once     run the pipeline once, print to stdout, exit
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from src.config import settings  # noqa: E402  (must follow load_dotenv)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# httpx logs every request at INFO, which drowns out our own lines.
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("signaldesk")


def _ellipsize(text: str, width: int) -> str:
    """Truncate on a word boundary. Cutting mid-word looks like a crash."""
    if len(text) <= width:
        return text
    return text[: width - 1].rsplit(" ", 1)[0] + "…"


async def run_once(demo: bool = False) -> None:
    """Dry run with no Telegram involved -- the fastest way to see the ranking."""
    from src import pipeline
    from src.llm.digest import build_digest

    if demo:
        from src.demo import run_demo

        result = run_demo()
        print("\n*** DEMO MODE — bundled sample data, no network ***")
    else:
        result = await pipeline.run()

    print(f"\n{'=' * 62}")
    print(f"  {result.stats.get('items_kept', 0)} items passed filters "
          f"-> {len(result.items)} selected")
    print(f"  feeds: {result.stats.get('feeds_ok')}/{result.stats.get('feeds_total')} ok")
    if result.stats.get("feeds_failed"):
        print(f"  down:  {', '.join(result.stats['feeds_failed'])}")
    print(f"{'=' * 62}\n")

    for i, item in enumerate(result.items, 1):
        bar = "█" * round(item.score * 20)
        print(f"{i:2}. [{item.score:.3f}] {bar}")
        print(f"    {_ellipsize(item.title, 76)}")
        print(f"    {item.source} · {item.bucket}"
              + (f" · x{item.source_count} outlets" if item.source_count > 1 else ""))
        if item.breakdown:
            drivers = ", ".join(
                f"{f.name}={f.raw:.2f}" for f in item.breakdown.top_drivers(3)
            )
            print(f"    drivers: {drivers}")
        print()

    if settings.tokenrouter_api_key and not demo:
        digest = await build_digest(result.items, result.market)
        print(f"{'=' * 62}")
        print(f"  DIGEST  ({digest.llm_model or 'fallback'})")
        print(f"{'=' * 62}")
        print(f"\n{digest.headline}\n")
        for bullet in digest.bullets:
            print(f"  • {bullet}")
        print()
    elif demo:
        print("(demo mode — skipping the LLM call; ranking above is real)\n")
    else:
        print("(TOKENROUTER_API_KEY unset — skipping the written digest)\n")


def run_bot() -> None:
    from telegram.ext import Application, CommandHandler

    from src.bot import handlers
    from src.bot.scheduler import register_jobs

    missing = settings.missing_required()
    if missing:
        log.error("missing required env vars: %s", ", ".join(missing))
        log.error("copy .env.example to .env and fill them in")
        sys.exit(1)

    app = Application.builder().token(settings.telegram_bot_token).build()

    for command, handler in [
        ("start", handlers.start),
        ("help", handlers.start),
        ("top", handlers.top),
        ("why", handlers.why),
        ("digest", handlers.digest),
        ("market", handlers.market),
        ("weights", handlers.weights),
        ("threshold", handlers.threshold),
        ("status", handlers.status),
    ]:
        app.add_handler(CommandHandler(command, handler))

    app.add_error_handler(handlers.on_error)
    register_jobs(app)

    log.info("SignalDesk is up. Talk to your bot on Telegram.")
    app.run_polling(drop_pending_updates=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="SignalDesk")
    parser.add_argument(
        "--once",
        action="store_true",
        help="run the pipeline once against live feeds, print the ranking, exit",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="same, but on bundled sample data with no network calls",
    )
    args = parser.parse_args()

    if args.once or args.demo:
        asyncio.run(run_once(demo=args.demo))
    else:
        run_bot()


if __name__ == "__main__":
    main()

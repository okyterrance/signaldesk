"""Price and sentiment snapshot from public, unauthenticated endpoints.

Binance's 24hr ticker and the alternative.me Fear & Greed index both
serve anonymous requests. Neither needs a key, an account, or a quota
negotiation, which keeps the whole bot's marginal cost at the LLM call
alone.

Market data is decoration here, not signal: it is context printed beside
the ranked stories, and nothing in the scoring formula reads it. So a
failure degrades the digest rather than blocking it.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.fetchers._http import get_with_retry, make_session
from src.models import MarketSnapshot

log = logging.getLogger(__name__)

BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"
FEAR_GREED = "https://api.alternative.me/fng/?limit=1"

SYMBOLS = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "SOLUSDT": "SOL",
    "XRPUSDT": "XRP",
}


async def fetch_market() -> MarketSnapshot:
    snapshot = MarketSnapshot(fetched_at=datetime.now(timezone.utc))

    async with make_session(timeout=15.0) as client:

        async def _prices() -> None:
            try:
                response = await get_with_retry(client, BINANCE_TICKER)
                for row in response.json():
                    label = SYMBOLS.get(row.get("symbol", ""))
                    if not label:
                        continue
                    snapshot.prices[label] = {
                        "price": float(row["lastPrice"]),
                        "change_pct": float(row["priceChangePercent"]),
                    }
            except Exception as exc:
                log.warning("binance ticker failed (%s)", type(exc).__name__)

        async def _sentiment() -> None:
            try:
                response = await get_with_retry(client, FEAR_GREED)
                row = (response.json().get("data") or [{}])[0]
                if row.get("value"):
                    snapshot.fear_greed = int(row["value"])
                    snapshot.fear_greed_label = row.get("value_classification", "")
            except Exception as exc:
                log.warning("fear & greed failed (%s)", type(exc).__name__)

        await asyncio.gather(_prices(), _sentiment())

    return snapshot

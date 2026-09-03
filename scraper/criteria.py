"""Kriter değerlendirme: 15 gün kuralı + iki acil bayrağı."""
import logging
from datetime import date, datetime, timezone

from . import config
from .market_calendar import minutes_to_close

log = logging.getLogger(__name__)

PURCHASE_KEYWORDS = ("purchase", "buy", " p ", "p")


def is_purchase(transaction_type: str) -> bool:
    t = (transaction_type or "").strip().lower()
    if not t:
        return False
    if t in ("p", "purchase", "buy"):
        return True
    return t.startswith("purchase") or t.startswith("buy")


def evaluate(tx: dict, filing_date: date, sp500_tickers: set, now_utc: datetime) -> dict:
    """tx: {'ticker','asset_name','transaction_type','transaction_date','amount_range'}
    Döner: {'passes_base','delay_days','urgent_reasons': [...]}"""
    tx_date = tx.get("transaction_date")
    result = {"passes_base": False, "delay_days": None, "urgent_reasons": []}

    if not tx_date or not filing_date:
        return result

    delay_days = (filing_date - tx_date).days
    result["delay_days"] = delay_days
    result["passes_base"] = delay_days < config.MAX_DELAY_DAYS

    if not result["passes_base"]:
        return result

    mins = minutes_to_close(now_utc)
    if mins is not None and mins <= config.URGENT_MINUTES_TO_CLOSE:
        result["urgent_reasons"].append("kapanışa_yakın")

    ticker = (tx.get("ticker") or "").strip().upper()
    if is_purchase(tx.get("transaction_type")) and ticker:
        if sp500_tickers and ticker not in sp500_tickers:
            result["urgent_reasons"].append("dev_şirket_dışı")

    return result

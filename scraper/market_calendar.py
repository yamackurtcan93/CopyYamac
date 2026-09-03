"""NYSE takvimi: kapanış saatine kalan süreyi hesaplar (tatiller ve erken
kapanış günleri dahil - pandas_market_calendars kütüphanesi sayesinde).
"""
import logging
from datetime import datetime, timedelta, timezone

import pandas_market_calendars as mcal

log = logging.getLogger(__name__)

_nyse = mcal.get_calendar("NYSE")


def minutes_to_close(now_utc: datetime):
    """Şu an (UTC) piyasa açıksa, kapanışa kalan dakikayı döner.
    Piyasa kapalıysa (hafta sonu, tatil, mesai dışı) None döner."""
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    start = (now_utc - timedelta(days=1)).date()
    end = (now_utc + timedelta(days=1)).date()
    schedule = _nyse.schedule(start_date=start, end_date=end)
    if schedule.empty:
        return None

    for _, row in schedule.iterrows():
        market_open = row["market_open"].to_pydatetime()
        market_close = row["market_close"].to_pydatetime()
        if market_open <= now_utc <= market_close:
            delta = market_close - now_utc
            return delta.total_seconds() / 60.0
    return None

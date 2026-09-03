"""S&P 500 bileşen listesini çeker ve önbelleğe alır.

'Dev şirket' tanımı: S&P 500 üyeliği. Bu listede OLMAYAN bir şirkette
gerçekleşen SATIN ALMA işlemi, acil kriterlerinden biridir.
"""
import logging
from datetime import datetime, timezone

import pandas as pd
import requests

from . import config
from .state import load_json, save_json

log = logging.getLogger(__name__)

# Birincil kaynak: topluluk tarafından bakımı yapılan, sık güncellenen CSV.
PRIMARY_SOURCE = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
    "main/data/constituents.csv"
)
# Yedek kaynak: Wikipedia'daki S&P 500 tablosu.
FALLBACK_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def _fetch_from_primary() -> set:
    resp = requests.get(PRIMARY_SOURCE, timeout=30)
    resp.raise_for_status()
    from io import StringIO

    df = pd.read_csv(StringIO(resp.text))
    col = "Symbol" if "Symbol" in df.columns else df.columns[0]
    return {str(s).strip().upper() for s in df[col].dropna()}


def _fetch_from_wikipedia() -> set:
    resp = requests.get(
        FALLBACK_WIKI_URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (congress-trade-alert bot)"},
    )
    resp.raise_for_status()
    tables = pd.read_html(resp.text)
    df = tables[0]
    col = "Symbol" if "Symbol" in df.columns else df.columns[0]
    return {str(s).strip().upper() for s in df[col].dropna()}


def get_sp500_tickers() -> set:
    """Önbellek yoksa/eskiyse günceller, aksi halde önbellekten döner."""
    cache = load_json(config.SP500_CACHE_PATH, None)
    if cache:
        fetched_at = datetime.fromisoformat(cache["fetched_at"])
        age_days = (datetime.now(timezone.utc) - fetched_at).days
        if age_days < config.SP500_REFRESH_DAYS and cache.get("tickers"):
            return set(cache["tickers"])

    tickers = None
    try:
        tickers = _fetch_from_primary()
    except Exception as e:  # noqa: BLE001
        log.warning("S&P 500 birincil kaynak başarısız: %s", e)

    if not tickers:
        try:
            tickers = _fetch_from_wikipedia()
        except Exception as e:  # noqa: BLE001
            log.warning("S&P 500 yedek kaynak (Wikipedia) da başarısız: %s", e)

    if not tickers:
        # Hiçbir kaynak çalışmadıysa, eski önbellek varsa onu kullan (yoksa boş küme).
        if cache and cache.get("tickers"):
            log.warning("Güncel S&P 500 listesi alınamadı, eski önbellek kullanılıyor.")
            return set(cache["tickers"])
        log.error("S&P 500 listesi hiçbir kaynaktan alınamadı.")
        return set()

    save_json(
        config.SP500_CACHE_PATH,
        {"fetched_at": datetime.now(timezone.utc).isoformat(), "tickers": sorted(tickers)},
    )
    return tickers

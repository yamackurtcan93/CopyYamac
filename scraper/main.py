"""Ana orkestrasyon: House + Senate'i tara, yeni filing'leri kriterlere göre
değerlendir, bildirim gönder, durumu kaydet."""
import logging
from datetime import datetime, timezone

import requests

from . import config, criteria, house, notify, senate, sp500
from .state import load_seen, save_seen, touch_last_run

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("main")


def process_source_items(items: list, seen: dict, source_key: str, sp500_tickers: set, now_utc):
    for item in items:
        report_id = item["report_id"]
        if report_id in seen[source_key]:
            continue

        for tx in item.get("transactions", []):
            result = criteria.evaluate(tx, item["filing_date"], sp500_tickers, now_utc)
            if result["passes_base"]:
                try:
                    notify.dispatch(item, tx, result)
                except Exception as e:  # noqa: BLE001
                    log.error("Bildirim gönderilirken hata: %s", e)
            else:
                log.info(
                    "Kriter dışı (gecikme=%s gün): %s - %s",
                    result["delay_days"],
                    item["filer_name"],
                    tx.get("ticker"),
                )

        seen[source_key].append(report_id)


def main():
    now_utc = datetime.now(timezone.utc)
    seen = load_seen(config.SEEN_STATE_PATH)
    seen.setdefault("house", [])
    seen.setdefault("senate", [])

    sp500_tickers = sp500.get_sp500_tickers()
    log.info("S&P 500 listesinde %d şirket var.", len(sp500_tickers))

    # --- Senate ---
    try:
        session = senate.get_session_ready()
        senate_items = senate.fetch_new_ptrs(session, days_back=10)
        log.info("Senate: %d yeni/aday PTR bulundu.", len(senate_items))
        process_source_items(senate_items, seen, "senate", sp500_tickers, now_utc)
    except Exception as e:  # noqa: BLE001
        log.error("Senate tarama hatası: %s", e)

    # --- House ---
    try:
        h_session = requests.Session()
        house_items = house.fetch_new_ptrs(h_session, set(seen["house"]))
        log.info("House: %d yeni PTR bulundu.", len(house_items))
        process_source_items(house_items, seen, "house", sp500_tickers, now_utc)
    except Exception as e:  # noqa: BLE001
        log.error("House tarama hatası: %s", e)

    save_seen(config.SEEN_STATE_PATH, seen)
    touch_last_run(config.LAST_RUN_PATH)
    log.info("Çalışma tamamlandı.")


if __name__ == "__main__":
    main()

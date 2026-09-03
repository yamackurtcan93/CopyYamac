"""Senate eFD (efdsearch.senate.gov) - Periodic Transaction Report (PTR) tarayıcı.

NOT: Bu site resmi bir devlet sistemi olup HTML/JS yapısı zaman zaman
değişebilir. Bu modül, halka açık benzer araçların (senate stock watcher
tarzı projeler) belgelediği istek biçimini temel alır. İlk canlı
çalıştırmada bir hata alınırsa, GitHub Actions log çıktısını paylaşmak
düzeltmeyi hızlandırır.
"""
import logging
import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE = "https://efdsearch.senate.gov"
HOME_URL = f"{BASE}/search/home/"
DATA_URL = f"{BASE}/search/report/data/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; congress-trade-alert/1.0)",
    "Referer": f"{BASE}/search/",
}


def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _get_csrf(session: requests.Session, url: str) -> str:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    inp = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if inp is None:
        raise RuntimeError(f"csrfmiddlewaretoken bulunamadı: {url}")
    return inp["value"]


def _accept_agreement(session: requests.Session) -> None:
    csrf = _get_csrf(session, HOME_URL)
    resp = session.post(
        HOME_URL,
        data={"csrfmiddlewaretoken": csrf, "prohibition_agreement": "1"},
        timeout=30,
    )
    resp.raise_for_status()


def _search_recent_reports(session: requests.Session, days_back: int) -> list:
    """Son N gün içinde submit edilmiş TÜM rapor tiplerini çeker; PTR
    filtresi çağıran main.py tarafında rapor başlığı metnine bakılarak
    yapılır (rapor tipi kodlarına güvenmek yerine)."""
    csrf = _get_csrf(session, f"{BASE}/search/")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%m/%d/%Y 00:00:00"
    )
    payload = {
        "start": "0",
        "length": "200",
        "report_types": "[]",
        "filer_types": "[]",
        "submitted_start_date": start_date,
        "submitted_end_date": "",
        "candidate_state": "",
        "senator_state": "",
        "office_id": "",
        "first_name": "",
        "last_name": "",
        "csrfmiddlewaretoken": csrf,
    }
    resp = session.post(DATA_URL, data=payload, timeout=30)
    resp.raise_for_status()
    js = resp.json()
    return js.get("data", [])


def _cell_text_and_href(cell_html: str):
    soup = BeautifulSoup(cell_html, "lxml")
    a = soup.find("a")
    if a is not None:
        return a.get_text(strip=True), a.get("href", "")
    return BeautifulSoup(cell_html, "lxml").get_text(strip=True), ""


def _parse_ptr_html(session: requests.Session, url: str) -> list:
    """Elektronik PTR raporunun HTML tablosunu ayrıştırır."""
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    target_table = None
    for table in soup.find_all("table"):
        header_text = table.get_text(" ", strip=True).lower()
        if "transaction date" in header_text and "ticker" in header_text:
            target_table = table
            break
    if target_table is None:
        log.warning("PTR tablosu bulunamadı: %s", url)
        return []

    headers_row = target_table.find("thead")
    if headers_row:
        headers = [th.get_text(strip=True).lower() for th in headers_row.find_all("th")]
    else:
        first_tr = target_table.find("tr")
        headers = [th.get_text(strip=True).lower() for th in first_tr.find_all(["th", "td"])]

    rows_out = []
    body = target_table.find("tbody") or target_table
    for tr in body.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cells or len(cells) != len(headers):
            continue
        row = dict(zip(headers, cells))
        rows_out.append(row)
    return rows_out


def fetch_new_ptrs(session: requests.Session, days_back: int = 10) -> list:
    """Son `days_back` gün içinde bildirilmiş PTR'leri döner.

    Her öğe: {
        'source': 'senate', 'report_id': str, 'filer_name': str,
        'filing_date': date, 'source_url': str,
        'transactions': [ {ticker, asset_name, transaction_type,
                            transaction_date, amount_range}, ... ]
    }
    """
    results = []
    rows = _search_recent_reports(session, days_back)
    for row in rows:
        try:
            first_name = BeautifulSoup(row[0], "lxml").get_text(strip=True)
            last_name = BeautifulSoup(row[1], "lxml").get_text(strip=True)
            report_text, href = _cell_text_and_href(row[3])
            filed_str = BeautifulSoup(row[4], "lxml").get_text(strip=True)
        except (IndexError, TypeError):
            continue

        if "periodic transaction" not in report_text.lower():
            continue
        if not href:
            continue

        report_url = href if href.startswith("http") else f"{BASE}{href}"
        try:
            filing_date = datetime.strptime(filed_str, "%m/%d/%Y").date()
        except ValueError:
            log.warning("Tarih ayrıştırılamadı: %s", filed_str)
            continue

        report_id = href.strip("/").split("/")[-1]

        if href.lower().endswith(".pdf") or "/paper/" in href.lower():
            log.info("Kağıt (PDF) PTR şimdilik atlanıyor: %s", report_url)
            continue

        try:
            tx_rows = _parse_ptr_html(session, report_url)
        except Exception as e:  # noqa: BLE001
            log.warning("PTR ayrıştırma hatası (%s): %s", report_url, e)
            continue

        transactions = []
        for tx in tx_rows:
            tx_date_str = tx.get("transaction date", "")
            try:
                tx_date = datetime.strptime(tx_date_str, "%m/%d/%Y").date()
            except ValueError:
                tx_date = None
            transactions.append(
                {
                    "ticker": tx.get("ticker", "").strip().upper(),
                    "asset_name": tx.get("asset name", tx.get("asset", "")).strip(),
                    "transaction_type": tx.get("type", "").strip(),
                    "transaction_date": tx_date,
                    "amount_range": tx.get("amount", "").strip(),
                }
            )

        results.append(
            {
                "source": "senate",
                "report_id": f"senate-{report_id}",
                "filer_name": f"{first_name} {last_name}".strip(),
                "filing_date": filing_date,
                "source_url": report_url,
                "transactions": transactions,
            }
        )
    return results


def get_session_ready() -> requests.Session:
    session = _new_session()
    _accept_agreement(session)
    return session

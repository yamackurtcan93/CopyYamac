"""House Clerk (disclosures-clerk.house.gov) - Periodic Transaction Report
(PTR) tarayıcı.

Yaklaşım: Her yıl için yayınlanan toplu ZIP indeksini indirir (tüm o yılki
filing'lerin metadata'sı), FilingType == 'P' (Periodic Transaction Report)
olanları süzer, ilgili PDF'i indirip pdfplumber ile tablo satırlarını
ayrıştırır.

NOT: PDF tablo yapısı yıllar içinde küçük farklılıklar gösterebilir. Bir
satır ayrıştırılamazsa o satır atlanır ve loglanır; tüm çalışma durmaz.
"""
import io
import logging
import zipfile
from datetime import datetime, timezone

import pdfplumber
import requests

log = logging.getLogger(__name__)

BASE = "https://disclosures-clerk.house.gov"
ZIP_URL_TMPL = f"{BASE}/public_disc/financial-pdfs/{{year}}FD.zip"
PDF_URL_TMPL = f"{BASE}/public_disc/ptr-pdfs/{{year}}/{{doc_id}}.pdf"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; congress-trade-alert/1.0)"}


def _download_index(year: int, session: requests.Session) -> list:
    url = ZIP_URL_TMPL.format(year=year)
    resp = session.get(url, timeout=60, headers=HEADERS)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    txt_name = next((n for n in zf.namelist() if n.lower().endswith(".txt")), None)
    if txt_name is None:
        log.warning("%s içinde .txt indeks bulunamadı", url)
        return []
    raw = zf.read(txt_name).decode("latin-1")

    lines = raw.splitlines()
    if not lines:
        return []
    delim = "\t" if "\t" in lines[0] else ("|" if "|" in lines[0] else ",")
    header = [h.strip().lower() for h in lines[0].split(delim)]

    records = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(delim)
        if len(parts) != len(header):
            continue
        rec = dict(zip(header, [p.strip() for p in parts]))
        records.append(rec)
    return records


def _find_col(rec: dict, *candidates):
    for c in candidates:
        if c in rec:
            return rec[c]
    return ""


def _parse_pdf_transactions(pdf_bytes: bytes) -> list:
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or not table[0]:
                    continue
                header = [str(c or "").strip().lower() for c in table[0]]
                if not any("asset" in h for h in header):
                    continue
                idx = {}
                for i, h in enumerate(header):
                    if "asset" in h:
                        idx["asset"] = i
                    elif "transaction" in h and "type" in h:
                        idx["type"] = i
                    elif h.startswith("date") or h == "date":
                        idx.setdefault("date", i)
                    elif "notification" in h:
                        idx["notification"] = i
                    elif "amount" in h:
                        idx["amount"] = i
                for row in table[1:]:
                    if not row or "asset" not in idx:
                        continue
                    try:
                        asset_cell = (row[idx["asset"]] or "").strip()
                    except IndexError:
                        continue
                    if not asset_cell:
                        continue
                    ticker = ""
                    if "(" in asset_cell and ")" in asset_cell:
                        try:
                            ticker = asset_cell.split("(")[-1].split(")")[0].strip()
                        except IndexError:
                            ticker = ""

                    def cell(key):
                        i = idx.get(key)
                        if i is None or i >= len(row):
                            return ""
                        return (row[i] or "").strip()

                    tx_date = None
                    for fmt in ("%m/%d/%Y",):
                        try:
                            tx_date = datetime.strptime(cell("date"), fmt).date()
                            break
                        except ValueError:
                            continue

                    out.append(
                        {
                            "ticker": ticker,
                            "asset_name": asset_cell,
                            "transaction_type": cell("type"),
                            "transaction_date": tx_date,
                            "amount_range": cell("amount"),
                        }
                    )
    return out


def fetch_new_ptrs(session: requests.Session, seen_doc_ids: set, year: int = None) -> list:
    """Bu yılki (veya belirtilen yılın) indeksten, daha önce görülmemiş
    PTR filing'lerini indirip ayrıştırır."""
    if year is None:
        year = datetime.now(timezone.utc).year

    try:
        records = _download_index(year, session)
    except Exception as e:  # noqa: BLE001
        log.warning("House indeksi indirilemedi (%s): %s", year, e)
        return []

    results = []
    for rec in records:
        filing_type = _find_col(rec, "filingtype", "filing_type", "type")
        if filing_type.strip().upper() != "P":
            continue
        doc_id = _find_col(rec, "docid", "doc_id")
        if not doc_id or f"house-{doc_id}" in seen_doc_ids:
            continue

        filing_date_str = _find_col(rec, "filingdate", "filing_date")
        try:
            filing_date = datetime.strptime(filing_date_str, "%m/%d/%Y").date()
        except ValueError:
            log.warning("House filing tarihi ayrıştırılamadı: %s", filing_date_str)
            continue

        last = _find_col(rec, "last")
        first = _find_col(rec, "first")
        state_dst = _find_col(rec, "statedst", "state_dst")

        pdf_url = PDF_URL_TMPL.format(year=year, doc_id=doc_id)
        try:
            resp = session.get(pdf_url, timeout=60, headers=HEADERS)
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001
            log.warning("House PDF indirilemedi (%s): %s", pdf_url, e)
            continue

        try:
            transactions = _parse_pdf_transactions(resp.content)
        except Exception as e:  # noqa: BLE001
            log.warning("House PDF ayrıştırma hatası (%s): %s", pdf_url, e)
            transactions = []

        results.append(
            {
                "source": "house",
                "report_id": f"house-{doc_id}",
                "filer_name": f"{first} {last} ({state_dst})".strip(),
                "filing_date": filing_date,
                "source_url": pdf_url,
                "transactions": transactions,
            }
        )
    return results

"""Telegram + e-posta bildirim gönderimi."""
import logging
import smtplib
from email.mime.text import MIMEText

import requests

from . import config

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

REASON_LABELS = {
    "kapanışa_yakın": "Borsa kapanışına ≤1 saat kala bildirildi",
    "dev_şirket_dışı": "S&P 500 dışı bir şirkette satın alma",
}


def format_message(item: dict, tx: dict, eval_result: dict) -> str:
    urgent = bool(eval_result["urgent_reasons"])
    prefix = "🔴 ACİL — " if urgent else "🔵 "
    lines = [
        f"{prefix}Kongre İşlem Bildirimi",
        f"👤 {item['filer_name']} ({item['source'].upper()})",
        f"📈 {tx.get('ticker') or '?'} — {tx.get('asset_name') or ''}",
        f"🔁 İşlem tipi: {tx.get('transaction_type') or '?'}",
        f"📅 İşlem tarihi: {tx.get('transaction_date')}",
        f"📝 Bildirim tarihi: {item['filing_date']} (gecikme: {eval_result['delay_days']} gün)",
        f"💰 Tutar aralığı: {tx.get('amount_range') or '?'}",
    ]
    if urgent:
        reasons = ", ".join(REASON_LABELS.get(r, r) for r in eval_result["urgent_reasons"])
        lines.append(f"⚠️ Acil sebebi: {reasons}")
    lines.append(f"🔗 Kaynak: {item['source_url']}")
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        log.warning("Telegram ayarları eksik, gönderilemedi.")
        return False
    url = TELEGRAM_API.format(token=config.TELEGRAM_BOT_TOKEN)
    try:
        resp = requests.post(
            url,
            data={"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
            timeout=20,
        )
        if resp.status_code != 200:
            log.warning("Telegram gönderim hatası: %s %s", resp.status_code, resp.text)
            return False
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("Telegram gönderim istisnası: %s", e)
        return False


def send_email(subject: str, body: str) -> bool:
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD or not config.EMAIL_TO:
        log.warning("E-posta ayarları eksik, gönderilemedi.")
        return False
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.EMAIL_TO
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            server.sendmail(config.GMAIL_ADDRESS, [config.EMAIL_TO], msg.as_string())
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("E-posta gönderim istisnası: %s", e)
        return False


def dispatch(item: dict, tx: dict, eval_result: dict) -> None:
    text = format_message(item, tx, eval_result)
    urgent = bool(eval_result["urgent_reasons"])

    if urgent:
        # Acil: iki kanala da anında gönder.
        ok_tg = send_telegram(text)
        ok_email = send_email("🔴 ACİL - Kongre İşlem Bildirimi", text)
        if not ok_tg:
            log.warning("Acil alert - Telegram başarısız, e-posta sonucu: %s", ok_email)
    else:
        ok_tg = send_telegram(text)
        if not ok_tg:
            log.info("Telegram başarısız, e-postaya düşülüyor.")
            send_email("Kongre İşlem Bildirimi", text)

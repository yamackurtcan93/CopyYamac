"""Ortam değişkenleri ve sabitler."""
import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "yamackurtcan93@gmail.com")

# Kriterler
MAX_DELAY_DAYS = 15          # işlem tarihi -> bildirim tarihi arası bu günden AZ olmalı
URGENT_MINUTES_TO_CLOSE = 60  # tespit anı, borsa kapanışına bu dakikadan az/eşit kalmışsa acil

STATE_DIR = "state"
SEEN_STATE_PATH = os.path.join(STATE_DIR, "seen.json")
SP500_CACHE_PATH = os.path.join(STATE_DIR, "sp500_cache.json")
LAST_RUN_PATH = os.path.join(STATE_DIR, "last_run.json")

SP500_REFRESH_DAYS = 7

HOUSE_YEAR = None  # None -> çalışma anındaki yıl kullanılır (main.py içinde belirlenir)

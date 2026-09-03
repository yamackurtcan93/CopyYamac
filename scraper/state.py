"""Basit JSON tabanlı durum (state) okuma/yazma.

GitHub Actions runner'ları her çalıştırmada sıfırdan başladığı için, hangi
filing'lerin daha önce işlendiğini hatırlamak amacıyla bu dosyalar workflow
sonunda git ile repoya commit edilir (bkz. .github/workflows/monitor.yml).
"""
import json
import os
from datetime import datetime, timezone


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: str, data) -> None:
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def load_seen(path: str) -> dict:
    return load_json(path, {"house": [], "senate": []})


def save_seen(path: str, seen: dict) -> None:
    save_json(path, seen)


def touch_last_run(path: str) -> None:
    """Her çalıştırmada güncellenir; böylece uzun süre yeni filing çıkmasa
    bile repo 'aktif' kalır ve GitHub Actions zamanlanmış görevi 60 günlük
    hareketsizlik nedeniyle otomatik devre dışı bırakmaz."""
    save_json(path, {"last_run_utc": datetime.now(timezone.utc).isoformat()})

"""yfinance data fetching with curl_cffi Chrome impersonation + disk cache (TTL 4h).

curl_cffi mimics a real Chrome browser at the TLS fingerprint level, which is
much harder for Yahoo Finance to detect and block than plain HTTP headers.
No API key required.
"""

import os
import pickle
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import yfinance as yf
from curl_cffi import requests as crequests

CACHE_DIR = Path(os.environ.get("CACHE_DIR", ".cache"))
CACHE_TTL_HOURS = 4

log = logging.getLogger(__name__)

# One shared session per process — reuses cookies and TLS connection
_SESSION = crequests.Session(impersonate="chrome110")


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol}.pkl"


def _is_fresh(cached: dict) -> bool:
    fetched_at = cached.get("fetched_at")
    if fetched_at is None:
        return False
    return datetime.utcnow() - fetched_at < timedelta(hours=CACHE_TTL_HOURS)


def _load_cache(symbol: str) -> dict | None:
    path = _cache_path(symbol)
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _save_cache(symbol: str, data: dict) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    try:
        with open(_cache_path(symbol), "wb") as f:
            pickle.dump(data, f)
    except Exception as e:
        log.warning("Cache write failed for %s: %s", symbol, e)


# ── Fetch ──────────────────────────────────────────────────────────────────────

def fetch_ticker(symbol: str, max_retries: int = 3) -> dict | None:
    """Fetch all data via yfinance using a Chrome-impersonating curl_cffi session."""
    for attempt in range(max_retries):
        try:
            t = yf.Ticker(symbol, session=_SESSION)
            info = t.info or {}
            return {
                "fetched_at":            datetime.utcnow(),
                "info":                  info,
                "financials":            t.financials,
                "quarterly_financials":  t.quarterly_financials,
                "balance_sheet":         t.balance_sheet,
                "cashflow":              t.cashflow,
                "history_1y":            t.history(period="1y"),
                "history_2y":            t.history(period="2y"),
            }
        except Exception as e:
            msg = str(e).lower()
            if ("too many requests" in msg or "429" in msg) and attempt < max_retries - 1:
                wait = 2 ** (attempt + 2)
                log.warning("Rate limited on %s, retrying in %ss…", symbol, wait)
                time.sleep(wait)
            else:
                log.warning("Failed to fetch %s: %s", symbol, e)
                return None
    return None


def load_ticker(symbol: str, force_refresh: bool = False) -> dict | None:
    if not force_refresh:
        cached = _load_cache(symbol)
        if cached is not None and _is_fresh(cached):
            return cached
    data = fetch_ticker(symbol)
    if data is not None:
        _save_cache(symbol, data)
    return data


def load_all(
    tickers: list[str],
    force_refresh: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, dict | None]:
    result: dict[str, dict | None] = {}
    total = len(tickers)
    for i, symbol in enumerate(tickers):
        if progress_callback:
            progress_callback(i, total, symbol)
        result[symbol] = load_ticker(symbol, force_refresh=force_refresh)
        time.sleep(0.5)
    if progress_callback:
        progress_callback(total, total, "")
    return result


def get_cache_status(tickers: list[str]) -> dict:
    status = {}
    for symbol in tickers:
        cached = _load_cache(symbol)
        if cached is None:
            status[symbol] = {"cached": False, "fetched_at": None, "fresh": False}
        else:
            status[symbol] = {
                "cached": True,
                "fetched_at": cached.get("fetched_at"),
                "fresh": _is_fresh(cached),
            }
    return status


def clear_cache(tickers: list[str] | None = None) -> None:
    if not CACHE_DIR.exists():
        return
    if tickers is None:
        for f in CACHE_DIR.glob("*.pkl"):
            f.unlink(missing_ok=True)
    else:
        for symbol in tickers:
            _cache_path(symbol).unlink(missing_ok=True)

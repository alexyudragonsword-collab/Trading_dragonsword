"""yfinance data fetching with disk-based pickle cache (TTL 4 hours)."""

import os
import pickle
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yfinance as yf

CACHE_DIR = Path(os.environ.get("CACHE_DIR", ".cache"))
CACHE_TTL_HOURS = 4

log = logging.getLogger(__name__)

# Browser-like headers to avoid Yahoo Finance blocking cloud server IPs
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# One shared session per process reuses cookies across tickers
_SESSION = _make_session()


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


def fetch_ticker(symbol: str, max_retries: int = 3) -> dict | None:
    """Fetch all needed data for one ticker via yfinance, with retry on rate-limit."""
    for attempt in range(max_retries):
        try:
            t = yf.Ticker(symbol, session=_SESSION)
            info = t.info or {}
            data = {
                "fetched_at": datetime.utcnow(),
                "info": info,
                "financials": t.financials,
                "quarterly_financials": t.quarterly_financials,
                "balance_sheet": t.balance_sheet,
                "quarterly_balance_sheet": t.quarterly_balance_sheet,
                "cashflow": t.cashflow,
                "quarterly_cashflow": t.quarterly_cashflow,
                "history_1y": t.history(period="1y"),
                "history_2y": t.history(period="2y"),
            }
            return data
        except Exception as e:
            msg = str(e).lower()
            is_rate_limit = "too many requests" in msg or "429" in msg or "rate limit" in msg
            if is_rate_limit and attempt < max_retries - 1:
                wait = 2 ** (attempt + 2)   # 4s, 8s, 16s
                log.warning("Rate limited on %s, retrying in %ss…", symbol, wait)
                time.sleep(wait)
            else:
                log.warning("Failed to fetch %s: %s", symbol, e)
                return None
    return None


def load_ticker(symbol: str, force_refresh: bool = False) -> dict | None:
    """Return ticker data from cache if fresh, otherwise refetch."""
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
    """
    Load data for all tickers. Returns dict mapping symbol → data dict (or None).
    progress_callback(i, total, symbol) is called before each fetch.
    """
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
    """Return info about what's cached and when it was last fetched."""
    status = {}
    for symbol in tickers:
        cached = _load_cache(symbol)
        if cached is None:
            status[symbol] = {"cached": False, "fetched_at": None, "fresh": False}
        else:
            fresh = _is_fresh(cached)
            status[symbol] = {
                "cached": True,
                "fetched_at": cached.get("fetched_at"),
                "fresh": fresh,
            }
    return status


def clear_cache(tickers: list[str] | None = None) -> None:
    """Delete cache files. If tickers is None, clears all."""
    if not CACHE_DIR.exists():
        return
    if tickers is None:
        for f in CACHE_DIR.glob("*.pkl"):
            f.unlink(missing_ok=True)
    else:
        for symbol in tickers:
            _cache_path(symbol).unlink(missing_ok=True)

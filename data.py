"""yfinance data fetching with curl_cffi + batch price download + disk cache (TTL 4h).

Strategy:
  1. yf.download(ALL_TICKERS, period="2y") — ONE batch call for all price history
  2. yf.Ticker(symbol).info               — one call per ticker for fundamentals
Total API calls: ~44 instead of ~129, dramatically reducing rate-limit failures.
"""

import os
import pickle
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd
import yfinance as yf
from curl_cffi import requests as crequests

CACHE_DIR = Path(os.environ.get("CACHE_DIR", ".cache"))
CACHE_TTL_HOURS = 4
_PRICES_CACHE = CACHE_DIR / "_prices.pkl"

log = logging.getLogger(__name__)

_SESSION = crequests.Session(impersonate="chrome110")


# ── Price batch cache ──────────────────────────────────────────────────────────

def _prices_fresh() -> bool:
    if not _PRICES_CACHE.exists():
        return False
    try:
        with open(_PRICES_CACHE, "rb") as f:
            cached = pickle.load(f)
        fetched_at = cached.get("fetched_at")
        return fetched_at and (datetime.utcnow() - fetched_at).seconds / 3600 < CACHE_TTL_HOURS
    except Exception:
        return False


def _load_prices() -> pd.DataFrame | None:
    try:
        with open(_PRICES_CACHE, "rb") as f:
            return pickle.load(f).get("df")
    except Exception:
        return None


def _save_prices(df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    try:
        with open(_PRICES_CACHE, "wb") as f:
            pickle.dump({"fetched_at": datetime.utcnow(), "df": df}, f)
    except Exception as e:
        log.warning("Price cache write failed: %s", e)


def fetch_prices(tickers: list[str]) -> pd.DataFrame:
    """Batch-download 2y of adjusted close prices for all tickers in one call."""
    df = yf.download(
        tickers=tickers,
        period="2y",
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        session=_SESSION,
    )
    return df


def get_close(prices_df: pd.DataFrame, symbol: str) -> pd.Series | None:
    """Extract the Close series for one symbol from the batch DataFrame."""
    try:
        if isinstance(prices_df.columns, pd.MultiIndex):
            close = prices_df[symbol]["Close"].dropna()
        else:
            close = prices_df["Close"].dropna()
        return close if len(close) > 0 else None
    except (KeyError, TypeError):
        return None


# ── Per-ticker info cache ──────────────────────────────────────────────────────

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


def fetch_info(symbol: str, max_retries: int = 3) -> dict | None:
    """Fetch only the info dict for one ticker (fundamentals)."""
    for attempt in range(max_retries):
        try:
            return yf.Ticker(symbol, session=_SESSION).info or {}
        except Exception as e:
            msg = str(e).lower()
            if ("too many requests" in msg or "429" in msg) and attempt < max_retries - 1:
                wait = 2 ** (attempt + 2)
                log.warning("Rate limited on %s, retrying in %ss…", symbol, wait)
                time.sleep(wait)
            else:
                log.warning("Failed to fetch info for %s: %s", symbol, e)
                return None
    return None


# ── Public API ─────────────────────────────────────────────────────────────────

def load_all(
    tickers: list[str],
    force_refresh: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, dict | None]:
    """
    Load data for all tickers.
    Step 1: batch-download price history (1 API call).
    Step 2: fetch info dict per ticker (N API calls).
    """
    total = len(tickers)

    # Step 1 — batch prices
    if progress_callback:
        progress_callback(0, total, "批量下载价格历史…")

    if force_refresh or not _prices_fresh():
        try:
            prices_df = fetch_prices(tickers)
            _save_prices(prices_df)
        except Exception as e:
            log.warning("Batch price download failed: %s", e)
            prices_df = _load_prices() or pd.DataFrame()
    else:
        prices_df = _load_prices() or pd.DataFrame()

    # Step 2 — per-ticker info
    result: dict[str, dict | None] = {}
    for i, symbol in enumerate(tickers):
        if progress_callback:
            progress_callback(i, total, symbol)

        # Check per-ticker cache
        cached = None if force_refresh else _load_cache(symbol)
        if cached and _is_fresh(cached):
            result[symbol] = cached
            continue

        info = fetch_info(symbol)
        if info is None:
            result[symbol] = None
            time.sleep(0.5)
            continue

        close = get_close(prices_df, symbol)
        data = {
            "fetched_at": datetime.utcnow(),
            "info":       info,
            "close":      close,   # pd.Series with DatetimeIndex, 2y of data
        }
        _save_cache(symbol, data)
        result[symbol] = data
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
    _PRICES_CACHE.unlink(missing_ok=True)
    if tickers is None:
        for f in CACHE_DIR.glob("*.pkl"):
            f.unlink(missing_ok=True)
    else:
        for symbol in tickers:
            _cache_path(symbol).unlink(missing_ok=True)

"""Alpha Vantage data fetching with disk cache (TTL 4h).

Two API calls per ticker:
  OVERVIEW                        → all fundamental ratios directly
  TIME_SERIES_DAILY_ADJUSTED      → price history for momentum & technical

Free tier: 25 requests/minute, 500/day.
Sleep 2.5s between calls keeps us at ~24 req/min.
Cold fetch for ~43 tickers ≈ 4 minutes; subsequent loads use cache.
"""

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

CACHE_DIR = Path(os.environ.get("CACHE_DIR", ".cache"))
CACHE_TTL_HOURS = 4
AV_BASE = "https://www.alphavantage.co/query"

log = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    retry = Retry(
        total=3, backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


_SESSION = _make_session()


def get_api_key() -> str | None:
    return os.environ.get("AV_API_KEY") or None


def _av_get(function: str, symbol: str, extra: dict | None = None) -> dict | None:
    api_key = get_api_key()
    if not api_key:
        return None
    params = {"function": function, "symbol": symbol, "apikey": api_key}
    if extra:
        params.update(extra)
    try:
        resp = _SESSION.get(AV_BASE, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        # AV returns {"Information": "..."} or {"Note": "..."} on quota/error
        if "Information" in data or "Note" in data:
            log.warning("AV quota/info message for %s %s: %s",
                        function, symbol,
                        data.get("Information") or data.get("Note"))
            return None
        if "Error Message" in data:
            log.warning("AV error for %s %s: %s", function, symbol, data["Error Message"])
            return None
        return data
    except Exception as e:
        log.warning("AV request failed %s %s: %s", function, symbol, e)
        return None


def fetch_ticker(symbol: str) -> dict | None:
    """Fetch overview + daily price history from Alpha Vantage (2 API calls)."""
    overview = _av_get("OVERVIEW", symbol)
    time.sleep(2.5)   # stay under 25 req/min free-tier limit

    prices_raw = _av_get(
        "TIME_SERIES_DAILY_ADJUSTED", symbol,
        {"outputsize": "full", "datatype": "json"},
    )
    time.sleep(2.5)

    if not overview and not prices_raw:
        log.warning("No data returned for %s", symbol)
        return None

    # Parse price history into a clean list [{date, close}] newest first
    ts = (prices_raw or {}).get("Time Series (Daily)", {})
    history = [
        {
            "date":  date,
            "close": float(vals.get("5. adjusted close") or vals.get("4. close") or 0),
        }
        for date, vals in ts.items()
        if vals.get("5. adjusted close") or vals.get("4. close")
    ]
    # ts dict is already newest-first from AV

    return {
        "fetched_at": datetime.utcnow(),
        "overview": overview or {},
        "history":  history,      # [{date, close}] newest first
    }


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
        # inter-ticker gap only (intra-ticker sleeps are in fetch_ticker)
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

"""FMP data fetching — free-tier endpoints only, with disk cache (TTL 4h).

Free endpoints used per ticker (5 calls):
  /v3/profile/{symbol}                          → price, mktCap, sector
  /v3/income-statement/{symbol}?limit=2         → revenue, margins, EPS (2 years)
  /v3/balance-sheet-statement/{symbol}?limit=1  → assets, equity, debt
  /v3/cash-flow-statement/{symbol}?limit=1      → operating CF, capex
  /v3/historical-price-full/{symbol}?timeseries=300 → price history
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
FMP_BASE = "https://financialmodelingprep.com/api"

log = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    retry = Retry(
        total=3, backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


_SESSION = _make_session()


def get_api_key() -> str | None:
    return os.environ.get("FMP_API_KEY") or None


def _fmp_get(path: str, params: dict | None = None) -> dict | list | None:
    api_key = get_api_key()
    if not api_key:
        return None
    url = f"{FMP_BASE}{path}"
    p = {"apikey": api_key}
    if params:
        p.update(params)
    try:
        resp = _SESSION.get(url, params=p, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and ("Error Message" in data or "error" in data):
            log.warning("FMP API error for %s: %s", path,
                        data.get("Error Message") or data.get("error"))
            return None
        return data
    except Exception as e:
        log.warning("FMP request failed %s: %s", path, e)
        return None


def fetch_ticker(symbol: str) -> dict | None:
    """Fetch all data for one ticker using only FMP free-tier endpoints."""
    profile_raw  = _fmp_get(f"/v3/profile/{symbol}")
    income_raw   = _fmp_get(f"/v3/income-statement/{symbol}",          {"limit": 2})
    balance_raw  = _fmp_get(f"/v3/balance-sheet-statement/{symbol}",   {"limit": 1})
    cashflow_raw = _fmp_get(f"/v3/cash-flow-statement/{symbol}",       {"limit": 1})
    price_raw    = _fmp_get(f"/v3/historical-price-full/{symbol}",     {"timeseries": 300})

    profile  = profile_raw[0]  if isinstance(profile_raw,  list) and profile_raw  else {}
    income   = income_raw      if isinstance(income_raw,   list) else []   # [current, prior]
    balance  = balance_raw[0]  if isinstance(balance_raw,  list) and balance_raw  else {}
    cashflow = cashflow_raw[0] if isinstance(cashflow_raw, list) and cashflow_raw else {}
    history  = price_raw.get("historical", []) if isinstance(price_raw, dict) else []

    if not profile and not income:
        log.warning("No data returned for %s", symbol)
        return None

    return {
        "fetched_at": datetime.utcnow(),
        "profile":  profile,   # price, mktCap, sector
        "income":   income,    # list: [most_recent_annual, prior_annual]
        "balance":  balance,   # totalAssets, totalEquity, totalDebt, cash
        "cashflow": cashflow,  # operatingCashFlow, capitalExpenditure, freeCashFlow
        "history":  history,   # [{date, adjClose, close, ...}] newest first
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
        time.sleep(0.3)
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

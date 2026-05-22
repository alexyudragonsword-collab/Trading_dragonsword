"""Compute 22 quantitative factors for a single ticker from FMP data."""

import numpy as np
import pandas as pd

from utils import safe_get


def _to_close_series(history: list) -> pd.Series | None:
    """Convert FMP history list (newest first) to a date-indexed Series (oldest first)."""
    if not history:
        return None
    items = list(reversed(history))
    dates, closes = [], []
    for item in items:
        val = item.get("adjClose") or item.get("close")
        if val is not None:
            dates.append(pd.to_datetime(item["date"]))
            closes.append(float(val))
    if not closes:
        return None
    return pd.Series(closes, index=dates, dtype=float)


def _pct_return(close: pd.Series, n_days: int) -> float | None:
    if close is None or len(close) < n_days + 1:
        return None
    return float(close.iloc[-1] / close.iloc[-(n_days + 1)] - 1)


def _rsi(close: pd.Series, period: int = 14) -> float | None:
    if close is None or len(close) < period + 1:
        return None
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    val   = rsi.iloc[-1]
    return float(val) if pd.notna(val) else None


def _macd_signal(close: pd.Series) -> float | None:
    if close is None or len(close) < 35:
        return None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    hist  = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
    val   = hist.iloc[-1]
    return float(np.sign(val)) if pd.notna(val) else None


def compute_factors(symbol: str, raw: dict) -> dict | None:
    """Return flat dict of 22 factor values (float | None), or None if data is unusable."""
    if raw is None:
        return None

    ratios  = raw.get("ratios")  or {}
    growth  = raw.get("growth")  or {}
    profile = raw.get("profile") or {}
    history = raw.get("history") or []

    close = _to_close_series(history)

    # ── Valuation ─────────────────────────────────────────────────────────────
    def _f(d, *keys):
        """Return first non-None float from d matching any key."""
        for k in keys:
            v = safe_get(d, k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return None

    pe       = _f(ratios, "peRatioTTM")
    pb       = _f(ratios, "priceToBookRatioTTM")
    ps       = _f(ratios, "priceToSalesRatioTTM")
    ev_ebitda = _f(ratios, "enterpriseValueMultipleTTM")

    # ── Growth ────────────────────────────────────────────────────────────────
    revenue_growth = _f(growth, "growthRevenue")
    eps_growth     = _f(growth, "growthEPS", "growthEps")

    # ── Profitability ─────────────────────────────────────────────────────────
    gross_margin     = _f(ratios, "grossProfitMarginTTM")
    operating_margin = _f(ratios, "operatingProfitMarginTTM")
    net_margin       = _f(ratios, "netProfitMarginTTM")
    roe              = _f(ratios, "returnOnEquityTTM")
    roa              = _f(ratios, "returnOnAssetsTTM")

    # ── Momentum ──────────────────────────────────────────────────────────────
    mom_1m  = _pct_return(close, 21)
    mom_3m  = _pct_return(close, 63)
    mom_6m  = _pct_return(close, 126)
    mom_12m = _pct_return(close, 252)

    # ── Technical ────────────────────────────────────────────────────────────
    rsi_14   = _rsi(close, 14)
    macd_sig = _macd_signal(close)

    above_50ma = above_200ma = golden_cross = None
    if close is not None and len(close) >= 50:
        price = float(close.iloc[-1])
        ma50  = float(close.rolling(50).mean().iloc[-1])
        above_50ma = 1.0 if price > ma50 else 0.0
        if len(close) >= 200:
            ma200 = float(close.rolling(200).mean().iloc[-1])
            above_200ma  = 1.0 if price > ma200 else 0.0
            golden_cross = 1.0 if ma50 > ma200 else 0.0

    # ── Quality ───────────────────────────────────────────────────────────────
    debt_to_equity = _f(ratios, "debtEquityRatioTTM")
    fcf_yield      = _f(ratios, "freeCashFlowYieldTTM")

    return {
        "pe": pe, "pb": pb, "ps": ps, "ev_ebitda": ev_ebitda,
        "revenue_growth": revenue_growth, "eps_growth": eps_growth,
        "gross_margin": gross_margin, "operating_margin": operating_margin,
        "net_margin": net_margin, "roe": roe, "roa": roa,
        "mom_1m": mom_1m, "mom_3m": mom_3m, "mom_6m": mom_6m, "mom_12m": mom_12m,
        "rsi_14": rsi_14, "macd_signal": macd_sig,
        "above_50ma": above_50ma, "above_200ma": above_200ma, "golden_cross": golden_cross,
        "debt_to_equity": debt_to_equity, "fcf_yield": fcf_yield,
    }

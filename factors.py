"""Compute 22 quantitative factors from Alpha Vantage OVERVIEW + price history."""

import numpy as np
import pandas as pd

from utils import safe_get


# ── Price helpers ──────────────────────────────────────────────────────────────

def _to_close_series(history: list) -> pd.Series | None:
    """Convert AV history list (newest first) to a date-indexed Series (oldest first)."""
    if not history:
        return None
    items = list(reversed(history))
    dates  = [pd.to_datetime(item["date"])  for item in items]
    closes = [float(item["close"])          for item in items]
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
    val   = (100 - 100 / (1 + gain / loss)).iloc[-1]
    return float(val) if pd.notna(val) else None


def _macd_signal(close: pd.Series) -> float | None:
    if close is None or len(close) < 35:
        return None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    hist  = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
    val   = hist.iloc[-1]
    return float(np.sign(val)) if pd.notna(val) else None


# ── Safe cast helpers ──────────────────────────────────────────────────────────

def _f(d: dict, *keys) -> float | None:
    """Return first finite float found in d under any of keys."""
    for k in keys:
        v = safe_get(d, k)
        if v is not None and v != "None" and v != "-":
            try:
                f = float(v)
                return f if np.isfinite(f) else None
            except (TypeError, ValueError):
                pass
    return None


def _div(a, b) -> float | None:
    if a is None or b is None or b == 0:
        return None
    r = a / b
    return float(r) if np.isfinite(r) else None


# ── Main ───────────────────────────────────────────────────────────────────────

def compute_factors(symbol: str, raw: dict) -> dict | None:
    if raw is None:
        return None

    ov      = raw.get("overview") or {}
    history = raw.get("history")  or []
    close   = _to_close_series(history)

    # ── Valuation ─────────────────────────────────────────────────────────────
    pe        = _f(ov, "TrailingPE", "PERatio")
    pb        = _f(ov, "PriceToBookRatio")
    ps        = _f(ov, "PriceToSalesRatioTTM")
    ev_ebitda = _f(ov, "EVToEBITDA")

    # ── Growth ────────────────────────────────────────────────────────────────
    revenue_growth = _f(ov, "QuarterlyRevenueGrowthYOY", "RevenueGrowthYOY")
    eps_growth     = _f(ov, "QuarterlyEarningsGrowthYOY", "EarningsGrowthYOY")

    # ── Profitability ─────────────────────────────────────────────────────────
    gross_profit = _f(ov, "GrossProfitTTM")
    revenue_ttm  = _f(ov, "RevenueTTM")
    gross_margin     = _div(gross_profit, revenue_ttm)
    operating_margin = _f(ov, "OperatingMarginTTM")
    net_margin       = _f(ov, "ProfitMargin")
    roe              = _f(ov, "ReturnOnEquityTTM")
    roa              = _f(ov, "ReturnOnAssetsTTM")

    # ── Momentum ─────────────────────────────────────────────────────────────
    mom_1m  = _pct_return(close, 21)
    mom_3m  = _pct_return(close, 63)
    mom_6m  = _pct_return(close, 126)
    mom_12m = _pct_return(close, 252)

    # ── Technical ─────────────────────────────────────────────────────────────
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
    # AV OVERVIEW doesn't expose D/E or FCF directly; derive from available fields
    book_value    = _f(ov, "BookValue")          # book value per share
    eps           = _f(ov, "EPS")
    shares        = _f(ov, "SharesOutstanding")
    mkt_cap       = _f(ov, "MarketCapitalization")
    ebitda        = _f(ov, "EBITDA")
    ev_to_rev     = _f(ov, "EVToRevenue")

    # Estimate total equity = BookValue × SharesOutstanding
    total_equity = _div(mkt_cap, _f(ov, "PriceToBookRatio"))   # mktCap / PB = equity

    # EV = EVToEBITDA × EBITDA;  Debt ≈ EV - mktCap + cash (cash unknown → proxy)
    # Simpler: EVToRevenue gives EV; then NetDebt = EV - mktCap
    ev = _div(ebitda, 1) and (ev_ebitda * ebitda if ev_ebitda and ebitda else None)
    net_debt = (ev - mkt_cap) if (ev and mkt_cap) else None
    debt_to_equity = _div(net_debt, total_equity) if net_debt and net_debt > 0 else None

    # FCF yield: AV doesn't give FCF in OVERVIEW; leave as None
    fcf_yield = None

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

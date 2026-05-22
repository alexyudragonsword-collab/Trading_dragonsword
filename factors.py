"""Compute 22 quantitative factors from FMP free-tier financial statement data."""

import numpy as np
import pandas as pd

from utils import safe_get


# ── Price history helpers ──────────────────────────────────────────────────────

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
    return pd.Series(closes, index=dates, dtype=float) if closes else None


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
    val   = (100 - 100 / (1 + rs)).iloc[-1]
    return float(val) if pd.notna(val) else None


def _macd_signal(close: pd.Series) -> float | None:
    if close is None or len(close) < 35:
        return None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    hist  = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
    val   = hist.iloc[-1]
    return float(np.sign(val)) if pd.notna(val) else None


# ── Safe numeric helper ────────────────────────────────────────────────────────

def _num(d: dict, *keys) -> float | None:
    for k in keys:
        v = safe_get(d, k)
        if v is not None:
            try:
                f = float(v)
                return f if np.isfinite(f) else None
            except (TypeError, ValueError):
                pass
    return None


def _safe_div(a, b) -> float | None:
    if a is None or b is None or b == 0:
        return None
    result = a / b
    return float(result) if np.isfinite(result) else None


# ── Main factor computation ────────────────────────────────────────────────────

def compute_factors(symbol: str, raw: dict) -> dict | None:
    """Return flat dict of 22 factor values (float | None), or None if unusable."""
    if raw is None:
        return None

    profile  = raw.get("profile")  or {}
    income   = raw.get("income")   or []   # [most_recent, prior_year]
    balance  = raw.get("balance")  or {}
    cashflow = raw.get("cashflow") or {}
    history  = raw.get("history")  or []

    cur  = income[0] if len(income) > 0 else {}
    prev = income[1] if len(income) > 1 else {}
    close = _to_close_series(history)

    # Shared base values
    price   = _num(profile, "price")
    mkt_cap = _num(profile, "mktCap")
    revenue     = _num(cur, "revenue")
    gross_prof  = _num(cur, "grossProfit")
    op_income   = _num(cur, "operatingIncome")
    net_income  = _num(cur, "netIncome")
    ebitda      = _num(cur, "ebitda")
    eps         = _num(cur, "epsdiluted", "eps")
    total_assets = _num(balance, "totalAssets")
    total_equity = _num(balance, "totalStockholdersEquity")
    total_debt   = _num(balance, "totalDebt")
    cash         = _num(balance, "cashAndCashEquivalents")
    op_cf        = _num(cashflow, "operatingCashFlow")
    capex        = _num(cashflow, "capitalExpenditure")  # negative in FMP
    fcf_direct   = _num(cashflow, "freeCashFlow")

    # ── Valuation ────────────────────────────────────────────────────────────
    pe = _safe_div(price, eps)
    pb = _safe_div(mkt_cap, total_equity)
    ps = _safe_div(mkt_cap, revenue)

    ev_ebitda = None
    if mkt_cap is not None and total_debt is not None and cash is not None and ebitda and ebitda > 0:
        ev = mkt_cap + total_debt - cash
        ev_ebitda = _safe_div(ev, ebitda)

    # ── Growth ───────────────────────────────────────────────────────────────
    prev_revenue = _num(prev, "revenue")
    prev_eps     = _num(prev, "epsdiluted", "eps")
    revenue_growth = _safe_div((revenue or 0) - (prev_revenue or 0), abs(prev_revenue)) \
        if revenue is not None and prev_revenue else None
    eps_growth = _safe_div((eps or 0) - (prev_eps or 0), abs(prev_eps)) \
        if eps is not None and prev_eps else None

    # ── Profitability ─────────────────────────────────────────────────────────
    gross_margin     = _safe_div(gross_prof, revenue)
    operating_margin = _safe_div(op_income,  revenue)
    net_margin       = _safe_div(net_income, revenue)
    roe              = _safe_div(net_income, total_equity)
    roa              = _safe_div(net_income, total_assets)

    # ── Momentum ─────────────────────────────────────────────────────────────
    mom_1m  = _pct_return(close, 21)
    mom_3m  = _pct_return(close, 63)
    mom_6m  = _pct_return(close, 126)
    mom_12m = _pct_return(close, 252)

    # ── Technical ────────────────────────────────────────────────────────────
    rsi_14   = _rsi(close, 14)
    macd_sig = _macd_signal(close)

    above_50ma = above_200ma = golden_cross = None
    if close is not None and len(close) >= 50:
        price_now = float(close.iloc[-1])
        ma50 = float(close.rolling(50).mean().iloc[-1])
        above_50ma = 1.0 if price_now > ma50 else 0.0
        if len(close) >= 200:
            ma200 = float(close.rolling(200).mean().iloc[-1])
            above_200ma  = 1.0 if price_now > ma200 else 0.0
            golden_cross = 1.0 if ma50 > ma200 else 0.0

    # ── Quality ──────────────────────────────────────────────────────────────
    debt_to_equity = _safe_div(total_debt, total_equity)

    # FCF = operating cash flow + capex (capex is negative in FMP)
    fcf = fcf_direct if fcf_direct is not None else (
        (op_cf + capex) if op_cf is not None and capex is not None else op_cf
    )
    fcf_yield = _safe_div(fcf, mkt_cap)

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

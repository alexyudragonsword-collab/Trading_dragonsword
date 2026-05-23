"""Compute 22 quantitative factors for a single ticker from yfinance data."""

import numpy as np
import pandas as pd

from utils import safe_get


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


def _revenue_growth_from_df(financials: pd.DataFrame) -> float | None:
    try:
        if financials is None or financials.empty:
            return None
        rev = financials.loc["Total Revenue"].dropna()
        if len(rev) < 2:
            return None
        return float((rev.iloc[0] - rev.iloc[1]) / abs(rev.iloc[1]))
    except (KeyError, ZeroDivisionError):
        return None


def compute_factors(symbol: str, raw: dict) -> dict | None:
    if raw is None:
        return None

    info       = raw.get("info") or {}
    financials = raw.get("financials")
    hist_1y    = raw.get("history_1y")
    hist_2y    = raw.get("history_2y")

    close_1y = hist_1y["Close"] if (hist_1y is not None and not hist_1y.empty) else None
    close_2y = hist_2y["Close"] if (hist_2y is not None and not hist_2y.empty) else None

    def _f(*keys):
        for k in keys:
            v = safe_get(info, k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return None

    # ── Valuation ─────────────────────────────────────────────────────────────
    pe        = _f("trailingPE")
    pb        = _f("priceToBook")
    ps        = _f("priceToSalesTrailing12Months")
    ev_ebitda = _f("enterpriseToEbitda")

    # ── Growth ────────────────────────────────────────────────────────────────
    revenue_growth = _f("revenueGrowth") or _revenue_growth_from_df(financials)
    eps_growth     = _f("earningsGrowth") or _f("earningsQuarterlyGrowth")

    # ── Profitability ─────────────────────────────────────────────────────────
    gross_margin     = _f("grossMargins")
    operating_margin = _f("operatingMargins")
    net_margin       = _f("netMargins")
    roe              = _f("returnOnEquity")
    roa              = _f("returnOnAssets")

    # ── Momentum ─────────────────────────────────────────────────────────────
    mom_1m  = _pct_return(close_1y, 21)
    mom_3m  = _pct_return(close_1y, 63)
    mom_6m  = _pct_return(close_1y, 126)
    close_12m = close_2y if (close_2y is not None and len(close_2y) >= 253) else close_1y
    mom_12m = _pct_return(close_12m, 252)

    # ── Technical ─────────────────────────────────────────────────────────────
    rsi_14   = _rsi(close_1y, 14)
    macd_sig = _macd_signal(close_1y)

    above_50ma = above_200ma = golden_cross = None
    if close_1y is not None and len(close_1y) >= 50:
        price = float(close_1y.iloc[-1])
        ma50  = float(close_1y.rolling(50).mean().iloc[-1])
        above_50ma = 1.0 if price > ma50 else 0.0
        if len(close_1y) >= 200:
            ma200 = float(close_1y.rolling(200).mean().iloc[-1])
            above_200ma  = 1.0 if price > ma200 else 0.0
            golden_cross = 1.0 if ma50 > ma200 else 0.0

    # ── Quality ───────────────────────────────────────────────────────────────
    debt_to_equity = _f("debtToEquity")
    fcf   = safe_get(info, "freeCashflow")
    mktcap = safe_get(info, "marketCap")
    fcf_yield = float(fcf) / float(mktcap) if fcf and mktcap else None

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

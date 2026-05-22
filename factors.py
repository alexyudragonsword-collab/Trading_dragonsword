"""Compute 22 quantitative factors for a single ticker from raw yfinance data."""

import numpy as np
import pandas as pd

from utils import safe_get


def _pct_return(close: pd.Series, n_days: int) -> float | None:
    """Price return over the last n_days trading days."""
    if close is None or len(close) < n_days + 1:
        return None
    return float(close.iloc[-1] / close.iloc[-(n_days + 1)] - 1)


def _rsi(close: pd.Series, period: int = 14) -> float | None:
    if close is None or len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if pd.notna(val) else None


def _macd_signal(close: pd.Series) -> float | None:
    """Returns +1 if MACD histogram is positive, -1 if negative, else None."""
    if close is None or len(close) < 35:
        return None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    val = hist.iloc[-1]
    if pd.isna(val):
        return None
    return float(np.sign(val))


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
    """Return flat dict of 22 factor values (float | None), or None if data is unusable."""
    if raw is None:
        return None

    info = raw.get("info") or {}
    financials = raw.get("financials")
    cashflow = raw.get("cashflow")

    # Use history_1y for technical/momentum; fall back to history_2y for 12M momentum
    hist_1y = raw.get("history_1y")
    hist_2y = raw.get("history_2y")

    close_1y = hist_1y["Close"] if (hist_1y is not None and not hist_1y.empty) else None
    close_2y = hist_2y["Close"] if (hist_2y is not None and not hist_2y.empty) else None

    # ── Valuation ────────────────────────────────────────────────────────────
    pe = safe_get(info, "trailingPE")
    pb = safe_get(info, "priceToBook")
    ps = safe_get(info, "priceToSalesTrailing12Months")
    ev_ebitda = safe_get(info, "enterpriseToEbitda")

    # Guard against negative / nonsensical values (e.g. negative PE handled downstream)
    if pe is not None:
        try:
            pe = float(pe)
        except (TypeError, ValueError):
            pe = None
    if pb is not None:
        try:
            pb = float(pb)
        except (TypeError, ValueError):
            pb = None
    if ps is not None:
        try:
            ps = float(ps)
        except (TypeError, ValueError):
            ps = None
    if ev_ebitda is not None:
        try:
            ev_ebitda = float(ev_ebitda)
        except (TypeError, ValueError):
            ev_ebitda = None

    # ── Growth ───────────────────────────────────────────────────────────────
    revenue_growth = safe_get(info, "revenueGrowth")
    if revenue_growth is None:
        revenue_growth = _revenue_growth_from_df(financials)
    else:
        revenue_growth = float(revenue_growth)

    eps_growth = safe_get(info, "earningsGrowth")
    if eps_growth is None:
        eps_growth = safe_get(info, "earningsQuarterlyGrowth")
    if eps_growth is not None:
        eps_growth = float(eps_growth)

    # ── Profitability ─────────────────────────────────────────────────────────
    gross_margin = safe_get(info, "grossMargins")
    operating_margin = safe_get(info, "operatingMargins")
    net_margin = safe_get(info, "netMargins")
    roe = safe_get(info, "returnOnEquity")
    roa = safe_get(info, "returnOnAssets")

    for name, val in [("gross_margin", gross_margin), ("operating_margin", operating_margin),
                      ("net_margin", net_margin), ("roe", roe), ("roa", roa)]:
        pass  # Already None-safe via safe_get; convert below
    gross_margin = float(gross_margin) if gross_margin is not None else None
    operating_margin = float(operating_margin) if operating_margin is not None else None
    net_margin = float(net_margin) if net_margin is not None else None
    roe = float(roe) if roe is not None else None
    roa = float(roa) if roa is not None else None

    # ── Momentum ──────────────────────────────────────────────────────────────
    mom_1m = _pct_return(close_1y, 21)
    mom_3m = _pct_return(close_1y, 63)
    mom_6m = _pct_return(close_1y, 126)
    # 12M: prefer 2y history so we always have 252 trading days
    close_for_12m = close_2y if (close_2y is not None and len(close_2y) >= 253) else close_1y
    mom_12m = _pct_return(close_for_12m, 252)

    # ── Technical ────────────────────────────────────────────────────────────
    rsi_14 = _rsi(close_1y, 14)
    macd_sig = _macd_signal(close_1y)

    above_50ma = None
    above_200ma = None
    golden_cross = None
    if close_1y is not None and len(close_1y) >= 50:
        price = float(close_1y.iloc[-1])
        ma50 = float(close_1y.rolling(50).mean().iloc[-1])
        above_50ma = 1.0 if price > ma50 else 0.0
        if len(close_1y) >= 200:
            ma200 = float(close_1y.rolling(200).mean().iloc[-1])
            above_200ma = 1.0 if price > ma200 else 0.0
            if pd.notna(ma50) and pd.notna(ma200):
                golden_cross = 1.0 if ma50 > ma200 else 0.0

    # ── Quality ───────────────────────────────────────────────────────────────
    debt_to_equity = safe_get(info, "debtToEquity")
    if debt_to_equity is not None:
        debt_to_equity = float(debt_to_equity)

    fcf_yield = None
    fcf = safe_get(info, "freeCashflow")
    mkt_cap = safe_get(info, "marketCap")
    if fcf is not None and mkt_cap and mkt_cap > 0:
        fcf_yield = float(fcf) / float(mkt_cap)

    return {
        # Valuation
        "pe": pe,
        "pb": pb,
        "ps": ps,
        "ev_ebitda": ev_ebitda,
        # Growth
        "revenue_growth": revenue_growth,
        "eps_growth": eps_growth,
        # Profitability
        "gross_margin": gross_margin,
        "operating_margin": operating_margin,
        "net_margin": net_margin,
        "roe": roe,
        "roa": roa,
        # Momentum
        "mom_1m": mom_1m,
        "mom_3m": mom_3m,
        "mom_6m": mom_6m,
        "mom_12m": mom_12m,
        # Technical
        "rsi_14": rsi_14,
        "macd_signal": macd_sig,
        "above_50ma": above_50ma,
        "above_200ma": above_200ma,
        "golden_cross": golden_cross,
        # Quality
        "debt_to_equity": debt_to_equity,
        "fcf_yield": fcf_yield,
    }

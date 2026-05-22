"""Z-score normalization and weighted composite scoring engine."""

import numpy as np
import pandas as pd

from utils import normalize_weights

# (display_name, group, higher_is_better)
# higher_is_better=None means special handling (RSI centrality)
FACTOR_META: dict[str, tuple[str, str, bool | None]] = {
    "pe":               ("P/E Ratio",       "Valuation",     False),
    "pb":               ("P/B Ratio",       "Valuation",     False),
    "ps":               ("P/S Ratio",       "Valuation",     False),
    "ev_ebitda":        ("EV/EBITDA",        "Valuation",     False),
    "revenue_growth":   ("Revenue Growth",  "Growth",        True),
    "eps_growth":       ("EPS Growth",      "Growth",        True),
    "gross_margin":     ("Gross Margin",    "Profitability",  True),
    "operating_margin": ("Op. Margin",      "Profitability",  True),
    "net_margin":       ("Net Margin",      "Profitability",  True),
    "roe":              ("ROE",             "Profitability",  True),
    "roa":              ("ROA",             "Profitability",  True),
    "mom_1m":           ("1M Return",       "Momentum",      True),
    "mom_3m":           ("3M Return",       "Momentum",      True),
    "mom_6m":           ("6M Return",       "Momentum",      True),
    "mom_12m":          ("12M Return",      "Momentum",      True),
    "rsi_14":           ("RSI-14",          "Technical",     None),
    "macd_signal":      ("MACD Signal",     "Technical",     True),
    "above_50ma":       ("Above 50-MA",     "Technical",     True),
    "above_200ma":      ("Above 200-MA",    "Technical",     True),
    "golden_cross":     ("Golden Cross",    "Technical",     True),
    "debt_to_equity":   ("D/E Ratio",       "Quality",       False),
    "fcf_yield":        ("FCF Yield",       "Quality",       True),
}

FACTOR_GROUPS = ["Valuation", "Growth", "Profitability", "Momentum", "Technical", "Quality"]

DEFAULT_GROUP_WEIGHTS: dict[str, float] = {
    "Valuation":     0.20,
    "Growth":        0.20,
    "Profitability": 0.20,
    "Momentum":      0.15,
    "Technical":     0.10,
    "Quality":       0.15,
}


def _zscore_series(s: pd.Series) -> pd.Series:
    mean, std = s.mean(), s.std()
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=s.index)
    return (s - mean) / std


def _rsi_centrality(rsi_val: float) -> float:
    """Map RSI to a centrality score: RSI=55 → 1.0, extremes → ~0."""
    return 1.0 - abs(rsi_val - 55.0) / 45.0


def compute_scores(
    factors_dict: dict[str, dict | None],
    group_weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Build a scored DataFrame from a dict of {ticker: factor_dict}.

    Returns DataFrame with columns:
      - all raw factor keys
      - z_<factor> for each factor
      - composite_score (float)
      - rank (int, 1 = best)
      - data_quality (float, fraction of factors with real data)
    """
    if group_weights is None:
        group_weights = DEFAULT_GROUP_WEIGHTS.copy()

    weights = normalize_weights({g: group_weights.get(g, 0.0) for g in FACTOR_GROUPS})

    # Build raw DataFrame
    valid = {sym: f for sym, f in factors_dict.items() if f is not None}
    if not valid:
        return pd.DataFrame()

    raw_df = pd.DataFrame.from_dict(valid, orient="index")
    # Ensure all factor columns exist
    for key in FACTOR_META:
        if key not in raw_df.columns:
            raw_df[key] = np.nan

    factor_keys = list(FACTOR_META.keys())
    raw_df = raw_df[factor_keys]

    # Data quality: fraction of factors that have real data per ticker
    data_quality = raw_df.notna().sum(axis=1) / len(factor_keys)

    # RSI centrality transform before fill/zscore
    rsi_col = raw_df["rsi_14"].copy()
    rsi_transformed = rsi_col.apply(
        lambda x: _rsi_centrality(x) if pd.notna(x) else np.nan
    )
    raw_df["rsi_14"] = rsi_transformed

    # Fill NaN with column median
    filled_df = raw_df.copy()
    for col in factor_keys:
        median = filled_df[col].median()
        filled_df[col] = filled_df[col].fillna(median if pd.notna(median) else 0.0)

    # Z-score each column, clip to [-3, 3]
    z_df = filled_df.copy()
    for col in factor_keys:
        z_df[col] = _zscore_series(filled_df[col]).clip(-3, 3)

    # Flip lower-is-better factors
    for key, (_, _, higher_is_better) in FACTOR_META.items():
        if higher_is_better is False:
            z_df[key] = -z_df[key]
        # higher_is_better=None (RSI) already transformed; keep sign as-is

    # Rename z columns
    z_renamed = z_df.rename(columns={k: f"z_{k}" for k in factor_keys})

    # Group scores
    group_scores = pd.DataFrame(index=z_renamed.index)
    for group in FACTOR_GROUPS:
        group_factor_keys = [k for k, (_, g, _) in FACTOR_META.items() if g == group]
        z_cols = [f"z_{k}" for k in group_factor_keys]
        group_scores[group] = z_renamed[z_cols].mean(axis=1)

    # Composite score
    composite = pd.Series(0.0, index=z_renamed.index)
    for group in FACTOR_GROUPS:
        composite += weights[group] * group_scores[group]

    # Assemble final DataFrame
    # Restore original RSI raw value (not the centrality-transformed one)
    result_raw = pd.DataFrame.from_dict(valid, orient="index")[factor_keys]
    result = result_raw.copy()
    for key in factor_keys:
        result[f"z_{key}"] = z_renamed[f"z_{key}"]
    result["composite_score"] = composite
    result["rank"] = composite.rank(ascending=False, method="min").astype(int)
    result["data_quality"] = data_quality
    result = result.sort_values("composite_score", ascending=False)

    return result

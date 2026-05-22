"""Shared utility helpers."""

import math
import pandas as pd


def safe_get(d: dict, key: str, default=None):
    """Return d[key] if present and not None/NaN, else default."""
    if not isinstance(d, dict):
        return default
    val = d.get(key, default)
    if val is None:
        return default
    try:
        if isinstance(val, float) and math.isnan(val):
            return default
    except TypeError:
        pass
    return val


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Scale weights so they sum to 1.0; handle zero-sum gracefully."""
    total = sum(weights.values())
    if total == 0:
        n = len(weights)
        return {k: 1.0 / n for k in weights}
    return {k: v / total for k, v in weights.items()}


def format_pct(val) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val * 100:.1f}%"


def format_ratio(val) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val:.2f}x"


def format_number(val, decimals: int = 2) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val:.{decimals}f}"

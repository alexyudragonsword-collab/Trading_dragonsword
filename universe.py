"""Semiconductor stock universe definitions."""

SUBSECTOR_MAP: dict[str, list[str]] = {
    "Fabless Design": [
        "NVDA", "AMD", "QCOM", "AVGO", "MRVL", "SWKS", "QRVO", "MPWR",
        "MTSI", "SMTC", "AMBA", "SLAB",
        "LSCC",   # Lattice Semiconductor
        "CRUS",   # Cirrus Logic
        "ALGM",   # Allegro MicroSystems
        "POWI",   # Power Integrations
        "SITM",   # SiTime
    ],
    "IDM / Foundry": [
        "INTC", "TXN", "ADI", "MCHP", "ON", "STM", "NXPI", "WOLF",
        "DIOD",     # Diodes Incorporated
        "GFS",      # GlobalFoundries
        "TSM",      # Taiwan Semiconductor (TSMC)
        "0981.HK",  # SMIC（中芯国际）
        "1347.HK",  # Hua Hong Semiconductor（华虹半导体）
    ],
    "Equipment / EDA": [
        "AMAT", "LRCX", "KLAC", "ASML", "ONTO", "FORM", "ICHR", "ACMR",
        "CAMT", "COHU",
        "KLIC",   # Kulicke & Soffa
        "ACLS",   # Axcelis Technologies
        "AEHR",   # Aehr Test Systems
    ],
    "Memory": [
        "MU", "WDC",
        "005930.KS",  # Samsung Electronics
        "000660.KS",  # SK Hynix
    ],
    "Packaging / Test": [
        "AMKR",
        "KLIC",   # Kulicke & Soffa (also packaging-adjacent)
    ],
}

# deduplicate while preserving order (KLIC appears in two groups above)
_seen: set[str] = set()
_deduped: dict[str, list[str]] = {}
for _sub, _tickers in SUBSECTOR_MAP.items():
    _deduped[_sub] = []
    for _t in _tickers:
        if _t not in _seen:
            _seen.add(_t)
            _deduped[_sub].append(_t)
SUBSECTOR_MAP = _deduped

ALL_TICKERS: list[str] = [
    ticker
    for tickers in SUBSECTOR_MAP.values()
    for ticker in tickers
]

TICKER_TO_SUBSECTOR: dict[str, str] = {
    ticker: subsector
    for subsector, tickers in SUBSECTOR_MAP.items()
    for ticker in tickers
}

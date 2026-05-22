"""Semiconductor stock universe definitions."""

SUBSECTOR_MAP: dict[str, list[str]] = {
    "Fabless Design": [
        "NVDA", "AMD", "QCOM", "AVGO", "MRVL", "SWKS", "QRVO", "MPWR",
        "MTSI", "SMTC", "AMBA", "SLAB",
    ],
    "IDM / Foundry": [
        "INTC", "TXN", "ADI", "MCHP", "ON", "STM", "NXPI", "WOLF",
    ],
    "Equipment / EDA": [
        "AMAT", "LRCX", "KLAC", "ASML", "ONTO", "FORM", "ICHR", "ACMR",
        "CAMT", "COHU",
    ],
    "Memory": [
        "MU", "WDC",
    ],
    "Packaging / Test": [
        "AMKR",
    ],
}

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

"""Stock universe — two top-level sectors, each with sub-sectors."""

SECTOR_MAP: dict[str, dict[str, list[str]]] = {
    "半导体": {
        "Fabless Design": [
            "NVDA", "AMD", "QCOM", "AVGO", "MRVL", "SWKS", "QRVO", "MPWR",
            "MTSI", "SMTC", "AMBA", "SLAB",
            "LSCC",     # Lattice Semiconductor
            "CRUS",     # Cirrus Logic
            "ALGM",     # Allegro MicroSystems
            "POWI",     # Power Integrations
            "SITM",     # SiTime
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
            "KLIC",     # Kulicke & Soffa
            "ACLS",     # Axcelis Technologies
            "AEHR",     # Aehr Test Systems
        ],
        "Memory": [
            "MU", "WDC",
            "005930.KS",  # Samsung Electronics
            "000660.KS",  # SK Hynix
        ],
        "Packaging / Test": [
            "AMKR",
            "KLIC",     # Kulicke & Soffa (deduped to Equipment / EDA)
        ],
    },
    "科技": {
        "Cloud / AI Platform": [
            "MSFT",   # Microsoft
            "GOOGL",  # Alphabet
            "AMZN",   # Amazon
            "META",   # Meta Platforms
            "ORCL",   # Oracle
            "IBM",    # IBM
        ],
        "Software / SaaS": [
            "ADBE",   # Adobe
            "CRM",    # Salesforce
            "NOW",    # ServiceNow
            "WDAY",   # Workday
            "INTU",   # Intuit
            "SNOW",   # Snowflake
            "MDB",    # MongoDB
            "DDOG",   # Datadog
            "TEAM",   # Atlassian
        ],
        "Cybersecurity": [
            "CRWD",   # CrowdStrike
            "PANW",   # Palo Alto Networks
            "FTNT",   # Fortinet
            "ZS",     # Zscaler
            "OKTA",   # Okta
            "S",      # SentinelOne
        ],
        "Hardware": [
            "AAPL",   # Apple
            "DELL",   # Dell Technologies
            "HPE",    # Hewlett Packard Enterprise
            "NTAP",   # NetApp
            "STX",    # Seagate
        ],
        "Internet": [
            "BABA",   # Alibaba
            "JD",     # JD.com
            "SHOP",   # Shopify
            "EBAY",   # eBay
            "SNAP",   # Snap
            "PINS",   # Pinterest
            "SPOT",   # Spotify
        ],
    },
}

# ── Flatten with global dedup (KLIC appears in two semi sub-sectors) ──────────

_seen: set[str] = set()
_subsector_map: dict[str, list[str]] = {}
_subsector_to_sector: dict[str, str] = {}

for _sector, _subsectors in SECTOR_MAP.items():
    for _sub, _tickers in _subsectors.items():
        _subsector_to_sector[_sub] = _sector
        _subsector_map[_sub] = []
        for _t in _tickers:
            if _t not in _seen:
                _seen.add(_t)
                _subsector_map[_sub].append(_t)

SUBSECTOR_MAP: dict[str, list[str]] = _subsector_map
SUBSECTOR_TO_SECTOR: dict[str, str] = _subsector_to_sector

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

TICKER_TO_SECTOR: dict[str, str] = {
    ticker: SUBSECTOR_TO_SECTOR[subsector]
    for ticker, subsector in TICKER_TO_SUBSECTOR.items()
}

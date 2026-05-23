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
        # Magnificent Seven listed first so dedup assigns AAPL/MSFT/GOOGL/AMZN/META here
        "Magnificent Seven": [
            "AAPL",   # Apple
            "MSFT",   # Microsoft
            "GOOGL",  # Alphabet
            "AMZN",   # Amazon
            "NVDA",   # NVIDIA (primary: 半导体 > Fabless Design; shown here for Mag7 context)
            "META",   # Meta Platforms
            "TSLA",   # Tesla
        ],
        "Cloud / AI Platform": [
            # MSFT, GOOGL, AMZN, META moved to Magnificent Seven
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
            # AAPL moved to Magnificent Seven
            "DELL",   # Dell Technologies
            "HPE",    # Hewlett Packard Enterprise
            "NTAP",   # NetApp
            "STX",    # Seagate
        ],
        "Internet": [
            # BABA, JD moved to 中国科技股
            "SHOP",   # Shopify
            "EBAY",   # eBay
            "SNAP",   # Snap
            "PINS",   # Pinterest
            "SPOT",   # Spotify
        ],
        "中国科技股": [
            "BABA",   # Alibaba（阿里巴巴）
            "JD",     # JD.com（京东）
            "BIDU",   # Baidu（百度）
            "PDD",    # PDD Holdings / Pinduoduo（拼多多）
            "NTES",   # NetEase（网易）
            "BILI",   # Bilibili（哔哩哔哩）
            "TCOM",   # Trip.com（携程）
            "TCEHY",  # Tencent Holdings ADR（腾讯控股）
            "FUTU",   # Futu Holdings（富途控股）
            "BOSS",   # Kanzhun / BOSS 直聘
        ],
    },
}

# ── Company names ─────────────────────────────────────────────────────────────

TICKER_NAMES: dict[str, str] = {
    # Fabless Design
    "NVDA": "NVIDIA",
    "AMD": "Advanced Micro Devices",
    "QCOM": "Qualcomm",
    "AVGO": "Broadcom",
    "MRVL": "Marvell Technology",
    "SWKS": "Skyworks Solutions",
    "QRVO": "Qorvo",
    "MPWR": "Monolithic Power Systems",
    "MTSI": "MACOM Technology",
    "SMTC": "Semtech",
    "AMBA": "Ambarella",
    "SLAB": "Silicon Laboratories",
    "LSCC": "Lattice Semiconductor",
    "CRUS": "Cirrus Logic",
    "ALGM": "Allegro MicroSystems",
    "POWI": "Power Integrations",
    "SITM": "SiTime",
    # IDM / Foundry
    "INTC": "Intel",
    "TXN": "Texas Instruments",
    "ADI": "Analog Devices",
    "MCHP": "Microchip Technology",
    "ON": "onsemi",
    "STM": "STMicroelectronics",
    "NXPI": "NXP Semiconductors",
    "WOLF": "Wolfspeed",
    "DIOD": "Diodes Incorporated",
    "GFS": "GlobalFoundries",
    "TSM": "TSMC",
    "0981.HK": "中芯国际 (SMIC)",
    "1347.HK": "华虹半导体",
    # Equipment / EDA
    "AMAT": "Applied Materials",
    "LRCX": "Lam Research",
    "KLAC": "KLA Corporation",
    "ASML": "ASML Holding",
    "ONTO": "Onto Innovation",
    "FORM": "FormFactor",
    "ICHR": "Ichor Holdings",
    "ACMR": "ACM Research",
    "CAMT": "Camtek",
    "COHU": "Cohu",
    "KLIC": "Kulicke & Soffa",
    "ACLS": "Axcelis Technologies",
    "AEHR": "Aehr Test Systems",
    # Memory
    "MU": "Micron Technology",
    "WDC": "Western Digital",
    "005930.KS": "三星电子 (Samsung)",
    "000660.KS": "SK 海力士 (SK Hynix)",
    # Packaging / Test
    "AMKR": "Amkor Technology",
    # Magnificent Seven
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "TSLA": "Tesla",
    # Cloud / AI Platform
    "ORCL": "Oracle",
    "IBM": "IBM",
    # Software / SaaS
    "ADBE": "Adobe",
    "CRM": "Salesforce",
    "NOW": "ServiceNow",
    "WDAY": "Workday",
    "INTU": "Intuit",
    "SNOW": "Snowflake",
    "MDB": "MongoDB",
    "DDOG": "Datadog",
    "TEAM": "Atlassian",
    # Cybersecurity
    "CRWD": "CrowdStrike",
    "PANW": "Palo Alto Networks",
    "FTNT": "Fortinet",
    "ZS": "Zscaler",
    "OKTA": "Okta",
    "S": "SentinelOne",
    # Hardware
    "DELL": "Dell Technologies",
    "HPE": "HP Enterprise",
    "NTAP": "NetApp",
    "STX": "Seagate",
    # Internet
    "SHOP": "Shopify",
    "EBAY": "eBay",
    "SNAP": "Snap",
    "PINS": "Pinterest",
    "SPOT": "Spotify",
    # 中国科技股
    "BABA": "阿里巴巴 (Alibaba)",
    "JD": "京东 (JD.com)",
    "BIDU": "百度 (Baidu)",
    "PDD": "拼多多 (PDD Holdings)",
    "NTES": "网易 (NetEase)",
    "BILI": "哔哩哔哩 (Bilibili)",
    "TCOM": "携程 (Trip.com)",
    "TCEHY": "腾讯控股 (Tencent)",
    "FUTU": "富途控股 (Futu)",
    "BOSS": "BOSS 直聘 (Kanzhun)",
}

# ── Derived mappings ──────────────────────────────────────────────────────────
#
# SUBSECTOR_MAP: full membership, no dedup — same ticker may appear in multiple sub-sectors.
# ALL_TICKERS:   deduped for data fetching (each ticker fetched once).
# TICKER_TO_SUBSECTORS / TICKER_TO_SECTORS: all memberships per ticker.
# TICKER_TO_SUBSECTOR / TICKER_TO_SECTOR:   primary (first) membership for table display.

# Sub-sector → sector lookup (no dedup needed here)
SUBSECTOR_TO_SECTOR: dict[str, str] = {
    sub: sector
    for sector, subsectors in SECTOR_MAP.items()
    for sub in subsectors
}

# SUBSECTOR_MAP: no dedup
SUBSECTOR_MAP: dict[str, list[str]] = {
    sub: list(tickers)
    for sector_subs in SECTOR_MAP.values()
    for sub, tickers in sector_subs.items()
}

# ALL_TICKERS: deduped (preserves first-occurrence order)
_seen: set[str] = set()
_all: list[str] = []
for _tickers in SUBSECTOR_MAP.values():
    for _t in _tickers:
        if _t not in _seen:
            _seen.add(_t)
            _all.append(_t)
ALL_TICKERS: list[str] = _all

# ticker → all sub-sectors it belongs to
TICKER_TO_SUBSECTORS: dict[str, list[str]] = {}
for _sub, _tickers in SUBSECTOR_MAP.items():
    for _t in _tickers:
        TICKER_TO_SUBSECTORS.setdefault(_t, []).append(_sub)

# ticker → all top-level sectors it belongs to (deduped, order preserved)
TICKER_TO_SECTORS: dict[str, list[str]] = {
    t: list(dict.fromkeys(SUBSECTOR_TO_SECTOR[s] for s in subs))
    for t, subs in TICKER_TO_SUBSECTORS.items()
}

# Primary (first) sub-sector and sector per ticker — used for table display
TICKER_TO_SUBSECTOR: dict[str, str] = {t: subs[0] for t, subs in TICKER_TO_SUBSECTORS.items()}
TICKER_TO_SECTOR: dict[str, str] = {t: sectors[0] for t, sectors in TICKER_TO_SECTORS.items()}


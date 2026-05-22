# CLAUDE.md — Trading Dragonsword

This file is the authoritative guide for AI assistants (Claude Code and similar tools) working in this repository. Read it fully before making any changes.

---

## Project Overview

**Trading Dragonsword** is a US semiconductor sector stock screening system. It pulls real-time market data from Yahoo Finance, computes 22 quantitative factors across 6 groups (Valuation, Growth, Profitability, Momentum, Technical, Quality), ranks ~45 semiconductor stocks by a weighted composite Z-score, and presents the results in an interactive Streamlit web dashboard.

- **Repository**: `alexyudragonsword-collab/trading_dragonsword`
- **Primary branch**: `main`
- **Development branch convention**: `claude/<description>-<id>` for AI-driven work
- **Language**: Python 3.11+
- **UI framework**: Streamlit
- **Data source**: yfinance (Yahoo Finance, free, no API key required)

---

## Development Branch

All AI-assisted changes must be committed to the designated feature branch and pushed before the session ends. Never push directly to `main` without explicit user approval.

```
git checkout -b claude/<description>-<id>
git push -u origin claude/<description>-<id>
```

---

## Git Conventions

- Commit messages should be concise and describe *why*, not just *what*.
- Never amend published commits; create new ones instead.
- Never skip pre-commit hooks (`--no-verify`) unless the user explicitly requests it.
- Never force-push to `main`.
- Stage specific files — avoid `git add -A` or `git add .` to prevent accidentally committing secrets.
- Do NOT create a pull request unless the user explicitly asks for one.

---

## Code Style (defaults until overridden)

- Prefer editing existing files over creating new ones.
- Do not add features, abstractions, or error handling beyond what the task requires.
- Write no comments by default. Only add a comment when the *why* is non-obvious.
- No docstrings unless the project language/framework convention requires them.
- Keep functions small and single-purpose.
- No backwards-compatibility shims for code that is simply being removed.

---

## Security

- Never commit secrets, API keys, tokens, or credentials. Use environment variables.
- Validate input only at system boundaries (user input, external APIs); trust internal guarantees.
- Avoid introducing OWASP Top 10 vulnerabilities: SQL injection, XSS, command injection, etc.
- If insecure code is introduced accidentally, fix it immediately before continuing.

---

## Environment Setup

**Requirements**: Python 3.11+ (no environment variables or external services needed).

```sh
pip install -r requirements.txt
```

No API keys are required. yfinance fetches data anonymously from Yahoo Finance.

The `.cache/` directory is created automatically on first run (git-ignored). It stores per-ticker pickle files with a 4-hour TTL to avoid re-fetching on browser refreshes.

---

## Build & Run

```sh
# Install dependencies
pip install -r requirements.txt

# Launch the Streamlit dashboard
streamlit run app.py

# The app opens at http://localhost:8501
# First cold load (~45 tickers) takes ~15 seconds; subsequent loads use cache
```

---

## Directory Structure

```
Trading_dragonsword/
├── CLAUDE.md             ← This file
├── requirements.txt      ← Pinned Python dependencies
├── app.py                ← Streamlit entry point; UI layout, widgets, charts
├── universe.py           ← ~45 semiconductor tickers grouped by sub-sector
├── data.py               ← yfinance fetch logic + .cache/*.pkl disk cache (TTL 4h)
├── factors.py            ← 22 quantitative factor calculations
├── scorer.py             ← Z-score normalization + weighted composite scoring
├── utils.py              ← safe_get, normalize_weights, format helpers
├── .gitignore
└── .cache/               ← Runtime cache (git-ignored)
    └── <TICKER>.pkl
```

### Module responsibilities

| File | Responsibility |
|------|----------------|
| `universe.py` | `ALL_TICKERS`, `SUBSECTOR_MAP`, `TICKER_TO_SUBSECTOR` |
| `data.py` | `load_all()`, `load_ticker()`, `clear_cache()` |
| `factors.py` | `compute_factors(symbol, raw) → dict[str, float\|None]` |
| `scorer.py` | `compute_scores(factors_dict, group_weights) → DataFrame`, `FACTOR_META`, `DEFAULT_GROUP_WEIGHTS` |
| `utils.py` | `safe_get()`, `normalize_weights()`, `format_pct()`, `format_ratio()` |
| `app.py` | Streamlit page, sidebar, 3 tabs (screener table, heatmap, stock detail) |

---

## Factor Reference

| Group | Factors |
|-------|---------|
| Valuation | PE, PB, PS, EV/EBITDA (lower = better) |
| Growth | Revenue Growth YoY, EPS Growth YoY |
| Profitability | Gross/Op/Net Margin, ROE, ROA |
| Momentum | 1M / 3M / 6M / 12M price return |
| Technical | RSI-14 (centrality-scored), MACD signal, above 50MA, above 200MA, golden cross |
| Quality | D/E ratio (lower = better), FCF Yield |

All factors are Z-score normalized across the universe, clipped to ±3. Lower-is-better factors are sign-flipped so all Z-scores are "higher = better". RSI uses a centrality transform (`1 - |RSI - 55| / 45`) before Z-scoring.

---

## Testing

No automated test suite yet. Manual verification:

1. `streamlit run app.py` — confirm the app loads without errors
2. Check that the screener table shows >30 rows and is sortable
3. Adjust weight sliders and confirm composite scores update immediately
4. Open the heatmap tab and confirm green/red coloring is consistent
5. Open stock detail for the top-ranked ticker; confirm price chart and MA overlays render
6. Click "刷新数据" — confirm the progress bar appears and data reloads

---

## Working with This Codebase as an AI

- Read this file at the start of every session.
- Before making changes, understand the existing patterns in the surrounding code.
- Match the code style of whatever file you are editing.
- Do not introduce new dependencies without discussing the trade-offs with the user.
- For exploratory questions, give a 2–3 sentence recommendation with the main trade-off before implementing.
- After pushing changes, confirm the branch and commit SHA so the user can verify.
- Update this CLAUDE.md whenever new conventions, tools, or workflows are established.

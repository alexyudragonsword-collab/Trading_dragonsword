"""Semiconductor Stock Screener — Streamlit entry point."""

import math
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import data as data_module
import factors as factors_module
import scorer as scorer_module
from scorer import FACTOR_META, FACTOR_GROUPS, DEFAULT_GROUP_WEIGHTS
from universe import ALL_TICKERS, SUBSECTOR_MAP, TICKER_TO_SUBSECTOR
from utils import format_pct, format_ratio, format_number, normalize_weights

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Semiconductor Stock Screener",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API key resolution (env var → st.secrets) ────────────────────────────────
# No API key needed — data is fetched from Yahoo Finance via yfinance + curl_cffi.

st.title("半导体板块选股系统")
st.caption("数据来源：Yahoo Finance  |  因子：估值 · 成长 · 盈利 · 动量 · 技术 · 质量")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("因子权重")
    group_weights: dict[str, float] = {}
    for group in FACTOR_GROUPS:
        default = DEFAULT_GROUP_WEIGHTS.get(group, 0.15)
        group_weights[group] = st.slider(
            group, min_value=0.0, max_value=1.0,
            value=default, step=0.05, key=f"w_{group}"
        )

    st.divider()
    st.header("筛选条件")

    subsector_options = list(SUBSECTOR_MAP.keys())
    selected_subsectors = st.multiselect(
        "子板块", options=subsector_options, default=subsector_options,
        key="filter_subsectors",
    )

    market_cap_options = {
        "全部": 0,
        "> 1B": 1e9,
        "> 5B": 5e9,
        "> 10B": 10e9,
        "> 50B": 50e9,
    }
    min_mktcap_label = st.selectbox(
        "最低市值", options=list(market_cap_options.keys()), index=0,
        key="filter_mktcap",
    )
    min_mktcap = market_cap_options[min_mktcap_label]

    min_score = st.slider(
        "最低合成分（过滤低分股）", min_value=-3.0, max_value=3.0,
        value=-3.0, step=0.1, key="filter_min_score",
    )

    st.divider()
    st.header("数据控制")

    if st.button("刷新数据", use_container_width=True):
        data_module.clear_cache(ALL_TICKERS)
        st.cache_data.clear()
        st.rerun()

# ── Data loading (cached) ─────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_all_raw(tickers: tuple[str, ...]) -> dict:
    progress_bar = st.progress(0, text="正在拉取行情数据…")

    def cb(i: int, total: int, symbol: str) -> None:
        frac = i / total if total > 0 else 1.0
        label = f"拉取中 {symbol} ({i}/{total})…" if symbol else "完成"
        progress_bar.progress(frac, text=label)

    result = data_module.load_all(list(tickers), progress_callback=cb)
    progress_bar.empty()
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def get_all_factors(raw_data_keys: tuple[str, ...]) -> dict:
    raw_data = get_all_raw(raw_data_keys)
    return {
        sym: factors_module.compute_factors(sym, raw)
        for sym, raw in raw_data.items()
    }


ticker_tuple = tuple(ALL_TICKERS)
with st.spinner("加载数据中，首次运行约需 15 秒…"):
    factors_data = get_all_factors(ticker_tuple)
    raw_data = get_all_raw(ticker_tuple)

# ── Scoring ───────────────────────────────────────────────────────────────────

scores_df = scorer_module.compute_scores(factors_data, group_weights)

# ── Filtering ─────────────────────────────────────────────────────────────────

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # Sub-sector filter
    if selected_subsectors and len(selected_subsectors) < len(SUBSECTOR_MAP):
        keep = [t for t in df.index if TICKER_TO_SUBSECTOR.get(t) in selected_subsectors]
        df = df.loc[keep]

    # Market cap filter
    if min_mktcap > 0:
        keep = []
        for ticker in df.index:
            info = (raw_data.get(ticker) or {}).get("info") or {}
            mktcap = info.get("marketCap") or 0
            if mktcap >= min_mktcap:
                keep.append(ticker)
        df = df.loc[keep]

    # Min composite score filter
    df = df[df["composite_score"] >= min_score]

    return df


filtered_df = apply_filters(scores_df.copy())

# Tickers that failed to load
failed_tickers = [sym for sym, v in factors_data.items() if v is None]
if failed_tickers:
    st.sidebar.warning(f"数据拉取失败：{', '.join(failed_tickers)}")

# ── Last fetched info ──────────────────────────────────────────────────────────

cache_status = data_module.get_cache_status(ALL_TICKERS)
fresh_count = sum(1 for v in cache_status.values() if v["fresh"])
last_times = [v["fetched_at"] for v in cache_status.values() if v["fetched_at"]]
if last_times:
    latest = max(last_times)
    st.sidebar.caption(f"缓存：{fresh_count}/{len(ALL_TICKERS)} 新鲜  |  最近拉取：{latest.strftime('%H:%M:%S')}")

# ── Universe Overview ─────────────────────────────────────────────────────────

with st.expander(f"📋 股票池（{len(ALL_TICKERS)} 只）", expanded=False):
    cols = st.columns(len(SUBSECTOR_MAP))
    for col, (subsector, tickers) in zip(cols, SUBSECTOR_MAP.items()):
        with col:
            st.markdown(f"**{subsector}** ({len(tickers)})")
            for t in tickers:
                st.markdown(f"- {t}")

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["选股排名", "因子热力图", "个股详情"])

# ─── Tab 1: Screener Table ───────────────────────────────────────────────────

with tab1:
    if filtered_df.empty:
        st.info("没有满足当前筛选条件的股票。")
    else:
        factor_keys = list(FACTOR_META.keys())
        display_cols = {
            "composite_score": "合成分",
            "rank": "排名",
            "data_quality": "数据完整度",
        }
        for key, (name, group, _) in FACTOR_META.items():
            display_cols[key] = name

        show_df = filtered_df[list(display_cols.keys())].copy()

        # Add sub-sector column
        show_df.insert(0, "子板块", [TICKER_TO_SUBSECTOR.get(t, "—") for t in show_df.index])
        show_df.index.name = "股票"

        st.subheader(f"共 {len(show_df)} 只股票")

        pct_factor_keys = [
            "gross_margin", "operating_margin", "net_margin", "roe", "roa",
            "revenue_growth", "eps_growth", "mom_1m", "mom_3m", "mom_6m", "mom_12m", "fcf_yield",
        ]

        col_config = {
            "合成分": st.column_config.ProgressColumn(
                "合成分", min_value=float(scores_df["composite_score"].min() - 0.1),
                max_value=float(scores_df["composite_score"].max() + 0.1),
                format="%.3f",
            ),
            "排名": st.column_config.NumberColumn("排名", format="%d"),
            "数据完整度": st.column_config.ProgressColumn(
                "数据完整度", min_value=0.0, max_value=1.0, format="%.0%%"
            ),
        }
        for key in pct_factor_keys:
            name = FACTOR_META[key][0]
            col_config[name] = st.column_config.NumberColumn(name, format="%.1f%%")

        renamed = show_df.rename(columns=display_cols)
        # Convert pct columns for display
        for key in pct_factor_keys:
            col_name = FACTOR_META[key][0]
            if col_name in renamed.columns:
                renamed[col_name] = renamed[col_name].apply(
                    lambda x: x * 100 if (x is not None and not (isinstance(x, float) and math.isnan(x))) else x
                )

        st.dataframe(
            renamed,
            use_container_width=True,
            height=600,
            column_config=col_config,
        )

# ─── Tab 2: Factor Heatmap ───────────────────────────────────────────────────

with tab2:
    if filtered_df.empty:
        st.info("没有数据可显示。")
    else:
        z_cols = [f"z_{k}" for k in FACTOR_META.keys()]
        available_z = [c for c in z_cols if c in filtered_df.columns]
        z_matrix = filtered_df[available_z]

        factor_display_names = [FACTOR_META[c[2:]][0] for c in available_z]

        # Sort tickers by composite score (already sorted, just reconfirm)
        tickers_ordered = z_matrix.index.tolist()

        fig = go.Figure(data=go.Heatmap(
            z=z_matrix.values,
            x=factor_display_names,
            y=tickers_ordered,
            colorscale="RdYlGn",
            zmid=0,
            zmin=-3,
            zmax=3,
            colorbar=dict(title="Z-Score"),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "因子：%{x}<br>"
                "Z-Score：%{z:.2f}<extra></extra>"
            ),
        ))
        fig.update_layout(
            title="因子 Z-Score 热力图（绿色=高分，红色=低分）",
            xaxis_title="因子",
            yaxis_title="股票",
            height=max(400, len(tickers_ordered) * 22 + 100),
            margin=dict(l=80, r=40, t=60, b=120),
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

# ─── Tab 3: Stock Detail ─────────────────────────────────────────────────────

with tab3:
    if filtered_df.empty:
        st.info("没有数据可显示。")
    else:
        ranked_tickers = filtered_df.index.tolist()
        selected = st.selectbox(
            "选择股票", options=ranked_tickers,
            index=0,
            format_func=lambda t: f"{t} (排名 #{int(filtered_df.loc[t, 'rank'])})",
            key="detail_ticker",
        )

        st.subheader(f"{selected}  —  {TICKER_TO_SUBSECTOR.get(selected, '半导体')}")

        col_score, col_quality, col_subsector = st.columns(3)
        composite = filtered_df.loc[selected, "composite_score"]
        rank = int(filtered_df.loc[selected, "rank"])
        dq = filtered_df.loc[selected, "data_quality"]
        col_score.metric("合成分", f"{composite:.3f}")
        col_quality.metric("数据完整度", f"{dq * 100:.0f}%")
        col_subsector.metric("排名", f"#{rank} / {len(filtered_df)}")

        # Price chart with MAs and MACD
        raw = raw_data.get(selected)
        close = (raw or {}).get("close")

        if close is not None and len(close) > 10:
            ma50 = close.rolling(50).mean()
            ma200 = close.rolling(200).mean()

            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_hist = macd_line - signal_line

            fig_price = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                row_heights=[0.7, 0.3],
                vertical_spacing=0.05,
                subplot_titles=("价格走势", "MACD"),
            )

            fig_price.add_trace(go.Scatter(
                x=close.index, y=close.values,
                name="收盘价", line=dict(color="#1f77b4", width=1.5),
            ), row=1, col=1)

            if ma50.notna().any():
                fig_price.add_trace(go.Scatter(
                    x=ma50.index, y=ma50.values,
                    name="50MA", line=dict(color="#ff7f0e", width=1, dash="dot"),
                ), row=1, col=1)

            if ma200.notna().any():
                fig_price.add_trace(go.Scatter(
                    x=ma200.index, y=ma200.values,
                    name="200MA", line=dict(color="#d62728", width=1, dash="dash"),
                ), row=1, col=1)

            colors = ["green" if v >= 0 else "red" for v in macd_hist.values]
            fig_price.add_trace(go.Bar(
                x=macd_hist.index, y=macd_hist.values,
                name="MACD柱", marker_color=colors,
            ), row=2, col=1)
            fig_price.add_trace(go.Scatter(
                x=signal_line.index, y=signal_line.values,
                name="信号线", line=dict(color="orange", width=1),
            ), row=2, col=1)

            fig_price.update_layout(
                height=500, showlegend=True,
                margin=dict(l=40, r=20, t=60, b=20),
            )
            st.plotly_chart(fig_price, use_container_width=True)
        else:
            st.warning("价格历史数据不可用。")

        st.divider()
        col_bar, col_raw = st.columns([3, 2])

        with col_bar:
            st.subheader("因子 Z-Score")
            z_vals = []
            z_names = []
            z_colors = []
            for key, (name, _, _) in FACTOR_META.items():
                z_col = f"z_{key}"
                if z_col in filtered_df.columns:
                    val = filtered_df.loc[selected, z_col]
                    if pd.notna(val):
                        z_vals.append(float(val))
                        z_names.append(name)
                        z_colors.append("green" if val >= 0 else "red")

            fig_bar = go.Figure(go.Bar(
                x=z_vals, y=z_names,
                orientation="h",
                marker_color=z_colors,
            ))
            fig_bar.update_layout(
                height=550, margin=dict(l=10, r=10, t=20, b=20),
                xaxis_title="Z-Score",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_raw:
            st.subheader("原始因子值")
            factor_row = factors_data.get(selected) or {}
            table_data = []
            for key, (name, group, _) in FACTOR_META.items():
                raw_val = factor_row.get(key)
                pct_keys = {
                    "gross_margin", "operating_margin", "net_margin", "roe", "roa",
                    "revenue_growth", "eps_growth",
                    "mom_1m", "mom_3m", "mom_6m", "mom_12m", "fcf_yield",
                }
                if raw_val is None or (isinstance(raw_val, float) and math.isnan(raw_val)):
                    display_val = "N/A"
                elif key in pct_keys:
                    display_val = format_pct(raw_val)
                elif key in ("pe", "pb", "ps", "ev_ebitda"):
                    display_val = format_ratio(raw_val)
                elif key in ("rsi_14",):
                    display_val = format_number(raw_val, 1)
                elif key in ("macd_signal", "above_50ma", "above_200ma", "golden_cross"):
                    display_val = str(int(raw_val)) if raw_val is not None else "N/A"
                else:
                    display_val = format_number(raw_val, 2)
                table_data.append({"因子": name, "组别": group, "数值": display_val})

            st.dataframe(
                pd.DataFrame(table_data).set_index("因子"),
                use_container_width=True,
                height=580,
            )

"""
components_group.py — Group & Traveler Intelligence tab for Dana Point PULSE.

Renders the dedicated 👥 Group & Travel tab with 4 sub-tabs:
  1. Group Strategy    — TBID opportunity, displacement heatmap, executive brief
  2. Traveler Types    — radar chart, booking windows, LOS benchmarks
  3. National Context  — $319B funnel, segment donut, recovery rates
  4. AI Analyst        — pre-loaded group travel prompts
"""

from __future__ import annotations

import sqlite3
import os
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── DB path ──────────────────────────────────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "analytics.sqlite")

# ── Thresholds (named constants) ─────────────────────────────────────────────
OCC_GROUP_SAFE_MAX  = 65.0   # below this: group blocks welcome, low displacement risk
OCC_GROUP_RISK_MIN  = 80.0   # above this: group blocks displace higher-rate transient
OCC_GROUP_WARN_MIN  = 70.0   # amber zone
TBID_RATE           = 0.0125
TOT_RATE            = 0.10
GROUP_SHARE_LOW     = 0.25
GROUP_SHARE_HIGH    = 0.32
GROUP_ADR_DISCOUNT  = 0.18   # group negotiated rate ~18% below blended ADR
SMERF_BOOKING_WINDOW_LOW  = 8   # weeks
SMERF_BOOKING_WINDOW_HIGH = 48
CACHE_TTL_GROUP     = 1800   # 30 min — semi-live group data
CACHE_TTL_NATIONAL  = 3600   # 1 hr  — historical benchmarks

_DARK_BG   = "rgba(0,0,0,0)"
_GRID_CLR  = "rgba(148,163,184,0.15)"
_FONT_CLR  = "#CBD5E1"
_LABEL_CLR = "#94A3B8"

_COLORWAY = [
    "#0891B2",  # teal
    "#F5B940",  # gold
    "#10B981",  # green
    "#A78BFA",  # purple
    "#FB923C",  # orange
    "#EF4444",  # red
    "#38BDF8",  # sky
    "#6EE7B7",  # seafoam
]


# ── Small utilities ───────────────────────────────────────────────────────────

def _dark_fig(height: int = 320) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        plot_bgcolor  = _DARK_BG,
        paper_bgcolor = _DARK_BG,
        font          = dict(color=_FONT_CLR, size=11.5),
        height        = height,
        margin        = dict(l=14, r=14, t=48, b=14),
        colorway      = _COLORWAY,
        legend        = dict(
            orientation="h", yanchor="bottom", y=1.04,
            xanchor="left", x=0,
            font=dict(size=11, color=_LABEL_CLR),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel    = dict(
            bgcolor="rgba(20,50,80,0.96)",
            bordercolor="rgba(0,212,200,0.60)",
            font=dict(size=13, color="#EFF6FF"),
        ),
    )
    fig.update_xaxes(showgrid=False, color=_LABEL_CLR)
    fig.update_yaxes(showgrid=True, gridcolor=_GRID_CLR, color=_LABEL_CLR)
    return fig


def _metric_box(label: str, value: str, note: str = "", color: str = "#0891B2",
                action: str = "") -> str:
    action_html = (
        f'<div style="margin-top:8px;padding:6px 10px;background:rgba(255,255,255,0.06);'
        f'border-radius:4px;font-size:10.5px;color:#93C5FD;line-height:1.5;">'
        f'<strong>Action:</strong> {action}</div>'
    ) if action else ""
    return (
        f'<div style="background:rgba(255,255,255,0.04);border-top:3px solid {color};'
        f'border-radius:8px;padding:14px 16px;text-align:center;">'
        f'<div style="color:{color};font-size:9.5px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.08em;margin-bottom:4px;">{label}</div>'
        f'<div style="color:#EFF6FF;font-size:24px;font-weight:800;line-height:1.1;">{value}</div>'
        f'<div style="color:#64748B;font-size:10.5px;margin-top:4px;">{note}</div>'
        f'{action_html}'
        f'</div>'
    )


def _action_card(icon: str, headline: str, body: str, action: str,
                 accent: str = "#0891B2") -> str:
    return (
        f'<div style="background:rgba(255,255,255,0.04);border-left:4px solid {accent};'
        f'border-radius:8px;padding:14px 18px;margin-bottom:10px;">'
        f'<div style="display:flex;align-items:flex-start;gap:10px;">'
        f'<span style="font-size:22px;margin-top:2px;">{icon}</span>'
        f'<div style="flex:1;">'
        f'<div style="color:#EFF6FF;font-weight:700;font-size:13.5px;margin-bottom:4px;">{headline}</div>'
        f'<div style="color:#94A3B8;font-size:12px;line-height:1.6;margin-bottom:8px;">{body}</div>'
        f'<div style="background:rgba(0,0,0,0.25);border-radius:4px;padding:6px 10px;'
        f'font-size:11px;color:{accent};font-weight:600;">→ {action}</div>'
        f'</div></div></div>'
    )


# ── Data loaders (cached inside this module) ──────────────────────────────────

@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_group_intel() -> dict:
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM group_intelligence ORDER BY benchmark_date DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception:
        return {}


@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_monthly_occ() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        df = pd.read_sql_query(
            """
            SELECT substr(as_of_date,1,7) AS month,
                   avg(occ_pct) AS avg_occ,
                   avg(adr)     AS avg_adr,
                   avg(revpar)  AS avg_revpar
            FROM kpi_daily_summary
            WHERE as_of_date >= date('now','-18 months')
            GROUP BY month
            ORDER BY month
            """,
            conn,
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_NATIONAL)
def _load_ust_segments() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        df = pd.read_sql_query("SELECT * FROM us_travel_group_segments", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_NATIONAL)
def _load_ust_biz() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        df = pd.read_sql_query("SELECT * FROM us_travel_business_travel", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_NATIONAL)
def _load_traveler_types() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        df = pd.read_sql_query(
            "SELECT * FROM us_travel_traveler_types ORDER BY revenue_contribution DESC",
            conn,
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_group_insights() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        df = pd.read_sql_query(
            """
            SELECT audience, category, headline, body, priority
            FROM insights_daily
            WHERE category LIKE '%group%'
               OR category LIKE '%traveler%'
               OR category = 'group_event_synergy'
               OR category = 'traveler_mix_revenue_gap'
               OR category = 'supply_pipeline_group_risk'
               OR category = 'competitive_set_group_gap'
               OR category = 'channel_group_attribution'
            ORDER BY priority ASC
            LIMIT 12
            """,
            conn,
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_social_summary() -> dict:
    """Latest IG + FB social metrics for group audience reach context."""
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        ig = conn.execute(
            "SELECT followers, reach, impressions FROM later_ig_profile_growth "
            "ORDER BY data_date DESC LIMIT 1"
        ).fetchone()
        fb = conn.execute(
            "SELECT page_followers, reach FROM later_fb_profile_growth "
            "ORDER BY data_date DESC LIMIT 1"
        ).fetchone()
        # IG recent engagement rate
        eng = conn.execute(
            "SELECT avg(engagement_rate) as avg_eng FROM later_ig_posts "
            "WHERE posted_at >= date('now','-30 days')"
        ).fetchone()
        conn.close()
        return {
            "ig_followers":  int(ig["followers"]  or 0) if ig and ig["followers"]  else 0,
            "fb_followers":  int(fb["page_followers"] or 0) if fb and fb["page_followers"] else 0,
            "ig_reach":      int(ig["reach"]       or 0) if ig and ig["reach"]       else 0,
            "ig_eng":        float(eng["avg_eng"]   or 0) if eng and eng["avg_eng"]   else 0.0,
        }
    except Exception:
        return {"ig_followers": 0, "fb_followers": 0, "ig_reach": 0, "ig_eng": 0.0}


@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_costar_chain() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        df = pd.read_sql_query(
            """
            SELECT chain_scale, supply_rooms, occupancy_pct, adr_usd, revpar_usd,
                   room_revenue_usd, market_share_revpar_pct
            FROM costar_chain_scale_breakdown
            ORDER BY revpar_usd DESC
            """,
            conn,
        )
        conn.close()
        return df
    except Exception as exc:
        import logging; logging.getLogger("vdp_dashboard").debug("_load_costar_chain failed: %s", exc)
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_competitive_set() -> pd.DataFrame:
    """Load costar_competitive_set: ADR, Occ, MPI, ARI, RGI per property."""
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='costar_competitive_set'")
        if not cur.fetchone():
            conn.close()
            return pd.DataFrame()
        df = pd.read_sql_query(
            """
            SELECT property_name, chain_scale, rooms, occupancy_pct, adr_usd,
                   revpar_usd, mpi, ari, rgi, submarket
            FROM costar_competitive_set
            ORDER BY adr_usd DESC
            """,
            conn,
        )
        conn.close()
        return df
    except Exception as exc:
        import logging; logging.getLogger("vdp_dashboard").debug("_load_competitive_set failed: %s", exc)
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_supply_pipeline() -> pd.DataFrame:
    """Load costar_supply_pipeline: upcoming hotel openings."""
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='costar_supply_pipeline'")
        if not cur.fetchone():
            conn.close()
            return pd.DataFrame()
        df = pd.read_sql_query(
            """
            SELECT property_name, city, rooms, chain_scale, status,
                   projected_open_date, brand, notes
            FROM costar_supply_pipeline
            ORDER BY projected_open_date ASC
            """,
            conn,
        )
        conn.close()
        return df
    except Exception as exc:
        import logging; logging.getLogger("vdp_dashboard").debug("_load_supply_pipeline failed: %s", exc)
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_attribution_groups() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load website + media group attribution data."""
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        web_df = pd.DataFrame()
        med_df = pd.DataFrame()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='datafy_attribution_website_groups'")
        if cur.fetchone():
            web_df = pd.read_sql_query("SELECT * FROM datafy_attribution_website_groups ORDER BY report_period_start", conn)
        cur2 = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='datafy_attribution_media_groups'")
        if cur2.fetchone():
            med_df = pd.read_sql_query("SELECT * FROM datafy_attribution_media_groups ORDER BY report_period_start", conn)
        conn.close()
        return web_df, med_df
    except Exception as exc:
        import logging; logging.getLogger("vdp_dashboard").debug("_load_attribution_groups failed: %s", exc)
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_GROUP)
def _load_costar_monthly() -> pd.DataFrame:
    """Load costar_monthly_performance for occupancy trend overlay."""
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='costar_monthly_performance'")
        if not cur.fetchone():
            conn.close()
            return pd.DataFrame()
        df = pd.read_sql_query(
            """
            SELECT as_of_date, occupancy_pct, adr_usd, revpar_usd
            FROM costar_monthly_performance
            WHERE as_of_date >= date('now','-24 months')
            ORDER BY as_of_date
            """,
            conn,
        )
        conn.close()
        return df
    except Exception as exc:
        import logging; logging.getLogger("vdp_dashboard").debug("_load_costar_monthly failed: %s", exc)
        return pd.DataFrame()


# ── Chart builders ────────────────────────────────────────────────────────────

def _chart_tbid_bar(g: dict) -> go.Figure:
    """Side-by-side TBID bar: current range vs group contribution vs +5pp uplift."""
    tbid_low   = g.get("estimated_group_tbid_rev_low",  3_603_940) / 1e6
    tbid_high  = g.get("estimated_group_tbid_rev_high", 4_613_043) / 1e6
    uplift     = g.get("tbid_uplift_per_5pp_shift",      720_788)  / 1e6
    tbid_mid   = (tbid_low + tbid_high) / 2

    categories = ["Group TBID\n(Low Est.)", "Group TBID\n(High Est.)", "+5pp Mix\nUplift"]
    values     = [tbid_low, tbid_high, uplift]
    colors     = ["#0891B2", "#10B981", "#F5B940"]
    text       = [f"${v:.2f}M" for v in values]

    fig = _dark_fig(height=300)
    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        text=text,
        textposition="outside",
        textfont=dict(size=13, color="#EFF6FF"),
        hovertemplate="<b>%{x}</b><br>$%{y:.2f}M annual TBID<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="TBID Revenue Opportunity — Group Business", font=dict(size=13, color="#EFF6FF")),
        yaxis_title="$M / Year",
        yaxis_tickprefix="$",
        yaxis_ticksuffix="M",
        showlegend=False,
    )
    return fig


def _chart_occ_heatmap(df_monthly: pd.DataFrame) -> go.Figure:
    """Monthly occupancy with group-safe/risk color bands."""
    if df_monthly.empty:
        return _dark_fig()

    months = df_monthly["month"].tolist()
    occs   = df_monthly["avg_occ"].tolist()

    colors = []
    for occ in occs:
        if occ >= OCC_GROUP_RISK_MIN:
            colors.append("#EF4444")   # red — group displaces transient
        elif occ >= OCC_GROUP_WARN_MIN:
            colors.append("#F59E0B")   # amber — monitor
        else:
            colors.append("#10B981")   # green — group blocks welcome

    fig = _dark_fig(height=300)
    fig.add_trace(go.Bar(
        x=months,
        y=occs,
        marker_color=colors,
        text=[f"{v:.0f}%" for v in occs],
        textposition="outside",
        textfont=dict(size=10.5, color="#EFF6FF"),
        hovertemplate="<b>%{x}</b><br>Avg Occ: %{y:.1f}%<extra></extra>",
    ))
    # Reference lines
    for level, color, label in [
        (OCC_GROUP_RISK_MIN, "#EF4444", "80% — group risk"),
        (OCC_GROUP_WARN_MIN, "#F59E0B", "70% — monitor"),
        (OCC_GROUP_SAFE_MAX, "#10B981", "65% — group safe"),
    ]:
        fig.add_hline(
            y=level, line_dash="dot", line_color=color, line_width=1.5,
            annotation_text=label,
            annotation_font_size=9,
            annotation_font_color=color,
            annotation_position="right",
        )
    fig.update_layout(
        title=dict(
            text="Monthly Occupancy — Group Safety Calendar  🟢 Safe  🟡 Monitor  🔴 Displace",
            font=dict(size=12.5, color="#EFF6FF"),
        ),
        yaxis_title="Avg Occupancy %",
        yaxis_range=[0, 100],
        showlegend=False,
    )
    return fig


def _chart_segment_donut(df_segs: pd.DataFrame) -> go.Figure:
    """National $319B group travel segment donut."""
    segs = df_segs[df_segs["segment"] != "total_group"].copy()
    if segs.empty:
        return _dark_fig()

    segs["label"] = segs["segment"].str.replace("_", " ").str.title()
    segs = segs.sort_values("spend_billion_usd", ascending=False)

    fig = _dark_fig(height=340)
    fig.add_trace(go.Pie(
        labels=segs["label"].tolist(),
        values=segs["spend_billion_usd"].tolist(),
        hole=0.52,
        marker=dict(colors=_COLORWAY[:len(segs)],
                    line=dict(color="rgba(0,0,0,0.4)", width=2)),
        texttemplate="<b>%{label}</b><br>$%{value:.0f}B",
        textposition="outside",
        hovertemplate="<b>%{label}</b><br>$%{value:.0f}B · %{percent}<extra></extra>",
        pull=[0.04] * len(segs),
    ))
    fig.update_layout(
        title=dict(text="U.S. Group Travel — $319B National Segments", font=dict(size=13, color="#EFF6FF")),
        annotations=[dict(
            text="$319B<br><span style='font-size:10px'>National Total</span>",
            x=0.5, y=0.5, font_size=15, showarrow=False,
            font=dict(color="#EFF6FF"),
        )],
        showlegend=True,
        legend=dict(orientation="v", x=1.0, y=0.5),
    )
    return fig


def _chart_revenue_funnel(g: dict) -> go.Figure:
    """Revenue funnel: $319B national → South OC market → Dana Point group → TBID."""
    national_group  = 319.0   # $B
    # South OC ~1.15B room revenue; group share midpoint
    annual_rev      = g.get("estimated_annual_room_rev", 1_153_261_000) / 1e9
    group_rev_mid   = annual_rev * ((GROUP_SHARE_LOW + GROUP_SHARE_HIGH) / 2)
    tbid_est        = group_rev_mid * TBID_RATE

    labels = [
        "U.S. Group Travel ($319B)",
        f"South OC Room Revenue (${annual_rev:.1f}B)",
        f"Dana Point Est. Group Rev (${group_rev_mid*1e3:.0f}M)",
        f"Group TBID Contribution (${tbid_est*1e3:.1f}M)",
    ]
    values = [national_group, annual_rev, group_rev_mid, tbid_est]

    fig = _dark_fig(height=320)
    fig.add_trace(go.Funnel(
        y=labels,
        x=values,
        textposition="inside",
        texttemplate="<b>%{x:.2f}</b>",
        marker=dict(color=["#0891B2", "#10B981", "#F5B940", "#A78BFA"],
                    line=dict(width=2, color="rgba(0,0,0,0.3)")),
        connector=dict(line=dict(color="#334155", dash="dot", width=1)),
        hovertemplate="<b>%{y}</b><extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Group Revenue Funnel — National to Dana Point TBID", font=dict(size=13, color="#EFF6FF")),
        funnelmode="stack",
    )
    return fig


def _chart_traveler_radar(df_types: pd.DataFrame) -> go.Figure:
    """Radar/spider chart comparing 4 key traveler types on 5 dimensions."""
    if df_types.empty:
        return _dark_fig()

    # Score map (normalize to 0–10)
    rev_score = {"highest": 10, "high": 7.5, "medium": 5, "low": 2.5}
    sea_score = {"year_round": 10, "shoulder": 6, "peak": 4, "winter": 3}

    TARGET_TYPES = ["business", "smerf", "family", "leisure"]
    subset = df_types[df_types["traveler_type"].isin(TARGET_TYPES)].copy()
    if subset.empty:
        subset = df_types.head(4)

    dims = ["Revenue Tier", "LOS Score", "Booking Window", "Seasonal Flex", "Group Fit"]

    def _scores(row) -> list[float]:
        rev  = rev_score.get(str(row.get("revenue_contribution", "medium")).lower(), 5)
        los  = min(float(row.get("typical_los_nights_high") or 3) / 7 * 10, 10)
        bkw  = min(float(row.get("booking_window_weeks_high") or 4) / 48 * 10, 10)
        sea  = sea_score.get(str(row.get("seasonal_pattern", "peak")).lower(), 5)
        grp_fit = 8 if row.get("traveler_type") in ("smerf", "business") else 5
        return [rev, los, bkw, sea, grp_fit]

    colors = ["#0891B2", "#F5B940", "#10B981", "#A78BFA"]
    fig = _dark_fig(height=380)

    for i, (_, row) in enumerate(subset.iterrows()):
        scores = _scores(row)
        scores.append(scores[0])  # close polygon
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=dims + [dims[0]],
            fill="toself",
            fillcolor=colors[i % len(colors)].replace(")", ",0.15)").replace("rgb", "rgba"),
            line=dict(color=colors[i % len(colors)], width=2),
            name=str(row.get("traveler_type", "")).title(),
            hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="Traveler Type Profile — 5-Dimension Comparison", font=dict(size=13, color="#EFF6FF")),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 10], color=_LABEL_CLR,
                            gridcolor=_GRID_CLR, tickfont=dict(size=9)),
            angularaxis=dict(color=_LABEL_CLR, gridcolor=_GRID_CLR,
                             tickfont=dict(size=11.5)),
        ),
        showlegend=True,
    )
    return fig


def _chart_competitive_scatter(df: pd.DataFrame) -> go.Figure:
    """ADR vs Occupancy scatter per property — coloured by chain scale."""
    if df.empty:
        return _dark_fig()

    scale_color = {
        "Luxury":       "#F5B940",
        "Upper Upscale": "#0891B2",
        "Upscale":      "#10B981",
        "Upper Midscale": "#A78BFA",
        "Midscale":     "#FB923C",
        "Economy":      "#6EE7B7",
    }
    colors = [scale_color.get(str(s), "#64748B") for s in df["chain_scale"]]

    fig = _dark_fig(height=360)
    for scale in df["chain_scale"].unique():
        sub = df[df["chain_scale"] == scale]
        fig.add_trace(go.Scatter(
            x=sub["occupancy_pct"].tolist(),
            y=sub["adr_usd"].tolist(),
            mode="markers+text",
            marker=dict(color=scale_color.get(str(scale), "#64748B"), size=14,
                        line=dict(width=1, color="rgba(255,255,255,0.3)")),
            text=sub["property_name"].str[:18].tolist(),
            textposition="top center",
            textfont=dict(size=9, color="#CBD5E1"),
            name=str(scale),
            hovertemplate=(
                "<b>%{text}</b><br>Occ: %{x:.1f}%<br>ADR: $%{y:.0f}"
                "<br>RevPAR: $%{customdata:.0f}<extra></extra>"
            ),
            customdata=sub["revpar_usd"].tolist(),
        ))
    fig.update_layout(
        title=dict(
            text="Competitive Set — ADR vs Occupancy (bubble = RevPAR)",
            font=dict(size=12.5, color="#EFF6FF"),
        ),
        xaxis_title="Occupancy %",
        yaxis_title="ADR ($)",
        yaxis_tickprefix="$",
        showlegend=True,
    )
    return fig


def _chart_tbid_chain_waterfall(df_chain: pd.DataFrame, g: dict) -> go.Figure:
    """TBID contribution waterfall by chain scale."""
    if df_chain.empty:
        return _dark_fig()

    _GROUP_SCALES = ["Luxury", "Upper Upscale", "Upscale"]
    subset = df_chain[df_chain["chain_scale"].isin(_GROUP_SCALES)].copy()
    if subset.empty:
        subset = df_chain.copy()

    group_share = (GROUP_SHARE_LOW + GROUP_SHARE_HIGH) / 2
    subset = subset.copy()
    subset["group_rev"] = (
        subset["supply_rooms"].fillna(0) *
        subset["adr_usd"].fillna(0) *
        subset["occupancy_pct"].fillna(0) / 100 *
        group_share * 365
    )
    subset["tbid_contribution"] = subset["group_rev"] * TBID_RATE

    colors = ["#F5B940", "#0891B2", "#10B981", "#A78BFA", "#FB923C"]

    fig = _dark_fig(height=300)
    fig.add_trace(go.Bar(
        x=subset["chain_scale"].tolist(),
        y=(subset["tbid_contribution"] / 1e6).tolist(),
        marker_color=colors[:len(subset)],
        text=[f"${v/1e6:.2f}M" for v in subset["tbid_contribution"]],
        textposition="outside",
        textfont=dict(size=12.5, color="#EFF6FF"),
        hovertemplate="<b>%{x}</b><br>Est. Group TBID: $%{y:.2f}M<extra></extra>",
    ))
    tbid_target = 4.1  # $4.1M midpoint target
    fig.add_hline(
        y=tbid_target, line_dash="dash", line_color="#F5B940", line_width=1.5,
        annotation_text=f"${tbid_target:.1f}M TBID midpoint target",
        annotation_font_size=9.5, annotation_font_color="#F5B940",
        annotation_position="right",
    )
    fig.update_layout(
        title=dict(text="TBID Waterfall by Chain Scale — rooms × ADR × 28% group share × 1.25%",
                   font=dict(size=12, color="#EFF6FF")),
        yaxis_title="Est. TBID $M/yr",
        yaxis_tickprefix="$",
        yaxis_ticksuffix="M",
        showlegend=False,
    )
    return fig


def _chart_supply_pipeline(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar timeline of supply pipeline by chain scale."""
    if df.empty:
        return _dark_fig()

    scale_color = {
        "Luxury":       "#F5B940",
        "Upper Upscale": "#0891B2",
        "Upscale":      "#10B981",
        "Upper Midscale": "#A78BFA",
        "Midscale":     "#FB923C",
        "Economy":      "#6EE7B7",
    }
    colors = [scale_color.get(str(s), "#64748B") for s in df["chain_scale"]]
    labels = [f"{r['property_name']} ({r.get('projected_open_date','?')})"
              for _, r in df.iterrows()]

    fig = _dark_fig(height=max(260, len(df) * 55))
    fig.add_trace(go.Bar(
        y=labels,
        x=df["rooms"].tolist(),
        orientation="h",
        marker_color=colors,
        text=[f"{int(v):,} rooms" for v in df["rooms"]],
        textposition="inside",
        textfont=dict(size=11, color="#EFF6FF"),
        hovertemplate="<b>%{y}</b><br>Rooms: %{x:,}<br>Scale: %{customdata}<extra></extra>",
        customdata=df["chain_scale"].tolist(),
    ))
    fig.update_layout(
        title=dict(text="Supply Pipeline — Upcoming Dana Point Hotel Openings",
                   font=dict(size=12.5, color="#EFF6FF")),
        xaxis_title="New Rooms",
        showlegend=False,
        margin=dict(l=250, r=20, t=48, b=14),
    )
    return fig


def _chart_attribution_channel(web_df: pd.DataFrame, med_df: pd.DataFrame) -> go.Figure:
    """Bar chart: website vs media attributed group trips and impact."""
    if web_df.empty and med_df.empty:
        return _dark_fig()

    TBID_TARGET_MID = 4_100_000  # $4.1M

    channels, trips_vals, impact_vals = [], [], []
    if not web_df.empty:
        channels.append("Website Attribution")
        trips_vals.append(float(web_df["trips"].sum()))
        impact_vals.append(float(web_df["est_impact_usd"].sum()))
    if not med_df.empty:
        channels.append("Media Attribution")
        trips_vals.append(float(med_df["trips"].sum()))
        impact_vals.append(float(med_df["est_impact_usd"].sum()))

    fig = _dark_fig(height=320)
    fig.add_trace(go.Bar(
        name="Attributed Trips",
        x=channels,
        y=trips_vals,
        marker_color="#0891B2",
        yaxis="y",
        text=[f"{int(v):,}" for v in trips_vals],
        textposition="outside",
        textfont=dict(size=12, color="#EFF6FF"),
        hovertemplate="<b>%{x}</b><br>Trips: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Est. Impact ($K)",
        x=channels,
        y=[v / 1000 for v in impact_vals],
        marker_color="#10B981",
        yaxis="y2",
        text=[f"${v/1000:.0f}K" for v in impact_vals],
        textposition="outside",
        textfont=dict(size=12, color="#EFF6FF"),
        hovertemplate="<b>%{x}</b><br>Impact: $%{y:.0f}K<extra></extra>",
    ))
    fig.add_hline(
        y=TBID_TARGET_MID / 1000, line_dash="dash",
        line_color="#F5B940", line_width=1.5,
        annotation_text="$4.1M TBID midpoint target",
        annotation_font_size=9.5, annotation_font_color="#F5B940",
        annotation_position="right",
        yref="y2",
    )
    fig.update_layout(
        title=dict(text="Group Attribution — Website vs Media Channels",
                   font=dict(size=12.5, color="#EFF6FF")),
        barmode="group",
        yaxis=dict(title="Attributed Trips", color=_LABEL_CLR),
        yaxis2=dict(title="Est. Impact ($K)", overlaying="y", side="right",
                    color=_LABEL_CLR, tickprefix="$", ticksuffix="K"),
        showlegend=True,
    )
    return fig


def _chart_costar_occ_overlay(df_costar: pd.DataFrame, web_df: pd.DataFrame) -> go.Figure:
    """Dual-axis line: CoStar monthly occ vs Datafy group attribution quarterly."""
    fig = _dark_fig(height=340)

    if not df_costar.empty and "as_of_date" in df_costar.columns:
        fig.add_trace(go.Scatter(
            x=df_costar["as_of_date"].tolist(),
            y=df_costar["occupancy_pct"].tolist(),
            name="CoStar Mkt Occ %",
            mode="lines+markers",
            line=dict(color="#0891B2", width=2.5),
            marker=dict(size=6),
            yaxis="y",
            hovertemplate="<b>%{x}</b><br>CoStar Occ: %{y:.1f}%<extra></extra>",
        ))

    if not web_df.empty and "est_impact_usd" in web_df.columns:
        q_totals = web_df.groupby("report_period_start")["est_impact_usd"].sum().reset_index()
        fig.add_trace(go.Scatter(
            x=q_totals["report_period_start"].tolist(),
            y=(q_totals["est_impact_usd"] / 1000).tolist(),
            name="Group Impact ($K)",
            mode="lines+markers",
            line=dict(color="#10B981", width=2.5, dash="dot"),
            marker=dict(size=8, symbol="diamond"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Impact: $%{y:.0f}K<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="CoStar Monthly Occ vs Datafy Group Attribution",
                   font=dict(size=12.5, color="#EFF6FF")),
        yaxis=dict(title="Occupancy %", color=_LABEL_CLR),
        yaxis2=dict(title="Group Impact ($K)", overlaying="y", side="right",
                    color=_LABEL_CLR, tickprefix="$", ticksuffix="K"),
        showlegend=True,
    )
    return fig


def _render_shoulder_alignment(df_types: pd.DataFrame, comp: pd.DataFrame) -> None:
    """Heatmap table: traveler types × quarters — Safe/Caution/Risk by occ threshold."""
    if df_types.empty or comp.empty:
        st.info("Traveler type or compression data not loaded.")
        return

    quarters = ["Q1", "Q2", "Q3", "Q4"]
    # Map compression days to occ risk level per quarter
    q_risk: dict[str, str] = {}
    for _, row in comp.iterrows():
        q = str(row.get("quarter", "")).split("-")[-1] if "-" in str(row.get("quarter", "")) else str(row.get("quarter", ""))
        days_high = int(row.get("days_above_80_occ") or 0)
        if days_high >= 20:
            q_risk[q] = "Risk"
        elif days_high >= 8:
            q_risk[q] = "Caution"
        else:
            q_risk[q] = "Safe"
    for q in quarters:
        q_risk.setdefault(q, "Safe")

    # Select traveler types to show
    _SHOW_TYPES = ["business", "smerf", "family", "leisure", "solo", "bleisure"]
    subset = df_types[df_types["traveler_type"].isin(_SHOW_TYPES)].copy()
    if subset.empty:
        subset = df_types.head(5)

    # Build seasonal affinity: which quarters does each type prefer?
    _SEASONAL_MAP = {
        "peak":       {"Q3": "Caution", "Q2": "Caution", "Q1": "Safe", "Q4": "Safe"},
        "year_round": {"Q1": "Safe",    "Q2": "Safe",    "Q3": "Safe", "Q4": "Safe"},
        "shoulder":   {"Q1": "Safe",    "Q4": "Safe",    "Q2": "Caution", "Q3": "Risk"},
        "winter":     {"Q1": "Safe",    "Q4": "Caution", "Q2": "Risk",  "Q3": "Risk"},
    }
    _CELL_COLOR = {"Safe": "#14532D", "Caution": "#78350F", "Risk": "#7F1D1D"}
    _TEXT_COLOR = {"Safe": "#4ADE80", "Caution": "#FCD34D", "Risk": "#FCA5A5"}

    rows_html = ""
    for _, trow in subset.iterrows():
        ttype = str(trow.get("traveler_type", "")).title()
        seasonal = str(trow.get("seasonal_pattern", "year_round")).lower()
        affinity = _SEASONAL_MAP.get(seasonal, _SEASONAL_MAP["year_round"])
        cells = ""
        for q in quarters:
            type_pref = affinity.get(q, "Safe")
            mkt_risk  = q_risk.get(q, "Safe")
            # Effective risk: max(market risk, type mismatch)
            _RANK = {"Safe": 0, "Caution": 1, "Risk": 2}
            effective = "Safe" if _RANK[mkt_risk] == 0 and _RANK[type_pref] == 0 else \
                        "Risk" if _RANK[mkt_risk] == 2 or _RANK[type_pref] == 2 else "Caution"
            bg = _CELL_COLOR[effective]
            fg = _TEXT_COLOR[effective]
            cells += (
                f'<td style="background:{bg};color:{fg};font-weight:700;font-size:11px;'
                f'text-align:center;padding:8px 4px;border:1px solid rgba(255,255,255,0.06);">'
                f'{effective}</td>'
            )
        rows_html += (
            f'<tr><td style="color:#EFF6FF;font-size:11.5px;padding:8px 12px;'
            f'border:1px solid rgba(255,255,255,0.06);font-weight:600;">{ttype}</td>'
            f'{cells}</tr>'
        )

    header_cells_parts = []
    for q in quarters:
        q_r = q_risk.get(q, "Safe")
        q_c = _TEXT_COLOR[q_r]
        header_cells_parts.append(
            f'<th style="color:#93C5FD;font-size:10.5px;text-align:center;padding:8px;'
            f'border:1px solid rgba(255,255,255,0.06);">{q}<br>'
            f'<span style="color:{q_c};font-size:9px;">({q_r})</span></th>'
        )
    header_cells = "".join(header_cells_parts)

    st.markdown(f"""
    <div style="margin-top:14px;margin-bottom:6px;color:#93C5FD;font-size:10px;
                font-weight:700;text-transform:uppercase;letter-spacing:.08em;">
      SHOULDER SEASON ALIGNMENT MATRIX — Traveler Types × Quarters
    </div>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;background:rgba(0,0,0,0.2);
                  border-radius:8px;overflow:hidden;">
      <thead>
        <tr>
          <th style="color:#93C5FD;font-size:10.5px;text-align:left;padding:8px 12px;
                     border:1px solid rgba(255,255,255,0.06);">Traveler Type</th>
          {header_cells}
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    </div>
    <div style="margin-top:8px;font-size:10px;color:#64748B;">
      🟢 Safe = low displacement risk + type alignment · 🟡 Caution = monitor demand ·
      🔴 Risk = high occ displacement or seasonal mismatch. Market occ threshold: 80%+.
    </div>
    """, unsafe_allow_html=True)


# ── Sub-tab renderers ─────────────────────────────────────────────────────────

def _render_group_strategy(g: dict, df_monthly: pd.DataFrame,
                           df_chain: pd.DataFrame, insights: pd.DataFrame,
                           social: dict,
                           df_comp: Optional[pd.DataFrame] = None,
                           df_pipeline: Optional[pd.DataFrame] = None,
                           web_groups: Optional[pd.DataFrame] = None,
                           med_groups: Optional[pd.DataFrame] = None) -> None:
    # ── Executive Brief ───────────────────────────────────────────────────────
    tbid_low   = g.get("estimated_group_tbid_rev_low",  3_603_940)
    tbid_high  = g.get("estimated_group_tbid_rev_high", 4_613_043)
    uplift     = g.get("tbid_uplift_per_5pp_shift",      720_788)
    compression = int(g.get("compression_days_annual", 0) or 0)
    market_adr  = float(g.get("market_blended_adr", 288.50) or 288.50)
    group_adr   = float(g.get("estimated_group_adr", 236.57) or 236.57)
    adr_gap     = market_adr - group_adr

    if compression >= 30:
        risk_label, risk_color, risk_action = "HIGH", "#EF4444", "Target Q1/Q4 shoulder exclusively"
    elif compression >= 10:
        risk_label, risk_color, risk_action = "MODERATE", "#F59E0B", "Focus shoulder + midweek group blocks"
    else:
        risk_label, risk_color, risk_action = "LOW", "#22C55E", "Group blocks viable year-round"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(8,145,178,0.12),rgba(16,185,129,0.06));
                border:1px solid rgba(8,145,178,0.3);border-radius:12px;padding:20px 24px;
                margin-bottom:18px;">
      <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:.1em;margin-bottom:10px;">EXECUTIVE BRIEF — GROUP BUSINESS CASE</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:14px;">
        <div style="text-align:center;">
          <div style="color:#EFF6FF;font-size:26px;font-weight:800;">${tbid_low/1e6:.1f}M–${tbid_high/1e6:.1f}M</div>
          <div style="color:#93C5FD;font-size:10.5px;margin-top:2px;">Est. Annual Group TBID</div>
          <div style="color:#64748B;font-size:9.5px;">25–32% demand share benchmark</div>
        </div>
        <div style="text-align:center;">
          <div style="color:{risk_color};font-size:26px;font-weight:800;">{risk_label}</div>
          <div style="color:#93C5FD;font-size:10.5px;margin-top:2px;">Displacement Risk</div>
          <div style="color:#64748B;font-size:9.5px;">{compression} compression days/yr</div>
        </div>
        <div style="text-align:center;">
          <div style="color:#F5B940;font-size:26px;font-weight:800;">+${uplift/1000:.0f}K/yr</div>
          <div style="color:#93C5FD;font-size:10.5px;margin-top:2px;">TBID Uplift per +5pp</div>
          <div style="color:#64748B;font-size:9.5px;">each 5pp shift in group mix</div>
        </div>
      </div>
      <div style="background:rgba(0,0,0,0.2);border-radius:6px;padding:10px 14px;">
        <div style="color:#FCD34D;font-size:10px;font-weight:700;text-transform:uppercase;
                    letter-spacing:.05em;margin-bottom:4px;">TOP RECOMMENDATION</div>
        <div style="color:#CBD5E1;font-size:12px;line-height:1.6;">
          {risk_action}. Group ADR is estimated at <strong>${group_adr:.0f}</strong> vs.
          <strong>${market_adr:.0f}</strong> blended market ADR — a
          <strong>${adr_gap:.0f}/room/night gap</strong>. Shoulder-season group bookings
          maximize TBID without displacing peak transient revenue.
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI row ───────────────────────────────────────────────────────────────
    total_rooms  = int(g.get("total_market_rooms", 5120) or 5120)
    group_rooms  = int(g.get("group_primary_rooms", 3098) or 3098)
    group_pct    = float(g.get("group_primary_pct", 0.605) or 0.605)

    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val, note, color, action in [
        (c1, "Group-Capable Rooms", f"{group_rooms:,}", f"{group_pct*100:.0f}% of {total_rooms:,} market rooms",
         "#0891B2", "Upper Upscale + Upscale carry highest group amenity density"),
        (c2, "Est. Annual Group TBID", f"${tbid_low/1e6:.1f}M–${tbid_high/1e6:.1f}M",
         "industry benchmark range", "#10B981",
         "Each 1pp growth in group demand mix = +$144K TBID/yr"),
        (c3, "TBID per +5pp Shift", f"+${uplift/1000:.0f}K/yr",
         "incremental on group mix growth", "#F5B940",
         "Set 5pp group mix growth as a 12-month TBID goal"),
        (c4, "Displacement Risk", f"{risk_label}", f"{compression} compression days/yr",
         risk_color, risk_action),
    ]:
        with col:
            st.markdown(_metric_box(lbl, val, note, color, action), unsafe_allow_html=True)

    st.markdown("<div style='margin:18px 0 8px;'></div>", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(_chart_tbid_bar(g), use_container_width=True, key="gt_tbid_bar")
    with col_b:
        st.plotly_chart(_chart_occ_heatmap(df_monthly), use_container_width=True, key="gt_occ_heat")

    # ── Chain scale context ───────────────────────────────────────────────────
    if not df_chain.empty:
        _GROUP_SCALES = {"Upper Upscale", "Upscale"}
        chain_s = df_chain.drop_duplicates("chain_scale").sort_values("revpar_usd", ascending=False)
        colors  = ["#0891B2" if str(r.get("chain_scale", "")) in _GROUP_SCALES else "#475569"
                   for _, r in chain_s.iterrows()]
        fig_ch = _dark_fig(height=260)
        fig_ch.add_trace(go.Bar(
            x=chain_s["chain_scale"].tolist(),
            y=chain_s["supply_rooms"].tolist(),
            marker_color=colors,
            text=[f"{int(v):,}" for v in chain_s["supply_rooms"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Rooms: %{y:,}<br>RevPAR: $%{customdata:.0f}<extra></extra>",
            customdata=chain_s["revpar_usd"].tolist(),
        ))
        fig_ch.update_layout(
            title=dict(text="Dana Point Supply by Chain Scale — Blue = Group-Primary", font=dict(size=12.5, color="#EFF6FF")),
            showlegend=False,
            yaxis_title="Supply Rooms",
        )
        st.plotly_chart(fig_ch, use_container_width=True, key="gt_chain_bar")

    # ── Social reach context ──────────────────────────────────────────────────
    ig_f = social.get("ig_followers", 0)
    fb_f = social.get("fb_followers", 0)
    ig_r = social.get("ig_reach", 0)
    ig_e = social.get("ig_eng", 0.0)
    if ig_f or fb_f:
        st.markdown("""
        <div style="margin-top:6px;margin-bottom:4px;color:#93C5FD;font-size:10px;
                    font-weight:700;text-transform:uppercase;letter-spacing:.06em;">
        SOCIAL AUDIENCE — GROUP OUTREACH CHANNEL
        </div>
        """, unsafe_allow_html=True)
        cols = st.columns(4)
        for col, lbl, val, note, color in [
            (cols[0], "Instagram Followers", f"{ig_f:,}" if ig_f else "–", "VDP @visitdanapoint", "#E1306C"),
            (cols[1], "Facebook Followers",  f"{fb_f:,}" if fb_f else "–", "VDP Facebook Page",   "#1877F2"),
            (cols[2], "IG Monthly Reach",    f"{ig_r:,}" if ig_r else "–", "unique accounts reached", "#A78BFA"),
            (cols[3], "IG Engagement Rate",  f"{ig_e:.1f}%" if ig_e else "–", "30-day avg", "#10B981"),
        ]:
            with col:
                st.markdown(_metric_box(lbl, val, note, color), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

    # ── A. Competitive Set Positioning ───────────────────────────────────────
    if df_comp is not None and not df_comp.empty:
        st.markdown("""
        <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                    letter-spacing:.06em;margin-bottom:10px;">
        A. COMPETITIVE SET POSITIONING — How Dana Point Properties Index Against the Set
        </div>
        """, unsafe_allow_html=True)

        col_scatter, col_index = st.columns([2, 1])
        with col_scatter:
            st.plotly_chart(_chart_competitive_scatter(df_comp), use_container_width=True,
                            key="gt_comp_scatter")
        with col_index:
            # Show MPI / ARI / RGI summary cards
            avg_mpi = df_comp["mpi"].mean() if "mpi" in df_comp.columns else None
            avg_ari = df_comp["ari"].mean() if "ari" in df_comp.columns else None
            avg_rgi = df_comp["rgi"].mean() if "rgi" in df_comp.columns else None
            for lbl, val, note, color in [
                ("Avg MPI", f"{avg_mpi:.1f}" if avg_mpi else "–",
                 "Market Penetration Index (100 = fair share)", "#0891B2"),
                ("Avg ARI", f"{avg_ari:.1f}" if avg_ari else "–",
                 "ADR Index (100 = fair share)", "#10B981"),
                ("Avg RGI", f"{avg_rgi:.1f}" if avg_rgi else "–",
                 "RevPAR Growth Index (100 = fair share)", "#F5B940"),
            ]:
                st.markdown(_metric_box(lbl, val, note, color), unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    # ── B. TBID Waterfall by Chain Scale ─────────────────────────────────────
    st.markdown("""
    <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                letter-spacing:.06em;margin:14px 0 10px;">
    B. TBID WATERFALL BY CHAIN SCALE — rooms × ADR × 28% group share × 1.25% TBID rate
    </div>
    """, unsafe_allow_html=True)
    if not df_chain.empty:
        col_wf, col_meta = st.columns([3, 1])
        with col_wf:
            st.plotly_chart(_chart_tbid_chain_waterfall(df_chain, g),
                            use_container_width=True, key="gt_tbid_waterfall")
        with col_meta:
            tbid_target = 4_100_000
            tbid_actual = g.get("estimated_group_tbid_rev_low", 3_603_940)
            gap = tbid_target - tbid_actual
            st.markdown(_metric_box(
                "Gap to $4.1M Target",
                f"${gap/1000:.0f}K",
                "midpoint TBID group target",
                "#EF4444" if gap > 0 else "#22C55E",
            ), unsafe_allow_html=True)
    else:
        st.info("Chain scale breakdown data not loaded. Run the pipeline.")

    # ── C. Supply Pipeline Timeline ───────────────────────────────────────────
    if df_pipeline is not None and not df_pipeline.empty:
        st.markdown("""
        <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                    letter-spacing:.06em;margin:14px 0 10px;">
        C. SUPPLY PIPELINE TIMELINE — Upcoming Hotel Openings
        </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(_chart_supply_pipeline(df_pipeline), use_container_width=True,
                        key="gt_supply_pipeline")
        # Detail table
        show_cols = ["property_name", "rooms", "chain_scale", "status",
                     "projected_open_date", "brand"]
        show_cols = [c for c in show_cols if c in df_pipeline.columns]
        if show_cols:
            st.dataframe(df_pipeline[show_cols].rename(columns={
                "property_name": "Property",
                "rooms": "Rooms",
                "chain_scale": "Scale",
                "status": "Status",
                "projected_open_date": "Est. Open",
                "brand": "Brand",
            }), use_container_width=True, hide_index=True)

    # ── D. Attribution Channel Contribution ───────────────────────────────────
    if (web_groups is not None and not web_groups.empty) or \
       (med_groups is not None and not med_groups.empty):
        st.markdown("""
        <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                    letter-spacing:.06em;margin:14px 0 10px;">
        D. ATTRIBUTION CHANNEL CONTRIBUTION — Website vs Media Group Trips & Impact
        </div>
        """, unsafe_allow_html=True)
        col_attr, col_gap = st.columns([3, 1])
        with col_attr:
            st.plotly_chart(
                _chart_attribution_channel(
                    web_groups if web_groups is not None else pd.DataFrame(),
                    med_groups if med_groups is not None else pd.DataFrame(),
                ),
                use_container_width=True,
                key="gt_attr_channel",
            )
        with col_gap:
            total_impact = 0.0
            if web_groups is not None and not web_groups.empty:
                total_impact += float(web_groups["est_impact_usd"].sum())
            if med_groups is not None and not med_groups.empty:
                total_impact += float(med_groups["est_impact_usd"].sum())
            tbid_from_impact = total_impact * TBID_RATE
            tbid_gap = 4_100_000 - tbid_from_impact
            st.markdown(_metric_box(
                "Attribution Impact",
                f"${total_impact/1e6:.2f}M",
                "website + media combined",
                "#10B981",
            ), unsafe_allow_html=True)
            st.markdown("<div style='margin:8px 0;'></div>", unsafe_allow_html=True)
            st.markdown(_metric_box(
                "TBID from Attribution",
                f"${tbid_from_impact/1000:.0f}K",
                f"gap to $4.1M: ${tbid_gap/1000:.0f}K",
                "#F5B940" if tbid_gap > 0 else "#22C55E",
            ), unsafe_allow_html=True)

    # ── STR Group Segment Coming Soon ─────────────────────────────────────────
    st.markdown("""
    <div style="background:rgba(8,145,178,0.04);border:1px dashed rgba(8,145,178,0.30);
                border-radius:8px;padding:14px 18px;margin:14px 0;">
      <div style="color:#38BDF8;font-weight:700;font-size:11.5px;margin-bottom:6px;">
        🔜 STR GROUP-SEGMENT DATA — COMING SOON
      </div>
      <div style="color:#94A3B8;font-size:11px;line-height:1.7;">
        When STR provides group-segment demand exports, this section will add live
        <strong>group demand rooms</strong>, <strong>group ADR actuals</strong>,
        <strong>SMERF vs. corporate split</strong>, and <strong>group vs. transient trend</strong>
        replacing benchmark estimates above.<br>
        To enable: save STR group export → <code>data/str/str_group_daily.xlsx</code>
        → <code>python scripts/run_pipeline.py</code>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── Actionable insights (by audience) ────────────────────────────────────
    if not insights.empty:
        _AUD_ORDER = ["dmo", "city", "cross", "visitor", "resident"]
        _AUD_LABELS = {
            "dmo":      ("🏢 DMO / TBID Board", "#0891B2"),
            "city":     ("🏛 City of Dana Point", "#4A6FA5"),
            "visitor":  ("✈️ Visitors", "#F59E0B"),
            "resident": ("🏡 Residents", "#6A4F8A"),
            "cross":    ("🔀 Hidden Signal", "#EF4444"),
        }
        _ACTION_BY_AUD = {
            "dmo":      "Integrate into VDP marketing and TBID strategy",
            "city":     "Present to City Council for infrastructure/policy decision",
            "visitor":  "Surface on visitdanapoint.com for trip-planning guidance",
            "resident": "Share via Dana Point community newsletter/social",
            "cross":    "Escalate to senior leadership — non-obvious signal",
        }
        for _aud in _AUD_ORDER:
            _aud_rows = insights[insights["audience"] == _aud] if "audience" in insights.columns else pd.DataFrame()
            if _aud_rows.empty:
                continue
            _albl, _aclr = _AUD_LABELS.get(_aud, ("Insight", "#64748B"))
            st.markdown(f"""
            <div style="color:{_aclr};font-size:10px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.06em;margin:14px 0 8px;">{_albl} — ACTIONABLE INTELLIGENCE</div>
            """, unsafe_allow_html=True)
            for _, row in _aud_rows.iterrows():
                pri    = int(row.get("priority") or 5)
                icon   = "🎯" if pri <= 2 else ("⚠️" if pri <= 4 else "ℹ️")
                _bdy   = str(row.get("body", ""))
                # Show first 2 sentences (up to 500 chars)
                _bddot = _bdy.find(". ", 80)
                _bdy_s = _bdy[:_bddot+1 if 0 < _bddot < 500 else 500].rstrip() + ("…" if len(_bdy) > 500 and _bddot < 0 else "")
                st.markdown(_action_card(
                    icon=icon,
                    headline=str(row.get("headline", ""))[:140],
                    body=_bdy_s,
                    action=_ACTION_BY_AUD.get(_aud, "Review and integrate into strategy"),
                    accent=_aclr,
                ), unsafe_allow_html=True)

    # ── STR scaffold notice ───────────────────────────────────────────────────
    if not g.get("str_group_data_available"):
        st.markdown("""
        <div style="background:rgba(245,158,11,0.06);border:1px dashed rgba(245,158,11,0.35);
                    border-radius:8px;padding:14px 18px;margin-top:12px;">
          <div style="color:#FCD34D;font-weight:700;font-size:11.5px;margin-bottom:6px;">
            📋 STR GROUP-SEGMENT DATA — PENDING INTEGRATION
          </div>
          <div style="color:#94A3B8;font-size:11px;line-height:1.7;">
            When STR provides group-segment demand exports, this panel will auto-populate with:
            <strong>group demand rooms</strong> · <strong>group ADR actuals</strong>
            · <strong>SMERF vs. corporate mix</strong> · <strong>group vs. transient trend</strong>.<br>
            To enable: save STR group export → <code>data/str/str_group_daily.xlsx</code>
            → <code>python scripts/run_pipeline.py</code>
          </div>
        </div>
        """, unsafe_allow_html=True)


def _render_traveler_types(df_types: pd.DataFrame) -> None:
    if df_types.empty:
        st.info("Traveler type data not loaded. Run `python scripts/run_pipeline.py`.")
        return

    st.markdown("""
    <div style="background:rgba(255,255,255,0.03);border-radius:10px;padding:16px 20px;
                margin-bottom:16px;">
      <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:.08em;margin-bottom:6px;">WHY THIS MATTERS</div>
      <div style="color:#CBD5E1;font-size:12.5px;line-height:1.7;">
        Not all travelers are equal. Business travelers generate <strong>highest revenue</strong>
        but represent only 20% of volume — they fund 60% of hotel revenue nationally.
        SMERF groups (shoulder-season buyers) are the <em>lowest displacement risk</em> because
        they book 8–48 weeks out into periods when transient demand is soft.
        Knowing which type Dana Point over- or under-indexes tells us where to invest marketing dollars.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Radar chart
    st.plotly_chart(_chart_traveler_radar(df_types), use_container_width=True, key="gt_radar")

    st.markdown("<div style='margin:12px 0 6px;'></div>", unsafe_allow_html=True)

    # Revenue contribution breakdown
    rev_order = {"highest": 0, "high": 1, "medium": 2, "low": 3}
    df_sorted = df_types.copy()
    df_sorted["_order"] = df_sorted["revenue_contribution"].map(rev_order).fillna(9)
    df_sorted = df_sorted.sort_values("_order")

    st.markdown("""
    <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                letter-spacing:.06em;margin-bottom:10px;">TRAVELER TYPE PROFILES — SORTED BY REVENUE CONTRIBUTION</div>
    """, unsafe_allow_html=True)

    for _, row in df_sorted.iterrows():
        t_type  = str(row.get("traveler_type", "")).title()
        rev     = str(row.get("revenue_contribution", "medium")).title()
        los_h   = row.get("typical_los_nights_high", 3)
        bkw_l   = row.get("booking_window_weeks_low", 1)
        bkw_h   = row.get("booking_window_weeks_high", 4)
        season  = str(row.get("seasonal_pattern", "year_round")).replace("_", " ").title()
        motiv   = str(row.get("primary_motivation", "")).replace("_", " ").title()
        group_s = str(row.get("group_size_typical", "")).replace("_", " ")

        rev_colors = {"Highest": "#10B981", "High": "#0891B2", "Medium": "#F5B940", "Low": "#EF4444"}
        rc = rev_colors.get(rev, "#64748B")

        # Booking window relative to SMERF (8–48 wks) for group outreach tip
        try:
            bkw_h_int = int(bkw_h)
        except Exception:
            bkw_h_int = 4
        if bkw_h_int >= 8:
            group_tip = f"✅ Book {bkw_l}–{bkw_h} wks out — ideal for group sales outreach"
        else:
            group_tip = f"⚡ Short booking window ({bkw_l}–{bkw_h} wks) — last-minute fill strategy"

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border-left:3px solid {rc};
                    border-radius:6px;padding:12px 16px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
              <span style="color:#EFF6FF;font-weight:700;font-size:14px;">{t_type}</span>
              <span style="color:{rc};font-size:10px;font-weight:700;text-transform:uppercase;
                           letter-spacing:.06em;margin-left:10px;">{rev} Revenue</span>
            </div>
            <div style="color:#64748B;font-size:10.5px;">{season}</div>
          </div>
          <div style="color:#94A3B8;font-size:11.5px;margin-top:4px;">{motiv}</div>
          <div style="display:flex;gap:24px;margin-top:8px;flex-wrap:wrap;">
            <div><span style="color:#64748B;font-size:10px;">LOS up to </span>
                 <span style="color:#CBD5E1;font-weight:600;font-size:11px;">{los_h} nights</span></div>
            <div><span style="color:#64748B;font-size:10px;">Books </span>
                 <span style="color:#CBD5E1;font-weight:600;font-size:11px;">{bkw_l}–{bkw_h} wks out</span></div>
            {f'<div><span style="color:#64748B;font-size:10px;">Group size: </span><span style="color:#CBD5E1;font-weight:600;font-size:11px;">{group_s}</span></div>' if group_s else ''}
          </div>
          <div style="margin-top:8px;font-size:10.5px;color:#93C5FD;">{group_tip}</div>
        </div>
        """, unsafe_allow_html=True)


def _render_national_context(df_segs: pd.DataFrame, df_biz: pd.DataFrame,
                              g: dict,
                              df_costar_monthly: Optional[pd.DataFrame] = None,
                              web_groups: Optional[pd.DataFrame] = None,
                              df_types: Optional[pd.DataFrame] = None,
                              comp: Optional[pd.DataFrame] = None) -> None:
    # National summary callout
    total_group = 319
    meetings_b  = 126
    spectator_b = 102
    sports_b    = 52
    leisure_b   = 39
    meetings_rec = 82   # % recovery vs 2019

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(8,145,178,0.10),rgba(167,139,250,0.06));
                border:1px solid rgba(8,145,178,0.25);border-radius:12px;padding:18px 22px;
                margin-bottom:16px;">
      <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:.1em;margin-bottom:10px;">U.S. GROUP TRAVEL — NATIONAL PICTURE</div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px;">
        <div style="text-align:center;">
          <div style="color:#EFF6FF;font-size:22px;font-weight:800;">${total_group}B</div>
          <div style="color:#93C5FD;font-size:10px;">Total Group Travel</div>
        </div>
        <div style="text-align:center;">
          <div style="color:#10B981;font-size:22px;font-weight:800;">{meetings_rec}%</div>
          <div style="color:#93C5FD;font-size:10px;">Meetings Recovery (2019)</div>
        </div>
        <div style="text-align:center;">
          <div style="color:#F5B940;font-size:22px;font-weight:800;">3M+</div>
          <div style="color:#93C5FD;font-size:10px;">U.S. Jobs Supported</div>
        </div>
        <div style="text-align:center;">
          <div style="color:#A78BFA;font-size:22px;font-weight:800;">$188B</div>
          <div style="color:#93C5FD;font-size:10px;">Meetings 2026 Projected</div>
        </div>
      </div>
      <div style="color:#CBD5E1;font-size:12px;line-height:1.7;">
        Meetings & events ($126B) are the largest group segment and at 82% recovery — still growing.
        Live spectator sports ($102B) and participatory sports ($52B) are segments where
        Dana Point can directly compete via surf events (Doheny), sailing regattas,
        and ocean-sports tourism. Leisure group travel ($39B) is fully recovered.
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        if not df_segs.empty:
            st.plotly_chart(_chart_segment_donut(df_segs), use_container_width=True, key="gt_donut")
    with col_b:
        st.plotly_chart(_chart_revenue_funnel(g), use_container_width=True, key="gt_funnel")

    # Business travel context
    if not df_biz.empty:
        biz_total = df_biz[df_biz["category"] == "total_business"]
        if not biz_total.empty:
            biz_s   = biz_total.iloc[0]
            biz_sp  = float(biz_s.get("spend_billion_usd") or 312)
            biz_rec = float(biz_s.get("pct_recovery_vs_2019") or 85)
            biz_lod = float(biz_s.get("pct_total_lodging_rev") or 60)
            st.markdown(f"""
            <div style="background:rgba(8,145,178,0.07);border-radius:10px;padding:16px 20px;
                        margin-top:14px;">
              <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                          letter-spacing:.08em;margin-bottom:10px;">BUSINESS TRAVEL — HOTEL IMPACT</div>
              <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                <div style="text-align:center;">
                  <div style="color:#EFF6FF;font-size:22px;font-weight:800;">${biz_sp:.0f}B</div>
                  <div style="color:#64748B;font-size:10px;">National Business Travel Spend</div>
                  <div style="color:#94A3B8;font-size:9.5px;">{biz_rec:.0f}% of 2019 recovery</div>
                </div>
                <div style="text-align:center;">
                  <div style="color:#EFF6FF;font-size:22px;font-weight:800;">{biz_lod:.0f}%</div>
                  <div style="color:#64748B;font-size:10px;">of Hotel Revenue</div>
                  <div style="color:#94A3B8;font-size:9.5px;">from just 20% of travelers</div>
                </div>
                <div style="text-align:center;">
                  <div style="color:#F5B940;font-size:22px;font-weight:800;">5×</div>
                  <div style="color:#64748B;font-size:10px;">Revenue per Traveler</div>
                  <div style="color:#94A3B8;font-size:9.5px;">vs. average leisure visitor</div>
                </div>
              </div>
              <div style="margin-top:10px;background:rgba(0,0,0,0.15);border-radius:6px;
                          padding:8px 12px;color:#CBD5E1;font-size:11.5px;line-height:1.6;">
                <strong>Dana Point implication:</strong> Corporate meeting planners evaluating
                South OC coastal venues represent the highest-value group segment. Waldorf Astoria
                and Ritz-Carlton carry national brand recognition that opens doors to corporate
                contracting. TBID investment in group sales missions targeting these planners
                has the highest potential ROI.
              </div>
            </div>
            """, unsafe_allow_html=True)

    # Dana Point opportunities
    st.markdown("""
    <div style="margin-top:16px;">
      <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:.08em;margin-bottom:10px;">DANA POINT SEGMENT OPPORTUNITIES</div>
    </div>
    """, unsafe_allow_html=True)

    opportunities = [
        ("🏄", "Participatory Sports ($52B)", "#0891B2",
         "Doheny surf events, sailing regattas, ocean sports tours target this fast-growing segment. "
         "Dana Point's natural assets position it as a West Coast hub.",
         "Develop 'Sports & Adventure' group package with participating hotels + TBID co-investment"),
        ("🎪", "Meetings & Events ($126B)", "#10B981",
         "82% recovery and growing. Waldorf Astoria and Ritz-Carlton can compete for corporate "
         "board retreats, incentive travel, and high-end association events.",
         "Launch group sales mission targeting corporate meeting planners in LA, San Diego, Phoenix"),
        ("👥", "SMERF Groups ($39B leisure group)", "#F5B940",
         "Social, Military, Educational, Religious, Fraternal — primary shoulder-season buyer. "
         "Books 8–48 weeks out into Q1/Q4 when displacement risk is lowest.",
         "Create SMERF rate program for Jan–Mar and Oct–Dec with dedicated group blocks"),
    ]
    for icon, title, accent, body, action in opportunities:
        st.markdown(_action_card(icon, title, body, action, accent), unsafe_allow_html=True)

    # ── E. CoStar Monthly Occ overlay ─────────────────────────────────────────
    if (df_costar_monthly is not None and not df_costar_monthly.empty) or \
       (web_groups is not None and not web_groups.empty):
        st.markdown("""
        <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                    letter-spacing:.08em;margin:18px 0 10px;">
        E. COSTAR MONTHLY OCC vs DATAFY GROUP ATTRIBUTION
        </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(
            _chart_costar_occ_overlay(
                df_costar_monthly if df_costar_monthly is not None else pd.DataFrame(),
                web_groups if web_groups is not None else pd.DataFrame(),
            ),
            use_container_width=True,
            key="gt_costar_occ_overlay",
        )

    # ── F. Shoulder Season Alignment Matrix ───────────────────────────────────
    if df_types is not None and not df_types.empty and comp is not None and not comp.empty:
        st.markdown("""
        <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                    letter-spacing:.08em;margin:18px 0 10px;">
        F. SHOULDER SEASON ALIGNMENT MATRIX — Traveler Types × Quarters
        </div>
        """, unsafe_allow_html=True)
        _render_shoulder_alignment(df_types, comp)


def _render_ai_analyst(ai_keys: dict, selected_model: str) -> None:
    """AI Analyst sub-tab with group travel pre-loaded prompts."""
    GROUP_PROMPTS = [
        ("🎯 TBID Opportunity",
         "Based on our group intelligence data, what is the estimated TBID revenue opportunity "
         "from growing group demand share by 5 percentage points, and which traveler segments "
         "should we prioritize to achieve this with the least displacement risk?"),
        ("📅 Shoulder Season Strategy",
         "Analyze our occupancy pattern and compression days. Which months have the lowest "
         "displacement risk for group business? What types of groups (SMERF, corporate, sports) "
         "should we target by quarter to maximize TBID without cannibalizing peak transient revenue?"),
        ("🏆 National Benchmark Gap",
         "Compare Dana Point's estimated group demand share to national benchmarks. "
         "Are we above or below the STR/CBRE industry standard of 25–32% for upper-upscale "
         "coastal resort markets? What would it take to reach the top of that range?"),
        ("💼 Corporate Sales Pitch",
         "Write a compelling one-paragraph pitch for a corporate meeting planner explaining "
         "why Dana Point should be their next incentive travel destination, using our actual "
         "ADR, occupancy, and amenity data."),
        ("📊 Board Report Summary",
         "Generate a board-ready executive summary of our group business intelligence, "
         "including TBID opportunity, displacement risk assessment, and 3 recommended actions "
         "for the next 12 months."),
    ]

    st.markdown("""
    <div style="background:rgba(255,255,255,0.03);border-radius:10px;padding:16px 20px;
                margin-bottom:16px;">
      <div style="color:#93C5FD;font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:.08em;margin-bottom:6px;">AI GROUP TRAVEL ANALYST</div>
      <div style="color:#CBD5E1;font-size:12px;line-height:1.6;">
        Ask the AI analyst a question about group travel strategy, or use one of the
        pre-loaded prompts below. The AI has full access to our group intelligence data,
        U.S. Travel benchmarks, and CoStar market data.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Pre-loaded Group Travel Prompts**")
    prompt_cols = st.columns(len(GROUP_PROMPTS))
    selected_prompt = ""
    for i, (label, prompt_text) in enumerate(GROUP_PROMPTS):
        with prompt_cols[i]:
            if st.button(label, key=f"gt_prompt_{i}", use_container_width=True):
                st.session_state["gt_ai_prompt"]     = prompt_text
                st.session_state["gt_ai_needs_call"] = True

    custom = st.text_area(
        "Or type your own group travel question:",
        value=st.session_state.get("gt_ai_prompt", ""),
        height=100,
        key="gt_ai_custom",
        placeholder="E.g., What shoulder months should we target for SMERF group blocks?",
    )
    if custom:
        st.session_state["gt_ai_prompt"] = custom

    if st.button("🔍 Ask AI Analyst", type="primary", key="gt_ai_submit"):
        st.session_state["gt_ai_needs_call"] = True

    if st.session_state.get("gt_ai_needs_call") and st.session_state.get("gt_ai_prompt"):
        # Delegate to the main app's AI panel by setting shared session keys
        st.session_state["ai_current_prompt"] = st.session_state["gt_ai_prompt"]
        st.session_state["ai_prompt_label"]   = "Group & Travel Analysis"
        st.session_state["ai_needs_call"]     = True
        st.session_state["gt_ai_needs_call"]  = False
        st.info("Prompt queued for AI Analyst. Switch to **Today's Overview → AI Assistant** tab to see the response, or scroll up if already there.")


# ── Main entry point ──────────────────────────────────────────────────────────

def render_group_tab(ai_keys: dict | None = None, selected_model: str = "claude") -> None:
    """Render the full Group & Traveler Intelligence tab."""

    # Load all data
    g                 = _load_group_intel()
    df_monthly        = _load_monthly_occ()
    df_segs           = _load_ust_segments()
    df_biz            = _load_ust_biz()
    df_types          = _load_traveler_types()
    insights          = _load_group_insights()
    social            = _load_social_summary()
    df_chain          = _load_costar_chain()
    df_comp           = _load_competitive_set()
    df_pipeline       = _load_supply_pipeline()
    web_groups, med_groups = _load_attribution_groups()
    df_costar_monthly = _load_costar_monthly()

    # Load compression for shoulder matrix
    try:
        _comp_conn = sqlite3.connect(_DB_PATH, timeout=10)
        df_compression = pd.read_sql_query(
            "SELECT quarter, days_above_80_occ, days_above_90_occ FROM kpi_compression_quarterly ORDER BY quarter",
            _comp_conn,
        )
        _comp_conn.close()
    except Exception as _exc:
        import logging; logging.getLogger("vdp_dashboard").debug("compression load failed: %s", _exc)
        df_compression = pd.DataFrame()

    # Hero banner
    tbid_low  = g.get("estimated_group_tbid_rev_low",  3_603_940)
    tbid_high = g.get("estimated_group_tbid_rev_high", 4_613_043)
    st.markdown(f"""
    <div class="hero-banner" style="margin-bottom:0;">
      <div class="hero-title">👥 Group &amp; Traveler Intelligence</div>
      <div class="hero-subtitle">
        Est. Group TBID Contribution: <strong>${tbid_low/1e6:.1f}M–${tbid_high/1e6:.1f}M/yr</strong>
        · U.S. Group Travel: <strong>$319B</strong> national market
        · Shoulder-Season Group Strategy · SMERF &amp; Corporate Targeting
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

    # Data quality notice
    if not g:
        st.warning("Group intelligence data not loaded. Run `python scripts/run_pipeline.py`.")
        return

    st.info(
        "📌 **Data context:** Group demand estimates use CoStar chain-scale supply + "
        "industry benchmarks (STR/CBRE 2024 upper-upscale coastal resort averages). "
        "Actual STR group-segment data will replace benchmarks when provided. "
        "U.S. Travel benchmarks sourced from U.S. Travel Association 2024 reports."
    )

    sub_strategy, sub_types, sub_national, sub_ai = st.tabs([
        "🎯 Group Strategy",
        "🧭 Traveler Types",
        "🌐 National Context",
        "🤖 AI Analyst",
    ])

    with sub_strategy:
        _render_group_strategy(
            g, df_monthly, df_chain, insights, social,
            df_comp=df_comp,
            df_pipeline=df_pipeline,
            web_groups=web_groups,
            med_groups=med_groups,
        )

    with sub_types:
        _render_traveler_types(df_types)

    with sub_national:
        _render_national_context(
            df_segs, df_biz, g,
            df_costar_monthly=df_costar_monthly,
            web_groups=web_groups,
            df_types=df_types,
            comp=df_compression,
        )

    with sub_ai:
        _render_ai_analyst(ai_keys or {}, selected_model)

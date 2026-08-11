"""
generate_weekly_report.py
--------------------------
Builds the Dana Point PULSE weekly report PDF from live data in analytics.sqlite.

Reads:  dashboard/report_template.html (static layout, [[TOKEN]] placeholders)
Writes: logs/weekly_report_latest.pdf   (also logs/weekly_report_<date>.pdf)

Charts are rendered server-side with matplotlib (no browser/JS dependency) and
embedded as base64 PNGs. Final HTML -> PDF conversion uses WeasyPrint (pure
Python, no headless-browser dependency -- reliable on Streamlit Cloud).

Run:
    python3 scripts/generate_weekly_report.py
"""

from __future__ import annotations

import base64
import io
import os
import sqlite3
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "analytics.sqlite")
TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "dashboard", "report_template.html")
LOGO_PATH = os.path.join(PROJECT_ROOT, "dashboard", "assets", "vdp_logo.svg")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")


def _logo_data_uri() -> str:
    try:
        with open(LOGO_PATH, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}"
    except FileNotFoundError:
        return ""

TEAL = "#0891B2"
TEAL_DK = "#0E7490"
TEAL_LT = "#7DD3E8"
MAROON = "#8E1B2E"
MAROON_LT = "#C4536A"
SLATE = "#94A3B8"

# Benchmark figures (industry STR/CBRE benchmarks; no live STR group-segment
# feed exists yet -- see CLAUDE.md "Group Business Estimate" methodology).
COMPSET_BENCHMARK = {
    "Newport": 246.48,
    "La Jolla": 216.06,
    "Monterey": 206.98,
    "Sta Barb": 201.84,
    "Hunt Bch": 198.06,
}
GROUP_BENCHMARK = {
    "adr_occ": "$324 / 72.9%",
    "demand_range": "25% – 32%",
    "revenue_range": "$116.3M – $148.9M",
    "tbid_range": "$1.82M – $2.33M",
    "tot_range": "$11.63M – $14.89M",
    "compression_days_annual": "135",
    "demand_share": "60.5%",
}


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("ascii")


def _bar_chart(labels, series, colors, ylabel, figsize=(4.6, 2.4), legend=False):
    fig, ax = plt.subplots(figsize=figsize)
    n = len(series)
    width = 0.8 / n
    x = range(len(labels))
    for i, (name, vals, color) in enumerate(zip([s[0] for s in series], [s[1] for s in series], colors)):
        offs = [xi + (i - (n - 1) / 2) * width for xi in x]
        ax.bar(offs, vals, width=width, color=color, label=name)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    if legend:
        ax.legend(fontsize=7, frameon=False, loc="upper left")
    fig.tight_layout()
    return _fig_to_b64(fig)


def _dual_axis_bar(labels, occ_vals, revpar_vals):
    fig, ax1 = plt.subplots(figsize=(9, 3.6))
    x = range(len(labels))
    width = 0.35
    ax1.bar([xi - width / 2 for xi in x], occ_vals, width=width, color=TEAL, label="Occupancy %")
    ax1.set_ylabel("Occupancy %", fontsize=9)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, fontsize=10)
    ax2 = ax1.twinx()
    ax2.bar([xi + width / 2 for xi in x], revpar_vals, width=width, color=TEAL_LT, label="RevPAR $")
    ax2.set_ylabel("RevPAR $", fontsize=9)
    ax1.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, frameon=False, loc="upper right")
    fig.tight_layout()
    return _fig_to_b64(fig)


def _pie_chart(labels, values, colors, figsize=(3.2, 3.2)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.pie(values, colors=colors, startangle=90, wedgeprops={"linewidth": 1, "edgecolor": "white"})
    ax.axis("equal")
    fig.tight_layout()
    return _fig_to_b64(fig)


def _donut_chart(labels, values, colors, figsize=(3, 3)):
    fig, ax = plt.subplots(figsize=figsize)
    wedges, _ = ax.pie(
        values, colors=colors, startangle=90,
        wedgeprops={"width": 0.42, "linewidth": 1, "edgecolor": "white"},
    )
    ax.legend(wedges, labels, loc="lower center", bbox_to_anchor=(0.5, -0.25),
              fontsize=8, frameon=False, ncol=1)
    ax.axis("equal")
    fig.tight_layout()
    return _fig_to_b64(fig)


def _hbar_chart(labels, values, color, xlabel, figsize=(6.4, 3.6)):
    fig, ax = plt.subplots(figsize=figsize)
    y = range(len(labels))
    ax.barh(list(y), values, color=color)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _fig_to_b64(fig)


def _fmt_pct(v, decimals=1, sign=False):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "N/A"
    s = f"{v:+.{decimals}f}%" if sign else f"{v:.{decimals}f}%"
    return s


def _fmt_usd(v, decimals=0):
    try:
        return f"${float(v):,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def build_report() -> str:
    """Returns path to the generated PDF."""
    con = _connect()

    kpi = pd.read_sql_query(
        "SELECT * FROM kpi_daily_summary ORDER BY as_of_date DESC LIMIT 400", con
    )
    kpi["as_of_date"] = pd.to_datetime(kpi["as_of_date"])
    latest_date = kpi["as_of_date"].max()

    # --- last complete 7-day window ---
    week_end = latest_date
    week_start = week_end - timedelta(days=6)
    week_df = kpi[(kpi["as_of_date"] >= week_start) & (kpi["as_of_date"] <= week_end)].copy()
    week_df = week_df.sort_values("as_of_date")

    occ_avg = week_df["occ_pct"].mean()
    adr_avg = week_df["adr"].mean()
    revpar_avg = week_df["revpar"].mean()
    occ_yoy_avg = week_df["occ_yoy"].mean() if "occ_yoy" in week_df else None
    adr_yoy_avg = week_df["adr_yoy"].mean() if "adr_yoy" in week_df else None
    revpar_yoy_avg = week_df["revpar_yoy"].mean() if "revpar_yoy" in week_df else None

    if week_start.month == week_end.month:
        week_label = f"{week_start.strftime('%B %-d')} – {week_end.strftime('%-d, %Y')}"
    else:
        week_label = f"{week_start.strftime('%B %-d')} – {week_end.strftime('%B %-d, %Y')}"

    # day-of-week occ/adr for the week (Sun-Sat order)
    week_df["dow"] = week_df["as_of_date"].dt.dayofweek  # Mon=0..Sun=6
    dow_order = [6, 0, 1, 2, 3, 4, 5]  # Sun,Mon,Tue,Wed,Thu,Fri,Sat
    dow_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    occ_by_dow, adr_by_dow = [], []
    for d in dow_order:
        row = week_df[week_df["dow"] == d]
        occ_by_dow.append(float(row["occ_pct"].mean()) if not row.empty else 0.0)
        adr_by_dow.append(float(row["adr"].mean()) if not row.empty else 0.0)

    chart_occ_dp = _bar_chart(dow_labels, [("Occupancy %", occ_by_dow)], [MAROON], "Occ %")
    chart_adr_dp = _bar_chart(dow_labels, [("ADR $", adr_by_dow)], [MAROON], "ADR $")

    # comp-set chart: Dana Point (live) + 5 benchmark markets
    compset_labels = ["Dana Pt"] + list(COMPSET_BENCHMARK.keys())
    compset_vals = [round(revpar_avg, 2)] + list(COMPSET_BENCHMARK.values())
    compset_colors = [MAROON] + [SLATE] * len(COMPSET_BENCHMARK)
    fig, ax = plt.subplots(figsize=(4.6, 2.4))
    ax.bar(compset_labels, compset_vals, color=compset_colors)
    ax.set_ylabel("RevPAR $", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    chart_compset = _fig_to_b64(fig)

    # compression by quarter
    comp_q = pd.read_sql_query(
        "SELECT quarter, days_above_80_occ, days_above_90_occ FROM kpi_compression_quarterly "
        "ORDER BY quarter DESC LIMIT 5", con
    ).iloc[::-1]
    q_labels = [q.replace("20", "") for q in comp_q["quarter"]]
    chart_compression = _bar_chart(
        q_labels,
        [("80%+ occ", comp_q["days_above_80_occ"].tolist()), ("90%+ occ", comp_q["days_above_90_occ"].tolist())],
        [MAROON, MAROON_LT], "Days", legend=True,
    )
    compression_label = comp_q["quarter"].iloc[-1] if not comp_q.empty else "Q-"
    compression_days = int(comp_q["days_above_80_occ"].iloc[-1]) if not comp_q.empty else 0

    # CoStar chain-scale segments
    seg = pd.read_sql_query(
        "SELECT chain_scale, occupancy_pct, revpar_usd, room_revenue_usd, year "
        "FROM costar_chain_scale_breakdown WHERE year = (SELECT MAX(year) FROM costar_chain_scale_breakdown) "
        "ORDER BY revpar_usd DESC", con
    )
    seg_year = seg["year"].iloc[0] if not seg.empty else "N/A"
    chart_segments = _dual_axis_bar(
        seg["chain_scale"].tolist(), seg["occupancy_pct"].tolist(), seg["revpar_usd"].tolist()
    )
    segment_list = " · ".join(seg["chain_scale"].tolist())

    # property detail + tax estimate (luxury / upper upscale only, matching template)
    props = pd.read_sql_query(
        "SELECT property_name, chain_scale, occupancy_pct, adr_usd, revpar_usd FROM costar_competitive_set "
        "WHERE chain_scale IN ('Luxury','Upper Upscale') ORDER BY chain_scale, revpar_usd DESC", con
    )
    pill = {"Luxury": "pill-luxury", "Upper Upscale": "pill-upper"}
    property_rows = ""
    for _, r in props.iterrows():
        cls = pill.get(r["chain_scale"], "pill-upper")
        property_rows += (
            f'<tr><td>{r["property_name"]}</td><td><span class="{cls}">{r["chain_scale"]}</span></td>'
            f'<td class="num">{r["occupancy_pct"]:.1f}%</td><td class="num">${r["adr_usd"]:,.0f}</td>'
            f'<td class="num strong">${r["revpar_usd"]:,.0f}</td></tr>\n'
        )

    tax_rows = ""
    total_rev = seg["room_revenue_usd"].sum() if not seg.empty else 0
    for _, r in seg[seg["chain_scale"].isin(["Luxury", "Upper Upscale"])].iterrows():
        rev = r["room_revenue_usd"]
        share = (rev / total_rev * 100) if total_rev else 0
        tbid = rev * 0.0125
        tot = rev * 0.10
        cls = pill.get(r["chain_scale"], "pill-upper")
        tax_rows += (
            f'<tr><td><span class="{cls}">{r["chain_scale"]}</span></td>'
            f'<td class="num">${rev/1e6:,.1f}M</td><td class="num">{share:.1f}%</td>'
            f'<td class="num">${tbid/1e6:,.2f}M</td><td class="num strong">${tot/1e6:,.2f}M</td></tr>\n'
        )

    # Datafy visitor profile
    dkpi = pd.read_sql_query(
        "SELECT total_trips, avg_length_of_stay_days, day_trips_pct, overnight_trips_pct, "
        "out_of_state_vd_pct, report_period_start, report_period_end FROM datafy_overview_kpis LIMIT 1", con
    )
    if not dkpi.empty:
        d = dkpi.iloc[0]
        total_trips = f"{int(d['total_trips']):,}"
        avg_los = f"{d['avg_length_of_stay_days']:.1f} nights"
        oos_pct = f"{d['out_of_state_vd_pct']:.1f}%"
        datafy_period = f"{d['report_period_start'][:4]} Annual"
        chart_trip = _donut_chart(
            ["Overnight Trips", "Day Trips"], [d["overnight_trips_pct"], d["day_trips_pct"]], [TEAL_DK, TEAL_LT]
        )
    else:
        total_trips, avg_los, oos_pct, datafy_period = "N/A", "N/A", "N/A", "N/A"
        chart_trip = _donut_chart(["Overnight", "Day"], [60, 40], [TEAL_DK, TEAL_LT])

    cat = pd.read_sql_query(
        "SELECT category, spend_share_pct FROM datafy_overview_category_spending "
        "ORDER BY spend_share_pct DESC LIMIT 6", con
    )
    chart_category = _hbar_chart(cat["category"].tolist()[::-1], cat["spend_share_pct"].tolist()[::-1], TEAL, "Spend Share %")

    # visitor origins
    dma = pd.read_sql_query(
        "SELECT dma, visitor_days_share_pct FROM datafy_overview_dma "
        "WHERE visitor_days_share_pct IS NOT NULL ORDER BY visitor_days_share_pct DESC LIMIT 10", con
    )
    origin_colors = [TEAL_DK, TEAL, "#22A6C4", "#5CC4DC", TEAL_LT, "#A78BFA", "#8B5CF6", "#C4B5FD", "#1E293B", "#475569"]
    chart_origins = _pie_chart(dma["dma"].tolist(), dma["visitor_days_share_pct"].tolist(), origin_colors[: len(dma)])
    origins_legend = ""
    for i, (_, r) in enumerate(dma.iterrows()):
        origins_legend += (
            f'<div class="origins-legend-row"><div class="dot" style="background:{origin_colors[i % len(origin_colors)]}">'
            f'</div><div style="flex:1;">{r["dma"]}</div><div style="font-weight:700;">{r["visitor_days_share_pct"]:.1f}%</div></div>\n'
        )

    # executive headline: top dmo insight(s) for the front page
    exec_insights = pd.read_sql_query(
        "SELECT headline, body FROM insights_daily WHERE audience='dmo' "
        "AND as_of_date=(SELECT MAX(as_of_date) FROM insights_daily WHERE audience='dmo') "
        "ORDER BY priority LIMIT 3", con
    )
    exec_headline_cards = ""
    for _, r in exec_insights.iterrows():
        tag = r["headline"].split(":")[0].split("→")[0][:44]
        body = r["body"]
        body = body if len(body) < 200 else body[:197] + "..."
        exec_headline_cards += (
            f'<div class="insight-card"><div class="insight-tag">{tag}</div>'
            f'<div class="insight-body">{body}</div></div>\n'
        )
    if not exec_headline_cards:
        exec_headline_cards = '<div class="insight-body">No headline insight available for this period.</div>'

    # cross-dataset insights
    insights = pd.read_sql_query(
        "SELECT headline, body FROM insights_daily WHERE audience='cross' "
        "AND as_of_date=(SELECT MAX(as_of_date) FROM insights_daily WHERE audience='cross') "
        "ORDER BY priority LIMIT 3", con
    )
    insight_cards = ""
    for _, r in insights.iterrows():
        tag = r["headline"].split(":")[0].split("→")[0][:40]
        body = r["body"]
        body = body if len(body) < 220 else body[:217] + "..."
        insight_cards += (
            f'<div class="insight-card"><div class="insight-tag">{tag}</div>'
            f'<div class="insight-body">{body}</div></div>\n'
        )
    if not insight_cards:
        insight_cards = '<div class="insight-body">No cross-dataset insights available for this period.</div>'

    con.close()

    tokens = {
        "WEEK_LABEL": week_label,
        "GEN_TIMESTAMP": datetime.now().strftime("%b %-d, %Y %-I:%M %p"),
        "OCC_PCT": _fmt_pct(occ_avg),
        "ADR": _fmt_usd(adr_avg),
        "REVPAR": _fmt_usd(revpar_avg),
        "COMPRESSION_DAYS": compression_days,
        "COMPRESSION_LABEL": compression_label,
        "OCC_YOY": _fmt_pct(occ_yoy_avg, sign=True) if occ_yoy_avg is not None else "N/A",
        "ADR_YOY": _fmt_pct(adr_yoy_avg, sign=True) if adr_yoy_avg is not None else "N/A",
        "REVPAR_YOY": _fmt_pct(revpar_yoy_avg, sign=True) if revpar_yoy_avg is not None else "N/A",
        "GROUP_DEMAND_SHARE": GROUP_BENCHMARK["demand_share"],
        "CHART_OCC_DP": chart_occ_dp,
        "CHART_COMPSET": chart_compset,
        "CHART_ADR_DP": chart_adr_dp,
        "CHART_COMPRESSION": chart_compression,
        "CHART_ORIGINS": chart_origins,
        "ORIGINS_LEGEND": origins_legend,
        "DATAFY_PERIOD": datafy_period,
        "COSTAR_SEGMENT_PERIOD": f"Full Year {seg_year}, South Orange County CA",
        "COSTAR_SEGMENT_LIST": segment_list,
        "CHART_SEGMENTS": chart_segments,
        "PROPERTY_ROWS": property_rows,
        "TAX_ROWS": tax_rows,
        "CHART_TRIP": chart_trip,
        "TOTAL_TRIPS": total_trips,
        "AVG_LOS": avg_los,
        "OOS_PCT": oos_pct,
        "CHART_CATEGORY": chart_category,
        "LATEST_STR_DATE": latest_date.strftime("%B %-d, %Y"),
        "GROUP_ADR_OCC": GROUP_BENCHMARK["adr_occ"],
        "GROUP_DEMAND_RANGE": GROUP_BENCHMARK["demand_range"],
        "GROUP_REVENUE_RANGE": GROUP_BENCHMARK["revenue_range"],
        "GROUP_TBID_RANGE": GROUP_BENCHMARK["tbid_range"],
        "GROUP_TOT_RANGE": GROUP_BENCHMARK["tot_range"],
        "COMPRESSION_DAYS_ANNUAL": GROUP_BENCHMARK["compression_days_annual"],
        "INSIGHT_CARDS": insight_cards,
        "EXEC_HEADLINE_CARDS": exec_headline_cards,
        "LOGO_DATA_URI": _logo_data_uri(),
    }

    html = open(TEMPLATE_PATH, encoding="utf-8").read()
    for k, v in tokens.items():
        html = html.replace(f"[[{k}]]", str(v))

    os.makedirs(LOGS_DIR, exist_ok=True)
    html_path = os.path.join(LOGS_DIR, "weekly_report_latest.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    from weasyprint import HTML
    pdf_path = os.path.join(LOGS_DIR, "weekly_report_latest.pdf")
    HTML(html_path).write_pdf(pdf_path)

    dated_path = os.path.join(LOGS_DIR, f"weekly_report_{latest_date.strftime('%Y-%m-%d')}.pdf")
    with open(pdf_path, "rb") as src, open(dated_path, "wb") as dst:
        dst.write(src.read())

    print(f"Report generated: {pdf_path}")
    print(f"Dated copy: {dated_path}")
    return pdf_path


if __name__ == "__main__":
    build_report()

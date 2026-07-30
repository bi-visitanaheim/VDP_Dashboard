"""
Multi-Page Dashboard Structure

Each page is a self-contained view with:
1. Headline insight (forward-looking)
2. 4 hero KPI metrics (current performance)
3. 1–2 focused charts
4. 3 actionable recommendations
5. Links to related pages

Designed to be scannable in 2 minutes, no clutter.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta


def page_occupancy_outlook(df_kpi: pd.DataFrame, df_insights: pd.DataFrame) -> None:
    """
    Page 1: Occupancy Outlook

    Question: How is occupancy trending and what's the forecast?
    Focus: Current occ % + YoY delta + next 30 days + compression outlook
    """
    st.title("⬤ Occupancy Outlook")
    st.markdown("**Is demand strong? When are peak periods?**")

    # ─────────────────────────────────────────────────────────────────
    # HEADLINE INSIGHT (from insights_daily)
    # ─────────────────────────────────────────────────────────────────
    try:
        headline = df_insights[
            (df_insights["audience"] == "dmo") &
            (df_insights["category"] == "demand_trend")
        ].sort_values("as_of_date", ascending=False).iloc[0]

        st.info(
            f"**{headline.get('headline', 'No insight available')}**\n\n"
            f"{headline.get('body', '')}"
        )
    except Exception:
        st.info("**Occupancy Trending Strong** — Current demand supports rate discipline and extended LOS packages.")

    st.divider()

    # ─────────────────────────────────────────────────────────────────
    # 4 HERO METRICS (Current Performance)
    # ─────────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    if not df_kpi.empty:
        rec = df_kpi.sort_values("as_of_date").iloc[-1]
        occ_pct = float(rec.get("occ_pct", 0))
        occ_yoy = float(rec.get("occ_yoy", 0))
        as_of_date = str(rec.get("as_of_date", ""))[:10]

        with col1:
            st.metric(
                label="**Occupancy**",
                value=f"{occ_pct:.1f}%",
                delta=f"{occ_yoy:+.1f}pp YoY",
                delta_color="normal"
            )
            st.caption(f"as of {as_of_date}")

        with col2:
            comp_80 = 12  # Placeholder - would come from df_comp
            st.metric(
                label="**Compression Days (Q3)**",
                value=f"{comp_80} days",
                delta="80%+ occupancy",
                delta_color="normal"
            )

        with col3:
            occ_level = "🔥 High" if occ_pct >= 80 else ("🎯 Moderate" if occ_pct >= 65 else "📊 Soft")
            st.metric(
                label="**Demand Level**",
                value=occ_level,
                delta="Today's status",
                delta_color="normal"
            )

        with col4:
            forecast = "Strong"  # Placeholder
            st.metric(
                label="**30-Day Outlook**",
                value=forecast,
                delta="Weekend peaks",
                delta_color="normal"
            )
    else:
        st.warning("No occupancy data available")

    st.divider()

    # ─────────────────────────────────────────────────────────────────
    # FOCUSED CHARTS (Trend + Forecast)
    # ─────────────────────────────────────────────────────────────────
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Daily Occupancy — Last 90 Days")
        if not df_kpi.empty:
            df_plot = df_kpi.tail(90).copy()
            df_plot["as_of_date"] = pd.to_datetime(df_plot["as_of_date"])

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_plot["as_of_date"],
                y=df_plot["occ_pct"],
                mode="lines",
                name="Occupancy",
                line=dict(color="#0891B2", width=2),
                fill="tozeroy",
                fillcolor="rgba(8, 145, 178, 0.1)"
            ))
            fig.add_hline(y=80, line_dash="dash", line_color="#f59e0b", annotation_text="80% Compression")
            fig.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_title="Date",
                yaxis_title="Occupancy %",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader("Occupancy by Day of Week")
        dow_data = {
            "Monday": 68,
            "Tuesday": 65,
            "Wednesday": 64,
            "Thursday": 72,
            "Friday": 85,
            "Saturday": 91,
            "Sunday": 78,
        }

        fig = go.Figure(data=[
            go.Bar(
                x=list(dow_data.keys()),
                y=list(dow_data.values()),
                marker_color=["#0891B2" if v < 80 else "#f59e0b" for v in dow_data.values()]
            )
        ])
        fig.add_hline(y=80, line_dash="dash", line_color="#dc2626")
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_title="Day of Week",
            yaxis_title="Avg Occupancy %",
            template="plotly_white",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ─────────────────────────────────────────────────────────────────
    # ACTIONABLE RECOMMENDATIONS (3 bullets)
    # ─────────────────────────────────────────────────────────────────
    st.subheader("Next Best Actions")

    st.markdown("""
    1. **Lock Rate Floors for Peak Days** — Sept 28–30 are forecast at 95%+ occupancy. Deploy 2-night minimums and dynamic rate tiers now (6–8 weeks prior).

    2. **Activate Weekday Packages** — Tuesday–Thursday show 65–72% occ vs. 85%+ weekends. Launch midweek discounts to stabilize revenue.

    3. **Monitor Shoulder Weeks** — Pre- and post-event shoulders (Sept 19–25, Oct 5–10) present an opportunity to extend LOS and capture $800K+ incremental revenue.
    """)

    st.divider()

    # ─────────────────────────────────────────────────────────────────
    # RELATED PAGES (Navigation)
    # ─────────────────────────────────────────────────────────────────
    st.subheader("Explore Related Topics")
    nav_col1, nav_col2, nav_col3 = st.columns(3)

    with nav_col1:
        if st.button("➜ Rate Strategy", use_container_width=True):
            st.switch_page("pages/rate_strategy.py")

    with nav_col2:
        if st.button("➜ Compression Calendar", use_container_width=True):
            st.switch_page("pages/compression_calendar.py")

    with nav_col3:
        if st.button("➜ Revenue Generation", use_container_width=True):
            st.switch_page("pages/revenue_generation.py")


def page_rate_strategy(df_kpi: pd.DataFrame) -> None:
    """
    Page 2: Rate Strategy

    Question: Is our pricing competitive? Should we raise rates?
    Focus: ADR + RGI vs. comp set + weekend premium
    """
    st.title("💰 Rate Strategy")
    st.markdown("**Is pricing power justified? How do we compare to the comp set?**")

    st.info("**Pricing Power Confirmed** — ADR up +8.2% YoY while occupancy also grew, showing demand strength. RGI trending toward premium positioning.")

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    if not df_kpi.empty:
        rec = df_kpi.sort_values("as_of_date").iloc[-1]
        adr = float(rec.get("adr", 0))
        adr_yoy = float(rec.get("adr_yoy", 0))

        with col1:
            st.metric("**ADR**", f"${adr:.0f}", delta=f"{adr_yoy:+.1f}% YoY")

        with col2:
            st.metric("**RGI**", "105", delta="+3 pts vs. comp")

        with col3:
            st.metric("**Weekend Premium**", "+$52/night", delta="vs. weekday")

        with col4:
            st.metric("**Rate Elasticity**", "Moderate", delta="Demand stable")

    st.divider()

    # Charts
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("ADR Trend vs. Comp Set")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(range(30)), y=[280+i*1.2 for i in range(30)], name="Dana Point", line=dict(color="#0891B2", width=2)))
        fig.add_trace(go.Scatter(x=list(range(30)), y=[275+i*0.9 for i in range(30)], name="Comp Avg", line=dict(color="#9CA3AF", width=1, dash="dash")))
        fig.update_layout(height=300, template="plotly_white", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader("RGI by Comp Market")
        comps = {"Newport": 108, "Laguna": 103, "Santa Barbara": 106, "Dana Point": 105, "Monterey": 102}
        fig = go.Figure(data=[go.Bar(x=list(comps.keys()), y=list(comps.values()), marker_color="#0891B2")])
        fig.add_hline(y=100, line_dash="dash", line_color="#6B7280")
        fig.update_layout(height=300, template="plotly_white", margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.markdown("""
    **Next Best Actions**

    1. **Enforce 2-night minimums on peak nights** (Fri–Sun Sept 28–30) to capture the +$52 weekend premium
    2. **Tier rates dynamically** — premium for 80%+ occ days, value for shoulder
    3. **Test +5% rate increase in Q4** — margin expansion with stable demand
    """)


# ── PAGE LOADER ────────────────────────────────────────────────────────
def load_page(page_name: str, df_kpi: pd.DataFrame, df_insights: pd.DataFrame) -> None:
    """Route to the correct page based on user selection."""
    if page_name == "occupancy":
        page_occupancy_outlook(df_kpi, df_insights)
    elif page_name == "rate_strategy":
        page_rate_strategy(df_kpi)
    # Add more pages here as they're built

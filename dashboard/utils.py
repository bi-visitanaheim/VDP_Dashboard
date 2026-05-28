# =============================================================================
# Copyright (c) 2026 Wilton John Picou, GloCon Solutions LLC.
# All rights reserved. Proprietary and confidential.
#
# Authored, developed, and owned solely by Wilton John Picou of GloCon
# Solutions LLC. Licensed exclusively and perpetually to Visit Dana Point as
# the sole authorized user. No part of this software may be copied, reproduced,
# modified, published, distributed, sublicensed, or used by any other person or
# entity without the prior express written consent of the copyright holder.
# Unauthorized use, reproduction, or distribution is strictly prohibited and
# constitutes a violation of U.S. and international copyright law
# (17 U.S.C. Sec. 101 et seq.).
#
# Attribution to "Wilton John Picou, GloCon Solutions LLC" must be retained.
# See the LICENSE file at the repository root for the full, binding terms.
# =============================================================================

"""
VDP Dashboard Utilities — Consolidated helpers for KPI formatting, SQL queries, and logging.
GloCon Solutions LLC — Dana Point PULSE
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any

_logger = logging.getLogger("vdp_dashboard")

# Proprietary ownership notice — embedded for runtime reference. Do not remove.
COPYRIGHT_HOLDER = "Wilton John Picou, GloCon Solutions LLC"
COPYRIGHT_YEAR = 2026
SOLE_LICENSEE = "Visit Dana Point"
COPYRIGHT_NOTICE = (
    f"© {COPYRIGHT_YEAR} {COPYRIGHT_HOLDER}. All rights reserved. "
    f"Licensed exclusively to {SOLE_LICENSEE}. Proprietary and confidential."
)
LICENSE_SUMMARY = (
    f"Dana Point PULSE is authored and owned solely by {COPYRIGHT_HOLDER}, and "
    f"licensed exclusively and perpetually to {SOLE_LICENSEE} as the sole "
    f"authorized user. Unauthorized copying, modification, or distribution is "
    f"prohibited under U.S. and international copyright law. See LICENSE."
)


def format_hero_kpi_card(label: str, value: str, delta: str = "", delta_class: str = "neutral", color: str = "#00D4C8") -> str:
    """
    Unified KPI card formatter for hero metrics (4-column layout on main Overview tab).

    Args:
        label: KPI label (e.g., "RevPAR (30d)")
        value: Main metric value (e.g., "$145")
        delta: Optional delta text (e.g., "+2.5%")
        delta_class: CSS class ("up", "down", "neutral")
        color: Accent border color

    Returns:
        HTML string for the card
    """
    delta_html = ""
    if delta:
        delta_html = f'<div class="hero-metric-delta {delta_class}">{delta}</div>'

    return (
        f'<div class="hero-metric-card">'
        f'<div class="hero-metric-label">{label}</div>'
        f'<div class="hero-metric-value">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


def format_exec_kpi_banner(label: str, value: str, sub: str = "", color: str = "#00D4C8") -> str:
    """
    Unified KPI box formatter for board executive summary banner (9-box grid).
    Used in sub-tabs and detailed views.

    Args:
        label: KPI label
        value: Main value
        sub: Optional subtext
        color: Accent color

    Returns:
        HTML string for KPI box
    """
    return (
        f'<div style="flex:1;min-width:140px;max-width:220px;padding:14px 18px;'
        f'background:rgba(255,255,255,0.05);'
        f'border-radius:12px;border:1px solid rgba(255,255,255,0.10);'
        f'border-top:3px solid {color};'
        f'box-shadow:0 2px 8px rgba(0,0,0,0.20);">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.08em;'
        f'text-transform:uppercase;color:#8AAEC6;margin-bottom:5px;">{label}</div>'
        f'<div style="font-size:22px;font-weight:900;letter-spacing:-.03em;font-family:\'Outfit\',sans-serif;color:#FFFFFF;">{value}</div>'
        + (f'<div style="font-size:11px;font-weight:600;margin-top:4px;color:{color};">{sub}</div>' if sub else '')
        + '</div>'
    )


def format_section_header(icon: str, title: str, subtitle: str = "") -> str:
    """
    Premium section header formatter with consistent styling across all tabs.

    Args:
        icon: Emoji icon (e.g., "📊")
        title: Section title
        subtitle: Optional subtitle/description

    Returns:
        HTML string for section header
    """
    subtitle_html = f'<p style="font-size:13px;color:#8EC4DC;margin:6px 0 0 0;font-weight:500;">{subtitle}</p>' if subtitle else ''

    return f"""<div style="margin-bottom:28px;margin-top:0;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
    <span style="font-size:24px;">{icon}</span>
    <h2 style="
    font-family:'Outfit',sans-serif;
    font-size:24px;
    font-weight:800;
    letter-spacing:-0.01em;
    color:#F4FAFF;
    margin:0;
    ">{title}</h2>
    </div>
    {subtitle_html}
    </div>"""


def format_metric_card(label: str, value: str, icon: str = "", context: str = "") -> str:
    """
    Consistent metric card for use throughout dashboard tabs.

    Args:
        label: Metric label
        value: Metric value
        icon: Optional icon/emoji
        context: Optional context text

    Returns:
        HTML string for metric card
    """
    icon_html = f'<div style="font-size:22px;margin-bottom:8px;opacity:0.8;">{icon}</div>' if icon else ''
    context_html = f'<div style="font-size:11px;color:#8EC4DC;margin-top:8px;font-weight:500;">{context}</div>' if context else ''

    return f"""<div style="
    background:linear-gradient(135deg,rgba(0,212,200,0.08) 0%,rgba(56,189,248,0.04) 100%);
    border:1px solid rgba(0,212,200,0.25);
    border-top:3px solid #00D4C8;
    border-radius:12px;
    padding:20px;
    box-shadow:0 2px 12px rgba(0,0,0,0.12);
    ">
    {icon_html}
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#8EC4DC;margin-bottom:6px;">{label}</div>
    <div style="font-family:'Outfit',sans-serif;font-size:28px;font-weight:900;letter-spacing:-0.03em;color:#F4FAFF;line-height:1;">{value}</div>
    {context_html}
    </div>"""


def safe_sql_query(conn, query: str, params: tuple = ()) -> pd.DataFrame:
    """
    Execute SQL query with error logging (no silent failures).

    Args:
        conn: SQLite connection
        query: SQL query string
        params: Optional query parameters

    Returns:
        DataFrame with results, or empty DataFrame on error
    """
    try:
        result = pd.read_sql_query(query, conn, params=params)
        return result
    except Exception as e:
        _logger.debug(f"SQL query failed: {query[:100]}... Error: {str(e)}")
        return pd.DataFrame()


def combine_social_followers(conn) -> Dict[str, int]:
    """
    Fetch latest social followers from all platforms in one query.
    Replaces 3 separate queries with 1 round-trip.

    Args:
        conn: SQLite connection

    Returns:
        Dict with 'ig', 'fb', 'tk' follower counts
    """
    result = {
        "ig": 0,
        "fb": 0,
        "tk": 0,
    }

    try:
        # IG followers
        ig_row = pd.read_sql_query(
            "SELECT followers FROM later_ig_profile_growth WHERE followers IS NOT NULL ORDER BY data_date DESC LIMIT 1",
            conn
        )
        if not ig_row.empty:
            result["ig"] = int(ig_row.iloc[0, 0] or 0)

        # FB followers
        fb_row = pd.read_sql_query(
            "SELECT page_followers FROM later_fb_profile_growth WHERE page_followers IS NOT NULL ORDER BY data_date DESC LIMIT 1",
            conn
        )
        if not fb_row.empty:
            result["fb"] = int(fb_row.iloc[0, 0] or 0)

        # TK followers
        tk_row = pd.read_sql_query(
            "SELECT followers FROM later_tk_profile_growth WHERE followers IS NOT NULL ORDER BY data_date DESC LIMIT 1",
            conn
        )
        if not tk_row.empty:
            result["tk"] = int(tk_row.iloc[0, 0] or 0)

    except Exception as e:
        _logger.debug(f"Failed to fetch social followers: {str(e)}")

    return result


def safe_execute_with_logging(func, *args, **kwargs) -> Any:
    """
    Execute any function with error logging (no silent failures).

    Args:
        func: Callable to execute
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result of func, or None on error (with logging)
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        _logger.debug(f"Function {func.__name__} failed: {str(e)}")
        return None


def format_metric_delta(value: float, decimals: int = 1, as_percentage: bool = True) -> tuple:
    """
    Format a metric delta and return (formatted_string, css_class).

    Args:
        value: Delta value
        decimals: Number of decimal places
        as_percentage: If True, format as %, else as number

    Returns:
        Tuple of (formatted_string, css_class)
    """
    arrow = "▲" if value >= 0 else "▼"
    formatted = f"{arrow} {abs(value):.{decimals}f}{'%' if as_percentage else ''}"
    css_class = "up" if value >= 0 else "down"
    return formatted, css_class


def format_insight_card(icon: str, title: str, main_value: str, subtitle: str = "", body: str = "", accent_color: str = "#0284C7") -> str:
    """
    Format a styled insight card with metric highlight, supporting text, and visual hierarchy.

    Args:
        icon: Emoji icon (e.g., "💰")
        title: Card title (e.g., "Transient Occupancy Tax")
        main_value: Large metric value (e.g., "$3.6M")
        subtitle: Optional subtext below title (e.g., "90-day trailing")
        body: Supporting context paragraph
        accent_color: Left border color

    Returns:
        HTML string for the insight card
    """
    subtitle_html = f'<div style="font-size:12px;color:#64748B;margin-top:4px;font-weight:500;">{subtitle}</div>' if subtitle else ''
    body_html = f'<p style="font-size:13px;color:#334155;line-height:1.6;margin:16px 0 0 0;">{body}</p>' if body else ''

    return f"""<div style="
    background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px solid #E2E8F0;
    border-left: 4px solid {accent_color};
    border-radius: 12px;
    padding: 20px 24px;
    margin: 16px 0;
    box-shadow: 0 1px 3px rgba(15,23,42,0.12), 0 1px 2px rgba(15,23,42,0.24);
    ">
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
    <span style="font-size: 24px;">{icon}</span>
    <div>
    <h3 style="font-family: 'Outfit', sans-serif; font-size: 16px; font-weight: 800; color: #0F172A; margin: 0; letter-spacing: -0.01em;">{title}</h3>
    {subtitle_html}
    </div>
    </div>
    <div style="font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 900; letter-spacing: -0.03em; color: {accent_color}; margin: 8px 0;">{main_value}</div>
    {body_html}
    </div>"""

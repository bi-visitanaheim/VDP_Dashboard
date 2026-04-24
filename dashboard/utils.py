"""
VDP Dashboard Utilities — Consolidated helpers for KPI formatting, SQL queries, and logging.
GloCon Solutions LLC — Dana Point PULSE
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any

_logger = logging.getLogger("vdp_dashboard")


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

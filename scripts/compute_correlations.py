"""
compute_correlations.py
-----------------------
Computes statistical correlations between external economic/environmental signals
and Dana Point hotel performance metrics (occupancy, ADR, RevPAR).

Writes results to: correlations_str_context table
One row per (indicator_source, indicator_name, hotel_metric, lag_months) combo.

Run: python scripts/compute_correlations.py
Called by run_pipeline.py after all fetch steps, before build_table_relationships.
"""

import os
import sqlite3
import warnings
from datetime import datetime

import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore", category=stats.ConstantInputWarning)
warnings.filterwarnings("ignore", message=".*constant.*", category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "analytics.sqlite")
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

LAGS = [0, 1, 2, 3]  # months

HOTEL_METRICS = [
    ("occ_pct",         "Occupancy %",          "%"),
    ("adr",             "ADR ($/night)",         "$"),
    ("revpar",          "RevPAR ($/available)",  "$"),
    ("occ_pct_yoy_pp",  "Occupancy YoY (pp)",    "pp"),
    ("adr_yoy_pct",     "ADR YoY %",             "%"),
]

# Significance threshold for reporting
ALPHA = 0.10  # include up to p<0.10 in table; flag p<0.05 as confirmed


def _sig_label(p: float) -> str:
    if p < 0.01:
        return "p<0.01 ✓✓"
    if p < 0.05:
        return "p<0.05 ✓"
    if p < 0.10:
        return "p<0.10 ~"
    return "ns"


def _strength(r: float) -> str:
    a = abs(r)
    if a >= 0.65:
        return "Strong"
    if a >= 0.45:
        return "Moderate"
    if a >= 0.25:
        return "Weak"
    return "Negligible"


def _direction(r: float) -> str:
    if r > 0.10:
        return "positive"
    if r < -0.10:
        return "negative"
    return "neutral"


def _interpretation(ind_name: str, metric_label: str, r: float, lag: int, p: float) -> str:
    """Generate a plain-English interpretation of the correlation."""
    dir_word = "rises with" if r > 0 else "falls when"
    strength = _strength(r)
    if strength == "Negligible":
        return f"No meaningful relationship found between {ind_name} and {metric_label}."

    lag_clause = ""
    if lag == 0:
        lag_clause = "in the same month"
    elif lag == 1:
        lag_clause = "1 month later"
    else:
        lag_clause = f"{lag} months later"

    sig_note = " (statistically significant)" if p < 0.05 else " (trend, p<0.10)" if p < 0.10 else ""
    return (
        f"{strength} signal{sig_note}: hotel {metric_label} {dir_word} {ind_name} "
        f"{lag_clause} (r={r:+.2f}). "
        + _action_note(ind_name, metric_label, r, lag)
    )


def _action_note(ind_name: str, metric_label: str, r: float, lag: int) -> str:
    """Generate a brief action-oriented note for dashboard display."""
    notes = {
        ("Gas Prices", "Occupancy %"):     "High gas prices suppress weekend drive-market demand.",
        ("Gas Prices", "ADR ($/night)"):   "Rate sensitivity increases when drive-market guests face cost pressure.",
        ("Beach Day Score", "Occupancy %"):"Ideal beach conditions pull demand — compress rates on 90+ score days.",
        ("Water Temp (°F)", "Occupancy %"):"Warmer water correlates with higher leisure hotel demand.",
        ("Consumer Sentiment", "ADR ($/night)"): "Confident consumers accept higher room rates.",
        ("Consumer Sentiment", "Occupancy %"):   "Travel intent rises with consumer confidence — activate campaigns.",
        ("Unemployment Rate", "Occupancy %"):    "Lower unemployment historically precedes 6–12 month occ recovery.",
        ("Disposable Income", "ADR ($/night)"):  "Real income growth supports rate expansion.",
        ("TSA Throughput", "Occupancy %"):       "Air travel surge signals fly-market demand 2–4 weeks out.",
        ("Booking Intent (hotel)", "Occupancy %"): "Search demand predicts bookings — increase CPC bids when trending up.",
        ("Booking Intent (beach)", "Occupancy %"): "Beach interest signals leisure demand — activate social campaigns.",
        ("CA L&H Employment", "ADR ($/night)"):  "Tight hospitality labor market correlates with higher achievable rates.",
        ("CA Accommodation Empl.", "Occupancy %"): "CA accommodation employment tracks regional hotel capacity and demand.",
        ("Lodging CPI", "ADR ($/night)"):         "ADR tracking above Lodging CPI = real rate gain; below = losing ground.",
    }
    for (k_ind, k_metric), note in notes.items():
        if k_ind.lower() in ind_name.lower() and k_metric.lower() in metric_label.lower():
            return note
    return ""


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_monthly_kpi(conn: sqlite3.Connection) -> pd.DataFrame:
    """Aggregate daily KPI to monthly mean — primary hotel signal."""
    df = pd.read_sql_query(
        "SELECT as_of_date, occ_pct, adr, revpar, occ_pct_yoy_pp, adr_yoy_pct, revpar_yoy_pct "
        "FROM kpi_daily_summary WHERE occ_pct IS NOT NULL",
        conn,
    )
    if df.empty:
        return df
    df["as_of_date"] = pd.to_datetime(df["as_of_date"])
    df["year"]  = df["as_of_date"].dt.year
    df["month"] = df["as_of_date"].dt.month
    monthly = df.groupby(["year", "month"]).agg(
        occ_pct        =("occ_pct",         "mean"),
        adr            =("adr",             "mean"),
        revpar         =("revpar",           "mean"),
        occ_pct_yoy_pp =("occ_pct_yoy_pp",  "mean"),
        adr_yoy_pct    =("adr_yoy_pct",     "mean"),
        revpar_yoy_pct =("revpar_yoy_pct",  "mean"),
    ).reset_index()
    monthly["date"] = pd.to_datetime(monthly[["year", "month"]].assign(day=1))
    return monthly.sort_values("date").reset_index(drop=True)


def load_gas_monthly(conn: sqlite3.Connection) -> list[dict]:
    """CA gas prices aggregated to monthly average."""
    df = pd.read_sql_query(
        "SELECT week_end_date, price_per_gallon FROM eia_gas_prices WHERE state_label='CA'",
        conn,
    )
    if df.empty:
        return []
    df["week_end_date"] = pd.to_datetime(df["week_end_date"])
    df["year"]  = df["week_end_date"].dt.year
    df["month"] = df["week_end_date"].dt.month
    m = df.groupby(["year", "month"])["price_per_gallon"].mean().reset_index()
    m["date"] = pd.to_datetime(m[["year", "month"]].assign(day=1))
    m = m.rename(columns={"price_per_gallon": "value"})
    m["indicator_source"] = "eia_gas"
    m["indicator_name"]   = "CA Gas Prices ($/gal)"
    m["display_name"]     = "Gas Prices"
    return [m]


def load_weather_monthly(conn: sqlite3.Connection) -> list[dict]:
    """Weather monthly — beach day score and temperature."""
    df = pd.read_sql_query(
        "SELECT year, month, beach_day_score, avg_temp_f FROM weather_monthly",
        conn,
    )
    if df.empty:
        return []
    df["date"] = pd.to_datetime(df[["year", "month"]].assign(day=1))
    out = []
    for col, name, disp in [
        ("beach_day_score", "Beach Day Score (/100)", "Beach Day Score"),
        ("avg_temp_f",      "Avg Temperature (°F)",   "Avg Temp (°F)"),
    ]:
        if col in df.columns and df[col].notna().sum() >= 5:
            m = df[["date", "year", "month", col]].rename(columns={col: "value"}).copy()
            m["indicator_source"] = "weather"
            m["indicator_name"]   = name
            m["display_name"]     = disp
            out.append(m)
    return out


def load_bls_monthly(conn: sqlite3.Connection) -> list[dict]:
    """BLS hospitality employment — CA series as regional proxy."""
    df = pd.read_sql_query(
        "SELECT series_name, geo, year, month, value_thousands FROM bls_employment_monthly",
        conn,
    )
    if df.empty:
        return []
    df["date"] = pd.to_datetime(df[["year", "month"]].assign(day=1))
    out = []
    for (geo, sname), g in df.groupby(["geo", "series_name"]):
        if len(g) < 8:
            continue
        short_names = {
            "US Leisure & Hospitality Employment": "US L&H Employment",
            "US Accommodation & Food Services Employment": "US Accommodation Empl.",
            "CA Leisure & Hospitality Employment": "CA L&H Employment",
            "CA Accommodation Employment": "CA Accommodation Empl.",
        }
        disp = short_names.get(sname, sname[:30])
        m = g[["date", "year", "month", "value_thousands"]].rename(columns={"value_thousands": "value"}).copy()
        m["indicator_source"] = "bls"
        m["indicator_name"]   = f"{sname} (thousands)"
        m["display_name"]     = disp
        out.append(m)
    return out


def load_fred_monthly(conn: sqlite3.Connection) -> list[dict]:
    """FRED economic indicators — key consumer and economic series."""
    INCLUDE_SERIES = {
        "CUUR0000SEHB": "Lodging CPI",
        "DSPIC96":      "Disposable Income",
        "UNRATE":       "Unemployment Rate",
        "UMCSENT":      "Consumer Sentiment",
        "CPALTT01USM657N": "Core CPI",
        "CEU7000000001":   "US L&H Employment (FRED)",
    }
    df = pd.read_sql_query(
        "SELECT series_id, series_name, data_date, value FROM fred_economic_indicators",
        conn,
    )
    if df.empty:
        return []
    df["data_date"] = pd.to_datetime(df["data_date"])
    df["year"]  = df["data_date"].dt.year
    df["month"] = df["data_date"].dt.month
    df["date"]  = pd.to_datetime(df[["year", "month"]].assign(day=1))
    out = []
    for sid, g in df.groupby("series_id"):
        if len(g) < 8:
            continue
        sname = g["series_name"].iloc[0]
        disp  = INCLUDE_SERIES.get(sid, sname[:30])
        m = g[["date", "year", "month", "value"]].copy().rename(columns={"value": "value"})
        m["indicator_source"] = "fred"
        m["indicator_name"]   = sname
        m["display_name"]     = disp
        out.append(m)
    return out


def load_trends_monthly(conn: sqlite3.Connection) -> list[dict]:
    """Google Trends search demand — aggregate weekly to monthly."""
    df = pd.read_sql_query(
        "SELECT term, week_date, interest_idx FROM google_trends_weekly",
        conn,
    )
    if df.empty:
        return []
    df["week_date"] = pd.to_datetime(df["week_date"])
    df["year"]  = df["week_date"].dt.year
    df["month"] = df["week_date"].dt.month
    KEY_TERMS = {
        "dana point hotel": "Booking Intent (hotel)",
        "dana point beach": "Booking Intent (beach)",
        "visit dana point": "Destination Intent",
        "dana point":       "Brand Awareness",
    }
    out = []
    for term, g in df.groupby("term"):
        if len(g) < 4:
            continue
        m = g.groupby(["year", "month"])["interest_idx"].mean().reset_index()
        m["date"] = pd.to_datetime(m[["year", "month"]].assign(day=1))
        m = m.rename(columns={"interest_idx": "value"})
        disp = KEY_TERMS.get(term.lower(), f"Trends: {term}")
        m["indicator_source"] = "google_trends"
        m["indicator_name"]   = f"Google Trends: {term}"
        m["display_name"]     = disp
        out.append(m)
    return out


def load_tsa_monthly(conn: sqlite3.Connection) -> list[dict]:
    """TSA checkpoint throughput — air travel demand proxy."""
    df = pd.read_sql_query(
        "SELECT travel_date, travelers_count FROM tsa_checkpoint_daily",
        conn,
    )
    if df.empty:
        return []
    df["travel_date"] = pd.to_datetime(df["travel_date"])
    df["year"]  = df["travel_date"].dt.year
    df["month"] = df["travel_date"].dt.month
    m = df.groupby(["year", "month"])["travelers_count"].mean().reset_index()
    m["date"] = pd.to_datetime(m[["year", "month"]].assign(day=1))
    m = m.rename(columns={"travelers_count": "value"})
    m["indicator_source"] = "tsa"
    m["indicator_name"]   = "TSA Checkpoint Throughput"
    m["display_name"]     = "TSA Throughput"
    return [m]


def load_noaa_monthly(conn: sqlite3.Connection) -> list[dict]:
    """NOAA ocean conditions — beach activity and water temperature."""
    df = pd.read_sql_query(
        "SELECT year, month, beach_activity_score, avg_water_temp_f FROM noaa_marine_monthly",
        conn,
    )
    if df.empty or len(df) < 4:
        return []
    df["date"] = pd.to_datetime(df[["year", "month"]].assign(day=1))
    out = []
    for col, name, disp in [
        ("beach_activity_score", "NOAA Beach Activity Score", "Beach Activity Score"),
        ("avg_water_temp_f",     "Ocean Water Temp (°F)",     "Water Temp (°F)"),
    ]:
        if col in df.columns and df[col].notna().sum() >= 4:
            m = df[["date", "year", "month", col]].rename(columns={col: "value"}).copy()
            m["indicator_source"] = "noaa"
            m["indicator_name"]   = name
            m["display_name"]     = disp
            out.append(m)
    return out


# ---------------------------------------------------------------------------
# Correlation engine
# ---------------------------------------------------------------------------

def compute_lag_correlations(
    kpi_monthly: pd.DataFrame,
    indicator_df: pd.DataFrame,
    metric_col: str,
    lag: int,
) -> tuple[float, float, int]:
    """
    Shift indicator backward by `lag` months so indicator[t-lag] aligns with kpi[t].
    Returns (pearson_r, p_value, n_obs).
    """
    ind = indicator_df[["date", "value"]].dropna(subset=["value"]).copy()
    ind = ind.rename(columns={"value": "ind_value"})

    kpi = kpi_monthly[["date", metric_col]].dropna(subset=[metric_col]).copy()

    # Shift indicator forward so that indicator at date d matches hotel at d+lag
    if lag > 0:
        ind = ind.copy()
        ind["date"] = ind["date"] + pd.DateOffset(months=lag)

    merged = pd.merge(kpi, ind, on="date", how="inner")
    if len(merged) < 5:
        return float("nan"), float("nan"), 0

    r, p = stats.pearsonr(merged["ind_value"], merged[metric_col])
    return float(r), float(p), int(len(merged))


def run_all_correlations(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load all indicators, compute lag correlations vs all hotel metrics."""
    print(f"  [compute_correlations] Loading monthly KPIs...")
    kpi = load_monthly_kpi(conn)
    if kpi.empty:
        print("  [compute_correlations] No KPI data — skipping.")
        return pd.DataFrame()

    print(f"  [compute_correlations] KPI range: {kpi['date'].min().date()} to {kpi['date'].max().date()}")

    print(f"  [compute_correlations] Loading indicators...")
    all_indicators: list[dict] = []
    all_indicators += load_gas_monthly(conn)
    all_indicators += load_weather_monthly(conn)
    all_indicators += load_bls_monthly(conn)
    all_indicators += load_fred_monthly(conn)
    all_indicators += load_trends_monthly(conn)
    all_indicators += load_tsa_monthly(conn)
    all_indicators += load_noaa_monthly(conn)

    print(f"  [compute_correlations] {len(all_indicators)} indicator series loaded.")

    rows = []
    for ind_df in all_indicators:
        ind_df = ind_df.copy()
        ind_df["date"] = pd.to_datetime(ind_df["date"])
        src   = ind_df["indicator_source"].iloc[0]
        name  = ind_df["indicator_name"].iloc[0]
        disp  = ind_df["display_name"].iloc[0]

        for metric_col, metric_label, metric_unit in HOTEL_METRICS:
            if metric_col not in kpi.columns:
                continue
            for lag in LAGS:
                r, p, n = compute_lag_correlations(kpi, ind_df, metric_col, lag)
                if n < 5 or pd.isna(r):
                    continue
                rows.append({
                    "indicator_source": src,
                    "indicator_name":   name,
                    "display_name":     disp,
                    "hotel_metric":     metric_col,
                    "metric_label":     metric_label,
                    "metric_unit":      metric_unit,
                    "lag_months":       lag,
                    "pearson_r":        round(r, 4),
                    "p_value":          round(p, 4),
                    "significance":     _sig_label(p),
                    "n_observations":   n,
                    "direction":        _direction(r),
                    "signal_strength":  _strength(r),
                    "interpretation":   _interpretation(disp, metric_label, r, lag, p),
                    "date_from":        kpi["date"].min().strftime("%Y-%m"),
                    "date_to":          kpi["date"].max().strftime("%Y-%m"),
                    "computed_at":      NOW,
                })

    df = pd.DataFrame(rows)
    print(f"  [compute_correlations] {len(df)} correlation records computed.")
    return df


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------

def init_table(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS correlations_str_context")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS correlations_str_context (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_source TEXT    NOT NULL,
            indicator_name   TEXT    NOT NULL,
            display_name     TEXT    NOT NULL,
            hotel_metric     TEXT    NOT NULL,
            metric_label     TEXT    NOT NULL,
            metric_unit      TEXT,
            lag_months       INTEGER NOT NULL,
            pearson_r        REAL,
            p_value          REAL,
            significance     TEXT,
            n_observations   INTEGER,
            direction        TEXT,
            signal_strength  TEXT,
            interpretation   TEXT,
            date_from        TEXT,
            date_to          TEXT,
            computed_at      TEXT    NOT NULL,
            UNIQUE(indicator_source, indicator_name, hotel_metric, lag_months)
        )
    """)
    conn.commit()


def upsert_correlations(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    cols = [
        "indicator_source", "indicator_name", "display_name",
        "hotel_metric", "metric_label", "metric_unit",
        "lag_months", "pearson_r", "p_value", "significance",
        "n_observations", "direction", "signal_strength",
        "interpretation", "date_from", "date_to", "computed_at",
    ]
    records = [tuple(row[c] for c in cols) for _, row in df.iterrows()]
    conn.executemany(
        f"""INSERT OR REPLACE INTO correlations_str_context
            ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})""",
        records,
    )
    conn.commit()
    return len(records)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"[compute_correlations] Starting — {NOW}")
    conn = sqlite3.connect(DB_PATH, timeout=15)

    try:
        init_table(conn)
        df = run_all_correlations(conn)
        n  = upsert_correlations(conn, df)
        print(f"[compute_correlations] Done — {n} correlation records written to correlations_str_context.")

        if not df.empty:
            top = (
                df[df["hotel_metric"] == "occ_pct"]
                .assign(abs_r=df["pearson_r"].abs())
                .nlargest(5, "abs_r")[["display_name", "lag_months", "pearson_r", "p_value", "signal_strength"]]
            )
            print("\n  Top 5 signals for Occupancy:")
            for _, row in top.iterrows():
                print(f"    lag={row['lag_months']}mo  r={row['pearson_r']:+.3f}  {row['signal_strength']}  {row['display_name']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "analytics.sqlite")
# STR raw exports live in data/str/  (legacy path: downloads/str_monthly.xlsx)
STR_DIR = os.path.join(PROJECT_ROOT, "data", "str")
MONTHLY_FILE = os.path.join(STR_DIR, "str_monthly.xlsx")


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, timeout=10)


def normalize_str_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize STR monthly export (downloads/str_monthly.xlsx) into fact_str_metrics long format.

    NOTE: Occupancy stored as decimal in fact_str_metrics (0.688 = 68.8%).
    kpi_daily_summary multiplies by 100 to get occ_pct for display.
    """
    date_col = "Period"

    # Map file columns -> (metric_name_in_db, unit)
    metric_columns = {
        "Supply": ("supply", "rooms"),
        "Demand": ("demand", "rooms"),
        "Revenue": ("revenue", "USD"),
        "Occ": ("occ", "decimal"),   # stored as 0.0–1.0 decimal
        "Occ %": ("occ", "decimal"),
        "ADR": ("adr", "USD"),
        "RevPAR": ("revpar", "USD"),
    }

    if date_col not in df.columns:
        raise ValueError(f"Missing expected STR column '{date_col}'")

    df = df.copy()

    # Parse Period to YYYY-MM-DD; coerce bad dates to NaT and warn
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    nat_count = df[date_col].isna().sum()
    if nat_count:
        print(f"  WARNING: {nat_count} rows have unparseable dates and will be dropped")
        df = df.dropna(subset=[date_col])
    df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")

    # Clean metrics: trim, treat "-" as missing, coerce to numeric
    for col_name in metric_columns.keys():
        if col_name in df.columns:
            s = df[col_name].astype(str).str.strip().replace("-", None)
            df[col_name] = pd.to_numeric(s, errors="coerce")

    frames = []

    for col_name, (metric_name, unit) in metric_columns.items():
        if col_name not in df.columns:
            continue

        tmp = df[[date_col, col_name]].copy()
        tmp.rename(columns={col_name: "metric_value"}, inplace=True)
        tmp["metric_name"] = metric_name
        tmp["unit"] = unit
        tmp["grain"] = "monthly"
        tmp["source"] = "STR"
        tmp["property_name"] = "VDP Select Portfolio"
        tmp["market"] = "Anaheim Area"
        tmp["submarket"] = None
        tmp.rename(columns={date_col: "as_of_date"}, inplace=True)
        frames.append(tmp)

    if not frames:
        raise ValueError("No known metric columns found in STR monthly export")

    out = pd.concat(frames, ignore_index=True)

    # Final column order expected by fact_str_metrics
    out = out[
        [
            "source",
            "grain",
            "property_name",
            "market",
            "submarket",
            "as_of_date",
            "metric_name",
            "metric_value",
            "unit",
        ]
    ]

    return out


def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_str_monthly(path: str, conn: sqlite3.Connection) -> int:
    if not os.path.exists(path):
        print(f"File not found, skipping: {path}")
        return 0

    print(f"Loading STR monthly file: {path}")
    df = pd.read_excel(path, engine="openpyxl")
    norm_df = normalize_str_monthly(df)

    cur = conn.cursor()

    # Bulk dedup: load all monthly keys in one query instead of N queries
    existing = set(
        cur.execute(
            "SELECT source, grain, property_name, market, as_of_date, metric_name "
            "FROM fact_str_metrics WHERE grain = 'monthly'"
        ).fetchall()
    )

    rows_to_insert = []
    for _, row in norm_df.iterrows():
        key = (
            row["source"],
            row["grain"],
            row["property_name"],
            row["market"],
            row["as_of_date"],
            row["metric_name"],
        )
        if key in existing:
            continue

        val = safe_float(row["metric_value"])
        # Preserve NULL for missing values; do not floor negative values to 0
        # (negative revenue/demand indicates data quality issue — log, don't mask)
        if val is not None and val < 0:
            print(
                f"  WARNING: Negative {row['metric_name']} value ({val}) "
                f"on {row['as_of_date']} — storing as NULL"
            )
            val = None

        rows_to_insert.append((
            row["source"],
            row["grain"],
            row["property_name"],
            row["market"],
            row["submarket"],
            row["as_of_date"],
            row["metric_name"],
            val,
            row["unit"],
        ))

    if rows_to_insert:
        cur.executemany(
            """
            INSERT INTO fact_str_metrics (
                source, grain, property_name, market, submarket,
                as_of_date, metric_name, metric_value, unit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )

    rows_inserted = len(rows_to_insert)
    conn.commit()

    cur.execute(
        "INSERT INTO load_log (source, grain, file_name, rows_inserted) VALUES (?, ?, ?, ?)",
        ("STR", "monthly", os.path.basename(path), rows_inserted),
    )
    conn.commit()

    print(f"Inserted {rows_inserted} new monthly rows from {os.path.basename(path)}")
    return rows_inserted


def main() -> None:
    conn = get_connection()
    try:
        rows = load_str_monthly(MONTHLY_FILE, conn)
        print(f"Done. Monthly rows inserted: {rows}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

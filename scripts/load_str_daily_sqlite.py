import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

DB_PATH = os.path.join(PROJECT_ROOT, "data", "analytics.sqlite")
STR_DIR = os.path.join(PROJECT_ROOT, "data", "str")
# Primary file (legacy / manual drop)
DAILY_FILE = os.path.join(STR_DIR, "str_daily.xlsx")
# Dropbox-synced weekly exports land here (multiple files, any # of sheets)
WEEKLY_DIR = os.path.join(STR_DIR, "weekly")


def get_connection():
    return sqlite3.connect(DB_PATH, timeout=10)


def normalize_str_daily(df):
    """
    Normalize STR DAILY export with columns:
    ['Period', 'Day of Week', 'Supply', 'Supply Chg (YOY)', 'Demand',
     'Demand Chg (YOY)', 'Revenue', 'Revenue Chg (YOY)', 'Occupancy',
     'Occupancy Chg (YOY)', 'ADR', 'ADR Chg (YOY)', 'RevPAR',
     'RevPAR Chg (YOY)', ...]

    NOTE: Occupancy stored as decimal in fact_str_metrics (0.688 = 68.8%).
    kpi_daily_summary multiplies by 100 to get occ_pct for display.
    """
    date_col = "Period"

    metric_columns = {
        "Supply": ("supply", "rooms"),
        "Demand": ("demand", "rooms"),
        "Revenue": ("revenue", "USD"),
        "Occupancy": ("occ", "decimal"),  # stored as 0.0–1.0 decimal
        "ADR": ("adr", "USD"),
        "RevPAR": ("revpar", "USD"),
    }

    required = [date_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected STR columns: {missing}")

    df = df.copy()

    # Parse dates with coerce so malformed values become NaT instead of crashing
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    nat_count = df[date_col].isna().sum()
    if nat_count:
        print(f"  WARNING: {nat_count} rows have unparseable dates and will be dropped")
        df = df.dropna(subset=[date_col])
    df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")

    long_frames = []
    for col_name, (metric_name, unit) in metric_columns.items():
        if col_name not in df.columns:
            continue

        tmp = df[[date_col, col_name]].copy()
        tmp.rename(columns={col_name: "metric_value"}, inplace=True)
        tmp["metric_name"] = metric_name
        tmp["unit"] = unit
        tmp["grain"] = "daily"
        tmp["source"] = "STR"
        tmp["property_name"] = "VDP Select Portfolio"
        tmp["market"] = "Anaheim Area"
        tmp["submarket"] = None
        tmp.rename(columns={date_col: "as_of_date"}, inplace=True)
        long_frames.append(tmp)

    if not long_frames:
        raise ValueError("No known metric columns found in STR daily export")

    long_df = pd.concat(long_frames, ignore_index=True)
    return long_df[
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


def _collect_daily_dataframes() -> list[pd.DataFrame]:
    """Collect raw dataframes from all STR daily/weekly sources.

    Sources (in priority order):
      1. data/str/weekly/*.xlsx  — Dropbox-synced weekly exports (all sheets)
      2. data/str/str_daily.xlsx — legacy single-file fallback
    """
    frames = []

    # Source 1: Dropbox weekly directory (multiple files, all sheets)
    if os.path.isdir(WEEKLY_DIR):
        xlsx_files = sorted(
            f for f in os.listdir(WEEKLY_DIR) if f.lower().endswith(".xlsx")
        )
        for fname in xlsx_files:
            fpath = os.path.join(WEEKLY_DIR, fname)
            try:
                xl = pd.ExcelFile(fpath, engine="openpyxl")
                for sheet in xl.sheet_names:
                    try:
                        df = xl.parse(sheet)
                        if "Period" in df.columns:
                            frames.append((fpath, sheet, df))
                        else:
                            print(f"  SKIP sheet '{sheet}' in {fname} — no 'Period' column")
                    except Exception as e:
                        print(f"  WARN: could not parse sheet '{sheet}' in {fname}: {e}")
            except Exception as e:
                print(f"  WARN: could not open {fname}: {e}")

    # Source 2: Legacy single file
    if os.path.exists(DAILY_FILE):
        try:
            xl = pd.ExcelFile(DAILY_FILE, engine="openpyxl")
            for sheet in xl.sheet_names:
                try:
                    df = xl.parse(sheet)
                    if "Period" in df.columns:
                        frames.append((DAILY_FILE, sheet, df))
                except Exception as e:
                    print(f"  WARN: could not parse sheet '{sheet}' in str_daily.xlsx: {e}")
        except Exception as e:
            print(f"  WARN: could not open str_daily.xlsx: {e}")

    return frames


def load_str_daily(conn):
    sources = _collect_daily_dataframes()
    if not sources:
        print(f"No STR daily data found in {WEEKLY_DIR}/ or {DAILY_FILE} — skipping")
        return 0

    print(f"Loading STR daily data: {len(sources)} sheet(s) across {len(set(s[0] for s in sources))} file(s)")

    all_norm = []
    for fpath, sheet, df in sources:
        fname = os.path.basename(fpath)
        try:
            norm_df = normalize_str_daily(df)
            all_norm.append(norm_df)
            print(f"  {fname} [{sheet}] → {len(norm_df)} rows")
        except Exception as e:
            print(f"  WARN: normalize failed for {fname} [{sheet}]: {e}")

    if not all_norm:
        print("  No normalizable data found — skipping")
        return 0

    norm_df = pd.concat(all_norm, ignore_index=True).drop_duplicates()

    cursor = conn.cursor()

    # Bulk dedup: load existing composite keys in one query instead of N queries
    existing = set(
        cursor.execute(
            "SELECT source, grain, property_name, market, as_of_date, metric_name "
            "FROM fact_str_metrics WHERE grain = 'daily'"
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
        val = row["metric_value"]
        try:
            val = float(val) if pd.notna(val) else None
        except (TypeError, ValueError):
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
        cursor.executemany(
            """
            INSERT INTO fact_str_metrics
            (source, grain, property_name, market, submarket,
             as_of_date, metric_name, metric_value, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )

    rows_inserted = len(rows_to_insert)
    conn.commit()

    file_label = f"weekly_dir({len(sources)} files)" if sources else os.path.basename(DAILY_FILE)
    cursor.execute(
        """
        INSERT INTO load_log (source, grain, file_name, rows_inserted)
        VALUES (?, ?, ?, ?)
        """,
        ("STR", "daily", file_label, rows_inserted),
    )
    conn.commit()

    print(f"Inserted {rows_inserted} new daily rows ({file_label})")
    return rows_inserted


def main():
    conn = get_connection()
    try:
        daily_rows = load_str_daily(conn)
        print(f"Done. Daily rows inserted: {daily_rows}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

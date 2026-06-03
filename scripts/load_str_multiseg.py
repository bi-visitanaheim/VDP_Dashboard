"""
load_str_multiseg.py

Loads multi-segment STR data (Transient, Group, Contract) from weekly and monthly files.
Extracts all tabs and segments, creates fact_str_group_metrics table.

Structure:
  Multi Seg Seg sheet (normalized):
    Row 0: Property name
    Row 1: Date range (weekly: "For the Week of X to Y"; monthly: month/year)
    Row 5: Section headers
    Row 6: Metric names (Occupancy %, ADR, RevPAR)
    Row 7: Segment columns (Trans., Grp., Cont., Total)
    Row 8+: Data for each property

Output table: fact_str_group_metrics
  (source, grain, as_of_date, property, market, segment,
   metric_name, metric_value, unit)
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent

DB_PATH = PROJECT_ROOT / "data" / "analytics.sqlite"
WEEKLY_DIR = PROJECT_ROOT / "data" / "str" / "weekly"
MONTHLY_DIR = PROJECT_ROOT / "data" / "str" / "monthly"


def get_connection():
    return sqlite3.connect(DB_PATH, timeout=10)


def ensure_table(conn):
    """Create fact_str_group_metrics table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fact_str_group_metrics (
            source        TEXT NOT NULL,
            grain         TEXT NOT NULL,
            as_of_date    TEXT NOT NULL,
            property      TEXT NOT NULL,
            market        TEXT NOT NULL,
            segment       TEXT NOT NULL,
            metric_name   TEXT NOT NULL,
            metric_value  REAL,
            unit          TEXT NOT NULL,
            UNIQUE(source, grain, as_of_date, property, segment, metric_name)
                ON CONFLICT REPLACE
        )
    """)
    conn.commit()


def extract_date_from_weekly(date_str):
    """Parse 'For the Week of April 26, 2026 to May 02, 2026' → '2026-04-26'."""
    if not date_str or "For the Week of" not in str(date_str):
        return None
    try:
        parts = str(date_str).split("to")
        start_part = parts[0].replace("For the Week of", "").strip()
        return pd.to_datetime(start_part).strftime("%Y-%m-%d")
    except:
        return None


def extract_date_from_monthly(date_str):
    """Parse month/year from filename or sheet like 'April 2026' → '2026-04-01'."""
    if not date_str:
        return None
    try:
        dt = pd.to_datetime(date_str, format="%B %Y", errors="coerce")
        if pd.isna(dt):
            dt = pd.to_datetime(date_str, errors="coerce")
        return dt.strftime("%Y-%m-%d") if not pd.isna(dt) else None
    except:
        return None


def parse_multiseg_sheet(df, grain):
    """
    Parse 'Multi Seg Seg' sheet with proper column mapping.

    Structure:
      Row 1: Date range
      Row 6: Metric names (Occupancy (%), ADR, RevPAR, repeated for sections)
      Row 7: Segment names (Trans., Grp., Cont., Total, repeated)
      Row 8+: Data by property

    Column layout (Current Week section):
      Col 1: Property name
      Cols 2-5: Trans./Grp./Cont./Total Occupancy (%)
      Cols 6-9: Trans./Grp./Cont./Total ADR
      Cols 10-13: Trans./Grp./Cont./Total RevPAR
      Col 14: Separator (NaN)
      Cols 15-28: Same metrics for Percent Change section
    """
    results = []

    if len(df) < 8:
        return results

    # Extract date from row 1
    date_str = df.iloc[1, 1]
    if grain == "daily":
        as_of_date = extract_date_from_weekly(date_str)
    else:
        as_of_date = extract_date_from_monthly(date_str)

    if not as_of_date:
        return results

    # Extract segment names from row 7 (columns 2-5 are Trans., Grp., Cont., Total)
    segments = []
    for col_idx in range(2, 6):
        seg = df.iloc[7, col_idx]
        if pd.notna(seg):
            segments.append(str(seg).strip())

    if not segments or len(segments) < 4:
        segments = ["Trans.", "Grp.", "Cont.", "Total"]

    # Map metrics: Occ% (cols 2-5), ADR (cols 6-9), RevPAR (cols 10-13)
    # The sections repeat for "Current Week" and "Percent Change", separated by NaN at col 14
    metrics = ["Occupancy (%)", "ADR", "RevPAR"]
    metric_col_starts = [2, 6, 10]  # Where each metric starts

    # Parse data rows (row 8 onwards)
    for row_idx in range(8, len(df)):
        property_name = df.iloc[row_idx, 1]
        if pd.isna(property_name) or property_name == "":
            continue

        property_name = str(property_name).strip()

        # Extract current week metrics (cols 2-13)
        for metric_idx, metric_name in enumerate(metrics):
            col_start = metric_col_starts[metric_idx]
            for seg_idx, segment in enumerate(segments):
                col = col_start + seg_idx
                if col < len(df.columns):
                    val = df.iloc[row_idx, col]
                    try:
                        val = float(val) if pd.notna(val) else None
                    except (TypeError, ValueError):
                        val = None

                    if val is not None:
                        results.append({
                            "as_of_date": as_of_date,
                            "property": property_name,
                            "segment": segment,
                            "metric_name": metric_name,
                            "metric_value": val,
                        })

    return results


def load_file(fpath, grain, conn):
    """Load a single .xls/.xlsx file."""
    fname = os.path.basename(fpath)
    engine = "xlrd" if fpath.endswith(".xls") else "openpyxl"

    try:
        xl = pd.ExcelFile(fpath, engine=engine)
    except Exception as e:
        print(f"  WARN: could not open {fname}: {e}")
        return 0

    rows_inserted = 0

    # Parse the multi-segment sheets
    for sheet_name in ["Multi Seg Seg", "Multi-Seg Seg Raw"]:
        if sheet_name not in xl.sheet_names:
            continue

        try:
            df = xl.parse(sheet_name)
            records = parse_multiseg_sheet(df, grain)

            for rec in records:
                try:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO fact_str_group_metrics
                        (source, grain, as_of_date, property, market, segment,
                         metric_name, metric_value, unit)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "STR",
                            grain,
                            rec["as_of_date"],
                            rec["property"],
                            "Anaheim Area",  # Market
                            rec["segment"],
                            rec["metric_name"],
                            rec["metric_value"],
                            "%" if rec["metric_name"] == "Occupancy (%)" else "USD",
                        ),
                    )
                    rows_inserted += 1
                except Exception as e:
                    print(f"    WARN: insert failed for {rec}: {e}")

            conn.commit()
            print(f"  {fname} [{sheet_name}] → {len(records)} records")

        except Exception as e:
            print(f"  WARN: could not parse {sheet_name} in {fname}: {e}")

    return rows_inserted


def main():
    conn = get_connection()
    ensure_table(conn)

    total_inserted = 0

    # Load weekly files (grain='daily')
    if WEEKLY_DIR.exists():
        print("\nLoading STR multi-segment WEEKLY files...")
        for fname in sorted(f for f in os.listdir(WEEKLY_DIR) if f.endswith((".xlsx", ".xls"))):
            fpath = WEEKLY_DIR / fname
            rows = load_file(str(fpath), "daily", conn)
            total_inserted += rows

    # Load monthly files (grain='monthly')
    if MONTHLY_DIR.exists():
        print("\nLoading STR multi-segment MONTHLY files...")
        for fname in sorted(f for f in os.listdir(MONTHLY_DIR) if f.endswith((".xlsx", ".xls"))):
            fpath = MONTHLY_DIR / fname
            rows = load_file(str(fpath), "monthly", conn)
            total_inserted += rows

    # Log the load
    try:
        conn.execute(
            "INSERT INTO load_log (source, grain, file_name, rows_inserted) VALUES (?, ?, ?, ?)",
            ("STR", "multiseg", "multiseg_weekly+monthly", total_inserted),
        )
        conn.commit()
    except:
        pass

    print(f"\nTotal multi-segment rows inserted: {total_inserted:,}")
    conn.close()


if __name__ == "__main__":
    main()

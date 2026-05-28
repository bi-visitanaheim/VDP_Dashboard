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
fetch_fred_data.py
------------------
Pulls economic indicator series from the Federal Reserve Bank of St. Louis
(FRED) public API.  These are the macro-level demand signals that platforms
like CoStar, Symphony (Tourism Economics), and STR supplementary reports use
to contextualize hotel performance.

FREE API KEY — instant registration:
  https://fred.stlouisfed.org/docs/api/api_key.html

Set env var:  FRED_API_KEY=your_key_here
Or add to .env file at project root.

Tables written:
  fred_economic_indicators — series_id, series_name, category, data_date, value, unit

Series pulled:
  CUUR0000SEHB  — CPI: Lodging Away From Home (hotel price benchmark)
  DSPIC96       — Real Disposable Personal Income (travel propensity)
  UNRATE        — US Unemployment Rate (macro demand signal)
  CPILFESL      — Core CPI (inflation backdrop for ADR management)
  CEU7000000001 — US Leisure & Hospitality Employment (sector health)
  UMCSENT       — University of Michigan Consumer Sentiment (leisure spend leading indicator)
  RSXFS         — Advance Retail & Food Services Sales (consumer spending proxy)
  HOUST         — Housing Starts (wealth effect → discretionary travel spending)
  PSAVERT       — Personal Savings Rate (inverse correlation with travel spend)
  ATNHPIUS06OC3A052NANN — Orange County CA Median House Price (local wealth effect)
"""

import os
import sys
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DB   = ROOT / "data" / "analytics.sqlite"

load_dotenv(ROOT / ".env")

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FRED_BASE    = "https://api.stlouisfed.org/fred/series/observations"

# Series to pull: id → (display_name, unit, category_description)
SERIES = {
    "CUUR0000SEHB": (
        "CPI: Lodging Away From Home",
        "index",
        "National hotel & motel price index — benchmark for ADR trend context",
    ),
    "DSPIC96": (
        "Real Disposable Personal Income",
        "bil_$",
        "Consumer spending power — primary driver of leisure travel propensity",
    ),
    "UNRATE": (
        "US Unemployment Rate",
        "%",
        "Macro labor demand signal — inverse correlation with discretionary travel",
    ),
    "CPILFESL": (
        "Core CPI (ex. Food & Energy)",
        "index",
        "Inflation backdrop — context for real ADR growth vs. cost-push pricing",
    ),
    "CEU7000000001": (
        "US Leisure & Hospitality Employment",
        "thousands",
        "Sector employment health — leading indicator for supply/demand balance",
    ),
    "UMCSENT": (
        "University of Michigan Consumer Sentiment",
        "index",
        "Consumer confidence — leading indicator for discretionary leisure travel spend (6–8 week lead)",
    ),
    "RSXFS": (
        "Advance Retail & Food Services Sales",
        "mil_$",
        "Consumer spending proxy — correlates with food/bev and retail spend at destination",
    ),
    "HOUST": (
        "US Housing Starts",
        "thousands",
        "Wealth-effect signal — new housing activity correlates with ADR tolerance in feeder markets",
    ),
    "PSAVERT": (
        "Personal Savings Rate",
        "%",
        "Inverse signal — when savings rate drops, discretionary leisure spending rises",
    ),
}

INIT_SQL = """
CREATE TABLE IF NOT EXISTS fred_economic_indicators (
    series_id    TEXT    NOT NULL,
    series_name  TEXT,
    category     TEXT,
    data_date    TEXT    NOT NULL,
    value        REAL,
    unit         TEXT,
    updated_at   TEXT    DEFAULT (datetime('now')),
    UNIQUE(series_id, data_date) ON CONFLICT REPLACE
);
"""


def _fetch_observations(series_id: str, start: str = "2019-01-01") -> list[dict]:
    import time
    params = {
        "series_id":         series_id,
        "observation_start": start,
        "api_key":           FRED_API_KEY,
        "file_type":         "json",
    }
    last_exc = None
    for attempt in range(3):
        try:
            r = requests.get(FRED_BASE, params=params, timeout=20)
            r.raise_for_status()
            return r.json().get("observations", [])
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            wait = 2 ** attempt
            print(f"  WARN: FRED request attempt {attempt + 1} failed ({exc}); retrying in {wait}s")
            time.sleep(wait)
        except requests.RequestException:
            raise
    raise last_exc


def main() -> int:
    if not FRED_API_KEY:
        print(
            "[SKIP] fetch_fred_data.py — FRED_API_KEY not set.\n"
            "       Get a free key in 30 seconds: https://fred.stlouisfed.org/docs/api/api_key.html\n"
            "       Then add  FRED_API_KEY=your_key  to your .env file."
        )
        return 0

    conn = sqlite3.connect(DB)
    conn.execute(INIT_SQL)
    conn.commit()

    total = 0
    for sid, (name, unit, category) in SERIES.items():
        try:
            obs = _fetch_observations(sid)
            rows = []
            for o in obs:
                raw = o.get("value", ".")
                val = None if raw == "." else float(raw)
                rows.append((sid, name, category, o["date"], val, unit))

            conn.executemany(
                """INSERT OR REPLACE INTO fred_economic_indicators
                   (series_id, series_name, category, data_date, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()
            total += len(rows)
            print(f"[OK]   FRED {sid} ({name}): {len(rows)} observations")
        except Exception as exc:
            print(f"[WARN] FRED {sid} failed: {exc}")

    conn.close()
    return total


if __name__ == "__main__":
    n = main()
    print(f"[DONE] fetch_fred_data: {n} rows inserted/updated")
    sys.exit(0)

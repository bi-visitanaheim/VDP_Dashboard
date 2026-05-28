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

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "analytics.sqlite")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS fact_str_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,        -- 'STR'
    grain TEXT NOT NULL,         -- 'daily' or 'monthly'
    property_name TEXT,
    market TEXT,
    submarket TEXT,
    as_of_date TEXT NOT NULL,    -- 'YYYY-MM-DD'
    metric_name TEXT NOT NULL,   -- 'demand', 'supply', 'adr', 'revpar', etc.
    metric_value REAL NOT NULL,
    unit TEXT,                   -- 'rooms', 'USD', 'index', etc.
    created_at TEXT DEFAULT (datetime('now'))
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS load_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,        -- 'STR'
    grain TEXT NOT NULL,         -- 'daily' or 'monthly'
    file_name TEXT NOT NULL,
    rows_inserted INTEGER NOT NULL,
    run_at TEXT DEFAULT (datetime('now'))
);
""")

conn.commit()
conn.close()

print(f"Initialized SQLite DB at {DB_PATH}")


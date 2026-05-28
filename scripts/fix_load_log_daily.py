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

# scripts/fix_load_log_daily.py

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "analytics.sqlite"


def recompute_daily_rows_inserted():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Count current STR daily rows in fact_str_metrics
    cur.execute(
        """
        SELECT COUNT(*)
        FROM fact_str_metrics
        WHERE source = 'STR'
          AND grain = 'daily';
        """
    )
    row = cur.fetchone()
    daily_count = row[0] if row else 0

    # Update the most recent STR daily log row to that count
    cur.execute(
        """
        UPDATE load_log
        SET rows_inserted = ?
        WHERE id = (
            SELECT id
            FROM load_log
            WHERE source = 'STR'
              AND grain = 'daily'
            ORDER BY run_at DESC
            LIMIT 1
        );
        """,
        (daily_count,),
    )

    conn.commit()
    conn.close()
    print(f"Updated latest STR daily load_log entry to {daily_count} rows.")


if __name__ == "__main__":
    recompute_daily_rows_inserted()


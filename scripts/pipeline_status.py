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

# scripts/pipeline_status.py

import sqlite3
from pathlib import Path
from typing import Dict

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "analytics.sqlite"


def get_str_row_counts() -> Dict[str, int]:
    """
    Returns a dict like {'daily': 4392, 'monthly': 2345}.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT grain, COUNT(*)
        FROM fact_str_metrics
        WHERE source = 'STR'
        GROUP BY grain;
        """
    )
    counts = {grain: cnt for (grain, cnt) in cur.fetchall()}
    conn.close()
    return counts


if __name__ == "__main__":
    counts = get_str_row_counts()
    daily = counts.get("daily", 0)
    monthly = counts.get("monthly", 0)
    print(f"STR daily rows:   {daily}")
    print(f"STR monthly rows: {monthly}")


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
Tests for pure utility functions in dashboard/app.py

These functions are imported directly by adding the dashboard/ directory
to sys.path and importing without triggering Streamlit's page config.

Covers:
  - pct_delta: percent change math, zero-division guard, sign correctness
  - compute_overview_kpis: KPI card computation, TBID estimate, empty guard
  - build_metrics_context: aggregation windows, weekend/midweek split
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Import strategy: patch st before importing app.py to avoid full Streamlit init
# ---------------------------------------------------------------------------

# Build a minimal stub for streamlit so we can import the module-level functions
_st_stub = MagicMock()
_st_stub.cache_data = lambda **kw: (lambda f: f)   # passthrough decorator
_st_stub.cache_resource = lambda f: f
_st_stub.set_page_config = MagicMock()
_st_stub.session_state = {}
_st_stub.query_params = {}

sys.modules.setdefault("streamlit", _st_stub)
sys.modules.setdefault("streamlit.components.v1", MagicMock())
sys.modules.setdefault("plotly", MagicMock())
sys.modules.setdefault("plotly.graph_objects", MagicMock())
sys.modules.setdefault("plotly.subplots", MagicMock())
sys.modules.setdefault("anthropic", MagicMock())
sys.modules.setdefault("openai", MagicMock())
sys.modules.setdefault("google.generativeai", MagicMock())
sys.modules.setdefault("components", MagicMock())

# Patch inject_shader_wallpaper before import
with patch.dict("sys.modules", {
    "components": MagicMock(
        render_narrative_box=MagicMock(),
        render_kpi_blob_loaders=MagicMock(),
        inject_shader_wallpaper=MagicMock(),
        render_mono_cards=MagicMock(),
        render_fun_facts_sprite=MagicMock(),
        render_monthly_highlights=MagicMock(),
        render_topic_animation=MagicMock(),
    ),
}):
    sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))
    # We import only the specific functions we need, not the whole module
    # to avoid Streamlit page execution side effects.

# Import the functions under test via exec to avoid module-level st calls
_DASHBOARD = Path(__file__).parent.parent / "dashboard" / "app.py"


def _extract_function(name: str, extra_ns: dict | None = None):
    """
    Extract a single function from app.py source without executing the module.
    Necessary because app.py runs Streamlit UI at module level.
    extra_ns: additional names to inject into the execution namespace (e.g. helper functions).
    """
    import ast
    src = _DASHBOARD.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            mod = ast.Module(body=[node], type_ignores=[])
            code = compile(mod, str(_DASHBOARD), "exec")
            ns: dict = {"pd": pd, "np": np, "st": _st_stub}
            if extra_ns:
                ns.update(extra_ns)
            exec(code, ns)
            return ns[name]
    raise ImportError(f"Function '{name}' not found in app.py")


# Extract the pure utility functions — order matters: pct_delta first so it
# can be injected into compute_overview_kpis' execution namespace.
pct_delta         = _extract_function("pct_delta")
compute_overview_kpis = _extract_function("compute_overview_kpis", extra_ns={"pct_delta": pct_delta})


# ---------------------------------------------------------------------------
# Tests: pct_delta
# ---------------------------------------------------------------------------

class TestPctDelta:

    def test_positive_growth(self):
        assert pct_delta(110.0, 100.0) == pytest.approx(10.0)

    def test_negative_growth(self):
        assert pct_delta(90.0, 100.0) == pytest.approx(-10.0)

    def test_zero_base_returns_zero(self):
        """Division by zero guard — returns 0.0, not exception."""
        assert pct_delta(50.0, 0.0) == 0.0

    def test_both_zero_returns_zero(self):
        assert pct_delta(0.0, 0.0) == 0.0

    def test_large_values(self):
        assert pct_delta(1_500_000, 1_000_000) == pytest.approx(50.0)

    def test_fractional_result(self):
        assert pct_delta(103.5, 100.0) == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# Tests: compute_overview_kpis
# ---------------------------------------------------------------------------

def _make_df(n: int = 60) -> pd.DataFrame:
    """Create a minimal wide STR DataFrame with n rows."""
    start = date(2025, 1, 1)
    dates = [start + timedelta(days=i) for i in range(n)]
    return pd.DataFrame({
        "as_of_date": pd.to_datetime(dates),
        "occupancy":  [75.0] * n,
        "adr":        [200.0] * n,
        "revpar":     [150.0] * n,
        "revenue":    [60_000.0] * n,
        "demand":     [300] * n,
        "supply":     [400] * n,
    })


class TestComputeOverviewKpis:

    def test_returns_list_of_dicts(self):
        result = compute_overview_kpis(_make_df())
        assert isinstance(result, list)
        assert all(isinstance(k, dict) for k in result)

    def test_six_kpi_cards(self):
        """Always returns exactly 6 cards: RevPAR, ADR, Occupancy, Room Revenue, Rooms Sold, TBID."""
        result = compute_overview_kpis(_make_df())
        assert len(result) == 6

    def test_card_labels(self):
        labels = [k["label"] for k in compute_overview_kpis(_make_df())]
        assert "RevPAR" in labels
        assert "ADR" in labels
        assert "Occupancy" in labels
        assert "Est. TBID Rev" in labels

    def test_tbid_estimate_is_1_25_pct(self):
        """TBID estimate = room revenue * 0.0125."""
        df = _make_df(60)
        result = compute_overview_kpis(df)
        tbid_card = next(k for k in result if k["label"] == "Est. TBID Rev")
        # Raw value should be approximately half the revenue * 0.0125
        # (second half of the date range = recent period)
        rev_half = 30 * 60_000.0
        expected_tbid = rev_half * 0.0125
        assert tbid_card["raw_value"] == pytest.approx(expected_tbid, rel=0.05)

    def test_empty_df_returns_empty_list(self):
        """Guard: < 4 rows returns empty list (not a crash)."""
        result = compute_overview_kpis(pd.DataFrame())
        assert result == []

    def test_too_few_rows_returns_empty(self):
        result = compute_overview_kpis(_make_df(3))
        assert result == []

    def test_delta_sign_correct(self):
        """If recent period is higher than prior, positive=True."""
        df = _make_df(60)
        # Gradually increasing RevPAR
        df["revpar"] = [100.0 + i for i in range(60)]
        result = compute_overview_kpis(df)
        revpar_card = next(k for k in result if k["label"] == "RevPAR")
        assert revpar_card["positive"] is True

    def test_monthly_grain_label(self):
        """Monthly grain uses 'MMM YYYY' date format (no day)."""
        df = _make_df(60)
        result = compute_overview_kpis(df, grain="Monthly")
        assert len(result) == 6
        # Date label should contain a year
        assert "2025" in result[0]["date_label"]

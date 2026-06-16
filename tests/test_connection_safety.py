"""
Regression fail-safes for the shared SQLite connection.

Background: load_str_compset / load_str_holiday_calendar /
load_str_property_roster used to call conn.close() on the connection returned
by get_connection() — a shared @st.cache_resource handle reused across every
Streamlit rerun. Closing it crashed the next rerun's load_str_daily() with
"sqlite3.ProgrammingError: Cannot operate on a closed database" and left the
app stuck on the loading screen in production.

These tests lock in the fix so it cannot regress:
  1. STATIC  — no code anywhere closes a get_connection() handle.
  2. RUNTIME — get_connection() is self-healing: even if its handle is closed,
               the next call returns a usable connection instead of raising.
"""

import ast
import logging
import sqlite3
import tempfile
from pathlib import Path

import pytest

APP_PATH = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


# ---------------------------------------------------------------------------
# 1. STATIC GUARD — no one may close the shared connection
# ---------------------------------------------------------------------------

def _names_bound_to_get_connection(func: ast.FunctionDef) -> set[str]:
    """Return local names assigned directly from a get_connection() call."""
    bound = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            callee = node.value.func
            if isinstance(callee, ast.Name) and callee.id == "get_connection":
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        bound.add(tgt.id)
    return bound


def test_no_code_closes_the_shared_connection():
    """Fail if any function closes a connection obtained from get_connection().

    Catches both `conn = get_connection(); conn.close()` and the inline
    `get_connection().close()` form.
    """
    tree = ast.parse(APP_PATH.read_text())
    offenders: list[str] = []

    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        bound = _names_bound_to_get_connection(func)
        for node in ast.walk(func):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            if node.func.attr != "close":
                continue
            obj = node.func.value
            # conn.close() where conn came from get_connection()
            if isinstance(obj, ast.Name) and obj.id in bound:
                offenders.append(f"{func.name}: {obj.id}.close() (line {node.lineno})")
            # get_connection().close()
            if (isinstance(obj, ast.Call) and isinstance(obj.func, ast.Name)
                    and obj.func.id == "get_connection"):
                offenders.append(f"{func.name}: get_connection().close() (line {node.lineno})")

    assert not offenders, (
        "Never call .close() on the shared get_connection() handle — it is a "
        "cached connection reused across reruns. Offenders:\n  "
        + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# 2. RUNTIME GUARD — get_connection() self-heals after a close
# ---------------------------------------------------------------------------

class _MemoCacheResource:
    """Minimal stand-in for st.cache_resource: memoizes one value, supports .clear()."""

    def __call__(self, func):
        store = {}

        def wrapper(*args, **kwargs):
            if "v" not in store:
                store["v"] = func(*args, **kwargs)
            return store["v"]

        wrapper.clear = store.clear
        return wrapper


def _load_connection_helpers(tmp_db: Path):
    """Extract _open_connection + get_connection from app.py and wire a real
    (memoizing) cache_resource + a temp DB, mirroring production behavior."""
    src = APP_PATH.read_text()
    tree = ast.parse(src)
    wanted = {"_open_connection", "get_connection"}
    bodies = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    assert {n.name for n in bodies} == wanted, "helper functions not found in app.py"

    st_stub = type("ST", (), {"cache_resource": _MemoCacheResource()})()
    ns = {
        "sqlite3": sqlite3,
        "st": st_stub,
        "DB_PATH": tmp_db,
        "_logger": logging.getLogger("test"),
        # _open_connection's helpers — behavior is exercised elsewhere; here we
        # only care about open/close/heal lifecycle.
        "_apply_read_pragmas": lambda conn: None,
        "_init_db": lambda conn: None,
    }
    module = ast.Module(body=bodies, type_ignores=[])
    exec(compile(module, str(APP_PATH), "exec"), ns)
    return ns["get_connection"]


def test_get_connection_self_heals_after_close():
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "t.sqlite"
        get_connection = _load_connection_helpers(db)

        conn1 = get_connection()
        assert conn1.execute("SELECT 1").fetchone()[0] == 1

        # Simulate the production bug: something closes the shared handle.
        conn1.close()
        with pytest.raises(sqlite3.ProgrammingError):
            conn1.execute("SELECT 1")

        # The fail-safe: the next acquisition must return a usable connection.
        conn2 = get_connection()
        assert conn2.execute("SELECT 1").fetchone()[0] == 1
        assert conn2 is not conn1


def test_get_connection_is_stable_when_not_closed():
    """Normal path: repeated calls return the same cached, live connection."""
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "t.sqlite"
        get_connection = _load_connection_helpers(db)
        assert get_connection() is get_connection()

"""
Per-cell position-axis follow-up exports → allen_data_repository.

Two analyses, two writers:

  export_axis_independence_metrics(repo_conn, session_id, unit_name,
      component_type, strategy, scalars)
        Upserts one row in AxisIndependenceMetrics. ``scalars`` is the
        dict produced by AxisIndependenceAnalysis.to_db_row().

  export_axis_composition_metrics(repo_conn, session_id, unit_name,
      component_type, strategy, axis_rows)
        Upserts one row per axis in AxisCompositionMetrics. ``axis_rows``
        is the list of dicts produced by AxisCompositionAnalysis.to_db_rows().

Read helpers return pandas DataFrames suitable for population-level plots.
"""

from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd

from clat.util.connection import Connection

from src.repository.create_axis_independence_tables import (
    create_axis_independence_tables,
)


_INDEPENDENCE_COLUMNS: tuple[str, ...] = (
    "n_stim_used",
    "r2_pos_only",
    "r2_shape_only",
    "r2_additive",
    "r2_interaction",
    "interaction_gap",
    "corr_p_s",
    "ridge_alpha_p",
    "ridge_alpha_s",
)


_COMPOSITION_COLUMNS: tuple[str, ...] = (
    "axis_rank",
    "r2_pos",
    "r2_shape",
    "psi",
    "axis_variance",
    "chance_baseline_pos",
    "n_stim_used",
)


def _safe_float(x) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(v) else v


def _safe_int(x) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def export_axis_independence_metrics(
    repo_conn: Connection,
    session_id: str,
    unit_name: str,
    component_type: str,
    strategy: str,
    scalars: dict,
) -> None:
    """Upsert one row into AxisIndependenceMetrics."""
    create_axis_independence_tables(repo_conn)
    cols = list(_INDEPENDENCE_COLUMNS)
    placeholders = ", ".join(["%s"] * (4 + len(cols)))
    update_clause = ", ".join(f"{c} = VALUES({c})" for c in cols)
    sql = (
        f"INSERT INTO AxisIndependenceMetrics "
        f"(session_id, unit_name, component_type, strategy, {', '.join(cols)}) "
        f"VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_clause}"
    )
    params = [session_id, unit_name, component_type, strategy]
    for c in cols:
        v = scalars.get(c)
        if c == "n_stim_used":
            params.append(_safe_int(v))
        else:
            params.append(_safe_float(v))
    repo_conn.execute(sql, params)


def export_axis_composition_metrics(
    repo_conn: Connection,
    session_id: str,
    unit_name: str,
    component_type: str,
    strategy: str,
    axis_rows: Iterable[dict],
) -> None:
    """Upsert one row per axis into AxisCompositionMetrics."""
    create_axis_independence_tables(repo_conn)
    cols = list(_COMPOSITION_COLUMNS)
    placeholders = ", ".join(["%s"] * (5 + len(cols)))
    update_clause = ", ".join(f"{c} = VALUES({c})" for c in cols)
    sql = (
        f"INSERT INTO AxisCompositionMetrics "
        f"(session_id, unit_name, component_type, strategy, axis_label, {', '.join(cols)}) "
        f"VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_clause}"
    )
    for row in axis_rows:
        params = [
            session_id, unit_name, component_type, strategy,
            str(row.get("axis_label")),
        ]
        for c in cols:
            v = row.get(c)
            if c in ("axis_rank", "n_stim_used"):
                params.append(_safe_int(v))
            else:
                params.append(_safe_float(v))
        repo_conn.execute(sql, params)


# ---------------------------------------------------------------------------
# Read helpers (population analysis)
# ---------------------------------------------------------------------------

def read_axis_independence_metrics(
    repo_conn: Connection,
    session_id: Optional[str] = None,
    component_type: Optional[str] = None,
    strategy: Optional[str] = None,
) -> pd.DataFrame:
    where, params = _build_where(
        session_id=session_id, component_type=component_type, strategy=strategy,
    )
    sql = f"SELECT * FROM AxisIndependenceMetrics{where}"
    repo_conn.execute(sql, params)
    rows = repo_conn.fetch_all()
    if not rows:
        return pd.DataFrame()
    cols = (
        ["session_id", "unit_name", "component_type", "strategy"]
        + list(_INDEPENDENCE_COLUMNS)
        + ["created_at"]
    )
    return pd.DataFrame(rows, columns=cols)


def read_axis_composition_metrics(
    repo_conn: Connection,
    session_id: Optional[str] = None,
    component_type: Optional[str] = None,
    strategy: Optional[str] = None,
    axis_label: Optional[str] = None,
) -> pd.DataFrame:
    where, params = _build_where(
        session_id=session_id, component_type=component_type,
        strategy=strategy, axis_label=axis_label,
    )
    sql = f"SELECT * FROM AxisCompositionMetrics{where}"
    repo_conn.execute(sql, params)
    rows = repo_conn.fetch_all()
    if not rows:
        return pd.DataFrame()
    cols = (
        ["session_id", "unit_name", "component_type", "strategy", "axis_label"]
        + list(_COMPOSITION_COLUMNS)
        + ["created_at"]
    )
    return pd.DataFrame(rows, columns=cols)


def _build_where(**kwargs) -> tuple[str, list]:
    clauses, params = [], []
    for key, val in kwargs.items():
        if val is None:
            continue
        clauses.append(f"{key} = %s")
        params.append(val)
    if not clauses:
        return "", []
    return " WHERE " + " AND ".join(clauses), params

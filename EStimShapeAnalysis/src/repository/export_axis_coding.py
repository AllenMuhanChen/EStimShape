"""
Per-cell, per-model axis-coding output → allen_data_repository.

One AxisCodingResult writes:

  - one row per ``model_fits[name]`` to AxisCodingFitMetrics (scalars)
  - several rows per model to AxisCodingFitArrays (variable-length arrays)

Read helpers return pandas DataFrames suitable for population-level plots.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd

from clat.util.connection import Connection

from src.repository.create_axis_coding_tables import create_axis_coding_tables


# Arrays we always export. Add to this list to ship a new array analysis;
# no schema change required.
_DEFAULT_ARRAY_NAMES: tuple[str, ...] = (
    "orth_tuning_x",
    "orth_tuning_mean",
    "orth_tuning_sd",
    "orth_tuning_count",
    "orth_tuning_per_axis",
    "orth_tuning_per_axis_modulation",
    "w_in_feature_space",
)


_METRICS_COLUMNS: tuple[str, ...] = (
    "n_stim", "n_features", "cv_r2_mean", "cv_r2_std", "train_r2",
    "noise_ceiling", "alpha",
    "spearman_rho", "spearman_p",
    "orth_n_axes_drawn", "orth_n_axes_used",
    "orth_z_range", "orth_fit_z_range",
    "orth_gauss_a", "orth_gauss_sigma", "orth_gauss_c",
    "orth_gauss_fit_ok", "orth_amplitude_norm",
    "orth_per_axis_mod_max", "orth_per_axis_mod_med",
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


def _scalars_for_model(fit: dict, ridge_summary: dict, noise_ceiling) -> dict:
    """Pull scalar metrics from one model_fits[name] dict + the ridge summary."""
    rs = ridge_summary or {}
    per_axis_mod = fit.get("orth_tuning_per_axis_modulation") or []
    per_axis_mod_arr = np.asarray(per_axis_mod, dtype=np.float64) if per_axis_mod else np.array([])
    finite_mod = per_axis_mod_arr[np.isfinite(per_axis_mod_arr)] if per_axis_mod_arr.size else np.array([])
    return {
        "n_stim": _safe_int(rs.get("n_samples")),
        "n_features": _safe_int(rs.get("n_features")),
        "cv_r2_mean": _safe_float(rs.get("cv_r2_mean")),
        "cv_r2_std": _safe_float(rs.get("cv_r2_std")),
        "train_r2": _safe_float(rs.get("train_r2")),
        "noise_ceiling": _safe_float(noise_ceiling),
        "alpha": _safe_float(rs.get("alpha")),
        "spearman_rho": _safe_float(fit.get("spearman_rho")),
        "spearman_p": _safe_float(fit.get("spearman_p")),
        "orth_n_axes_drawn": _safe_int(fit.get("orth_tuning_n_axes_drawn")),
        "orth_n_axes_used": _safe_int(fit.get("orth_tuning_n_axes_used")),
        "orth_z_range": _safe_float(fit.get("orth_tuning_z_range")),
        "orth_fit_z_range": _safe_float(fit.get("orth_tuning_fit_z_range")),
        "orth_gauss_a": _safe_float(fit.get("orth_gauss_a")),
        "orth_gauss_sigma": _safe_float(fit.get("orth_gauss_sigma")),
        "orth_gauss_c": _safe_float(fit.get("orth_gauss_c")),
        "orth_gauss_fit_ok": int(bool(fit.get("orth_gauss_fit_ok"))),
        "orth_amplitude_norm": _safe_float(fit.get("orth_amplitude_norm")),
        "orth_per_axis_mod_max": float(finite_mod.max()) if finite_mod.size else None,
        "orth_per_axis_mod_med": float(np.median(finite_mod)) if finite_mod.size else None,
    }


def export_axis_coding_result(
    repo_conn: Connection,
    session_id: str,
    unit_name: str,
    component_type: str,
    strategy: str,
    result: Any,
    array_names: Iterable[str] = _DEFAULT_ARRAY_NAMES,
) -> None:
    """
    Upsert one AxisCodingResult into AxisCodingFitMetrics + AxisCodingFitArrays.

    ``result`` is an AxisCodingResult; we pull from result.model_fits and the
    top-level ridge_summary / noise_ceiling for the shape model. For non-shape
    models we use the model's own ridge_summary and the same noise_ceiling
    (NC is a property of the data, not the model).
    """
    create_axis_coding_tables(repo_conn)

    fits = getattr(result, "model_fits", None) or {}
    if not fits:
        print(f"  [export] {session_id}/{unit_name}/{component_type}/{strategy}: no model_fits, skipping.")
        return

    nc = getattr(result, "noise_ceiling", None)

    for model_name, fit in fits.items():
        scalars = _scalars_for_model(fit, fit.get("ridge_summary") or {}, nc)
        _upsert_metrics_row(
            repo_conn, session_id, unit_name, component_type,
            strategy, model_name, scalars,
        )
        for array_name in array_names:
            payload = fit.get(array_name)
            if payload is None:
                continue
            _upsert_array_row(
                repo_conn, session_id, unit_name, component_type,
                strategy, model_name, array_name, payload,
            )

    print(
        f"  [export] {session_id}/{unit_name}/{component_type}/{strategy}: "
        f"{len(fits)} models written"
    )


def _upsert_metrics_row(
    conn: Connection,
    session_id: str,
    unit_name: str,
    component_type: str,
    strategy: str,
    model_name: str,
    scalars: dict,
) -> None:
    cols = list(_METRICS_COLUMNS)
    placeholders = ", ".join(["%s"] * (5 + len(cols)))
    update_clause = ", ".join(f"{c} = VALUES({c})" for c in cols)
    sql = (
        f"INSERT INTO AxisCodingFitMetrics "
        f"(session_id, unit_name, component_type, strategy, model_name, {', '.join(cols)}) "
        f"VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_clause}"
    )
    params = [session_id, unit_name, component_type, strategy, model_name]
    params.extend(scalars.get(c) for c in cols)
    conn.execute(sql, params)


def _upsert_array_row(
    conn: Connection,
    session_id: str,
    unit_name: str,
    component_type: str,
    strategy: str,
    model_name: str,
    array_name: str,
    payload,
) -> None:
    sql = (
        "INSERT INTO AxisCodingFitArrays "
        "(session_id, unit_name, component_type, strategy, model_name, array_name, array_json) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE array_json = VALUES(array_json)"
    )
    array_json = json.dumps(payload, default=_json_default)
    conn.execute(sql, [
        session_id, unit_name, component_type,
        strategy, model_name, array_name, array_json,
    ])


def _json_default(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        v = float(x)
        return None if not np.isfinite(v) else v
    if isinstance(x, np.ndarray):
        return x.tolist()
    return None


# ---------------------------------------------------------------------------
# Read helpers (population analysis)
# ---------------------------------------------------------------------------

def read_axis_coding_metrics(
    repo_conn: Connection,
    session_id: Optional[str] = None,
    component_type: Optional[str] = None,
    strategy: Optional[str] = None,
    model_name: Optional[str] = None,
) -> pd.DataFrame:
    """Return a DataFrame of AxisCodingFitMetrics filtered by any kwargs."""
    where, params = _build_where(
        session_id=session_id, component_type=component_type,
        strategy=strategy, model_name=model_name,
    )
    sql = f"SELECT * FROM AxisCodingFitMetrics{where}"
    repo_conn.execute(sql, params)
    rows = repo_conn.fetch_all()
    if not rows:
        return pd.DataFrame()
    cols = ["session_id", "unit_name", "component_type", "strategy", "model_name"] \
            + list(_METRICS_COLUMNS) + ["created_at"]
    return pd.DataFrame(rows, columns=cols)


def read_axis_coding_arrays(
    repo_conn: Connection,
    array_name: str,
    session_id: Optional[str] = None,
    component_type: Optional[str] = None,
    strategy: Optional[str] = None,
    model_name: Optional[str] = None,
) -> pd.DataFrame:
    """Return a DataFrame with parsed list/list-of-lists in an 'array' column."""
    where, params = _build_where(
        session_id=session_id, component_type=component_type,
        strategy=strategy, model_name=model_name,
        array_name=array_name,
    )
    sql = f"SELECT session_id, unit_name, component_type, strategy, model_name, array_json FROM AxisCodingFitArrays{where}"
    repo_conn.execute(sql, params)
    rows = repo_conn.fetch_all()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        rows,
        columns=["session_id", "unit_name", "component_type", "strategy", "model_name", "array_json"],
    )
    df["array"] = df["array_json"].apply(lambda s: json.loads(s) if s else None)
    return df.drop(columns=["array_json"])


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

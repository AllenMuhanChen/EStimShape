"""
plot_rwa_scatter.py
-------------------
Compiles fresh data and plots real vs RWA-predicted responses with dots
coloured and/or shaped by grouping variables.

Adjust the constants below to switch dimensions or filter the data.

COLOR_BY  — column used for dot colour.  Any column in the compiled DataFrame:
    "Lineage"   — one colour per lineage (default)
    "GenId"     — one colour per generation
    "StimType"  — 3D vs 2D, texture, etc.  (add StimTypeField to compile)

SYMBOL_BY — column used for dot shape.  Set to None for uniform circles.
    e.g. "GenId" while COLOR_BY="Lineage" lets you read two conditions at once.

TOP_N     — keep only the top-N colour groups by stimulus count; the rest
            become an "Other" group rendered in gray.  None = show all.

FILTERS   — dict of {column: value_or_list} to subset rows before plotting.
FILTER_MODE — "include" keeps matching rows; "exclude" drops them.

Run directly:
    python -m src.pga.app.plot_rwa_scatter
"""

from __future__ import annotations

import os
import pickle

import matplotlib.pyplot as plt
import pandas as pd

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.util.connection import Connection
from src.analysis.fields.cached_task_fields import StimTypeField
from src.analysis.fields.matchstick_fields import ShaftField, TerminationField, JunctionField, StimSpecDataField
from src.analysis.ga.cached_ga_fields import LineageField, GenIdField, RegimeScoreField
from src.analysis.ga.rwa import get_next
from src.analysis.ga.rwa_prediction import (
    compute_predictions, plot_real_vs_predicted_grouped,
    limit_groups_to_top_n, apply_filters,
)
from src.analysis.lightness.lightness_analysis import TextureField
from src.pga.app.run_rwa import ClusterResponseField, remove_catch_trials
from src.pga.mock.mock_rwa_analysis import (
    remove_empty_response_trials, condition_spherical_angles, hemisphericalize_orientation,
)
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context

# ── Colour grouping ──────────────────────────────────────────────────────────
COLOR_BY    = "Texture"   # any column in the compiled DataFrame
TOP_N       = 4           # top N colour groups by count; rest → "Other"
                          # set to None to show all groups individually

# ── Symbol grouping ──────────────────────────────────────────────────────────
SYMBOL_BY   = "StimType"        # any column to vary marker shape (e.g. "GenId")
                          # set to None for uniform circles

# ── Row filters ─────────────────────────────────────────────────────────────
# Keys are column names; values are a scalar or list of values to match.
# FILTER_MODE = "include" → keep rows where the column is in the value list.
# FILTER_MODE = "exclude" → drop rows where the column is in the value list.
#
# Examples:
FILTERS     = {}
# FILTERS = {"Texture": "2D"}
FILTERS = {"Lineage": [1775840518446908]}          # only these lineages
#   FILTERS = {"GenId": 0}                     # drop (with "exclude") gen 0
#   FILTERS = {"Lineage": [1, 2], "GenId": 5}  # must match ALL conditions

FILTER_MODE = "include"
# ────────────────────────────────────────────────────────────────────────────


def main():
    conn = Connection(context.ga_database)
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    plot_dir = f"/home/connorlab/Documents/plots/{session_id}"

    experiment_id = input("Enter the experiment id (enter nothing for most recent): ").strip()
    if experiment_id == "":
        experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    else:
        experiment_id = int(experiment_id)

    shaft_rwa, termination_rwa, junction_rwa = load_rwas(experiment_id, None)
    data = compile_data(conn)


    fig = plot_rwa_scatter(
        data, shaft_rwa, termination_rwa, junction_rwa,
        color_by=COLOR_BY,
        top_n=TOP_N,
        symbol_by=SYMBOL_BY,
        filters=FILTERS,
        filter_mode=FILTER_MODE,
        experiment_id=experiment_id,
        plot_dir=plot_dir,
    )
    plt.show()


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_rwas(experiment_id, subdir=None):
    """Load the three saved RWA pickle files for the given experiment."""
    def _load(name):
        if subdir:
            path = os.path.join(context.rwa_output_dir, subdir, f"{experiment_id}_{name}.pkl")
        else:
            path = os.path.join(context.rwa_output_dir, f"{experiment_id}_{name}.pkl")
        with open(path, "rb") as f:
            return pickle.load(f)
    return _load("shaft_rwa"), _load("termination_rwa"), _load("junction_rwa")


def compile_data(conn: Connection) -> pd.DataFrame:
    """
    Compile spike + stimulus feature data fresh from the GA database.

    Add extra fields here as new colouring/symbol dimensions become needed,
    e.g.:
        fields.append(StimTypeField(conn))
        fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, path))
    """
    task_ids = TaskIdCollector(conn).collect_task_ids()
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(LineageField(conn))
    fields.append(GenIdField(conn))
    fields.append(RegimeScoreField(conn))
    fields.append(ClusterResponseField(conn))
    fields.append(TextureField(conn))  # for SYMBOL_BY example
    fields.append(StimTypeField(conn))
    fields.append(ShaftField(conn, mstick_spec_data_source))
    fields.append(TerminationField(conn, mstick_spec_data_source))
    fields.append(JunctionField(conn, mstick_spec_data_source))

    data = fields.to_data(task_ids)
    data = remove_empty_response_trials(data)
    data = remove_catch_trials(data)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)
    return data


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_rwa_scatter(
        data: pd.DataFrame,
        shaft_rwa,
        termination_rwa,
        junction_rwa,
        color_by: str = "Lineage",
        top_n: int = None,
        symbol_by: str = None,
        filters: dict = None,
        filter_mode: str = "include",
        experiment_id=None,
        plot_dir: str = None,
) -> plt.Figure:
    """
    Plot real vs RWA-predicted response for shaft, termination, and junction.

    Dots can be coloured by one condition and shaped by another simultaneously,
    making it possible to compare two experimental dimensions at a glance.

    Args:
        data:             Compiled DataFrame with stimulus features + responses.
        shaft_rwa:        Loaded shaft RWAMatrix.
        termination_rwa:  Loaded termination RWAMatrix.
        junction_rwa:     Loaded junction RWAMatrix.
        color_by:         Column name used for dot colour (e.g. "Lineage").
        top_n:            Keep only the top-N colour groups by count; rest →
                          "Other" (gray, lower alpha).  None = show all.
        symbol_by:        Column name used for dot marker shape.  None =
                          uniform circles.
        filters:          Dict of {column: value_or_list} to subset rows.
                          Each entry must match for a row to be selected.
        filter_mode:      ``"include"`` keeps matching rows (default);
                          ``"exclude"`` drops them.
        experiment_id:    Used only for the figure title and filename.
        plot_dir:         If provided, saves the figure here.

    Returns:
        The matplotlib Figure.
    """
    # ── filter ───────────────────────────────────────────────────────────────
    if filters:
        data = apply_filters(data, filters, mode=filter_mode)

    # ── colour groups ─────────────────────────────────────────────────────────
    groups = data[color_by] if color_by in data.columns else None
    if groups is None:
        print(f"Warning: column '{color_by}' not found — plotting without colour grouping.")
    elif top_n is not None:
        groups = limit_groups_to_top_n(groups, top_n)

    # ── symbol groups ─────────────────────────────────────────────────────────
    symbols = data[symbol_by] if symbol_by and symbol_by in data.columns else None
    if symbol_by and symbols is None:
        print(f"Warning: column '{symbol_by}' not found — plotting without symbol grouping.")

    # ── figure ────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)

    for ax, (rwa_mat, col, label) in zip(axes, [
        (shaft_rwa,       "Shaft",       "Shaft"),
        (termination_rwa, "Termination", "Termination"),
        (junction_rwa,    "Junction",    "Junction"),
    ]):
        preds = compute_predictions(rwa_mat, data[col])
        plot_real_vs_predicted_grouped(
            data["Response-1"], preds,
            groups=groups,
            symbols=symbols,
            title=f"{label} RWA",
            ax=ax,
            group_label=color_by,
            symbol_label=symbol_by or "",
        )

    # ── title ─────────────────────────────────────────────────────────────────
    title = f"RWA Prediction — color: {color_by}"
    if symbol_by:
        title += f" / symbol: {symbol_by}"
    if filters:
        title += f"  [{filter_mode}: {filters}]"
    if experiment_id is not None:
        title += f" — Experiment {experiment_id}"
    fig.suptitle(title, fontsize=12, fontweight='bold')

    # ── save ──────────────────────────────────────────────────────────────────
    if plot_dir:
        os.makedirs(plot_dir, exist_ok=True)
        suffix = color_by.lower()
        if symbol_by:
            suffix += f"_sym_{symbol_by.lower()}"
        fname = f"{experiment_id}_rwa_scatter_{suffix}.png"
        path = os.path.join(plot_dir, fname)
        fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f"Saved {path}")

    return fig


if __name__ == "__main__":
    main()

"""
plot_rwa_scatter.py
-------------------
Compiles fresh data and plots real vs RWA-predicted responses with dots
coloured by a grouping variable.

Change `COLOR_BY` below to switch the colouring dimension.  Any column
present in the compiled DataFrame works:
    "Lineage"   — one colour per lineage (default)
    "GenId"     — one colour per generation
    "StimType"  — 3D vs 2D, texture, etc.  (add StimTypeField to compile)
    "A-009"     — colour by a specific channel's spike rate (add that field)

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
from src.analysis.fields.matchstick_fields import ShaftField, TerminationField, JunctionField, StimSpecDataField
from src.analysis.ga.cached_ga_fields import LineageField, GenIdField, RegimeScoreField
from src.analysis.ga.rwa import get_next
from src.analysis.ga.rwa_prediction import compute_predictions, plot_real_vs_predicted_grouped
from src.pga.app.run_rwa import ClusterResponseField, remove_catch_trials
from src.pga.mock.mock_rwa_analysis import (
    remove_empty_response_trials, condition_spherical_angles, hemisphericalize_orientation,
)
from src.startup import context

# ── Change this to colour by a different dimension ──────────────────────────
COLOR_BY = "Lineage"
# ────────────────────────────────────────────────────────────────────────────


def main():
    conn = Connection(context.ga_database)

    experiment_id = input("Enter the experiment id (enter nothing for most recent): ").strip()
    if experiment_id == "":
        experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    else:
        experiment_id = int(experiment_id)

    shaft_rwa, termination_rwa, junction_rwa = load_rwas(experiment_id)
    data = compile_data(conn)

    fig = plot_rwa_scatter(
        data, shaft_rwa, termination_rwa, junction_rwa,
        color_by=COLOR_BY,
        experiment_id=experiment_id,
        plot_dir=context.ga_plot_path,
    )
    plt.show()


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_rwas(experiment_id):
    """Load the three saved RWA pickle files for the given experiment."""
    def _load(name):
        path = os.path.join(context.rwa_output_dir, f"{experiment_id}_{name}.pkl")
        with open(path, "rb") as f:
            return pickle.load(f)
    return _load("shaft_rwa"), _load("termination_rwa"), _load("junction_rwa")


def compile_data(conn: Connection) -> pd.DataFrame:
    """
    Compile spike + stimulus feature data fresh from the GA database.

    Add extra fields here as new colouring dimensions become needed,
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
        experiment_id=None,
        plot_dir: str = None,
) -> plt.Figure:
    """
    Plot real vs RWA-predicted response for shaft, termination, and junction,
    with dots coloured by *color_by* (any column in *data*).

    Args:
        data:             Compiled DataFrame with stimulus features + responses.
        shaft_rwa:        Loaded shaft RWAMatrix.
        termination_rwa:  Loaded termination RWAMatrix.
        junction_rwa:     Loaded junction RWAMatrix.
        color_by:         Column name to use for colouring (e.g. "Lineage").
        experiment_id:    Used only for the figure title and filename.
        plot_dir:         If provided, saves the figure here.

    Returns:
        The matplotlib Figure.
    """
    groups = data[color_by] if color_by in data.columns else None
    if groups is None:
        print(f"Warning: column '{color_by}' not found — plotting without colour grouping.")

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
            title=f"{label} RWA",
            ax=ax,
            group_label=color_by,
        )

    title = f"RWA Prediction — colored by {color_by}"
    if experiment_id is not None:
        title += f" — Experiment {experiment_id}"
    fig.suptitle(title, fontsize=13, fontweight='bold')

    if plot_dir:
        os.makedirs(plot_dir, exist_ok=True)
        fname = f"{experiment_id}_rwa_scatter_{color_by.lower()}.png"
        path = os.path.join(plot_dir, fname)
        fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f"Saved {path}")

    return fig


if __name__ == "__main__":
    main()

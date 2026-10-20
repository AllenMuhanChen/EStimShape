"""
delta_variant_correlation.py
-----------------------------
Z-scored Spearman correlations between all channels using two stimulus sets, plus
model-prediction r and the variant vs delta |d'|, down the probe:

  Delta/variant — stimuli (variants + deltas) found in the IncludedDeltas table.
  Top N         — top-N stimuli by GA Response from the full GA session.
  RWA           — (optional) Pearson r between each channel's real response and the
                  shaft / termination / junction RWA-predicted response.
  Axis coding   — (optional) the same for the axis-coding predictions.
  |d'|          — variant vs delta discriminability per channel.

The figure is drawn by src/analysis/probe_analysis: these are the corr_dv, corr_topn,
rwa, axis and dprime columns of the explorer's "Probe analysis" module, which can
show them next to the preference columns.

Saved artefacts (into <save_root>/<session>/probe_analysis/<timestamp>/):
  probe_analysis.png / .svg + config.json   — main figure
  rwa_channel_scatters/                     — per-channel real-vs-RWA scatters
  axis_channel_scatters/                    — per-channel real-vs-axis scatters
  ga_channel_scatters/                      — per-channel channel-vs-GA-response scatters
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.ga.rwa_prediction import (
    plot_real_vs_predicted_grouped, limit_groups_to_top_n,
)
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context

# ── Scatter subfolder colour grouping ────────────────────────────────────────
# Applied to both rwa_channel_scatters/ and ga_channel_scatters/ figures.
# Must be a column present in the compiled data (loaded alongside the RWA).
# Set to None for single-colour dots.
SCATTER_COLOR_BY = "Texture"   # e.g. "Texture", "Lineage", "GenId"
SCATTER_TOP_N    = 5           # top-N groups by count; rest → "Other"
# ─────────────────────────────────────────────────────────────────────────────


def main():
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    # Figure + scatter subfolders go in <save_root>/<session>/probe_analysis/<timestamp>/
    save_root = "/home/connorlab/Documents/plots"
    experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)

    # Axis-coding JSONs live in the standard AxisCodingAnalysis save_dir.
    # If the directory doesn't exist (e.g. axis-coding wasn't run on this
    # session) the axis-coding columns are skipped.
    axis_coding_save_dir = (
        f"/home/connorlab/Documents/plots/{session_id}/axis_coding"
    )

    plot_delta_variant_correlation(
        session_id=session_id,
        included_only=True,
        top_n=20,
        experiment_id=experiment_id,
        scatter_color_by=SCATTER_COLOR_BY,
        scatter_top_n=SCATTER_TOP_N,
        axis_coding_save_dir=axis_coding_save_dir,
        axis_coding_strategy="multi_prototype_pca",
        save_root=save_root,
    )


# ---------------------------------------------------------------------------
# Scatter subfolders
# ---------------------------------------------------------------------------

def _build_groups(
        stim_ids: list,
        group_map: Optional[Dict[int, any]],
        top_n: Optional[int],
) -> Optional[pd.Series]:
    """
    Build a pandas Series of group labels aligned to *stim_ids*, applying
    top-N truncation if requested.  Returns None when no group_map is given.
    """
    if not group_map:
        return None
    labels = [group_map.get(sid) for sid in stim_ids]
    groups = pd.Series(labels)
    if top_n is not None:
        groups = limit_groups_to_top_n(groups, top_n)
    return groups


def _save_prediction_channel_scatters(
        channel_matrix: Dict[str, Dict[int, float]],
        pred_map: Dict[int, Tuple],
        scatter_dir: str,
        *,
        labels: Tuple[str, ...] = ("Shaft", "Termination", "Junction"),
        predictor_name: str = "RWA",
        filename_suffix: str = "vs_rwa",
        group_map: Optional[Dict[int, any]] = None,
        color_by: str = "Group",
        top_n: Optional[int] = None,
):
    """
    For each channel save a 3-panel figure: real spike rate vs the three
    component-type predictions (Shaft / Termination / Junction by default).
    ``predictor_name`` is the legend / title token (e.g. "RWA", "Axis");
    ``filename_suffix`` is the per-channel filename token.
    """
    os.makedirs(scatter_dir, exist_ok=True)
    for channel, stim_rates in sorted(channel_matrix.items()):
        common = [sid for sid in stim_rates if sid in pred_map]
        if len(common) < 3:
            continue

        real = np.array([stim_rates[sid] for sid in common], dtype=float)
        preds_by_label = {
            label: np.array(
                [pred_map[sid][i] for sid in common], dtype=float,
            )
            for i, label in enumerate(labels)
        }

        groups = _build_groups(common, group_map, top_n)

        fig, axes = plt.subplots(
            1, len(labels), figsize=(5 * len(labels), 5),
            constrained_layout=True,
        )
        if len(labels) == 1:
            axes = [axes]
        for ax, label in zip(axes, labels):
            plot_real_vs_predicted_grouped(
                real, preds_by_label[label],
                groups=groups, group_label=color_by,
                title=f"{label} {predictor_name}", ax=ax,
            )
            ax.set_xlabel(f"Real Response ({channel})", fontsize=9)
            ax.set_ylabel(f"Predicted ({predictor_name} {label})", fontsize=9)

        fig.suptitle(
            f"{predictor_name} Prediction Scatter — {channel}",
            fontsize=12, fontweight='bold',
        )
        path = os.path.join(scatter_dir, f"{channel}_{filename_suffix}.png")
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)

    print(f"Saved {predictor_name} channel scatters to {scatter_dir}")


# Back-compat alias — anything that imported _save_rwa_channel_scatters
# directly keeps working.
def _save_rwa_channel_scatters(
        channel_matrix, rwa_pred_map, scatter_dir,
        group_map=None, color_by: str = "Group", top_n: Optional[int] = None,
):
    return _save_prediction_channel_scatters(
        channel_matrix, rwa_pred_map, scatter_dir,
        predictor_name="RWA", filename_suffix="vs_rwa",
        group_map=group_map, color_by=color_by, top_n=top_n,
    )


def _save_ga_channel_scatters(
        channel_matrix: Dict[str, Dict[int, float]],
        ga_responses: Dict[int, float],
        scatter_dir: str,
        group_map: Optional[Dict[int, any]] = None,
        color_by: str = "Group",
        top_n: Optional[int] = None,
):
    """
    For each channel save a scatter of GA response (x-axis) vs channel spike
    rate (y-axis), with dots optionally coloured by *color_by*.
    """
    os.makedirs(scatter_dir, exist_ok=True)
    for channel, stim_rates in sorted(channel_matrix.items()):
        common = [sid for sid in stim_rates if sid in ga_responses]
        if len(common) < 3:
            continue

        ga = np.array([ga_responses[sid] for sid in common], dtype=float)
        ch = np.array([stim_rates[sid]   for sid in common], dtype=float)

        groups = _build_groups(common, group_map, top_n)

        fig, ax = plt.subplots(figsize=(5, 5))
        plot_real_vs_predicted_grouped(
            ga, ch,
            groups=groups, group_label=color_by,
            title=f"{channel} vs GA Response", ax=ax,
        )
        ax.set_xlabel("GA Response", fontsize=10)
        ax.set_ylabel(f"{channel} Spike Rate", fontsize=10)

        path = os.path.join(scatter_dir, f"{channel}_vs_ga_response.png")
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)

    print(f"Saved GA channel scatters to {scatter_dir}")


# ---------------------------------------------------------------------------
# Main plotting function
# ---------------------------------------------------------------------------

def plot_delta_variant_correlation(
        session_id: str,
        included_only: bool = True,
        top_n: int = 10,
        headstage_label: str = "A",
        experiment_id=None,
        scatter_color_by: Optional[str] = "Texture",
        scatter_top_n: Optional[int] = 4,
        axis_coding_save_dir: Optional[str] = None,
        axis_coding_strategy: str = "multi_prototype_pca",
        save_root: Optional[str] = None,
):
    """
    Main entry point. The figure is drawn by probe_analysis (the same columns as
    the explorer's "Probe analysis" module): z-scored Spearman ρ vs each GA channel
    on the delta/variant stims and on the top-N GA stims, the RWA and axis-coding
    prediction r (when their files exist) and the variant vs delta |d'|.

    Saves the figure into <save_root>/<session>/probe_analysis/<timestamp>/ and the
    per-channel scatter subfolders (rwa_channel_scatters/, axis_channel_scatters/,
    ga_channel_scatters/) next to it.

    Args:
        session_id:        e.g. "260410_0"
        included_only:     If True, only use stims from included pairs in IncludedDeltas.
        top_n:             Number of top stimuli by GA Response for the top-N columns.
        headstage_label:   Headstage prefix for channel names (default "A")
        experiment_id:     If None the RWA columns are skipped.
        scatter_color_by:  Column in compiled_data used to colour dots in the per-channel
                           scatter subfolders (e.g. "Texture", "Lineage").  None = no colour.
        scatter_top_n:     Keep only the top-N groups by count in scatter subfolders;
                           rest → "Other".  None = show all groups.
        axis_coding_save_dir: AxisCodingAnalysis output folder (None = skip).
        save_root:         Root folder for the timestamped output; None = don't save.
    """
    from src.analysis.probe_analysis.probe_analysis import run_probe_analysis
    from src.analysis.probe_analysis.probe_data import ProbeData

    data = ProbeData(session_id, headstage=headstage_label,
                     axis_coding_dir=axis_coding_save_dir)
    columns = ['corr_dv', 'corr_topn']
    if experiment_id is not None:
        columns.append('rwa')
    if axis_coding_save_dir is not None:
        columns.append('axis')
    columns.append('dprime')
    options = dict(top_n=top_n, included_only=included_only,
                   axis_strategy=axis_coding_strategy)
    _fig, blocks, out_dir = run_probe_analysis(session_id, columns, options=options,
                                               save_root=save_root, data=data, show=False)
    keys = {b.key for b in blocks}

    # ---- scatter subfolders ----
    if out_dir and (keys & {'rwa', 'axis'} or data.ga_responses()):
        compiled_data = data.compiled_ga_data()
        group_map = None
        if scatter_color_by and scatter_color_by in compiled_data.columns:
            group_map = dict(zip(compiled_data["StimSpecId"].astype(int),
                                 compiled_data[scatter_color_by]))
        elif scatter_color_by:
            print(f"Warning: scatter_color_by column '{scatter_color_by}' not found "
                  f"— scatter plots uncoloured.")
        all_matrix = data.all_ga_matrix()
        common = dict(group_map=group_map, color_by=scatter_color_by or "Group",
                      top_n=scatter_top_n)
        if 'rwa' in keys:
            _save_prediction_channel_scatters(
                all_matrix, data.rwa_loader().pred_map,
                os.path.join(out_dir, "rwa_channel_scatters"),
                predictor_name="RWA", filename_suffix="vs_rwa", **common)
        if 'axis' in keys:
            _save_prediction_channel_scatters(
                all_matrix, data.axis_coding_loader(axis_coding_strategy).pred_map,
                os.path.join(out_dir, "axis_channel_scatters"),
                predictor_name="Axis", filename_suffix="vs_axis", **common)
        if data.ga_responses():
            _save_ga_channel_scatters(
                all_matrix, data.ga_responses(),
                os.path.join(out_dir, "ga_channel_scatters"), **common)

    plt.show()


if __name__ == "__main__":
    main()

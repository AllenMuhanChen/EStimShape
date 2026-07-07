"""
delta_variant_correlation.py
-----------------------------
Plots z-scored Spearman correlations between all channels using two stimulus sets:

  Left group   — stimuli (variants + deltas) found in the IncludedDeltas table.
  Right group  — top-N stimuli per cluster channel from the full GA session.
  RWA group    — (columns 3-5, optional) Pearson r between each channel's real
                 response and the shaft / termination / junction RWA-predicted
                 response.  Only drawn when RWA pickle files are found.

Visual style mirrors preference_cluster.py:
  - y-axis = all 32 channels top → bottom
  - one column per cluster channel, dots coloured by correlation on RdBu_r
  - cluster channels marked with ★, others with ●

Saved artefacts (when save_path is given):
  <save_dir>/delta_variant_correlation.png     — main figure
  <save_dir>/rwa_channel_scatters/             — per-channel real-vs-RWA scatters
  <save_dir>/ga_channel_scatters/              — per-channel channel-vs-GA-response scatters

Usage:
    python -m src.analysis.ga.delta_variant_correlation
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Set, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec

import pandas as pd

from clat.util.connection import Connection
from src.analysis.channel_data_loaders import (
    AxisCodingPredictionLoader,
    ClusterChannelLoader,
    DeltaVariantStimLoader,
    GAResponseLoader,
    RawSpikeResponseLoader,
    RWALoader,
)
from src.analysis.channel_metric_plot import (
    LookupMetric,
    StimVectorCorrelation,
    build_channel_strings,
    cluster_marker_legend_handles,
    default_cmap_norm,
    render_metric,
)
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
    save_path = f"/home/connorlab/Documents/plots/{session_id}/delta_variant_correlation.png"
    experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)

    # Axis-coding JSONs live in the standard AxisCodingAnalysis save_dir.
    # If the directory doesn't exist (e.g. axis-coding wasn't run on this
    # session) plot_delta_variant_correlation skips the axis-coding columns
    # silently.
    axis_coding_save_dir = (
        f"/home/connorlab/Documents/plots/{session_id}/axis_coding"
    )

    plot_delta_variant_correlation(
        session_id=session_id,
        ga_database=context.ga_database,
        included_only=True,
        top_n=20,
        experiment_id=experiment_id,
        scatter_color_by=SCATTER_COLOR_BY,
        scatter_top_n=SCATTER_TOP_N,
        axis_coding_save_dir=axis_coding_save_dir,
        axis_coding_strategy="multi_prototype_pca",
        save_path=save_path,
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
        ga_database: str = None,
        included_only: bool = True,
        top_n: int = 10,
        headstage_label: str = "A",
        experiment_id=None,
        scatter_color_by: Optional[str] = "Texture",
        scatter_top_n: Optional[int] = 4,
        axis_coding_save_dir: Optional[str] = None,
        axis_coding_strategy: str = "multi_prototype_pca",
        save_path: Optional[str] = None,
):
    """
    Main entry point.  Connects to the GA database and the repository,
    builds two response matrices (delta/variant stimuli and top-N stimuli),
    correlates, and plots side-by-side.  If RWA pickle files are found for
    *experiment_id*, three additional columns show Pearson r between each
    channel's real response and the shaft/termination/junction RWA predictions.

    Args:
        session_id:        e.g. "260410_0"
        ga_database:       Name of the GA database (defaults to context.ga_database)
        included_only:     If True, only use stims from included pairs in IncludedDeltas.
        top_n:             Number of top stimuli (per cluster channel) for the right group.
        headstage_label:   Headstage prefix for channel names (default "A")
        experiment_id:     Integer experiment id used to locate RWA pickle files.
                           If None the RWA columns are skipped.
        scatter_color_by:  Column in compiled_data used to colour dots in the per-channel
                           scatter subfolders (e.g. "Texture", "Lineage").  None = no colour.
        scatter_top_n:     Keep only the top-N groups by count in scatter subfolders;
                           rest → "Other".  None = show all groups.
        save_path:         Optional path to save the main PNG figure.
    """
    if ga_database is None:
        ga_database = context.ga_database

    channel_strings = build_channel_strings(headstage_label)
    plot_dir = os.path.dirname(save_path) if save_path else None

    ga_conn   = Connection(ga_database)
    repo_conn = Connection("allen_data_repository")

    # ---- load data via loader classes ----
    cluster_channels = ClusterChannelLoader(session_id, repo_conn).load()
    print(f"Cluster channels: {sorted(cluster_channels)}")

    dv_stim_ids = DeltaVariantStimLoader(ga_conn, included_only).load()
    if not dv_stim_ids:
        print("No stim IDs found — check IncludedDeltas table.")
        return

    dv_matrix = RawSpikeResponseLoader(repo_conn, dv_stim_ids).load()
    if not dv_matrix:
        print("No spike data found for delta/variant stim IDs.")
        return

    ga_responses = GAResponseLoader(session_id, repo_conn).load()
    topn_matrix: Dict[str, Dict[int, float]] = {}
    if not ga_responses:
        print("Warning: no GA Response data found in GAStimInfo — skipping top-N group.")
    else:
        sorted_by_ga = sorted(ga_responses, key=lambda s: ga_responses[s], reverse=True)
        top_stim_ids = set(sorted_by_ga[:top_n])
        print(f"Top {top_n} stim_ids by GA Response selected.")
        topn_matrix = RawSpikeResponseLoader(repo_conn, top_stim_ids).load()

    # ---- compile fresh GA data (for scatter colouring + RWA) ----
    from src.pga.app.plot_rwa_scatter import compile_data as _compile_ga_data
    compiled_data = _compile_ga_data(ga_conn)

    group_map = None
    if scatter_color_by and scatter_color_by in compiled_data.columns:
        group_map = dict(zip(
            compiled_data["StimSpecId"].astype(int),
            compiled_data[scatter_color_by],
        ))
    elif scatter_color_by:
        print(f"Warning: scatter_color_by column '{scatter_color_by}' not found — scatter plots uncoloured.")

    # ---- RWA GROUP (optional, columns 3-5) ----
    all_stim_ids = set(compiled_data["StimSpecId"].astype(int))
    all_matrix = RawSpikeResponseLoader(repo_conn, all_stim_ids).load()

    rwa_loader = RWALoader(experiment_id, compiled_data, context.rwa_output_dir) \
        if experiment_id is not None else None
    rwa_metrics = rwa_loader.as_metrics(all_matrix) if rwa_loader is not None else None
    has_rwa = rwa_metrics is not None

    # ---- AXIS-CODING PREDICTION GROUP (optional, mirrors RWA) ----
    axis_loader = None
    axis_metrics = None
    if axis_coding_save_dir is not None and os.path.isdir(axis_coding_save_dir):
        axis_loader = AxisCodingPredictionLoader(
            save_dir=axis_coding_save_dir,
            strategy=axis_coding_strategy,
        )
        axis_metrics = axis_loader.as_metrics(all_matrix)
    elif axis_coding_save_dir is not None:
        print(
            f"axis_coding_save_dir not found ({axis_coding_save_dir}) — "
            f"skipping axis-coding columns."
        )
    has_axis = axis_metrics is not None

    # ---- cluster channel list (channels with response data in either matrix) ----
    cluster_channel_list = sorted(
        ch for ch in cluster_channels
        if ch in dv_matrix or ch in topn_matrix
    )
    n_cols = len(cluster_channel_list)

    if n_cols == 0:
        print("No correlations computed (no cluster channels with data).")
        return

    # ---- build metric objects ----
    dv_metrics = [
        StimVectorCorrelation.vs_channel(
            dv_matrix, ch, method='spearman', zscore=True,
            title=f"ρ vs {ch}\ndelta/variant",
        )
        for ch in cluster_channel_list
    ]
    topn_metrics = [
        StimVectorCorrelation.vs_channel(
            topn_matrix, ch, method='spearman', zscore=True,
            title=f"ρ vs {ch}\ntop {top_n}",
        )
        for ch in cluster_channel_list
    ]

    # ---- delta/variant per-channel d' (variant-anchored |dz|) ----
    # One column: for each channel, |d'| between variant and its deltas' responses,
    # over the same delta/variant stimuli. This is a per-channel discriminability,
    # not a channel-vs-channel correlation, so it gets its own colormap (>= 0).
    from src.analysis.nafc.group_analysis.compute_estim_neighbor_scores import (
        DeltaVariantDPrime, fetch_variant_delta_pairs)
    from matplotlib.colors import Normalize
    dprime_metric = None
    dprime_vmax = 1.0
    try:
        variant_to_deltas, _dv_counts = fetch_variant_delta_pairs(ga_conn, included_only)
    except Exception as exc:
        print(f"Could not load delta/variant pairs for d': {exc}")
        variant_to_deltas = {}
    if variant_to_deltas:
        _dprime = DeltaVariantDPrime('dprime', dv_matrix, variant_to_deltas, min_pairs=2)
        dprime_data = {ch: _dprime.channel_score(ch) for ch in channel_strings}
        _finite = [v for v in dprime_data.values() if v is not None and np.isfinite(v)]
        if _finite:
            dprime_metric = LookupMetric(dprime_data, title="|d'|\nvariant vs delta")
            dprime_vmax = max(_finite)
            print(f"Delta/variant d': scored {len(_finite)}/{len(channel_strings)} "
                  f"channels (max |d'| = {dprime_vmax:.2f})")
    has_dprime = dprime_metric is not None

    # ---- figure layout ----
    cmap, norm = default_cmap_norm()

    col_width   = 3
    spacer_width = 0.5

    # widths: [n_cols left] [spacer] [n_cols right]
    #         ([spacer] [3 rwa cols])? ([spacer] [3 axis cols])?
    width_ratios = (
        [col_width] * n_cols + [spacer_width] + [col_width] * n_cols
        + ([spacer_width] + [col_width] * 3 if has_rwa else [])
        + ([spacer_width] + [col_width] * 3 if has_axis else [])
        + ([spacer_width] + [col_width] if has_dprime else [])
    )
    n_gs_cols = len(width_ratios)
    fig_width = sum(w for w in width_ratios if w == col_width) + 2
    fig = plt.figure(figsize=(fig_width, 12))

    gs = GridSpec(1, n_gs_cols, width_ratios=width_ratios, wspace=0.15, figure=fig)

    axes_left  = [fig.add_subplot(gs[0, i]) for i in range(n_cols)]
    axes_right = [
        fig.add_subplot(gs[0, n_cols + 1 + i], sharey=axes_left[0])
        for i in range(n_cols)
    ]
    if has_rwa:
        rwa_start = 2 * n_cols + 2   # after left + spacer + right + spacer
        ax_shaft = fig.add_subplot(gs[0, rwa_start],     sharey=axes_left[0])
        ax_term  = fig.add_subplot(gs[0, rwa_start + 1], sharey=axes_left[0])
        ax_junc  = fig.add_subplot(gs[0, rwa_start + 2], sharey=axes_left[0])
    if has_axis:
        axis_start = 2 * n_cols + 2 + (4 if has_rwa else 0)
        ax_axis_shaft = fig.add_subplot(gs[0, axis_start],     sharey=axes_left[0])
        ax_axis_term  = fig.add_subplot(gs[0, axis_start + 1], sharey=axes_left[0])
        ax_axis_junc  = fig.add_subplot(gs[0, axis_start + 2], sharey=axes_left[0])
    if has_dprime:
        # Same convention as rwa_start/axis_start: this index is the d' COLUMN
        # itself (its spacer is the index before it).
        dprime_col = 2 * n_cols + 2 + (4 if has_rwa else 0) + (4 if has_axis else 0)
        ax_dprime = fig.add_subplot(gs[0, dprime_col], sharey=axes_left[0])

    scatter_ref = None
    included_label = "included pairs only" if included_only else "all pairs"

    # All columns rendered through the same metric pipeline; show_yticks only
    # on the leftmost axis.
    rwa_axes = [ax_shaft, ax_term, ax_junc] if has_rwa else []
    axis_axes = [ax_axis_shaft, ax_axis_term, ax_axis_junc] if has_axis else []
    column_axes = list(axes_left) + list(axes_right) + rwa_axes + axis_axes
    column_metrics = (
        list(dv_metrics) + list(topn_metrics)
        + (rwa_metrics or []) + (axis_metrics or [])
    )
    for col_idx, (ax, metric) in enumerate(zip(column_axes, column_metrics)):
        _, ref = render_metric(
            ax, metric, channel_strings, cluster_channels,
            cmap=cmap, norm=norm,
            show_yticks=(col_idx == 0),
            title_fontsize=10,
        )
        scatter_ref = scatter_ref or ref

    # d' column: own sequential colormap (|d'| >= 0) and its own colorbar.
    if has_dprime:
        from matplotlib.cm import ScalarMappable
        dp_cmap = plt.cm.magma
        dp_norm = Normalize(vmin=0.0, vmax=dprime_vmax)
        render_metric(
            ax_dprime, dprime_metric, channel_strings, cluster_channels,
            cmap=dp_cmap, norm=dp_norm, show_yticks=False, title_fontsize=10,
        )
        ax_dprime.annotate(
            "Δ/variant d'", xy=(0.5, 1.0), xycoords='axes fraction',
            xytext=(0, 30), textcoords='offset points',
            ha='center', fontsize=11, fontweight='bold', color='#333333',
        )
        cbar_dp = fig.colorbar(ScalarMappable(norm=dp_norm, cmap=dp_cmap),
                               ax=ax_dprime, fraction=0.12, pad=0.04)
        cbar_dp.set_label("|d'|  (0 = indistinct, higher = more separable)", fontsize=8)

    # Bracket label for RWA group
    if has_rwa:
        ax_term.annotate(
            "RWA Prediction r",
            xy=(0.5, 1.0), xycoords='axes fraction',
            xytext=(0, 30), textcoords='offset points',
            ha='center', fontsize=11, fontweight='bold', color='#333333',
        )

    # Bracket label for axis-coding group
    if has_axis:
        ax_axis_term.annotate(
            f"Axis-coding ({axis_coding_strategy}) Prediction r",
            xy=(0.5, 1.0), xycoords='axes fraction',
            xytext=(0, 30), textcoords='offset points',
            ha='center', fontsize=11, fontweight='bold', color='#333333',
        )

    # -- group bracket labels --
    left_mid  = axes_left[len(axes_left) // 2]
    right_mid = axes_right[len(axes_right) // 2]
    left_mid.annotate(
        f"Delta/Variant ({included_label}, {len(dv_stim_ids)} stims)",
        xy=(0.5, 1.0), xycoords='axes fraction',
        xytext=(0, 30), textcoords='offset points',
        ha='center', fontsize=11, fontweight='bold', color='#333333',
    )
    right_mid.annotate(
        f"Top {top_n} GA stimuli by GA Response",
        xy=(0.5, 1.0), xycoords='axes fraction',
        xytext=(0, 30), textcoords='offset points',
        ha='center', fontsize=11, fontweight='bold', color='#333333',
    )

    fig.suptitle(
        f"Z-scored Spearman Correlations  |  Session: {session_id}",
        fontsize=13, fontweight='bold', y=0.99,
    )

    plt.tight_layout(rect=[0, 0.06, 1, 0.96])

    # Shared colorbar at the bottom
    if scatter_ref is not None:
        cbar_ax = fig.add_axes([0.15, 0.02, 0.7, 0.02])
        cbar = plt.colorbar(
            plt.cm.ScalarMappable(norm=norm, cmap=cmap),
            cax=cbar_ax, orientation='horizontal',
        )
        cbar.set_label("Correlation  (Red = positive, Blue = negative)", fontsize=10)

    # Legend
    axes_left[0].legend(
        handles=cluster_marker_legend_handles(),
        loc='upper left', fontsize=8,
    )

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved to {save_path}")

    # ---- scatter subfolders ----
    if plot_dir and has_rwa:
        _save_prediction_channel_scatters(
            all_matrix, rwa_loader.pred_map,
            os.path.join(plot_dir, "rwa_channel_scatters"),
            predictor_name="RWA", filename_suffix="vs_rwa",
            group_map=group_map,
            color_by=scatter_color_by or "Group",
            top_n=scatter_top_n,
        )

    if plot_dir and has_axis:
        _save_prediction_channel_scatters(
            all_matrix, axis_loader.pred_map,
            os.path.join(plot_dir, "axis_channel_scatters"),
            predictor_name="Axis", filename_suffix="vs_axis",
            group_map=group_map,
            color_by=scatter_color_by or "Group",
            top_n=scatter_top_n,
        )

    if plot_dir and ga_responses:
        _save_ga_channel_scatters(
            all_matrix, ga_responses,
            os.path.join(plot_dir, "ga_channel_scatters"),
            group_map=group_map,
            color_by=scatter_color_by or "Group",
            top_n=scatter_top_n,
        )

    plt.show()


if __name__ == "__main__":
    main()

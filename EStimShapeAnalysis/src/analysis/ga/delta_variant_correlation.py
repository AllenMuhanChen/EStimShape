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
import pickle
from collections import defaultdict
from typing import Dict, Optional, Set, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from scipy.stats import linregress, spearmanr

import pandas as pd

from clat.util.connection import Connection
from src.analysis.channel_metric_plot import (
    build_channel_strings,
    cluster_marker_legend_handles,
    default_cmap_norm,
    format_single_column_axis,
    plot_metric_column,
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
    plot_delta_variant_correlation(
        session_id=session_id,
        ga_database=context.ga_database,
        included_only=False,
        top_n=20,
        experiment_id=experiment_id,
        scatter_color_by=SCATTER_COLOR_BY,
        scatter_top_n=SCATTER_TOP_N,
        save_path=save_path,
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_delta_variant_stim_ids(ga_conn: Connection,
                                 included_only: bool = True) -> Set[int]:
    """
    Return the set of stim_ids (both delta_id and variant_id sides) from
    IncludedDeltas, optionally filtering to only the included pairs.
    """
    if included_only:
        ga_conn.execute("SELECT delta_id, variant_id FROM IncludedDeltas WHERE included = TRUE")
    else:
        ga_conn.execute("SELECT delta_id, variant_id FROM IncludedDeltas")

    rows = ga_conn.fetch_all()
    stim_ids: Set[int] = set()
    for delta_id, variant_id in rows:
        stim_ids.add(int(delta_id))
        stim_ids.add(int(variant_id))

    print(f"Found {len(stim_ids)} unique stim_ids in IncludedDeltas "
          f"({'included only' if included_only else 'all pairs'})")
    return stim_ids


def load_ga_responses(repo_conn: Connection, session_id: str) -> Dict[int, float]:
    """
    Load GA Response values from GAStimInfo for the given session.
    Returns {stim_id: ga_response}, skipping rows where ga_response is NULL.
    """
    experiment_id = f"{session_id}_ga"
    repo_conn.execute(
        """SELECT g.stim_id, g.ga_response
           FROM GAStimInfo g
           JOIN StimExperimentMapping s ON g.stim_id = s.stim_id
           WHERE s.experiment_id = %s AND g.ga_response IS NOT NULL""",
        (experiment_id,),
    )
    ga_responses = {int(r[0]): float(r[1]) for r in repo_conn.fetch_all()}
    print(f"Loaded GA Response for {len(ga_responses)} stim_ids")
    return ga_responses


def build_response_matrix(repo_conn: Connection,
                           stim_ids: Set[int]) -> Dict[str, Dict[int, float]]:
    """
    Query RawSpikeResponses for the given stim_ids and return:
        {channel_id: {stim_id: mean_spike_rate}}
    Mean is taken across repeated trials of the same stimulus.
    """
    if not stim_ids:
        return {}

    placeholders = ', '.join(['%s'] * len(stim_ids))
    repo_conn.execute(
        f"SELECT task_id, stim_id FROM TaskStimMapping WHERE stim_id IN ({placeholders})",
        list(stim_ids),
    )
    task_stim_pairs = repo_conn.fetch_all()
    if not task_stim_pairs:
        print("Warning: no TaskStimMapping entries found for these stim_ids")
        return {}

    task_ids = [r[0] for r in task_stim_pairs]
    task_to_stim = {r[0]: int(r[1]) for r in task_stim_pairs}

    placeholders = ', '.join(['%s'] * len(task_ids))
    repo_conn.execute(
        f"SELECT task_id, channel_id, response_rate "
        f"FROM RawSpikeResponses WHERE task_id IN ({placeholders})",
        task_ids,
    )

    raw: Dict[str, Dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for task_id, channel_id, rate in repo_conn.fetch_all():
        stim_id = task_to_stim[task_id]
        raw[channel_id][stim_id].append(float(rate))

    matrix = {
        ch: {sid: float(np.mean(rates)) for sid, rates in stim_dict.items()}
        for ch, stim_dict in raw.items()
    }
    print(f"Built response matrix for {len(matrix)} channels "
          f"over up to {len(stim_ids)} stimuli")
    return matrix


# ---------------------------------------------------------------------------
# RWA helpers
# ---------------------------------------------------------------------------

def _try_load_rwa(experiment_id) -> Optional[Tuple]:
    """
    Attempt to load the three RWA matrix pkl files.

    Returns (shaft_rwa, termination_rwa, junction_rwa) or None if any file
    is missing.  The compiled stimulus data is NOT loaded here — it is always
    compiled fresh from the GA database instead.
    """
    try:
        def _load(name):
            path = os.path.join(context.rwa_output_dir, f"{experiment_id}_{name}.pkl")
            with open(path, "rb") as f:
                return pickle.load(f)

        shaft       = _load("shaft_rwa")
        termination = _load("termination_rwa")
        junction    = _load("junction_rwa")
        print(f"Loaded RWA matrices for experiment {experiment_id}")
        return shaft, termination, junction
    except FileNotFoundError as exc:
        print(f"RWA matrices not found — skipping RWA columns: {exc}")
        return None


def _build_rwa_pred_map(shaft_rwa, term_rwa, junc_rwa, compiled_data) -> Dict[int, Tuple]:
    """
    For every stimulus in compiled_data, compute shaft/termination/junction
    RWA-predicted responses.

    Returns {stim_id: (shaft_pred, term_pred, junc_pred)}.
    """
    from src.analysis.ga.rwa_prediction import compute_predictions

    stim_ids = list(compiled_data["StimSpecId"].astype(int))
    shaft_p = compute_predictions(shaft_rwa, compiled_data["Shaft"])
    term_p = compute_predictions(term_rwa, compiled_data["Termination"])
    junc_p = compute_predictions(junc_rwa, compiled_data["Junction"])

    return {
        sid: (shaft_p[i], term_p[i], junc_p[i])
        for i, sid in enumerate(stim_ids)
    }


def _compute_rwa_r_values(
        channel_matrix: Dict[str, Dict[int, float]],
        rwa_pred_map: Dict[int, Tuple],
) -> Dict[str, Tuple[float, float, float]]:
    """
    For each channel compute Pearson r between real spike rate and each of the
    three RWA-predicted response types.

    Returns {channel: (shaft_r, term_r, junc_r)}.
    """
    def _r(real_v, pred_v):
        valid = np.isfinite(real_v) & np.isfinite(pred_v)
        if valid.sum() < 3:
            return np.nan
        return float(linregress(real_v[valid], pred_v[valid]).rvalue)

    results = {}
    for channel, stim_rates in channel_matrix.items():
        common = [sid for sid in stim_rates if sid in rwa_pred_map]
        if len(common) < 3:
            results[channel] = (np.nan, np.nan, np.nan)
            continue

        real = np.array([stim_rates[sid] for sid in common], dtype=float)
        shaft = np.array([rwa_pred_map[sid][0] for sid in common], dtype=float)
        term  = np.array([rwa_pred_map[sid][1] for sid in common], dtype=float)
        junc  = np.array([rwa_pred_map[sid][2] for sid in common], dtype=float)

        results[channel] = (_r(real, shaft), _r(real, term), _r(real, junc))
    return results


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


def _save_rwa_channel_scatters(
        channel_matrix: Dict[str, Dict[int, float]],
        rwa_pred_map: Dict[int, Tuple],
        scatter_dir: str,
        group_map: Optional[Dict[int, any]] = None,
        color_by: str = "Group",
        top_n: Optional[int] = None,
):
    """
    For each channel save a 3-panel figure: real spike rate vs shaft / termination
    / junction RWA-predicted response, with dots optionally coloured by *color_by*.
    One PNG per channel.
    """
    os.makedirs(scatter_dir, exist_ok=True)
    for channel, stim_rates in sorted(channel_matrix.items()):
        common = [sid for sid in stim_rates if sid in rwa_pred_map]
        if len(common) < 3:
            continue

        real  = np.array([stim_rates[sid]      for sid in common], dtype=float)
        shaft = np.array([rwa_pred_map[sid][0]  for sid in common], dtype=float)
        term  = np.array([rwa_pred_map[sid][1]  for sid in common], dtype=float)
        junc  = np.array([rwa_pred_map[sid][2]  for sid in common], dtype=float)

        groups = _build_groups(common, group_map, top_n)

        fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
        for ax, (pred, label) in zip(axes, [
            (shaft, "Shaft"), (term, "Termination"), (junc, "Junction"),
        ]):
            plot_real_vs_predicted_grouped(
                real, pred,
                groups=groups, group_label=color_by,
                title=f"{label} RWA", ax=ax,
            )
            ax.set_xlabel(f"Real Response ({channel})", fontsize=9)
            ax.set_ylabel(f"Predicted (RWA {label})", fontsize=9)

        fig.suptitle(f"RWA Prediction Scatter — {channel}", fontsize=12, fontweight='bold')
        path = os.path.join(scatter_dir, f"{channel}_vs_rwa.png")
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)

    print(f"Saved RWA channel scatters to {scatter_dir}")


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
# Z-score + correlation
# ---------------------------------------------------------------------------

def _zscore(v: np.ndarray) -> np.ndarray:
    sd = np.std(v)
    return (v - np.mean(v)) / sd if sd > 0 else v - np.mean(v)


def compute_zscore_correlations(
        response_matrix: Dict[str, Dict[int, float]],
        cluster_channels: Set[str],
) -> Dict[str, Dict[str, float]]:
    """
    For each cluster channel, compute the Spearman correlation of its
    z-scored response vector with every other channel's z-scored vector.

    Returns:
        {cluster_channel: {channel: rho}}   (NaN when < 3 common stimuli)
    """
    correlations: Dict[str, Dict[str, float]] = {}

    for cluster_ch in cluster_channels:
        if cluster_ch not in response_matrix:
            print(f"Warning: cluster channel {cluster_ch} has no spike data")
            continue

        correlations[cluster_ch] = {}
        c_stims = response_matrix[cluster_ch]

        for channel, stim_rates in response_matrix.items():
            common = sorted(set(c_stims) & set(stim_rates))
            if len(common) < 3:
                correlations[cluster_ch][channel] = np.nan
                continue

            c_vec = np.array([c_stims[s] for s in common], dtype=float)
            h_vec = np.array([stim_rates[s] for s in common], dtype=float)

            rho, _ = spearmanr(_zscore(c_vec), _zscore(h_vec))
            correlations[cluster_ch][channel] = float(rho)

    return correlations


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

    # ---- connections ----
    ga_conn   = Connection(ga_database)
    repo_conn = Connection("allen_data_repository")

    # ---- cluster channels ----
    repo_conn.execute(
        """SELECT DISTINCT c.channel
           FROM ClusterInfo c
           JOIN Experiments e ON c.experiment_id = e.experiment_id
           WHERE e.session_id = %s""",
        (session_id,),
    )
    cluster_channels: Set[str] = {row[0] for row in repo_conn.fetch_all()}
    print(f"Cluster channels: {sorted(cluster_channels)}")

    # ---- LEFT GROUP: delta/variant stim ids ----
    dv_stim_ids = load_delta_variant_stim_ids(ga_conn, included_only=included_only)
    if not dv_stim_ids:
        print("No stim IDs found — check IncludedDeltas table.")
        return

    dv_matrix = build_response_matrix(repo_conn, dv_stim_ids)
    if not dv_matrix:
        print("No spike data found for delta/variant stim IDs.")
        return

    dv_correlations = compute_zscore_correlations(dv_matrix, cluster_channels)

    # ---- RIGHT GROUP: top-N by GA Response ----
    ga_responses = load_ga_responses(repo_conn, session_id)
    if not ga_responses:
        print("Warning: no GA Response data found in GAStimInfo — skipping top-N group.")
        topn_correlations = {}
    else:
        sorted_by_ga = sorted(ga_responses, key=lambda s: ga_responses[s], reverse=True)
        top_stim_ids = set(sorted_by_ga[:top_n])
        print(f"Top {top_n} stim_ids by GA Response selected.")
        topn_matrix = build_response_matrix(repo_conn, top_stim_ids)
        topn_correlations = compute_zscore_correlations(topn_matrix, cluster_channels)

    # ---- compile fresh GA data ----
    from src.pga.app.plot_rwa_scatter import compile_data as _compile_ga_data
    compiled_data = _compile_ga_data(ga_conn)

    # Build group_map for scatter colouring (always available from fresh compile)
    group_map = None
    if scatter_color_by and scatter_color_by in compiled_data.columns:
        group_map = dict(zip(
            compiled_data["StimSpecId"].astype(int),
            compiled_data[scatter_color_by],
        ))
    elif scatter_color_by:
        print(f"Warning: scatter_color_by column '{scatter_color_by}' not found — scatter plots uncoloured.")

    # ---- RWA GROUP (optional, columns 3-5) ----
    rwa_matrices = _try_load_rwa(experiment_id) if experiment_id is not None else None
    rwa_r_values = None   # {channel: (shaft_r, term_r, junc_r)}
    rwa_pred_map = None
    all_matrix   = None

    if rwa_matrices is not None:
        shaft_rwa, term_rwa, junc_rwa = rwa_matrices
        rwa_pred_map = _build_rwa_pred_map(shaft_rwa, term_rwa, junc_rwa, compiled_data)
        all_stim_ids = set(compiled_data["StimSpecId"].astype(int))
        all_matrix   = build_response_matrix(repo_conn, all_stim_ids)
        rwa_r_values = _compute_rwa_r_values(all_matrix, rwa_pred_map)

    # ---- cluster channel list ----
    cluster_channel_list = sorted(
        set(dv_correlations.keys()) | set(topn_correlations.keys())
    )
    n_cols = len(cluster_channel_list)

    if n_cols == 0:
        print("No correlations computed (no cluster channels with data).")
        return

    # ---- figure layout ----
    cmap, norm = default_cmap_norm()

    col_width   = 3
    spacer_width = 0.5
    has_rwa = rwa_r_values is not None

    # widths: [n_cols left] [spacer] [n_cols right] ([spacer] [3 rwa cols])?
    width_ratios = (
        [col_width] * n_cols + [spacer_width] + [col_width] * n_cols
        + ([spacer_width] + [col_width] * 3 if has_rwa else [])
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

    scatter_ref = None

    # -- left group --
    included_label = "included pairs only" if included_only else "all pairs"
    for col_idx, (ax, cluster_ch) in enumerate(zip(axes_left, cluster_channel_list)):
        ref = plot_metric_column(
            ax, dv_correlations.get(cluster_ch, {}),
            channel_strings, cluster_channels,
            cmap=cmap, norm=norm,
            self_channel=cluster_ch,
            show_yticks=(col_idx == 0),
        )
        format_single_column_axis(ax)
        scatter_ref = scatter_ref or ref
        ax.set_title(f"ρ vs {cluster_ch}\ndelta/variant", fontsize=10, fontweight='bold')

    # -- right group --
    for col_idx, (ax, cluster_ch) in enumerate(zip(axes_right, cluster_channel_list)):
        ref = plot_metric_column(
            ax, topn_correlations.get(cluster_ch, {}),
            channel_strings, cluster_channels,
            cmap=cmap, norm=norm,
            self_channel=cluster_ch,
        )
        format_single_column_axis(ax)
        scatter_ref = scatter_ref or ref
        ax.set_title(f"ρ vs {cluster_ch}\ntop {top_n}", fontsize=10, fontweight='bold')

    # -- RWA group (columns 3-5) --
    if has_rwa:
        shaft_r_corr = {ch: rwa_r_values[ch][0] for ch in rwa_r_values}
        term_r_corr  = {ch: rwa_r_values[ch][1] for ch in rwa_r_values}
        junc_r_corr  = {ch: rwa_r_values[ch][2] for ch in rwa_r_values}

        for ax, corr_data, label in [
            (ax_shaft, shaft_r_corr, "Shaft RWA\nr (Pearson)"),
            (ax_term,  term_r_corr,  "Termination RWA\nr (Pearson)"),
            (ax_junc,  junc_r_corr,  "Junction RWA\nr (Pearson)"),
        ]:
            ref = plot_metric_column(
                ax, corr_data,
                channel_strings, cluster_channels,
                cmap=cmap, norm=norm,
            )
            format_single_column_axis(ax)
            scatter_ref = scatter_ref or ref
            ax.set_title(label, fontsize=10, fontweight='bold')

        # Bracket label for RWA group
        ax_term.annotate(
            "RWA Prediction r",
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
    if plot_dir and rwa_matrices is not None:
        _save_rwa_channel_scatters(
            all_matrix, rwa_pred_map,
            os.path.join(plot_dir, "rwa_channel_scatters"),
            group_map=group_map,
            color_by=scatter_color_by or "Group",
            top_n=scatter_top_n,
        )

    if plot_dir and ga_responses:
        # Use all_matrix if already built (RWA path), otherwise build from compiled stim_ids
        if all_matrix is None:
            all_matrix = build_response_matrix(
                repo_conn, set(compiled_data["StimSpecId"].astype(int))
            )
        ga_matrix = all_matrix
        _save_ga_channel_scatters(
            ga_matrix, ga_responses,
            os.path.join(plot_dir, "ga_channel_scatters"),
            group_map=group_map,
            color_by=scatter_color_by or "Group",
            top_n=scatter_top_n,
        )

    plt.show()


if __name__ == "__main__":
    main()

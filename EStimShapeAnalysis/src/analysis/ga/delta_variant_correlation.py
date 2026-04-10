"""
delta_variant_correlation.py
-----------------------------
Plots z-scored Spearman correlations between all channels using only the
stimuli (variants + deltas) found in the IncludedDeltas table.

Visual style mirrors preference_cluster.py:
  - y-axis = all 32 channels top → bottom
  - one column per cluster channel, dots coloured by Spearman ρ on RdBu_r
  - cluster channels marked with ★, others with ●

Usage:
    python -m src.analysis.ga.delta_variant_correlation
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Optional, Set

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
from scipy.stats import spearmanr

from clat.util.connection import Connection
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context

# Channel order top → bottom (same as DBCChannelMapper)
CHANNEL_ORDER = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]


def main():
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    save_path = f"/home/connorlab/Documents/plots/{session_id}/delta_variant_correlation.png"
    plot_delta_variant_correlation(
        session_id=session_id,
        ga_database=context.ga_database,
        included_only=True,   # ← set False to include all pairs from IncludedDeltas
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


def build_response_matrix(repo_conn: Connection,
                           stim_ids: Set[int]) -> Dict[str, Dict[int, float]]:
    """
    Query RawSpikeResponses for the given stim_ids and return:
        {channel_id: {stim_id: mean_spike_rate}}
    Mean is taken across repeated trials of the same stimulus.
    """
    if not stim_ids:
        return {}

    # Task ids for these stim_ids
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

    # Spike rates
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

    # Average across trials
    matrix = {
        ch: {sid: float(np.mean(rates)) for sid, rates in stim_dict.items()}
        for ch, stim_dict in raw.items()
    }
    print(f"Built response matrix for {len(matrix)} channels "
          f"over up to {len(stim_ids)} stimuli")
    return matrix


# ---------------------------------------------------------------------------
# Z-score + correlation
# ---------------------------------------------------------------------------

def compute_zscore_correlations(
        response_matrix: Dict[str, Dict[int, float]],
        cluster_channels: Set[str],
) -> Dict[str, Dict[str, float]]:
    """
    For each cluster channel, compute the Spearman correlation of its
    z-scored response vector with every other channel's z-scored vector.
    Common stimuli are computed pairwise so no channel is excluded just
    because it is missing a few stimuli.

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

            # Z-score each vector independently
            def _zscore(v):
                sd = np.std(v)
                return (v - np.mean(v)) / sd if sd > 0 else v - np.mean(v)

            rho, _ = spearmanr(_zscore(c_vec), _zscore(h_vec))
            correlations[cluster_ch][channel] = float(rho)

    return correlations


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_delta_variant_correlation(
        session_id: str,
        ga_database: str = None,
        included_only: bool = True,
        headstage_label: str = "A",
        save_path: Optional[str] = None,
):
    """
    Main entry point.  Connects to the GA database and the repository,
    builds the response matrix, correlates, and plots.

    Args:
        session_id:     e.g. "260410_0"
        ga_database:    Name of the GA database (defaults to context.ga_database)
        included_only:  If True, only use stims from included pairs in IncludedDeltas.
                        If False, use all pairs regardless of the included flag.
        headstage_label: Headstage prefix for channel names (default "A")
        save_path:      Optional path to save the PNG figure.
    """
    if ga_database is None:
        ga_database = context.ga_database

    channel_strings = [f"{headstage_label}-{num:03d}" for num in CHANNEL_ORDER]

    # ---- connections ----
    ga_conn = Connection(ga_database)
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

    # ---- delta / variant stim ids ----
    stim_ids = load_delta_variant_stim_ids(ga_conn, included_only=included_only)
    if not stim_ids:
        print("No stim IDs found — check IncludedDeltas table.")
        return

    # ---- response matrix ----
    response_matrix = build_response_matrix(repo_conn, stim_ids)
    if not response_matrix:
        print("No spike data found for these stim IDs.")
        return

    # ---- correlations ----
    correlations = compute_zscore_correlations(response_matrix, cluster_channels)
    cluster_channel_list = sorted(correlations.keys())
    n_corr_cols = len(cluster_channel_list)

    if n_corr_cols == 0:
        print("No correlations computed (no cluster channels with data).")
        return

    # ---- figure ----
    cmap = plt.cm.RdBu_r
    norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)

    fig, axes = plt.subplots(
        1, n_corr_cols,
        figsize=(3 * n_corr_cols + 1, 12),
        sharey=True,
        gridspec_kw={'wspace': 0.15},
    )
    if n_corr_cols == 1:
        axes = [axes]

    scatter_ref = None
    for col_idx, (ax, cluster_ch) in enumerate(zip(axes, cluster_channel_list)):
        corr_data = correlations[cluster_ch]

        for row_idx, channel_str in enumerate(channel_strings):
            y_pos = len(channel_strings) - row_idx  # top → bottom
            is_cluster = channel_str in cluster_channels
            is_self = channel_str == cluster_ch

            rho = corr_data.get(channel_str, np.nan)

            if not np.isnan(rho):
                scatter_ref = ax.scatter(
                    0, y_pos,
                    c=rho, s=200 if is_cluster else 100,
                    marker='*' if is_cluster else 'o',
                    cmap=cmap, norm=norm,
                    edgecolors='black',
                    linewidths=2.0 if is_self else 0.5,
                    alpha=0.9 if is_cluster else 0.8,
                    zorder=10 if is_cluster else 1,
                )
            else:
                ax.scatter(
                    0, y_pos,
                    c='lightgray', s=120 if is_cluster else 50,
                    marker='*' if is_cluster else 'o',
                    edgecolors='black' if is_cluster else 'gray',
                    linewidths=0.5,
                    alpha=0.7 if is_cluster else 0.5,
                    zorder=10 if is_cluster else 1,
                )

        ax.set_xlim(-0.5, 0.5)
        ax.set_xticks([])
        ax.set_title(f"ρ vs {cluster_ch}", fontsize=11, fontweight='bold')
        ax.axvline(0, color='black', linewidth=0.5, alpha=0.3)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.set_ylim(0.5, len(channel_strings) + 0.5)

        if col_idx == 0:
            ax.set_yticks(range(1, len(channel_strings) + 1))
            ax.set_yticklabels(channel_strings[::-1], fontsize=8)
            ax.set_ylabel('Channel (Top → Bottom)', fontsize=10)

    included_label = "included pairs only" if included_only else "all pairs"
    fig.suptitle(
        f"Z-scored Spearman Correlations — Variant/Delta Stimuli\n"
        f"Session: {session_id}  |  {included_label}  |  {len(stim_ids)} stimuli",
        fontsize=13, fontweight='bold', y=0.97,
    )

    plt.tight_layout(rect=[0, 0.06, 1, 0.95])

    # Shared colorbar at the bottom
    if scatter_ref is not None:
        cbar_ax = fig.add_axes([0.15, 0.02, 0.7, 0.02])
        cbar = plt.colorbar(
            plt.cm.ScalarMappable(norm=norm, cmap=cmap),
            cax=cbar_ax, orientation='horizontal',
        )
        cbar.set_label("Spearman ρ  (Red = positive, Blue = negative)", fontsize=10)

    # Legend
    legend_elements = [
        Line2D([0], [0], marker='*', color='w', markerfacecolor='lightcoral',
               markeredgecolor='black', markersize=14, markeredgewidth=2,
               label='Cluster channel', linestyle='None'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='lightcoral',
               markeredgecolor='black', markersize=10, markeredgewidth=0.5,
               label='Other channel', linestyle='None'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgray',
               markeredgecolor='gray', markersize=10, markeredgewidth=0.5,
               label='No data', linestyle='None'),
    ]
    axes[0].legend(handles=legend_elements, loc='upper left', fontsize=8)

    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved to {save_path}")

    plt.show()


if __name__ == "__main__":
    main()

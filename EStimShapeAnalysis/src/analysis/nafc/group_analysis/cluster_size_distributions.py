"""
Histogram of the cluster sizes — correlation half-distance (µm) — of the estim specs
tested across the experiments used by effect_vs_spread_viewer and
avg_estim_per_experiment.

The half-distance is not stored in the DB; it is computed per (session, estim spec)
by plot_current_spread_vs_tuning (compute_session_half_distance). This builds the same
effect-points table the viewer does (shared COMPARISON_* config: session range,
excluded sessions, trial types, min ON trials) and histograms one value per
(session, estim spec) — a spec tested under several trial types is counted once.
"""

import sys
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis import plot_current_spread_vs_tuning as cs


def load_spec_half_distances():
    """DataFrame (session_id, estim_spec_id, half-distance) for every spec in the
    viewer's effect-points table that has a half-distance."""
    config = cs._comparison_config_kwargs()
    config.pop('save_dir')
    config.pop('by_polarity')
    _, _, points = cs.prepare_effect_points(**config)
    if len(points) == 0:
        return points
    specs = (points[['session_id', 'estim_spec_id', cs.HALFDIST_COL]]
             .drop_duplicates(['session_id', 'estim_spec_id']))
    n_missing = specs[cs.HALFDIST_COL].isna().sum()
    if n_missing:
        print(f"{n_missing} specs have no half-distance; dropped")
    return specs.dropna(subset=[cs.HALFDIST_COL]).reset_index(drop=True)


def plot_cluster_size_distributions(bin_width=50, save_path=None):
    """Histogram of corr half-distance (µm), one count per estim spec. bin_width in µm
    (None -> matplotlib 'auto')."""
    specs = load_spec_half_distances()
    if len(specs) == 0:
        print("No estim specs with a half-distance.")
        return specs

    values = specs[cs.HALFDIST_COL].to_numpy(dtype=float)
    n_sessions = specs['session_id'].nunique()
    print(f"{len(values)} estim specs across {n_sessions} sessions; "
          f"median half-distance = {np.median(values):.0f} µm "
          f"(range {values.min():.0f}-{values.max():.0f} µm)")

    if bin_width:
        lo = np.floor(values.min() / bin_width) * bin_width
        hi = np.ceil(values.max() / bin_width) * bin_width + bin_width
        bins = np.arange(lo, hi, bin_width)
    else:
        bins = 'auto'

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(values, bins=bins, color='tab:blue', edgecolor='white')
    ax.axvline(np.median(values), color='k', ls='--', lw=1,
               label=f'median = {np.median(values):.0f} µm')
    ax.set_xlabel('Cluster size: correlation half-distance (µm)')
    ax.set_ylabel('# estim specs')
    ax.set_title(f'Cluster sizes tested (n = {len(values)} specs, '
                 f'{n_sessions} sessions)')
    ax.legend(frameon=False)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=200, bbox_inches='tight')
        print(f"Saved {save_path}")
    plt.show()
    return specs


def main():
    plot_cluster_size_distributions(
        bin_width=50,
        save_path="/home/connorlab/Documents/plots/across_experiments/cluster_size_distributions.png")


if __name__ == "__main__":
    main()

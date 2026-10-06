"""
Histogram of the cluster sizes (number of channels actively delivering current) tested
across the experiments used by effect_vs_spread_viewer and avg_estim_per_experiment.

Sessions: every session with rows in EStimEffects, restricted to the shared
COMPARISON_START_SESSION_ID / COMPARISON_EXCLUDE_SESSION_IDS config (the same session
selection both of those scripts use).

Cluster size of an estim spec = number of channels in EStimParameters with a1 > 0 for
that (session_id, estim_spec_id) — the same "active channel" definition as
fetch_active_estim_channels_by_spec.

Left panel: one count per estim spec. Right panel: one count per (session, size), i.e.
how many experiments tested each cluster size at least once.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
    COMPARISON_START_SESSION_ID, COMPARISON_EXCLUDE_SESSION_IDS)


def _get_sessions(start_session_id=None, exclude_session_ids=None):
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM EStimEffects ORDER BY session_id")
    session_ids = [row[0] for row in conn.fetch_all()]
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    return session_ids


def fetch_cluster_sizes(session_ids):
    """DataFrame (session_id, estim_spec_id, cluster_size) from EStimParameters."""
    if not session_ids:
        return pd.DataFrame(columns=['session_id', 'estim_spec_id', 'cluster_size'])
    conn = Connection("allen_data_repository")
    placeholders = ', '.join(['%s'] * len(session_ids))
    conn.execute(
        "SELECT session_id, estim_spec_id, COUNT(DISTINCT channel) AS cluster_size "
        f"FROM EStimParameters WHERE a1 > 0 AND session_id IN ({placeholders}) "
        "GROUP BY session_id, estim_spec_id ORDER BY session_id, estim_spec_id",
        tuple(session_ids))
    df = pd.DataFrame(conn.fetch_all(),
                      columns=['session_id', 'estim_spec_id', 'cluster_size'])
    df['estim_spec_id'] = df['estim_spec_id'].astype(int)
    df['cluster_size'] = df['cluster_size'].astype(int)
    return df


def _integer_hist(ax, values, color, title, ylabel):
    values = np.asarray(values, dtype=int)
    edges = np.arange(values.min() - 0.5, values.max() + 1.5, 1.0)
    counts, _, bars = ax.hist(values, bins=edges, color=color, edgecolor='white')
    ax.bar_label(bars, labels=[str(int(c)) if c else '' for c in counts], fontsize=8)
    ax.set_xticks(np.arange(values.min(), values.max() + 1))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel('Cluster size (# active estim channels)')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.spines[['top', 'right']].set_visible(False)


def plot_cluster_size_distributions(start_session_id=COMPARISON_START_SESSION_ID,
                                    exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
                                    save_path=None):
    session_ids = _get_sessions(start_session_id, exclude_session_ids)
    df = fetch_cluster_sizes(session_ids)
    if len(df) == 0:
        print("No estim specs found.")
        return df

    n_sessions = df['session_id'].nunique()
    print(f"{len(df)} estim specs across {n_sessions} sessions")
    print(df.groupby('session_id')['cluster_size']
          .agg(lambda s: sorted(s.unique().tolist())).to_string())

    per_session = df.drop_duplicates(['session_id', 'cluster_size'])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    _integer_hist(axes[0], df['cluster_size'], 'tab:blue',
                  f'Per estim spec (n = {len(df)})', '# estim specs')
    _integer_hist(axes[1], per_session['cluster_size'], 'tab:orange',
                  f'Per experiment (n = {n_sessions} sessions)', '# sessions testing size')
    fig.suptitle(f'Cluster sizes tested (sessions >= {start_session_id}, '
                 f'excluding {", ".join(exclude_session_ids or []) or "none"})')
    fig.tight_layout()
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=200, bbox_inches='tight')
        print(f"Saved {save_path}")
    plt.show()
    return df


def main():
    plot_cluster_size_distributions(
        save_path="/home/connorlab/Documents/plots/across_experiments/cluster_size_distributions.png")


if __name__ == "__main__":
    main()

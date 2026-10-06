"""
Distribution of how many GA stimuli each experiment has.

For every session in EStimShapeTrials (allen_data_repository), open that session's own
GA database (same naming as ``apply_session_context``, via ExperimentManager) and count
the distinct stim_ids in StimGaInfo, grouped by stim_type. Stim types that match any
token in ``excluded_type_tokens`` (case-insensitive substring match, so "SHUFFLE" also
drops SHUFFLE_PIXEL, SHUFFLE_PHASE, ...) are left out of the count.

Outputs, in a new timestamped folder under ``output_root``:
  - ga_stim_counts.csv:          one row per session (n_included, n_excluded, per-type counts)
  - ga_stim_count_histogram.png/.svg: histogram of n_included across experiments
  - ga_stim_count_per_experiment.png/.svg: per-experiment bars, stacked by included stim type
  - config.json:                 the parameters used for this run
"""

from __future__ import annotations

import json
import os
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from clat.util.connection import Connection

from src.startup.startup_system import ExperimentManager

plt.rcParams.update({
    "font.size": 14,
    "axes.titlesize": 16,
    "axes.labelsize": 15,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 11,
})

HIST_COLOR = "#2a78d6"
MEDIAN_COLOR = "#222222"


def all_estim_session_ids(repo_conn) -> list[str]:
    """Every session_id present in EStimShapeTrials, in DB order."""
    repo_conn.execute("SELECT DISTINCT session_id FROM EStimShapeTrials ORDER BY session_id")
    return [row[0] for row in repo_conn.fetch_all()]


def ga_database_for_session(session_id: str) -> str:
    """GA database name for a session id like '260426_0'."""
    manager = ExperimentManager(session_id=session_id)
    db_names = {exp.get_context_variable_name(): exp.get_database_name()
                for exp in manager.experiments}
    return db_names["ga_database"]


def stim_type_counts(ga_conn) -> dict[str, int]:
    """stim_type -> number of distinct stim_ids in StimGaInfo."""
    ga_conn.execute(
        "SELECT stim_type, COUNT(DISTINCT stim_id) FROM StimGaInfo GROUP BY stim_type")
    return {str(stim_type): int(n) for stim_type, n in ga_conn.fetch_all()}


def is_excluded(stim_type: str, excluded_type_tokens) -> bool:
    upper = stim_type.upper()
    return any(token.upper() in upper for token in excluded_type_tokens)


def summarize_session(counts: dict[str, int], excluded_type_tokens) -> dict:
    """Split one session's per-type counts into included / excluded totals."""
    included = {t: n for t, n in counts.items() if not is_excluded(t, excluded_type_tokens)}
    excluded = {t: n for t, n in counts.items() if is_excluded(t, excluded_type_tokens)}
    return {
        "n_included": sum(included.values()),
        "n_excluded": sum(excluded.values()),
        "included_types": included,
        "excluded_types": excluded,
    }


def compute_count_table(session_ids, excluded_type_tokens) -> pd.DataFrame:
    """One row per session. Sessions whose GA database can't be read are reported and skipped."""
    repo_conn = Connection("allen_data_repository")
    if session_ids is None:
        session_ids = all_estim_session_ids(repo_conn)

    rows = []
    for sid in session_ids:
        try:
            ga_db = ga_database_for_session(sid)
            counts = stim_type_counts(Connection(ga_db))
        except Exception:
            print(f"[ga stim count] failed for session {sid}:")
            traceback.print_exc()
            continue
        rows.append({"session_id": sid, "ga_database": ga_db,
                     **summarize_session(counts, excluded_type_tokens)})
    return pd.DataFrame(rows)


def flatten_for_csv(table: pd.DataFrame) -> pd.DataFrame:
    """Expand the per-type dicts into one column per stim type."""
    included = pd.DataFrame(list(table["included_types"])).fillna(0).astype(int)
    excluded = pd.DataFrame(list(table["excluded_types"])).fillna(0).astype(int)
    included = included[sorted(included.columns)].add_prefix("n_")
    excluded = excluded[sorted(excluded.columns)].add_prefix("excluded_n_")
    base = table[["session_id", "ga_database", "n_included", "n_excluded"]].reset_index(drop=True)
    return pd.concat([base, included, excluded], axis=1)


def plot_histogram(table: pd.DataFrame, n_bins):
    counts = table["n_included"].to_numpy()
    median = float(np.median(counts))

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.hist(counts, bins=n_bins, color=HIST_COLOR, edgecolor="white", linewidth=1.5)
    ax.axvline(median, color=MEDIAN_COLOR, linestyle="--", linewidth=2,
               label=f"median = {median:g}")
    ax.set_xlabel("GA stimuli per experiment")
    ax.set_ylabel("Number of experiments")
    ax.set_title(f"GA stimuli per experiment (n = {len(counts)} experiments)")
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def plot_per_experiment(table: pd.DataFrame):
    """One bar per experiment, stacked by included stim type."""
    per_type = pd.DataFrame(list(table["included_types"]),
                            index=table["session_id"]).fillna(0)
    per_type = per_type[per_type.sum().sort_values(ascending=False).index]

    cmap = plt.get_cmap("tab20")
    colors = [cmap(i % 20) for i in range(per_type.shape[1])]

    fig, ax = plt.subplots(figsize=(max(9, 0.45 * len(per_type) + 3), 6.5))
    x = np.arange(len(per_type))
    bottom = np.zeros(len(per_type))
    for color, stim_type in zip(colors, per_type.columns):
        values = per_type[stim_type].to_numpy()
        ax.bar(x, values, bottom=bottom, color=color, edgecolor="white", linewidth=0.5,
               label=stim_type)
        bottom += values
    ax.set_xticks(x)
    ax.set_xticklabels(per_type.index, rotation=60, ha="right")
    ax.set_xlabel("Experiment (session)")
    ax.set_ylabel("GA stimuli")
    ax.set_title("GA stimuli per experiment, by stim type")
    ax.legend(frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def save_figure(fig, out_dir: str, name: str):
    fig.savefig(os.path.join(out_dir, f"{name}.png"), bbox_inches="tight", dpi=150)
    fig.savefig(os.path.join(out_dir, f"{name}.svg"), bbox_inches="tight")


def main():
    # ---- parameters ----
    # None = every session in EStimShapeTrials; or a list like ["260426_0", "260427_0"].
    session_ids = None
    # Stim types containing any of these (case-insensitive) are not counted.
    # "SHUFFLE" covers SHUFFLE_PIXEL / SHUFFLE_PHASE / SHUFFLE_MAGNITUDE / ...
    # Add "LIGHTING" here to also drop the lighting side test.
    excluded_type_tokens = ["CATCH", "BASELINE", "SHUFFLE"]
    n_bins = 20
    output_root = "/home/connorlab/Documents/plots/across_experiments/ga_stim_count_distribution"
    show_plots = True
    # --------------------

    table = compute_count_table(session_ids, excluded_type_tokens)
    if table.empty:
        print("No sessions found.")
        return

    out_dir = os.path.join(output_root, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump({
            "session_ids": session_ids,
            "sessions_counted": list(table["session_id"]),
            "excluded_type_tokens": excluded_type_tokens,
            "n_bins": n_bins,
        }, f, indent=2)

    csv_table = flatten_for_csv(table)
    csv_table.to_csv(os.path.join(out_dir, "ga_stim_counts.csv"), index=False)

    with pd.option_context("display.max_rows", None, "display.width", 120):
        print(csv_table[["session_id", "n_included", "n_excluded"]].to_string(index=False))
    counts = table["n_included"]
    print(f"\n{len(counts)} experiments: median {counts.median():g}, "
          f"mean {counts.mean():.1f}, range {counts.min()}-{counts.max()}")
    print(f"Saved to {out_dir}")

    save_figure(plot_histogram(table, n_bins), out_dir,
                "ga_stim_count_histogram")
    save_figure(plot_per_experiment(table), out_dir, "ga_stim_count_per_experiment")
    if show_plots:
        plt.show()


if __name__ == '__main__':
    main()

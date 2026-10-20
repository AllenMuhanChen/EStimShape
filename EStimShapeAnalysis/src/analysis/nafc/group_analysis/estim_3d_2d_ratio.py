"""
Per-experiment count of 3D vs 2D base stimuli used in EStim sessions.

For every session in EStimShapeTrials (allen_data_repository), take the distinct
``base_mstick_id``s its trials were built from and look each one up in that
session's own GA database (``StimTexture.texture_type``). A base stimulus counts
as 3D when its texture is SHADE/SPECULAR and 2D when it is "2D" (see
``src.pga.stim_types``). Ids with no StimTexture row are reported as unknown and
left out of the ratio. ratio_3d_2d is NaN when a session has no 2D base stimuli.

The GA database name comes from ExperimentManager (same naming as
``apply_session_context``), but the global context is not switched.

Prints one row per session: n_3d, n_2d, n_unknown, ratio_3d_2d, frac_3d, category.
Each session is categorized as "3D" when it has more 3D than 2D base stimuli, otherwise
"2D" (a 50/50 split counts as 2D). Sessions with no 2D or 3D base stimuli at all are
"unknown". A pie chart shows how many sessions fall in each category.

Each session also gets mean_spi: its solid preference index (SolidPreferenceIndices)
averaged over its GA channels (the latest-generation ClusterInfo channels), plotted as a
histogram across sessions. Bars are split by whether the session's GA channels are
significantly 3D- or 2D-preferring: the per-channel permutation p-values
(SolidPreferenceIndices.p_value, two-tailed) are combined with Stouffer's method, each
channel signed by its SPI, so z_i = sign(SPI_i) * Phi^-1(1 - p_i / 2) and
Z = sum(z_i) / sqrt(k). A session is significantly 3D when Z > 0 and p(Z) < SIGNIFICANCE_ALPHA,
significantly 2D when Z < 0 and p(Z) < SIGNIFICANCE_ALPHA, otherwise n.s. Sessions with no
p-values (permutation test not run) are "no test".

A scatterplot puts each session's mean_spi against its average estim effect, computed as in
avg_estim_per_experiment: every qualifying condition of the session (ON and OFF groups both
>= ESTIM_EFFECT_MIN_TRIALS trials) pooled into one ON/OFF table, effect = % ON - % OFF
(percentage points; OFF trials shared by conditions counted once), with its one-sided
Fisher's exact p. Metric, cutoff label and min trials are the ESTIM_EFFECT_* settings below,
matching avg_estim_per_experiment.main(). Sessions with no qualifying condition are left off.

A second scatter puts the same estim effect against receptive field size: mean_rf_radius is
the ReceptiveFieldInfo radius (deg) averaged over the session's GA channels, using the
cluster fallback in spi_vs_ici_preferred_freq.merge_receptive_field_radius. If none of the
GA channels has an RF, it falls back to the mean over every RF mapped in that session
(rf_source says which). Sessions with no RF at all are left off.

Both estim-effect scatters are drawn a second time with the average taken over only the
session's conditions in the top half of EStim parameter fitness: the condition set
TOP_FITNESS_CONDITION_SET that avg_estim_per_experiment saves to the data repository (its
'closest' rule split). Re-run avg_estim_per_experiment to refresh the set.
All figures are shown and saved to SAVE_DIR.
"""

from __future__ import annotations

import json
import os
import traceback

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr
from matplotlib import pyplot as plt
from clat.util.connection import Connection

from src.analysis.channel_data_loaders import ClusterChannelLoader, SolidPreferenceLoader
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import METRIC_PCT_HYP_VS_DELTA
from src.analysis.nafc.group_analysis.avg_estim_per_experiment import (
    build_pooled_table_for_session, fisher_exact_for_table)
from src.analysis.nafc.group_analysis.estim_condition_sets import (
    in_condition_set, load_condition_set)
from src.analysis.spi_vs_ici.spi_vs_ici_preferred_freq import merge_receptive_field_radius
from src.pga.stim_types import THREE_D_TEXTURES
from src.startup.startup_system import ExperimentManager

TWO_D_TEXTURE = "2D"

SAVE_DIR = "/home/connorlab/Documents/plots/across_experiments/"

SIGNIFICANCE_ALPHA = 0.05

# Average estim effect per session, same settings as avg_estim_per_experiment.main().
ESTIM_EFFECT_METRIC = METRIC_PCT_HYP_VS_DELTA
ESTIM_EFFECT_ALGORITHM_LABEL = 'None'
ESTIM_EFFECT_MIN_TRIALS = 5

# Condition set written by avg_estim_per_experiment.main(): top half by EStim parameter fitness.
TOP_FITNESS_CONDITION_SET = 'estim_rule_top_half'

SPI_SIG_ORDER = ("3D", "2D", "n.s.", "no test")
SPI_SIG_LABELS = {"3D": "Significantly 3D", "2D": "Significantly 2D",
                  "n.s.": "Not significant", "no test": "No permutation test"}
SPI_SIG_COLORS = {"3D": "#2a78d6", "2D": "#eb6834", "n.s.": "#a9a9a9", "no test": "#dddddd"}

CATEGORY_COLORS = {"3D": "#2a78d6", "2D": "#eb6834", "unknown": "#a9a9a9"}


def all_estim_session_ids(repo_conn) -> list[str]:
    """Every session_id present in EStimShapeTrials, in DB order."""
    repo_conn.execute("SELECT DISTINCT session_id FROM EStimShapeTrials ORDER BY session_id")
    return [row[0] for row in repo_conn.fetch_all()]


def base_mstick_ids_for_session(repo_conn, session_id: str) -> list[int]:
    """Distinct non-null base_mstick_ids used in a session's trials."""
    repo_conn.execute(
        "SELECT DISTINCT base_mstick_id FROM EStimShapeTrials "
        "WHERE session_id = %s AND base_mstick_id IS NOT NULL",
        (session_id,))
    return [int(row[0]) for row in repo_conn.fetch_all()]


def ga_database_for_session(session_id: str) -> str:
    """GA database name for a session id like '260426_0'."""
    manager = ExperimentManager(session_id=session_id)
    db_names = {exp.get_context_variable_name(): exp.get_database_name()
                for exp in manager.experiments}
    return db_names["ga_database"]


def textures_for_stims(ga_conn, stim_ids: list[int]) -> dict[int, str]:
    """stim_id -> texture_type from StimTexture; ids without a row are absent."""
    if not stim_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(stim_ids))
    ga_conn.execute(
        f"SELECT stim_id, texture_type FROM StimTexture WHERE stim_id IN ({placeholders})",
        tuple(stim_ids))
    return {int(stim_id): texture for stim_id, texture in ga_conn.fetch_all()}


def count_textures(stim_ids: list[int], textures: dict[int, str]) -> dict:
    """Tally 3D / 2D / unknown and compute the 3D:2D ratio and 3D fraction."""
    n_3d = sum(1 for s in stim_ids if textures.get(s) in THREE_D_TEXTURES)
    n_2d = sum(1 for s in stim_ids if textures.get(s) == TWO_D_TEXTURE)
    return summarize(n_3d, n_2d, len(stim_ids) - n_3d - n_2d)


def summarize(n_3d: int, n_2d: int, n_unknown: int) -> dict:
    known = n_3d + n_2d
    return {
        "n_base_msticks": known + n_unknown,
        "n_3d": n_3d,
        "n_2d": n_2d,
        "n_unknown": n_unknown,
        "ratio_3d_2d": n_3d / n_2d if n_2d else float("nan"),
        "frac_3d": n_3d / known if known else float("nan"),
    }


def categorize(n_3d: int, n_2d: int) -> str:
    """Predominately 3D or 2D; ties count as 2D."""
    if n_3d + n_2d == 0:
        return "unknown"
    return "3D" if n_3d > n_2d else "2D"


def combine_signed_pvalues(spis: list[float], pvalues: list[float]) -> tuple[float, float]:
    """Stouffer's Z over channels, each two-tailed p signed by its SPI. Returns (Z, two-tailed p)."""
    # Clip so p = 0 (no permutation beat the actual SPI) doesn't give an infinite z.
    p = np.clip(np.asarray(pvalues, dtype=float), 1e-12, 1.0)
    z = np.sign(spis) * norm.isf(p / 2)
    combined_z = float(z.sum() / np.sqrt(len(z)))
    return combined_z, float(2 * norm.sf(abs(combined_z)))


def ga_channel_spi_summary(repo_conn, session_id: str) -> dict:
    """Mean SPI over the session's GA channels, plus the combined significance of those
    channels' permutation tests (see module docstring)."""
    ga_channels = ClusterChannelLoader(session_id, repo_conn).load()
    loader = SolidPreferenceLoader(session_id, repo_conn)
    spi_by_channel = loader.load()
    values = [spi_by_channel[ch] for ch in ga_channels
              if ch in spi_by_channel and spi_by_channel[ch] is not None]

    tested = [(spi, p) for ch, spi, p in loader._load_index_and_pvalue()
              if ch in ga_channels and spi is not None and p is not None]
    if tested:
        spi_z, spi_p = combine_signed_pvalues(*zip(*tested))
        if spi_p >= SIGNIFICANCE_ALPHA:
            spi_sig = "n.s."
        else:
            spi_sig = "3D" if spi_z > 0 else "2D"
    else:
        spi_z, spi_p, spi_sig = float("nan"), float("nan"), "no test"

    return {
        "mean_spi": float(np.mean(values)) if values else float("nan"),
        "n_spi_channels": len(values),
        "spi_z": spi_z,
        "spi_p": spi_p,
        "spi_sig": spi_sig,
    }


def rf_size_summary(repo_conn, session_id: str) -> dict:
    """Mean RF radius over the session's GA channels (with cluster fallback); if none of them
    has an RF, the mean over every RF mapped in the session. NaN when the session has none."""
    ga_channels = sorted(ClusterChannelLoader(session_id, repo_conn).load())
    if ga_channels:
        ga = merge_receptive_field_radius(
            pd.DataFrame({"session_id": session_id, "unit_name": ga_channels}))
        radii = pd.to_numeric(ga["rf_radius"], errors="coerce")
        radii = radii[radii > 0]
        if not radii.empty:
            return {"mean_rf_radius": float(radii.mean()), "n_rf_channels": len(radii),
                    "rf_source": "GA channels"}

    repo_conn.execute("SELECT radius FROM ReceptiveFieldInfo WHERE session_id = %s", (session_id,))
    radii = [float(r[0]) for r in repo_conn.fetch_all() if r[0] is not None and float(r[0]) > 0]
    if radii:
        return {"mean_rf_radius": float(np.mean(radii)), "n_rf_channels": len(radii),
                "rf_source": "all mapped"}
    return {"mean_rf_radius": float("nan"), "n_rf_channels": 0, "rf_source": "none"}


def average_effect(session_id: str, condition_filter=None) -> dict:
    """Pooled ON - OFF % (percentage points) over the session's qualifying conditions (those
    passing condition_filter, if given), its one-sided Fisher's exact p, and the condition
    count. NaN when no condition qualifies."""
    table = build_pooled_table_for_session(
        session_id, ESTIM_EFFECT_ALGORITHM_LABEL, ESTIM_EFFECT_METRIC,
        min_trials=ESTIM_EFFECT_MIN_TRIALS, condition_filter=condition_filter)
    if table is None:
        return {"effect": float("nan"), "p": float("nan"), "n_conditions": 0}
    _, p = fisher_exact_for_table(table, alternative='greater')
    effect = 100.0 * table['on_yes'] / table['n_on'] - 100.0 * table['off_yes'] / table['n_off']
    return {"effect": float(effect), "p": float(p), "n_conditions": int(table['n_conditions'])}


def estim_effect_summary(session_id: str, top_fitness_members: dict) -> dict:
    """Average estim effect over all qualifying conditions, and over only those in the
    top-half-fitness condition set."""
    def in_top_half(sid, cond):
        return in_condition_set([sid], [json.dumps(cond)], top_fitness_members)[0]

    all_conds = average_effect(session_id)
    top = average_effect(session_id, in_top_half)
    return {"estim_effect": all_conds["effect"], "estim_effect_p": all_conds["p"],
            "n_effect_conditions": all_conds["n_conditions"],
            "estim_effect_top_fitness": top["effect"], "estim_effect_top_fitness_p": top["p"],
            "n_top_fitness_conditions": top["n_conditions"]}


def compute_ratio_table(exclude_session_ids=None, start_session_id=None) -> pd.DataFrame:
    """One row per session in EStimShapeTrials, filtered the same way as
    max_estim_per_experiment: drop ``exclude_session_ids``, then keep only sessions whose
    session_id >= ``start_session_id`` (if given). Sessions whose GA database can't be read
    are reported and skipped."""
    repo_conn = Connection("allen_data_repository")
    session_ids = all_estim_session_ids(repo_conn)
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]

    top_fitness_members = load_condition_set(TOP_FITNESS_CONDITION_SET)
    if not top_fitness_members:
        print(f"[3d/2d] condition set '{TOP_FITNESS_CONDITION_SET}' is empty or missing; "
              f"run avg_estim_per_experiment to create it")

    rows = []
    for sid in session_ids:
        try:
            stim_ids = base_mstick_ids_for_session(repo_conn, sid)
            ga_db = ga_database_for_session(sid)
            textures = textures_for_stims(Connection(ga_db), stim_ids)
        except Exception:
            print(f"[3d/2d] failed for session {sid}:")
            traceback.print_exc()
            continue
        counts = count_textures(stim_ids, textures)
        counts["category"] = categorize(counts["n_3d"], counts["n_2d"])
        try:
            counts.update(ga_channel_spi_summary(repo_conn, sid))
        except Exception:
            print(f"[3d/2d] could not load SPI for session {sid}:")
            traceback.print_exc()
            counts.update(mean_spi=float("nan"), n_spi_channels=0,
                          spi_z=float("nan"), spi_p=float("nan"), spi_sig="no test")
        try:
            counts.update(estim_effect_summary(sid, top_fitness_members))
        except Exception:
            print(f"[3d/2d] could not load estim effect for session {sid}:")
            traceback.print_exc()
            counts.update(estim_effect=float("nan"), estim_effect_p=float("nan"),
                          n_effect_conditions=0, estim_effect_top_fitness=float("nan"),
                          estim_effect_top_fitness_p=float("nan"), n_top_fitness_conditions=0)
        try:
            counts.update(rf_size_summary(repo_conn, sid))
        except Exception:
            print(f"[3d/2d] could not load RF size for session {sid}:")
            traceback.print_exc()
            counts.update(mean_rf_radius=float("nan"), n_rf_channels=0, rf_source="none")
        rows.append({"session_id": sid, **counts})

    return pd.DataFrame(rows)


def plot_category_pie(table: pd.DataFrame):
    """Pie of how many sessions are predominately 3D vs 2D."""
    counts = table["category"].value_counts()
    labels = [c for c in ("3D", "2D", "unknown") if counts.get(c, 0)]
    sizes = [counts[c] for c in labels]

    fig, ax = plt.subplots(figsize=(5, 5))
    _, _, pct_texts = ax.pie(
        sizes,
        labels=[f"Predominately {c}" if c != "unknown" else "No texture data" for c in labels],
        colors=[CATEGORY_COLORS[c] for c in labels],
        autopct=lambda pct: f"{round(pct * sum(sizes) / 100)} ({pct:.0f}%)",
        startangle=90,
        counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        textprops={"color": "#222222"},
    )
    for t in pct_texts:
        t.set_color("white")
    ax.set_title(f"EStim sessions by test stimulus type (n = {sum(sizes)})")
    ax.axis("equal")
    fig.tight_layout()
    return fig


def plot_spi_histogram(table: pd.DataFrame):
    """Histogram across sessions of the GA-channel-averaged solid preference index,
    stacked by whether the session is significantly 3D, significantly 2D, or neither."""
    with_spi = table.dropna(subset=["mean_spi"])
    groups = [g for g in SPI_SIG_ORDER if (with_spi["spi_sig"] == g).any()]

    fig, ax = plt.subplots(figsize=(8.5, 4))
    ax.hist([with_spi.loc[with_spi["spi_sig"] == g, "mean_spi"] for g in groups],
            bins=np.linspace(-1, 1, 21), stacked=True,
            color=[SPI_SIG_COLORS[g] for g in groups],
            label=[SPI_SIG_LABELS[g] for g in groups],
            edgecolor="white", linewidth=2)
    # Outside the axes, right of the plot, so it never covers bars.
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0, frameon=False, title=f"Combined GA channels, p < {SIGNIFICANCE_ALPHA}")
    ax.axvline(0, color="#888888", linewidth=1, linestyle="--", zorder=0)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Mean solid preference index over GA channels  (2D ← → 3D)")
    ax.set_ylabel("Sessions")
    ax.set_title("Solid preference index per EStim session")
    ax.yaxis.get_major_locator().set_params(integer=True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    return fig


EFFECT_AXIS_LABELS = {
    "estim_effect": "Average EStim effect (% points)",
    "estim_effect_top_fitness": "Average EStim effect, top-half-fitness conditions (% points)",
}
EFFECT_TITLE_SUFFIX = {"estim_effect": "", "estim_effect_top_fitness": " (top half fitness)"}


def plot_spi_vs_estim_effect(table: pd.DataFrame, show_stats: bool = False,
                             effect_col: str = "estim_effect"):
    """Scatter of mean GA-channel SPI vs average estim effect, one point per session,
    colored by the session's SPI significance (same colors as the histogram).
    effect_col="estim_effect_top_fitness" plots the top-fitness-only effect instead."""
    data = table.dropna(subset=["mean_spi", effect_col])

    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.axvline(0, color="#888888", linewidth=1, linestyle="--", zorder=0)
    ax.axhline(0, color="#888888", linewidth=1, linestyle="--", zorder=0)
    for g in SPI_SIG_ORDER:
        group = data[data["spi_sig"] == g]
        if group.empty:
            continue
        ax.scatter(group["mean_spi"], group[effect_col], s=64, color=SPI_SIG_COLORS[g],
                   edgecolor="white", linewidth=1.5, label=SPI_SIG_LABELS[g], zorder=3)

    if len(data) >= 3:
        rho, p = spearmanr(data["mean_spi"], data[effect_col])
        print(f"SPI vs {effect_col}: Spearman rho = {rho:.2f}, p = {p:.3g} (n = {len(data)})")
    if show_stats and len(data) >= 3:
        ax.text(0.02, 0.97, f"Spearman ρ = {rho:.2f}, p = {p:.3g}", transform=ax.transAxes,
                va="top", ha="left", fontsize=9, color="#444444")

    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0, frameon=False,
              title=f"Combined GA channels, p < {SIGNIFICANCE_ALPHA}")
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Mean solid preference index over GA channels  (2D ← → 3D)")
    ax.set_ylabel(EFFECT_AXIS_LABELS[effect_col])
    ax.set_title("Solid preference index vs EStim effect" + EFFECT_TITLE_SUFFIX[effect_col])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    return fig


def plot_rf_size_vs_estim_effect(table: pd.DataFrame, show_stats: bool = False,
                                 effect_col: str = "estim_effect"):
    """Scatter of mean RF radius vs average estim effect, one point per session.
    effect_col="estim_effect_top_fitness" plots the top-fitness-only effect instead."""
    data = table.dropna(subset=["mean_rf_radius", effect_col])

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.axhline(0, color="#888888", linewidth=1, linestyle="--", zorder=0)
    ax.scatter(data["mean_rf_radius"], data[effect_col], s=64, color=SPI_SIG_COLORS["3D"],
               edgecolor="white", linewidth=1.5, zorder=3)

    if len(data) >= 3:
        rho, p = spearmanr(data["mean_rf_radius"], data[effect_col])
        print(f"RF size vs {effect_col}: Spearman rho = {rho:.2f}, p = {p:.3g} (n = {len(data)})")
        if show_stats:
            ax.text(0.02, 0.97, f"Spearman \u03c1 = {rho:.2f}, p = {p:.3g}", transform=ax.transAxes,
                    va="top", ha="left", fontsize=9, color="#444444")

    ax.set_xlim(left=0)
    ax.set_xlabel("Mean receptive field radius (deg)")
    ax.set_ylabel(EFFECT_AXIS_LABELS[effect_col])
    ax.set_title("Receptive field size vs EStim effect" + EFFECT_TITLE_SUFFIX[effect_col])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    return fig


def save_figure(fig, name: str):
    os.makedirs(SAVE_DIR, exist_ok=True)
    path = os.path.join(SAVE_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}")


def main():
    SHOW_PLOTS = True
    SHOW_STATS_ON_PLOT = False  # Spearman rho/p on the scatter; always printed to console
    # Same session selection as max_estim_per_experiment / avg_estim_per_experiment main().
    exclude_session_ids = ["260421_0", "260410_0"]
    start_session_id = "260402_0"  # first variant experiment; None = no lower bound

    table = compute_ratio_table(exclude_session_ids=exclude_session_ids,
                                start_session_id=start_session_id)
    if table.empty:
        print("No sessions found.")
        return

    # Pooled row: sums the per-session counts (a stimulus id is only unique within its GA db).
    total = summarize(*(int(table[c].sum()) for c in ("n_3d", "n_2d", "n_unknown")))
    total["category"] = ""
    total["mean_spi"] = table["mean_spi"].mean()
    total["n_spi_channels"] = int(table["n_spi_channels"].sum())
    total.update(spi_z=float("nan"), spi_p=float("nan"), spi_sig="",
                 estim_effect=table["estim_effect"].mean(), estim_effect_p=float("nan"),
                 n_effect_conditions=int(table["n_effect_conditions"].sum()),
                 estim_effect_top_fitness=table["estim_effect_top_fitness"].mean(),
                 estim_effect_top_fitness_p=float("nan"),
                 n_top_fitness_conditions=int(table["n_top_fitness_conditions"].sum()),
                 mean_rf_radius=table["mean_rf_radius"].mean(),
                 n_rf_channels=int(table["n_rf_channels"].sum()), rf_source="")
    printed = pd.concat([table, pd.DataFrame([{"session_id": "ALL", **total}])], ignore_index=True)

    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(printed.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print()
    print(table["category"].value_counts().to_string())
    print()
    print(table["spi_sig"].value_counts().to_string())

    save_figure(plot_category_pie(table), "estim_3d_2d_category_pie.png")
    save_figure(plot_spi_histogram(table), "estim_session_spi_histogram.png")
    save_figure(plot_spi_vs_estim_effect(table, show_stats=SHOW_STATS_ON_PLOT), "estim_session_spi_vs_estim_effect.png")
    save_figure(plot_rf_size_vs_estim_effect(table, show_stats=SHOW_STATS_ON_PLOT),
                "estim_session_rf_size_vs_estim_effect.png")
    save_figure(plot_spi_vs_estim_effect(table, show_stats=SHOW_STATS_ON_PLOT,
                                         effect_col="estim_effect_top_fitness"),
                "estim_session_spi_vs_estim_effect_top_fitness.png")
    save_figure(plot_rf_size_vs_estim_effect(table, show_stats=SHOW_STATS_ON_PLOT,
                                             effect_col="estim_effect_top_fitness"),
                "estim_session_rf_size_vs_estim_effect_top_fitness.png")
    if SHOW_PLOTS:
        plt.show()


if __name__ == '__main__':
    main()

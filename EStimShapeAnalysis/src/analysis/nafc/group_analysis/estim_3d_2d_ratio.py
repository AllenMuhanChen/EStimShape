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

A scatterplot puts each session's mean_spi against its estim effect. The estim effect is
the per-experiment max-stat effect from max_estim_per_experiment (EStimPermutationTests):
the session's best condition, chosen after studentizing each condition by its own null,
reported as the raw effect in percentage points, with the max-stat p-value. The metric,
cutoff label and min-trials filter are the ESTIM_EFFECT_* settings below, matching that
script's main(). Sessions without permutation data have no estim effect and are left off.
All figures are shown and saved to SAVE_DIR.
"""

from __future__ import annotations

import os
import traceback

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr
from matplotlib import pyplot as plt
from clat.util.connection import Connection

from src.analysis.channel_data_loaders import ClusterChannelLoader, SolidPreferenceLoader
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import METRIC_PCT_HYP_VS_DELTA
from src.analysis.nafc.group_analysis.max_estim_per_experiment import _build_max_stat_for_session
from src.pga.stim_types import THREE_D_TEXTURES
from src.startup.startup_system import ExperimentManager

TWO_D_TEXTURE = "2D"

SAVE_DIR = "/home/connorlab/Documents/plots/across_experiments/"

SIGNIFICANCE_ALPHA = 0.05

# Estim effect per session, same settings as max_estim_per_experiment.main().
ESTIM_EFFECT_METRIC = METRIC_PCT_HYP_VS_DELTA
ESTIM_EFFECT_ALGORITHM_LABEL = 'None'
ESTIM_EFFECT_MIN_TRIALS = 10

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


def estim_effect_summary(session_id: str) -> dict:
    """Best-condition estim effect (percentage points) and its max-stat p-value."""
    result = _build_max_stat_for_session(
        session_id, algorithm_label=ESTIM_EFFECT_ALGORITHM_LABEL, metric=ESTIM_EFFECT_METRIC,
        min_trials=ESTIM_EFFECT_MIN_TRIALS, studentize=True)
    if result is None:
        return {"estim_effect": float("nan"), "estim_effect_p": float("nan")}
    return {"estim_effect": result["observed_raw"], "estim_effect_p": result["p_value"]}


def compute_ratio_table(session_ids=None) -> pd.DataFrame:
    """One row per session. Sessions whose GA database can't be read are reported and skipped."""
    repo_conn = Connection("allen_data_repository")
    if session_ids is None:
        session_ids = all_estim_session_ids(repo_conn)

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
            counts.update(estim_effect_summary(sid))
        except Exception:
            print(f"[3d/2d] could not load estim effect for session {sid}:")
            traceback.print_exc()
            counts.update(estim_effect=float("nan"), estim_effect_p=float("nan"))
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


def plot_spi_vs_estim_effect(table: pd.DataFrame, show_stats: bool = False):
    """Scatter of mean GA-channel SPI vs best-condition estim effect, one point per session,
    colored by the session's SPI significance (same colors as the histogram)."""
    data = table.dropna(subset=["mean_spi", "estim_effect"])

    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.axvline(0, color="#888888", linewidth=1, linestyle="--", zorder=0)
    ax.axhline(0, color="#888888", linewidth=1, linestyle="--", zorder=0)
    for g in SPI_SIG_ORDER:
        group = data[data["spi_sig"] == g]
        if group.empty:
            continue
        ax.scatter(group["mean_spi"], group["estim_effect"], s=64, color=SPI_SIG_COLORS[g],
                   edgecolor="white", linewidth=1.5, label=SPI_SIG_LABELS[g], zorder=3)

    if len(data) >= 3:
        rho, p = spearmanr(data["mean_spi"], data["estim_effect"])
        print(f"SPI vs estim effect: Spearman rho = {rho:.2f}, p = {p:.3g} (n = {len(data)})")
    if show_stats and len(data) >= 3:
        ax.text(0.02, 0.97, f"Spearman ρ = {rho:.2f}, p = {p:.3g}", transform=ax.transAxes,
                va="top", ha="left", fontsize=9, color="#444444")

    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0, frameon=False,
              title=f"Combined GA channels, p < {SIGNIFICANCE_ALPHA}")
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Mean solid preference index over GA channels  (2D ← → 3D)")
    ax.set_ylabel("EStim effect, best condition (% points)")
    ax.set_title("Solid preference index vs EStim effect")
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
    # Edit this list to target specific sessions; None = every session in EStimShapeTrials.
    session_ids = None

    table = compute_ratio_table(session_ids)
    if table.empty:
        print("No sessions found.")
        return

    # Pooled row: sums the per-session counts (a stimulus id is only unique within its GA db).
    total = summarize(*(int(table[c].sum()) for c in ("n_3d", "n_2d", "n_unknown")))
    total["category"] = ""
    total["mean_spi"] = table["mean_spi"].mean()
    total["n_spi_channels"] = int(table["n_spi_channels"].sum())
    total.update(spi_z=float("nan"), spi_p=float("nan"), spi_sig="",
                 estim_effect=table["estim_effect"].mean(), estim_effect_p=float("nan"))
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
    if SHOW_PLOTS:
        plt.show()


if __name__ == '__main__':
    main()

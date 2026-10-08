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
histogram across sessions. Both figures are shown and saved to SAVE_DIR.
"""

from __future__ import annotations

import os
import traceback

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from clat.util.connection import Connection

from src.analysis.channel_data_loaders import ClusterChannelLoader, SolidPreferenceLoader
from src.pga.stim_types import THREE_D_TEXTURES
from src.startup.startup_system import ExperimentManager

TWO_D_TEXTURE = "2D"

SAVE_DIR = "/home/connorlab/Documents/plots/across_experiments/"

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


def mean_ga_channel_spi(repo_conn, session_id: str) -> tuple[float, int]:
    """Solid preference index averaged over the session's GA channels, and how many
    GA channels had an SPI. NaN when none did."""
    ga_channels = ClusterChannelLoader(session_id, repo_conn).load()
    spi_by_channel = SolidPreferenceLoader(session_id, repo_conn).load()
    values = [spi_by_channel[ch] for ch in ga_channels
              if ch in spi_by_channel and spi_by_channel[ch] is not None]
    return (float(np.mean(values)) if values else float("nan")), len(values)


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
            counts["mean_spi"], counts["n_spi_channels"] = mean_ga_channel_spi(repo_conn, sid)
        except Exception:
            print(f"[3d/2d] could not load SPI for session {sid}:")
            traceback.print_exc()
            counts["mean_spi"], counts["n_spi_channels"] = float("nan"), 0
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
    """Histogram across sessions of the GA-channel-averaged solid preference index."""
    spi = table["mean_spi"].dropna()

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(spi, bins=np.linspace(-1, 1, 21), color=CATEGORY_COLORS["3D"],
            edgecolor="white", linewidth=2)
    ax.axvline(0, color="#888888", linewidth=1, linestyle="--", zorder=0)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Mean solid preference index over GA channels  (2D ← → 3D)")
    ax.set_ylabel("Sessions")
    ax.set_title(f"Solid preference index per EStim session (n = {len(spi)})")
    ax.yaxis.get_major_locator().set_params(integer=True)
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
    printed = pd.concat([table, pd.DataFrame([{"session_id": "ALL", **total}])], ignore_index=True)

    with pd.option_context("display.max_rows", None, "display.width", 120):
        print(printed.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print()
    print(table["category"].value_counts().to_string())

    save_figure(plot_category_pie(table), "estim_3d_2d_category_pie.png")
    save_figure(plot_spi_histogram(table), "estim_session_spi_histogram.png")
    plt.show()


if __name__ == '__main__':
    main()

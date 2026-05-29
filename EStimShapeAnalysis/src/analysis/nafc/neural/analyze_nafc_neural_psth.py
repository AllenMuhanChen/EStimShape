"""
NAFC neural PSTH: firing-rate histograms aligned to sample_off.

  Rows    : Variant (IsDelta=False) | Delta (IsDelta=True) | Removed (IsRemovedTrial=True)
  Columns : EStim Off | EStim On | EStim On by EStimSpecId
  Lines   : col 0-1: one per semantic choice (Hypothesized/Delta/Removed/Rand)
            col 2  : one per unique EStimSpecId

Semantic choice mapping (mirrors IsHypothesizedField):
  Variant trial  : match→Hypothesized, delta→Delta, *→Rand
  Delta trial    : delta→Hypothesized, match→Delta, *→Rand
  Removed trial  : variant→Hypothesized, match→Removed, *→Rand

t = 0 is sample_off.  Median choices_on / choices_off marked per panel.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.gridspec import GridSpec

from clat.util import time_util

from src.analysis.nafc.neural.analyze_nafc_neural_raster import load_data


# ─────────────────────────── CONFIG ─────────────────────────────────────────
EXP_DB_NAME     = "allen_estimshape_exp_260426_0"
INTAN_BASE_PATH = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_estimshape_exp_260426_0/2026-04-26/"
CHANNEL_NAME    = "A-022"
SINCE_DATE      = time_util.from_date_to_now(2026, 4, 26)
TIME_BEFORE_S   = 0.0    # seconds before sample_off shown on x-axis
TIME_AFTER_S    = 3.0    # seconds after sample_off shown on x-axis
BIN_SIZE_S      = 0.05   # 50 ms bins
SHOW_STD        = True   # shaded ± 1 SEM band
# ────────────────────────────────────────────────────────────────────────────

SEMANTIC_CHOICE_COLORS = {
    "Hypothesized": "tab:green",
    "Delta":        "tab:blue",
    "Removed":      "tab:red",
    "Rand":         "tab:gray",
}

_PANEL_EVENT_DEFS = [
    ("choices_on",  "cornflowerblue", ":",  "Choices On"),
    ("choices_off", "darkorange",     ":",  "Choices Off"),
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _spikes_for_channel(neural: dict, channel_name: str) -> list:
    return neural.get("spikes_by_channel", {}).get(channel_name, [])


def _aligned_spikes(neural: dict, channel_name: str,
                    time_before: float, time_after: float) -> list:
    s_off = neural.get("sample_off")
    if s_off is None:
        return []
    raw = _spikes_for_channel(neural, channel_name)
    return [s - s_off for s in raw if -time_before <= (s - s_off) <= time_after]


def _compute_psth(spike_lists: list, bins: np.ndarray,
                  bin_size: float) -> tuple[np.ndarray, np.ndarray]:
    rates = []
    for spikes in spike_lists:
        counts, _ = np.histogram(spikes, bins=bins)
        rates.append(counts / bin_size)
    if not rates:
        n = len(bins) - 1
        return np.zeros(n), np.zeros(n)
    arr = np.array(rates)
    mean = arr.mean(axis=0)
    sem  = arr.std(axis=0) / np.sqrt(len(arr))
    return mean, sem


def _median_event_rel(group_df, key: str) -> float | None:
    vals = []
    for _, trial in group_df.iterrows():
        neural = trial.get("NeuralData")
        if not isinstance(neural, dict):
            continue
        s_off = neural.get("sample_off")
        t_abs = neural.get(key)
        if s_off is not None and t_abs is not None:
            vals.append(t_abs - s_off)
    return float(np.median(vals)) if vals else None


# ── semantic choice mapping ───────────────────────────────────────────────────

def _semantic_choice(row) -> str:
    is_removed = row.get("IsRemovedTrial", False)
    is_delta   = row.get("IsDelta", False)
    choice     = row.get("Choice", "")
    if is_removed:
        if choice == "variant":
            return "Hypothesized"
        if choice == "match":
            return "Removed"
        if choice == "delta":
            return "Delta"
        return "Rand"
    if is_delta:
        if choice == "delta":
            return "Hypothesized"
        if choice == "delta_distractor":
            # An extra delta of the same variant offered alongside the hypothesized comparison.
            # Distinct from "Rand" so it doesn't get pooled with random distractors.
            return "DeltaDistractor"
        if choice == "match":
            return "Delta"
        if choice == "removed":
            return "Removed"
        return "Rand"
    # variant trial
    if choice == "match":
        return "Hypothesized"
    if choice == "delta":
        return "Delta"
    if choice == "removed":
        return "Removed"
    return "Rand"


# ── colormap for EStimSpecId lines ───────────────────────────────────────────

def _estim_id_colors(estim_ids: list) -> dict:
    cmap = plt.cm.get_cmap("tab20", max(len(estim_ids), 1))
    return {eid: cmap(i) for i, eid in enumerate(estim_ids)}


# ── single-panel PSTH ─────────────────────────────────────────────────────────

def plot_psth_panel(ax, group_df, channel_name: str,
                    time_before: float, time_after: float,
                    bin_size: float, show_std: bool, title: str) -> None:
    bins        = np.arange(-time_before, time_after + bin_size, bin_size)
    bin_centers = bins[:-1] + bin_size / 2

    spikes_by_choice: dict[str, list] = {}
    for _, trial in group_df.iterrows():
        neural = trial.get("NeuralData")
        if not isinstance(neural, dict) or neural.get("sample_off") is None:
            continue
        sem_choice = trial.get("SemanticChoice", "Rand")
        spikes = _aligned_spikes(neural, channel_name, time_before, time_after)
        spikes_by_choice.setdefault(sem_choice, []).append(spikes)

    for sem_choice, spike_lists in sorted(spikes_by_choice.items()):
        color = SEMANTIC_CHOICE_COLORS.get(sem_choice, "tab:purple")
        mean, sem = _compute_psth(spike_lists, bins, bin_size)
        n = len(spike_lists)
        ax.plot(bin_centers, mean, color=color, linewidth=1.8,
                label=f"{sem_choice} (n={n})")
        if show_std and n > 1:
            ax.fill_between(bin_centers, mean - sem, mean + sem,
                            color=color, alpha=0.25, linewidth=0)

    for key, color, linestyle, _ in _PANEL_EVENT_DEFS:
        t_rel = _median_event_rel(group_df, key)
        if t_rel is not None and -time_before <= t_rel <= time_after:
            ax.axvline(t_rel, color=color, linestyle=linestyle,
                       linewidth=1.5, alpha=0.8)

    ax.axvline(0, color="black", linewidth=1.2, linestyle="-", alpha=0.6)
    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.set_xlim(-time_before, time_after)
    ax.set_xlabel("Time from sample_off (s)", fontsize=8)
    ax.set_ylabel("Firing rate (spikes/s)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.4)


def plot_psth_panel_by_estim_id(ax, group_df, channel_name: str,
                                time_before: float, time_after: float,
                                bin_size: float, show_std: bool, title: str) -> None:
    bins        = np.arange(-time_before, time_after + bin_size, bin_size)
    bin_centers = bins[:-1] + bin_size / 2

    spikes_by_estim_id: dict[str, list] = {}
    for _, trial in group_df.iterrows():
        neural = trial.get("NeuralData")
        if not isinstance(neural, dict) or neural.get("sample_off") is None:
            continue
        estim_id = trial.get("EStimSpecId", None)
        label = str(estim_id) if estim_id is not None else "None"
        spikes = _aligned_spikes(neural, channel_name, time_before, time_after)
        spikes_by_estim_id.setdefault(label, []).append(spikes)

    sorted_ids = sorted(spikes_by_estim_id.keys())
    colors = _estim_id_colors(sorted_ids)

    for label in sorted_ids:
        spike_lists = spikes_by_estim_id[label]
        color = colors[label]
        mean, sem = _compute_psth(spike_lists, bins, bin_size)
        n = len(spike_lists)
        ax.plot(bin_centers, mean, color=color, linewidth=1.8,
                label=f"{label} (n={n})")
        if show_std and n > 1:
            ax.fill_between(bin_centers, mean - sem, mean + sem,
                            color=color, alpha=0.25, linewidth=0)

    for key, color, linestyle, _ in _PANEL_EVENT_DEFS:
        t_rel = _median_event_rel(group_df, key)
        if t_rel is not None and -time_before <= t_rel <= time_after:
            ax.axvline(t_rel, color=color, linestyle=linestyle,
                       linewidth=1.5, alpha=0.8)

    ax.axvline(0, color="black", linewidth=1.2, linestyle="-", alpha=0.6)
    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.set_xlim(-time_before, time_after)
    ax.set_xlabel("Time from sample_off (s)", fontsize=8)
    ax.set_ylabel("Firing rate (spikes/s)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6, loc="upper right", title="EStimSpecId", title_fontsize=7)
    ax.grid(True, linestyle="--", alpha=0.4)


# ── figure builder (choice × EStimSpecId) ────────────────────────────────────
# Layout: rows = trial type, cols = semantic choice, lines = EStimSpecId.
# Each panel has a single semantic dimension, so color can be fully dedicated
# to EStimSpecId without needing linestyle tricks.
# To add this as a column to run() instead, pass each pre-filtered group
# to plot_psth_panel_by_estim_id for column 3.

def run_by_choice_and_estim_id(data, channel_name: str, time_before: float,
                                time_after: float, bin_size: float,
                                show_std: bool) -> None:
    data = data.copy()
    data["SemanticChoice"] = data.apply(_semantic_choice, axis=1)

    not_removed = data["IsRemovedTrial"] == False
    is_removed  = data["IsRemovedTrial"] == True
    estim_on    = data["EStimEnabled"] == True

    row_keys   = ["variant",               "delta",                           "removed"]
    row_labels = ["Variant\n(IsDelta=False)", "Delta\n(IsDelta=True)", "Removed\n(IsRemovedTrial=True)"]
    row_masks  = [
        not_removed & (data["IsDelta"] == False) & estim_on,
        not_removed & (data["IsDelta"] == True)  & estim_on,
        is_removed  & estim_on,
    ]

    sem_choices = list(SEMANTIC_CHOICE_COLORS.keys())  # Hypothesized, Delta, Removed, Rand

    fig = plt.figure(figsize=(22, 10))
    gs  = GridSpec(3, 4, figure=fig, hspace=0.5, wspace=0.35)

    all_axes = []
    for r, (row_label, row_mask) in enumerate(zip(row_labels, row_masks)):
        row_data = data[row_mask]
        for c, sem_choice in enumerate(sem_choices):
            ax = fig.add_subplot(gs[r, c])
            grp = row_data[row_data["SemanticChoice"] == sem_choice]
            title = sem_choice if r == 0 else ""
            plot_psth_panel_by_estim_id(ax, grp, channel_name,
                                        time_before, time_after, bin_size, show_std, title)
            if c == 0:
                ax.set_ylabel(f"{row_label}\n\nFiring rate (spikes/s)", fontsize=8)
            all_axes.append(ax)

    global_ymax = max(ax.get_ylim()[1] for ax in all_axes)
    for ax in all_axes:
        ax.set_ylim(bottom=0, top=global_ymax)

    fig.suptitle(
        f"NAFC Neural PSTH — channel: {channel_name}  ·  EStim On only\n"
        f"Rows: trial type  ·  Cols: semantic choice  ·  Lines: EStimSpecId",
        fontsize=11,
    )
    plt.tight_layout()
    plt.show()


# ── legend ────────────────────────────────────────────────────────────────────

def _legend_handles():
    handles = [
        mlines.Line2D([], [], color=c, linewidth=1.8, label=name)
        for name, c in SEMANTIC_CHOICE_COLORS.items()
    ]
    handles.append(
        mlines.Line2D([], [], color="black", linestyle="-",
                      linewidth=1.2, label="Sample Off (t=0)")
    )
    for _, color, linestyle, label in _PANEL_EVENT_DEFS:
        handles.append(
            mlines.Line2D([], [], color=color, linestyle=linestyle,
                          linewidth=1.2, label=f"{label} (median)")
        )
    return handles


# ── figure builder ────────────────────────────────────────────────────────────

def run(data, channel_name: str, time_before: float, time_after: float,
        bin_size: float, show_std: bool) -> None:
    data = data.copy()
    data["SemanticChoice"] = data.apply(_semantic_choice, axis=1)

    not_removed = data["IsRemovedTrial"] == False
    is_removed  = data["IsRemovedTrial"] == True

    choice_groups = {
        ("variant", False): ("Variant · EStim Off", data[not_removed & (data["IsDelta"] == False) & (data["EStimEnabled"] == False)]),
        ("variant", True):  ("Variant · EStim On",  data[not_removed & (data["IsDelta"] == False) & (data["EStimEnabled"] == True)]),
        ("delta",   False): ("Delta · EStim Off",   data[not_removed & (data["IsDelta"] == True)  & (data["EStimEnabled"] == False)]),
        ("delta",   True):  ("Delta · EStim On",    data[not_removed & (data["IsDelta"] == True)  & (data["EStimEnabled"] == True)]),
        ("removed", False): ("Removed · EStim Off", data[is_removed  & (data["EStimEnabled"] == False)]),
        ("removed", True):  ("Removed · EStim On",  data[is_removed  & (data["EStimEnabled"] == True)]),
    }
    estim_id_groups = {
        "variant": ("Variant · By EStimSpecId", data[not_removed & (data["IsDelta"] == False) & (data["EStimEnabled"] == True)]),
        "delta":   ("Delta · By EStimSpecId",   data[not_removed & (data["IsDelta"] == True)  & (data["EStimEnabled"] == True)]),
        "removed": ("Removed · By EStimSpecId", data[is_removed  & (data["EStimEnabled"] == True)]),
    }

    fig = plt.figure(figsize=(20, 12))
    gs  = GridSpec(3, 3, figure=fig, hspace=0.5, wspace=0.35)

    col_labels = ["EStim Off", "EStim On", "EStim On · by EStimSpecId"]
    row_keys   = ["variant", "delta", "removed"]
    row_labels = ["Variant\n(IsDelta=False)", "Delta\n(IsDelta=True)", "Removed\n(IsRemovedTrial=True)"]

    all_axes = []
    for r, (row_key, row_label) in enumerate(zip(row_keys, row_labels)):
        for c, estim_on in enumerate([False, True]):
            ax = fig.add_subplot(gs[r, c])
            label, grp = choice_groups[(row_key, estim_on)]
            full_title = f"{col_labels[c]}\n{label}" if r == 0 else label
            plot_psth_panel(ax, grp, channel_name,
                            time_before, time_after, bin_size, show_std, full_title)
            if c == 0:
                ax.set_ylabel(f"{row_label}\n\nFiring rate (spikes/s)", fontsize=8)
            all_axes.append(ax)

        ax3 = fig.add_subplot(gs[r, 2])
        label3, grp3 = estim_id_groups[row_key]
        full_title3 = f"{col_labels[2]}\n{label3}" if r == 0 else label3
        plot_psth_panel_by_estim_id(ax3, grp3, channel_name,
                                    time_before, time_after, bin_size, show_std, full_title3)
        all_axes.append(ax3)

    global_ymax = max(ax.get_ylim()[1] for ax in all_axes)
    for ax in all_axes:
        ax.set_ylim(bottom=0, top=global_ymax)

    fig.legend(handles=_legend_handles(), loc="upper right", fontsize=8,
               bbox_to_anchor=(0.99, 0.99), framealpha=0.9)
    fig.suptitle(
        f"NAFC Neural PSTH — channel: {channel_name}\n"
        f"Aligned to sample_off  ·  Rows: Variant / Delta / Removed  ·"
        f"  Cols: EStim Off / EStim On (by choice) / EStim On (by EStimSpecId)",
        fontsize=11,
    )
    plt.tight_layout()
    plt.show()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    data, err = load_data(EXP_DB_NAME, INTAN_BASE_PATH, SINCE_DATE)
    if err or data.empty:
        print(err or "No matching trials — check EXP_DB_NAME / SINCE_DATE.")
        return
    run(data, CHANNEL_NAME, TIME_BEFORE_S, TIME_AFTER_S, BIN_SIZE_S, SHOW_STD)


if __name__ == "__main__":
    main()

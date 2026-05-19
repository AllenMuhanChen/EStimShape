"""
NAFC neural PSTH: firing-rate histograms aligned to sample_off.

  Rows    : Variant (IsDelta=False) | Delta (IsDelta=True) | Removed (IsRemovedTrial=True)
  Columns : EStim Off | EStim On
  Lines   : one per choice (match / delta / rand / procedural)

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

CHOICE_COLORS = {
    "match":      "tab:green",
    "delta":      "tab:blue",
    "rand":       "tab:gray",
    "procedural": "tab:orange",
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
        choice = trial.get("Choice", "None")
        spikes = _aligned_spikes(neural, channel_name, time_before, time_after)
        spikes_by_choice.setdefault(choice, []).append(spikes)

    for choice, spike_lists in sorted(spikes_by_choice.items()):
        color = CHOICE_COLORS.get(choice, "tab:purple")
        mean, sem = _compute_psth(spike_lists, bins, bin_size)
        n = len(spike_lists)
        ax.plot(bin_centers, mean, color=color, linewidth=1.8,
                label=f"{choice} (n={n})")
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


# ── legend ────────────────────────────────────────────────────────────────────

def _legend_handles():
    handles = [
        mlines.Line2D([], [], color=c, linewidth=1.8, label=name)
        for name, c in CHOICE_COLORS.items()
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
    not_removed = data["IsRemovedTrial"] == False
    is_removed  = data["IsRemovedTrial"] == True

    groups = {
        ("variant", False): ("Variant · EStim Off", data[not_removed & (data["IsDelta"] == False) & (data["EStimEnabled"] == False)]),
        ("variant", True):  ("Variant · EStim On",  data[not_removed & (data["IsDelta"] == False) & (data["EStimEnabled"] == True)]),
        ("delta",   False): ("Delta · EStim Off",   data[not_removed & (data["IsDelta"] == True)  & (data["EStimEnabled"] == False)]),
        ("delta",   True):  ("Delta · EStim On",    data[not_removed & (data["IsDelta"] == True)  & (data["EStimEnabled"] == True)]),
        ("removed", False): ("Removed · EStim Off", data[is_removed  & (data["EStimEnabled"] == False)]),
        ("removed", True):  ("Removed · EStim On",  data[is_removed  & (data["EStimEnabled"] == True)]),
    }

    fig = plt.figure(figsize=(14, 12))
    gs  = GridSpec(3, 2, figure=fig, hspace=0.5, wspace=0.35)

    col_labels = ["EStim Off", "EStim On"]
    row_keys   = ["variant", "delta", "removed"]
    row_labels = ["Variant\n(IsDelta=False)", "Delta\n(IsDelta=True)", "Removed\n(IsRemovedTrial=True)"]

    all_axes = []
    for r, (row_key, row_label) in enumerate(zip(row_keys, row_labels)):
        for c, estim_on in enumerate([False, True]):
            ax = fig.add_subplot(gs[r, c])
            label, grp = groups[(row_key, estim_on)]
            full_title = f"{col_labels[c]}\n{label}" if r == 0 else label
            plot_psth_panel(ax, grp, channel_name,
                            time_before, time_after, bin_size, show_std, full_title)
            if c == 0:
                ax.set_ylabel(f"{row_label}\n\nFiring rate (spikes/s)", fontsize=8)
            all_axes.append(ax)

    global_ymax = max(ax.get_ylim()[1] for ax in all_axes)
    for ax in all_axes:
        ax.set_ylim(bottom=0, top=global_ymax)

    fig.legend(handles=_legend_handles(), loc="upper right", fontsize=8,
               bbox_to_anchor=(0.99, 0.99), framealpha=0.9)
    fig.suptitle(
        f"NAFC Neural PSTH — channel: {channel_name}\n"
        f"Aligned to sample_off  ·  Rows: Variant / Delta / Removed  ·  Cols: EStim Off / On",
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

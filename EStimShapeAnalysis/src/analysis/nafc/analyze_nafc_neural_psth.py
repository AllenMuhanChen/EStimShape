"""
NAFC neural PSTH: firing-rate histograms aligned to sample_off.

Same 2×2 layout as the raster analysis:
  Rows    : Variant (IsDelta=False) | Delta (IsDelta=True)
  Columns : EStim Off | EStim On

Each panel overlays two PSTH lines:
  green = Correct trials  |  red = Incorrect trials
  shaded band = ± 1 SEM

t = 0 is sample_off.  Median choices_on / choices_off are marked per panel.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.gridspec import GridSpec

from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    ChoiceField, IsCorrectField, StimTypeField,
    BaseMStickIdField, IsDeltaField, EStimEnabledField,
)
from src.analysis.nafc.nafc_neural_database_fields import NafcNeuralDataField
from src.analysis.nafc.psychometric_curves import collect_choice_trials
from src.startup import context


# ─────────────────────────── CONFIG ─────────────────────────────────────────
EXP_DB_NAME     = "allen_estimshape_exp_260426_0"
INTAN_BASE_PATH = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_estimshape_exp_260426_0/2026-04-26/"
CHANNEL_NAME    = "A-000"
SINCE_DATE      = time_util.from_date_to_now(2026, 4, 26)
TIME_BEFORE_S   = 0.1    # seconds before sample_off shown on x-axis
TIME_AFTER_S    = 3.0    # seconds after sample_off shown on x-axis
BIN_SIZE_S      = 0.05   # 50 ms bins
SHOW_STD        = True   # shaded ± 1 SEM band
# ────────────────────────────────────────────────────────────────────────────

CHOICE_COLORS = {
    "match":       "tab:green",
    "delta":       "tab:blue",
    "rand":        "tab:gray",
    "procedural":  "tab:orange",
}

_PANEL_EVENT_DEFS = [
    # (neural_key, color, linestyle, legend_label)
    ("choices_on",  "cornflowerblue", ":",  "Choices On"),
    ("choices_off", "darkorange",     ":",  "Choices Off"),
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _spikes_for_channel(neural: dict, channel_name: str) -> list:
    return neural.get("spikes_by_channel", {}).get(channel_name, [])


def _aligned_spikes(neural: dict, channel_name: str,
                    time_before: float, time_after: float) -> list:
    """Return spike times relative to sample_off, clipped to window."""
    s_off = neural.get("sample_off")
    if s_off is None:
        return []
    raw = _spikes_for_channel(neural, channel_name)
    return [s - s_off for s in raw if -time_before <= (s - s_off) <= time_after]


def _compute_psth(spike_lists: list, bins: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (mean_rate, sem_rate) in spikes/s.
    spike_lists: list of per-trial aligned spike lists.
    """
    rates = []
    for spikes in spike_lists:
        counts, _ = np.histogram(spikes, bins=bins)
        rates.append(counts / BIN_SIZE_S)
    if not rates:
        n = len(bins) - 1
        return np.zeros(n), np.zeros(n)
    arr = np.array(rates)
    mean = arr.mean(axis=0)
    sem  = arr.std(axis=0) / np.sqrt(len(arr))
    return mean, sem


def _median_event_rel(group_df, key: str) -> float | None:
    """Median of (event_abs - sample_off) across trials that have both."""
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
                    bin_size: float, title: str) -> None:
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
        mean, sem = _compute_psth(spike_lists, bins)
        n = len(spike_lists)
        ax.plot(bin_centers, mean, color=color, linewidth=1.8,
                label=f"{choice} (n={n})")
        if SHOW_STD and n > 1:
            ax.fill_between(bin_centers, mean - sem, mean + sem,
                            color=color, alpha=0.25, linewidth=0)

    # Median event markers
    for key, color, linestyle, _ in _PANEL_EVENT_DEFS:
        t_rel = _median_event_rel(group_df, key)
        if t_rel is not None and -time_before <= t_rel <= time_after:
            ax.axvline(t_rel, color=color, linestyle=linestyle,
                       linewidth=1.5, alpha=0.8)

    # sample_off reference
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


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    exp_conn = Connection(EXP_DB_NAME)

    trial_tstamps = collect_choice_trials(exp_conn, SINCE_DATE)
    if not trial_tstamps:
        print("No trials found.")
        return

    fields = CachedFieldList()
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(NafcNeuralDataField(INTAN_BASE_PATH, exp_conn))

    data = fields.to_data(trial_tstamps)
    data = data[data["StimType"] == "EStimShapeVariantsDeltaNAFCStim"].copy()
    print(f"{len(data)} EStimShapeVariantsDeltaNAFCStim trials")
    if data.empty:
        print("No matching trials — check EXP_DB_NAME / SINCE_DATE.")
        return

    groups = {
        (False, False): ("Variant · EStim Off", data[(data["IsDelta"] == False) & (data["EStimEnabled"] == False)]),
        (False, True):  ("Variant · EStim On",  data[(data["IsDelta"] == False) & (data["EStimEnabled"] == True)]),
        (True,  False): ("Delta · EStim Off",   data[(data["IsDelta"] == True)  & (data["EStimEnabled"] == False)]),
        (True,  True):  ("Delta · EStim On",    data[(data["IsDelta"] == True)  & (data["EStimEnabled"] == True)]),
    }

    for key, (label, grp) in groups.items():
        print(f"  {label}: {len(grp)} trials")

    fig = plt.figure(figsize=(14, 8))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.5, wspace=0.35)

    col_labels = ["EStim Off", "EStim On"]
    row_labels = ["Variant\n(IsDelta=False)", "Delta\n(IsDelta=True)"]

    for r, is_delta in enumerate([False, True]):
        for c, estim_on in enumerate([False, True]):
            ax = fig.add_subplot(gs[r, c])
            label, grp = groups[(is_delta, estim_on)]
            full_title = f"{col_labels[c]}\n{label}" if r == 0 else label
            plot_psth_panel(ax, grp, CHANNEL_NAME,
                            TIME_BEFORE_S, TIME_AFTER_S, BIN_SIZE_S, full_title)
            if c == 0:
                ax.set_ylabel(f"{row_labels[r]}\n\nFiring rate (spikes/s)", fontsize=8)

    fig.legend(
        handles=_legend_handles(),
        loc="upper right",
        fontsize=8,
        bbox_to_anchor=(0.99, 0.99),
        framealpha=0.9,
    )
    fig.suptitle(
        f"NAFC Neural PSTH — channel: {CHANNEL_NAME}\n"
        f"Aligned to sample_off  ·  Rows: Variant / Delta  ·  Cols: EStim Off / On",
        fontsize=11,
    )
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()

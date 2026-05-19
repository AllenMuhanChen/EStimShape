"""
NAFC neural raster: spike activity for EStimShapeVariantsDeltaNAFCStim trials.

  Rows      : Variant (IsDelta=False) | Delta (IsDelta=True) | Removed (IsRemovedTrial=True)
  Columns   : EStim Off | EStim On
  Tick color: by choice (match / delta / rand / procedural)

X-axis aligned to sample_on.  Per-trial lines mark sample_off, choices_on, choices_off.
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
    BaseMStickIdField, IsDeltaField, EStimEnabledField, IsRemovedTrialField, EStimSpecIdField,
)
from src.analysis.nafc.nafc_neural_database_fields import NafcNeuralDataField
from src.analysis.nafc.psychometric_curves import collect_choice_trials


# ─────────────────────────── CONFIG ─────────────────────────────────────────
EXP_DB_NAME     = "allen_estimshape_exp_260426_0"
INTAN_BASE_PATH = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_estimshape_exp_260426_0/2026-04-26/"
CHANNEL_NAME    = "A-022"
SINCE_DATE      = time_util.from_date_to_now(2026, 4, 26)
TIME_BEFORE_S   = 0.2   # seconds before sample_on
TIME_AFTER_S    = 1.5   # seconds after sample_on
# ────────────────────────────────────────────────────────────────────────────

CHOICE_COLORS = {
    "match":      "tab:green",
    "delta":      "tab:blue",
    "rand":       "tab:gray",
    "procedural": "tab:orange",
}

_EVENT_DEFS = [
    ("sample_off",  "gray",            "--", "Sample Off"),
    ("choices_on",  "cornflowerblue",  ":",  "Choices On"),
    ("choices_off", "darkorange",      ":",  "Choices Off"),
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _spikes_for_channel(neural: dict, channel_name: str) -> list:
    if not isinstance(neural, dict):
        return []
    return neural.get('spikes_by_channel', {}).get(channel_name, [])


# ── single-panel raster ───────────────────────────────────────────────────────

def plot_raster_panel(ax, group_df, channel_name: str,
                      time_before: float, time_after: float, title: str) -> None:
    ax.set_title(title, fontsize=9, fontweight="bold")
    counts_by_choice: dict[str, int] = {}

    for row_idx, (_, trial) in enumerate(group_df.iterrows()):
        neural = trial.get("NeuralData")
        if not isinstance(neural, dict) or neural.get('sample_on') is None:
            continue

        s_on   = neural['sample_on']
        choice = trial.get("Choice", "None")
        tick_color = CHOICE_COLORS.get(choice, "tab:purple")
        counts_by_choice[choice] = counts_by_choice.get(choice, 0) + 1

        raw_spikes = _spikes_for_channel(neural, channel_name)
        aligned = [s - s_on for s in raw_spikes
                   if -time_before <= (s - s_on) <= time_after]
        if aligned:
            ax.vlines(aligned, row_idx + 0.05, row_idx + 0.95,
                      color=tick_color, linewidth=0.8, alpha=0.9)

        for attr, color, linestyle, _ in _EVENT_DEFS:
            t_abs = neural.get(attr)
            if t_abs is not None:
                t_rel = t_abs - s_on
                ax.vlines([t_rel], row_idx, row_idx + 1,
                          color=color, linewidth=1.5, linestyle=linestyle, alpha=0.7)

    n_total = len(group_df)
    ax.axvline(0, color="black", linewidth=1.2, linestyle="-", alpha=0.6)
    ax.set_xlim(-time_before, time_after)
    ax.set_ylim(0, max(n_total, 1))
    ax.set_xlabel("Time from sample_on (s)", fontsize=8)
    ax.set_ylabel("Trial", fontsize=8)
    ax.tick_params(labelsize=7)
    summary = "  ".join(f"{k}={v}" for k, v in sorted(counts_by_choice.items()))
    ax.text(0.02, 0.98, f"n={n_total}  {summary}",
            transform=ax.transAxes, fontsize=7, va="top", color="black")


# ── legend ────────────────────────────────────────────────────────────────────

def _legend_handles():
    handles = [
        mlines.Line2D([], [], color=c, linewidth=1.5, label=name)
        for name, c in CHOICE_COLORS.items()
    ]
    handles.append(
        mlines.Line2D([], [], color="black", linestyle="-",
                      linewidth=1.2, label="Sample On (t=0)")
    )
    for _, color, linestyle, label in _EVENT_DEFS:
        handles.append(
            mlines.Line2D([], [], color=color, linestyle=linestyle,
                          linewidth=0.8, label=label)
        )
    return handles


# ── figure builder ────────────────────────────────────────────────────────────

def run(data, channel_name: str, time_before: float, time_after: float) -> None:
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

    row_keys   = ["variant", "delta", "removed"]
    row_labels = ["Variant\n(IsDelta=False)", "Delta\n(IsDelta=True)", "Removed\n(IsRemovedTrial=True)"]

    n_rows = [max(len(groups[(k, False)][1]), len(groups[(k, True)][1]), 1) for k in row_keys]
    fig_height = max(8, sum(n_rows) * 0.2 + 3)

    fig = plt.figure(figsize=(14, fig_height))
    gs  = GridSpec(3, 2, figure=fig,
                   height_ratios=n_rows,
                   hspace=0.45, wspace=0.35)

    col_labels = ["EStim Off", "EStim On"]

    for r, (row_key, row_label) in enumerate(zip(row_keys, row_labels)):
        for c, estim_on in enumerate([False, True]):
            ax = fig.add_subplot(gs[r, c])
            label, grp = groups[(row_key, estim_on)]
            full_title = f"{col_labels[c]}\n{label}" if r == 0 else label
            plot_raster_panel(ax, grp, channel_name, time_before, time_after, full_title)
            if c == 0:
                ax.set_ylabel(f"{row_label}\n\nTrial", fontsize=8)

    fig.legend(handles=_legend_handles(), loc="upper right", fontsize=8,
               bbox_to_anchor=(0.99, 0.99), framealpha=0.9)
    fig.suptitle(
        f"NAFC Neural Raster — channel: {channel_name}\n"
        f"Rows: Variant / Delta / Removed  ·  Cols: EStim Off / On  ·  Colors: choice",
        fontsize=11,
    )
    plt.tight_layout()
    plt.show()


# ── main ──────────────────────────────────────────────────────────────────────

def load_data(exp_db_name: str, intan_base_path: str, since_date):
    exp_conn = Connection(exp_db_name)
    trial_tstamps = collect_choice_trials(exp_conn, since_date)
    if not trial_tstamps:
        return None, "No trials found."

    fields = CachedFieldList()
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    fields.append(IsRemovedTrialField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(EStimSpecIdField(exp_conn))
    fields.append(NafcNeuralDataField(intan_base_path, exp_conn))

    data = fields.to_data(trial_tstamps)
    # data = data[data["StimType"] == "EStimShapeVariantsDeltaNAFCStim"].copy()
    print(f"{len(data)} EStimShapeVariantsDeltaNAFCStim trials")
    return data, None


def main():
    data, err = load_data(EXP_DB_NAME, INTAN_BASE_PATH, SINCE_DATE)
    if err or data.empty:
        print(err or "No matching trials — check EXP_DB_NAME / SINCE_DATE.")
        return
    run(data, CHANNEL_NAME, TIME_BEFORE_S, TIME_AFTER_S)


if __name__ == "__main__":
    main()

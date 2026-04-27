"""
NAFC neural raster: spike activity for EStimShapeVariantsDeltaNAFCStim trials.

3 binary conditions mapped to visual dimensions:
  Rows      : Variant (IsDelta=False) | Delta (IsDelta=True)
  Columns   : EStim Off | EStim On
  Tick color: green = Correct  |  red = Incorrect

X-axis is time aligned to sample_on (sample_on → t = 0 s).
Per-trial thin lines mark sample_off, choices_on, choices_off.
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
from src.analysis.nafc.nafc_neural_parser import NafcTrialEvents
from src.analysis.nafc.psychometric_curves import collect_choice_trials
from src.startup import context


# ─────────────────────────── CONFIG ─────────────────────────────────────────
EXP_DB_NAME     = "allen_estimshape_exp_260426_0"
INTAN_BASE_PATH = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_estimshape_exp_260426_0/2026-04-26/"  # flat dir of {task_id}_* folders
CHANNEL_NAME    = "A-000"                            # Channel.value string to display
SINCE_DATE      = time_util.from_date_to_now(2026, 4, 26)
TIME_BEFORE_S   = 0.2   # seconds before sample_on shown on x-axis
TIME_AFTER_S    = 1.5   # seconds after sample_on shown on x-axis
# ────────────────────────────────────────────────────────────────────────────

COLOR_CORRECT   = "tab:green"
COLOR_INCORRECT = "tab:red"

_EVENT_DEFS = [
    # (attr_name, color, linestyle, legend_label)
    ("sample_off",  "gray",         "--", "Sample Off"),
    ("choices_on",  "cornflowerblue", ":", "Choices On"),
    ("choices_off", "darkorange",    ":", "Choices Off"),
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _spikes_for_channel(neural: NafcTrialEvents, channel_name: str) -> list:
    if neural is None:
        return []
    for ch, spikes in neural.spikes_by_channel.items():
        if getattr(ch, "value", str(ch)) == channel_name or str(ch) == channel_name:
            return list(spikes)
    return []


def _is_correct(trial) -> bool:
    v = trial.get("IsCorrect")
    return v is True


# ── single-panel raster ───────────────────────────────────────────────────────

def plot_raster_panel(ax, group_df, channel_name: str,
                      time_before: float, time_after: float, title: str) -> None:
    """
    Draw one raster panel.  Each row = one trial.
    Spike ticks colored by correctness; per-trial event markers as thin lines.
    """
    ax.set_title(title, fontsize=9, fontweight="bold")
    n_correct = n_incorrect = 0

    for row_idx, (_, trial) in enumerate(group_df.iterrows()):
        neural: NafcTrialEvents = trial.get("NeuralData")
        if neural is None or neural.sample_on is None:
            continue

        s_on = neural.sample_on
        correct = _is_correct(trial)
        tick_color = COLOR_CORRECT if correct else COLOR_INCORRECT
        if correct:
            n_correct += 1
        else:
            n_incorrect += 1

        # Spikes aligned to sample_on, windowed
        raw_spikes = _spikes_for_channel(neural, channel_name)
        aligned = [s - s_on for s in raw_spikes
                   if -time_before <= (s - s_on) <= time_after]
        if aligned:
            ax.vlines(aligned, row_idx + 0.05, row_idx + 0.95,
                      color=tick_color, linewidth=0.8, alpha=0.9)

        # Per-trial event markers
        for attr, color, linestyle, _ in _EVENT_DEFS:
            t_abs = getattr(neural, attr, None)
            if t_abs is not None:
                t_rel = t_abs - s_on
                ax.vlines([t_rel], row_idx, row_idx + 1,
                          color=color, linewidth=0.6, linestyle=linestyle, alpha=0.4)

    n_total = len(group_df)
    ax.axvline(0, color="black", linewidth=1.2, linestyle="-", alpha=0.6)
    ax.set_xlim(-time_before, time_after)
    ax.set_ylim(0, max(n_total, 1))
    ax.set_xlabel("Time from sample_on (s)", fontsize=8)
    ax.set_ylabel("Trial", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.text(0.02, 0.98,
            f"n={n_total}  correct={n_correct}  incorrect={n_incorrect}",
            transform=ax.transAxes, fontsize=7, va="top", color="black")


# ── legend ────────────────────────────────────────────────────────────────────

def _legend_handles():
    handles = [
        mlines.Line2D([], [], color=COLOR_CORRECT,  linewidth=1.5, label="Correct"),
        mlines.Line2D([], [], color=COLOR_INCORRECT, linewidth=1.5, label="Incorrect"),
        mlines.Line2D([], [], color="black", linestyle="-",  linewidth=1.2, label="Sample On (t=0)"),
    ]
    for _, color, linestyle, label in _EVENT_DEFS:
        handles.append(
            mlines.Line2D([], [], color=color, linestyle=linestyle,
                          linewidth=0.8, label=label)
        )
    return handles


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    exp_conn = Connection(EXP_DB_NAME)

    trial_tstamps = collect_choice_trials(exp_conn, SINCE_DATE)
    if not trial_tstamps:
        print("No trials found.")
        return

    # Child fields must come after their parents so get_cached_super finds them.
    fields = CachedFieldList()
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))          # required by IsCorrectField
    fields.append(IsCorrectField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))    # required by IsDeltaField
    fields.append(IsDeltaField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(NafcNeuralDataField(INTAN_BASE_PATH, exp_conn))

    data = fields.to_data(trial_tstamps)
    data = data[data["StimType"] == "EStimShapeVariantsDeltaNAFCStim"].copy()
    print(f"{len(data)} EStimShapeVariantsDeltaNAFCStim trials")
    if data.empty:
        print("No matching trials — check EXP_DB_NAME / SINCE_DATE.")
        return

    # 2×2 groups: rows=IsDelta, cols=EStimEnabled
    groups = {
        (False, False): ("Variant · EStim Off", data[(data["IsDelta"] == False) & (data["EStimEnabled"] == False)]),
        (False, True):  ("Variant · EStim On",  data[(data["IsDelta"] == False) & (data["EStimEnabled"] == True)]),
        (True,  False): ("Delta · EStim Off",   data[(data["IsDelta"] == True)  & (data["EStimEnabled"] == False)]),
        (True,  True):  ("Delta · EStim On",    data[(data["IsDelta"] == True)  & (data["EStimEnabled"] == True)]),
    }

    for key, (label, grp) in groups.items():
        print(f"  {label}: {len(grp)} trials")

    # Figure height scales with trial counts so rows stay readable
    n_row0 = max(len(groups[(False, False)][1]), len(groups[(False, True)][1]), 1)
    n_row1 = max(len(groups[(True,  False)][1]), len(groups[(True,  True)][1]), 1)
    fig_height = max(6, (n_row0 + n_row1) * 0.2 + 3)

    fig = plt.figure(figsize=(14, fig_height))
    gs  = GridSpec(2, 2, figure=fig,
                   height_ratios=[n_row0, n_row1],
                   hspace=0.45, wspace=0.35)

    col_labels = ["EStim Off", "EStim On"]
    row_labels = ["Variant\n(IsDelta=False)", "Delta\n(IsDelta=True)"]

    for r, is_delta in enumerate([False, True]):
        for c, estim_on in enumerate([False, True]):
            ax = fig.add_subplot(gs[r, c])
            label, grp = groups[(is_delta, estim_on)]

            # Column header on top row
            full_title = f"{col_labels[c]}\n{label}" if r == 0 else label
            plot_raster_panel(ax, grp, CHANNEL_NAME, TIME_BEFORE_S, TIME_AFTER_S, full_title)

            # Row label on left column
            if c == 0:
                ax.set_ylabel(f"{row_labels[r]}\n\nTrial", fontsize=8)

    fig.legend(
        handles=_legend_handles(),
        loc="upper right",
        fontsize=8,
        bbox_to_anchor=(0.99, 0.99),
        framealpha=0.9,
    )
    fig.suptitle(
        f"NAFC Neural Raster — channel: {CHANNEL_NAME}\n"
        f"Rows: Variant / Delta  ·  Cols: EStim Off / On  ·  Colors: Correct / Incorrect",
        fontsize=11,
    )
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()

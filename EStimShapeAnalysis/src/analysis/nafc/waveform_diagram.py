"""
Stimulus timing diagram.

Row 1: Visual stimulus envelope  (ms, shared axis with row 2)
Row 2: Microstimulation envelope (ms)
Row 3: Single biphasic/triphasic current pulse (µs, independent axis)

To add row 3, pass session_id + estim_spec_id; it reads EStimParameters from
allen_data_repository and finds the first channel with a1 > 0 (skipping
grounding channels that have zero current but active charge recovery).
"""

import os
import sys
from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import numpy as np
from matplotlib import pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from clat.util.connection import Connection

_REPO_DB = "allen_data_repository"
_BLACK   = "#111111"
_GRAY    = "#888888"
_LINE_W  = 1.8
_LABEL_FS = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _square_pulse(t_on: float, t_off: float, t_min: float, t_max: float):
    """(t, y) arrays for a crisp square pulse — exact vertical edges."""
    eps = 1e-6
    t = [t_min, t_on - eps, t_on, t_off, t_off + eps, t_max]
    y = [0.0,   0.0,        1.0,  1.0,   0.0,          0.0]
    return np.array(t), np.array(y)


def _style_envelope_ax(ax):
    """Strip all spines and ticks from an envelope row."""
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_yticks([])
    ax.tick_params(which="both", bottom=False, top=False,
                   labelbottom=False, labeltop=False)


def _load_estim_params(session_id: str, estim_spec_id: int) -> dict | None:
    """Return parameters for the first channel with a1 > 0 (skips grounding channels)."""
    conn = Connection(_REPO_DB)
    conn.execute(
        "SELECT shape, polarity, d1, d2, dp, a1, a2, "
        "       pulse_repetition, num_repetitions, pulse_train_period, "
        "       post_stim_refractory_period "
        "FROM EStimParameters "
        "WHERE session_id = %s AND estim_spec_id = %s "
        "ORDER BY channel",
        (session_id, estim_spec_id),
    )
    for row in conn.fetch_all():
        a1 = row[5]
        if a1 is not None and float(a1) > 0:
            return dict(
                shape=row[0],
                polarity=row[1],
                d1=float(row[2] or 0),
                d2=float(row[3] or 0),
                dp=float(row[4] or 0),
                a1=float(row[5]),
                a2=float(row[6] or 0),
                pulse_repetition=row[7],
                num_repetitions=int(row[8]) if row[8] else 1,
                pulse_train_period=float(row[9] or 0),
                post_stim_refractory_period=float(row[10] or 0),
            )
    return None


def _pulse_train_waveform(p: dict, n_show: int = 3):
    """
    Concatenate n_show pulses separated by post_stim_refractory_period.
    The inter-pulse onset interval is pulse_duration + post_stim_refractory_period.
    Each pulse ends at y=0 and the next starts at y=0, so matplotlib
    draws the flat inter-pulse baseline automatically without extra points.
    """
    t_single, y_single = _biphasic_waveform(p)
    pulse_dur  = t_single[-1]
    refractory = p.get("post_stim_refractory_period") or 0.0
    period     = pulse_dur + refractory

    if period <= pulse_dur or n_show <= 1:
        return t_single, y_single

    t_parts = [t_single + i * period for i in range(n_show)]
    y_parts = [y_single] * n_show
    return np.concatenate(t_parts), np.concatenate(y_parts)


def _biphasic_waveform(p: dict):
    """
    Build (t, y) in (µs, µA) for one biphasic / BiphasicWithInterphaseDelay pulse.
    Duplicate x-values produce exact vertical step edges.
    """
    sign1 = -1 if p["polarity"] == "NegativeFirst" else +1
    sign2 = -sign1
    d1, d2 = p["d1"], p["d2"]
    dp = p["dp"] if p["shape"] == "BiphasicWithInterphaseDelay" else 0.0
    a1, a2 = p["a1"], p["a2"]

    t = [0,    0,        d1,       d1,  d1 + dp,  d1 + dp,  d1 + dp + d2, d1 + dp + d2]
    y = [0, sign1*a1, sign1*a1,     0,       0,  sign2*a2,  sign2*a2,            0    ]
    return np.array(t, float), np.array(y, float)


# ---------------------------------------------------------------------------
# Main plot function
# ---------------------------------------------------------------------------

def plot_timing_diagram(
    visual_start:  float = 0,
    visual_end:    float = 500,
    estim_start:   float = 100,
    estim_end:     float = 500,
    pre_time:      float = -100,
    post_time:     float = 600,
    session_id:      str = None,
    estim_spec_id:   int = None,
    n_pulses_shown:  int = 3,
    save_path:       str = None,
):
    params = None
    if session_id is not None and estim_spec_id is not None:
        params = _load_estim_params(session_id, estim_spec_id)
        if params is None:
            print(f"WARNING: no non-zero channel found for "
                  f"session={session_id} spec={estim_spec_id}. Skipping waveform row.")

    show_waveform = params is not None

    # ------------------------------------------------------------------
    # Figure + gridspec
    # Rows 0 & 1 live in a tight inner gridspec; row 2 (waveform) gets
    # its own outer cell so the gap between the two sections is larger.
    # ------------------------------------------------------------------
    fig_h = 3.6 if show_waveform else 2.2
    fig   = plt.figure(figsize=(6, fig_h))

    if show_waveform:
        outer = gridspec.GridSpec(2, 1, figure=fig,
                                  height_ratios=[2, 1.8], hspace=0.55)
        inner = gridspec.GridSpecFromSubplotSpec(2, 1, subplot_spec=outer[0],
                                                 hspace=0.05)
        ax2 = fig.add_subplot(outer[1])
    else:
        inner = gridspec.GridSpec(2, 1, figure=fig, hspace=0.05)

    ax0 = fig.add_subplot(inner[0])
    ax1 = fig.add_subplot(inner[1], sharex=ax0)

    # ------------------------------------------------------------------
    # Envelope rows
    # ------------------------------------------------------------------
    t_min, t_max = pre_time, post_time

    for ax, label, t_on, t_off in [
        (ax0, "Visual\nStimulus",    visual_start, visual_end),
        (ax1, "Micro-\nstimulation", estim_start,  estim_end),
    ]:
        t, y = _square_pulse(t_on, t_off, t_min, t_max)
        ax.plot(t, y, color=_BLACK, linewidth=_LINE_W,
                solid_joinstyle="miter", solid_capstyle="butt", clip_on=False)
        ax.set_ylim(-0.25, 1.4)
        _style_envelope_ax(ax)
        ax.set_ylabel(label, fontsize=_LABEL_FS, rotation=0,
                      ha="right", va="center", labelpad=8)

    # Time axis on the bottom envelope row
    ax1.spines["bottom"].set_visible(True)
    ax1.spines["bottom"].set_color(_GRAY)
    ax1.tick_params(bottom=True, labelbottom=True,
                    color=_GRAY, labelcolor=_BLACK, labelsize=9, length=3)
    ax1.xaxis.set_major_locator(ticker.MultipleLocator(100))
    ax1.set_xlabel("Time (ms)", fontsize=_LABEL_FS, labelpad=4)
    ax1.set_xlim(t_min, t_max)

    # ------------------------------------------------------------------
    # Waveform row — ms axis, physically aligned with estim_start
    # ------------------------------------------------------------------
    if show_waveform:
        t_wave, y_wave = _pulse_train_waveform(params, n_show=n_pulses_shown)

        # Convert µs → ms; first pulse starts exactly at estim_start
        t_ms     = t_wave / 1000.0 + estim_start
        total_ms = t_ms[-1]

        t_plot = np.concatenate([[estim_start], t_ms, [total_ms]])
        y_plot = np.concatenate([[0],           y_wave, [0]])

        ax2.plot(t_plot, y_plot, color=_BLACK, linewidth=_LINE_W,
                 solid_joinstyle="miter", solid_capstyle="butt")
        ax2.set_xlim(estim_start, total_ms)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.spines["left"].set_visible(False)
        ax2.spines["bottom"].set_color(_GRAY)

        ax2.set_yticks([])
        ax2.tick_params(axis="x", color=_GRAY, labelcolor=_BLACK, labelsize=9, length=3)
        ax2.xaxis.set_major_locator(ticker.MultipleLocator(100))

        ax2.set_xlabel("Time (ms)", fontsize=_LABEL_FS, labelpad=4)
        ax2.set_ylabel("Micro-\nstimulation\n(zoomed)", fontsize=_LABEL_FS, rotation=0,
                       ha="right", va="center", labelpad=8)

    fig.suptitle("Stimulus Timing", fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout(rect=[0.12, 0, 1, 1])

    # After layout: align ax2's left edge with estim_start on ax1, right edge with ax1.
    # Then draw two dashed vertical zoom lines in figure coordinates at
    # estim_start and total_ms, connecting the bottom of ax1 to the top of ax2.
    if show_waveform:
        from matplotlib.lines import Line2D

        pos1  = ax1.get_position()
        pos2  = ax2.get_position()   # full-width, set by tight_layout

        # Figure-fraction x of the narrow source region on ax1
        src_left  = pos1.x0 + (estim_start - t_min) / (t_max - t_min) * pos1.width
        src_right = pos1.x0 + (total_ms    - t_min) / (t_max - t_min) * pos1.width

        # Diagonal zoom lines: narrow region (bottom of ax1) → full width (top of ax2)
        for src_x, dst_x in [(src_left, pos2.x0), (src_right, pos2.x1)]:
            fig.add_artist(Line2D(
                [src_x, dst_x], [pos1.y0, pos2.y0 + pos2.height],
                transform=fig.transFigure,
                color=_GRAY, linestyle="--", linewidth=0.8, clip_on=False,
            ))

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {save_path}")

    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    plot_timing_diagram(
        visual_start=0,
        visual_end=500,
        estim_start=100,
        estim_end=500,
        pre_time=-100,
        post_time=650,
        session_id="260426_0",
        estim_spec_id=3,
        n_pulses_shown=3,
        save_path="/home/connorlab/Documents/plots/waveform_diagram/timing.png",
    )


if __name__ == "__main__":
    main()

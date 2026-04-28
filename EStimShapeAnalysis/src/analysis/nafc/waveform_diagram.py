"""
Stimulus timing diagram.

Row 1: Sample envelope       (ms, shared axis with rows 2-3)
Row 2: Choices envelope      (ms, rises at sample offset, never steps down)
Row 3: Microstimulation      (ms)
Row 4: Zoomed pulse waveform (ms, independent axis)

To add row 4, pass session_id + estim_spec_id; it reads EStimParameters from
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

_REPO_DB  = "allen_data_repository"
_BLACK    = "#111111"
_GRAY     = "#888888"
_LINE_W   = 1.8
_LABEL_FS = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _square_pulse(t_on: float, t_off: float, t_min: float, t_max: float):
    """(t, y) for a crisp square pulse — exact vertical edges."""
    eps = 1e-6
    t = [t_min, t_on - eps, t_on, t_off, t_off + eps, t_max]
    y = [0.0,   0.0,        1.0,  1.0,   0.0,          0.0]
    return np.array(t), np.array(y)


def _step_up(t_on: float, t_min: float, t_max: float):
    """(t, y) for a step that rises at t_on and never comes back down."""
    eps = 1e-6
    t = [t_min, t_on - eps, t_on, t_max]
    y = [0.0,   0.0,        1.0,  1.0]
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


def _pulse_train_waveform(p: dict, n_show: int = 3):
    """
    Concatenate n_show pulses separated by post_stim_refractory_period.
    Each pulse ends at y=0 and the next starts at y=0, so matplotlib
    draws the flat inter-pulse baseline automatically without extra points.
    """
    t_single, y_single = _biphasic_waveform(p)
    period = p.get("post_stim_refractory_period") or 0.0

    if period <= 0 or n_show <= 1:
        return t_single, y_single

    t_parts = [t_single + i * period for i in range(n_show)]
    y_parts = [y_single] * n_show
    return np.concatenate(t_parts), np.concatenate(y_parts)


# ---------------------------------------------------------------------------
# Main plot function
# ---------------------------------------------------------------------------

def plot_timing_diagram(
    visual_start:    float = 0,
    visual_end:      float = 500,
    choices_dur:     float = 500,   # ms; choices rise at visual_end, no falling edge shown
    estim_start:     float = 100,
    estim_end:       float = 500,
    pre_time:        float = -100,
    post_time:       float = 600,
    session_id:        str = None,
    estim_spec_id:     int = None,
    n_pulses_shown:    int = 3,
    save_path:         str = None,
):
    params = None
    if session_id is not None and estim_spec_id is not None:
        params = _load_estim_params(session_id, estim_spec_id)
        if params is None:
            print(f"WARNING: no non-zero channel found for "
                  f"session={session_id} spec={estim_spec_id}. Skipping waveform row.")

    show_waveform = params is not None
    t_min, t_max  = pre_time, post_time
    n_env_rows    = 3   # Sample, Choices, Microstimulation

    # ------------------------------------------------------------------
    # Figure + gridspec
    # Envelope rows share a tight inner gridspec; waveform gets its own
    # outer cell so the visual gap between sections is larger.
    # ------------------------------------------------------------------
    fig_h = 4.2 if show_waveform else 2.8
    fig   = plt.figure(figsize=(6, fig_h))

    if show_waveform:
        outer   = gridspec.GridSpec(2, 1, figure=fig,
                                    height_ratios=[n_env_rows, 1.8], hspace=0.55)
        inner   = gridspec.GridSpecFromSubplotSpec(n_env_rows, 1,
                                                   subplot_spec=outer[0], hspace=0.05)
        ax_wave = fig.add_subplot(outer[1])
    else:
        inner = gridspec.GridSpec(n_env_rows, 1, figure=fig, hspace=0.05)

    ax_sample  = fig.add_subplot(inner[0])
    ax_choices = fig.add_subplot(inner[1], sharex=ax_sample)
    ax_estim   = fig.add_subplot(inner[2], sharex=ax_sample)

    # ------------------------------------------------------------------
    # Envelope rows
    # ------------------------------------------------------------------
    # Sample — square pulse
    t, y = _square_pulse(visual_start, visual_end, t_min, t_max)
    ax_sample.plot(t, y, color=_BLACK, linewidth=_LINE_W,
                   solid_joinstyle="miter", solid_capstyle="butt", clip_on=False)
    ax_sample.set_ylim(-0.25, 1.4)
    _style_envelope_ax(ax_sample)
    ax_sample.set_ylabel("Sample", fontsize=_LABEL_FS, rotation=0,
                          ha="right", va="center", labelpad=8)

    # Choices — step up at visual_end, never steps down
    t, y = _step_up(visual_end, t_min, t_max)
    ax_choices.plot(t, y, color=_BLACK, linewidth=_LINE_W,
                    solid_joinstyle="miter", solid_capstyle="butt", clip_on=False)
    ax_choices.set_ylim(-0.25, 1.4)
    _style_envelope_ax(ax_choices)
    ax_choices.set_ylabel("Choices", fontsize=_LABEL_FS, rotation=0,
                           ha="right", va="center", labelpad=8)

    # Microstimulation — square pulse
    t, y = _square_pulse(estim_start, estim_end, t_min, t_max)
    ax_estim.plot(t, y, color=_BLACK, linewidth=_LINE_W,
                  solid_joinstyle="miter", solid_capstyle="butt", clip_on=False)
    ax_estim.set_ylim(-0.25, 1.4)
    _style_envelope_ax(ax_estim)
    ax_estim.set_ylabel("Micro-\nstimulation", fontsize=_LABEL_FS, rotation=0,
                         ha="right", va="center", labelpad=8)

    # Time axis on the bottom envelope row
    ax_estim.spines["bottom"].set_visible(True)
    ax_estim.spines["bottom"].set_color(_GRAY)
    ax_estim.tick_params(bottom=True, labelbottom=True,
                         color=_GRAY, labelcolor=_BLACK, labelsize=9, length=3)
    ax_estim.xaxis.set_major_locator(ticker.MultipleLocator(100))
    ax_estim.set_xlabel("Time (ms)", fontsize=_LABEL_FS, labelpad=4)
    ax_estim.set_xlim(t_min, t_max)

    # ------------------------------------------------------------------
    # Waveform row
    # ------------------------------------------------------------------
    if show_waveform:
        t_wave, y_wave = _pulse_train_waveform(params, n_show=n_pulses_shown)

        t_ms            = t_wave / 1000.0 + estim_start
        total_ms        = t_ms[-1]
        pulse_period_ms = params["post_stim_refractory_period"] / 1000.0

        # Extend one more refractory period as a flat tail so the train isn't cut off
        tail_end = total_ms + pulse_period_ms
        t_plot = np.concatenate([[estim_start], t_ms, [total_ms, tail_end]])
        y_plot = np.concatenate([[0],           y_wave, [0,       0]])

        ax_wave.plot(t_plot, y_plot, color=_BLACK, linewidth=_LINE_W,
                     solid_joinstyle="miter", solid_capstyle="butt")
        ax_wave.set_xlim(estim_start, tail_end)
        ax_wave.spines["top"].set_visible(False)
        ax_wave.spines["right"].set_visible(False)
        ax_wave.spines["left"].set_visible(False)
        ax_wave.spines["bottom"].set_color(_GRAY)

        ax_wave.set_yticks([])
        ax_wave.tick_params(axis="x", color=_GRAY, labelcolor=_BLACK, labelsize=9, length=3)

        tick_positions  = [estim_start + i * pulse_period_ms for i in range(n_pulses_shown + 1)]
        ax_wave.set_xticks(tick_positions)

        ax_wave.set_xlabel("Time (ms)", fontsize=_LABEL_FS, labelpad=4)
        ax_wave.set_ylabel("Micro-\nstimulation\n(zoomed)", fontsize=_LABEL_FS, rotation=0,
                            ha="right", va="center", labelpad=8)

    fig.suptitle("Stimulus Timing", fontsize=12, fontweight="bold")
    plt.tight_layout()

    # ------------------------------------------------------------------
    # Zoom lines — drawn in figure fraction AFTER tight_layout
    # ------------------------------------------------------------------
    if show_waveform:
        from matplotlib.lines import Line2D

        pos_e  = ax_estim.get_position()
        pos_w  = ax_wave.get_position()

        src_left  = pos_e.x0 + (estim_start - t_min) / (t_max - t_min) * pos_e.width
        src_right = pos_e.x0 + (total_ms    - t_min) / (t_max - t_min) * pos_e.width

        # Diagonal lines: narrow region on ax_estim → full width of ax_wave
        for src_x, dst_x in [(src_left, pos_w.x0), (src_right, pos_w.x1)]:
            fig.add_artist(Line2D(
                [src_x, dst_x], [pos_e.y0, pos_w.y0 + pos_w.height],
                transform=fig.transFigure,
                color=_GRAY, linestyle="--", linewidth=0.8, clip_on=False,
            ))

        # Vertical markers on ax_estim from baseline to y=1 (ON level)
        ymin, ymax = ax_estim.get_ylim()
        y1_fig = pos_e.y0 + (1.0 - ymin) / (ymax - ymin) * pos_e.height
        for src_x in [src_left, src_right]:
            fig.add_artist(Line2D(
                [src_x, src_x], [pos_e.y0, y1_fig],
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
        choices_dur=500,
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

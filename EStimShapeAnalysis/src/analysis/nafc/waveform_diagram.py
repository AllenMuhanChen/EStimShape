"""
Stimulus timing diagram — square-wave envelopes for visual and microstimulation.

Future: add a third row with a zoomed-in actual estim waveform (biphasic/triphasic
pulse shape). The subplot grid is already structured to accommodate it.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


def _square_pulse(t_on: float, t_off: float, t_min: float, t_max: float):
    """Return (t, y) arrays that draw a crisp square pulse with exact vertical edges."""
    eps = 1e-6
    t = [t_min, t_on - eps, t_on, t_off, t_off + eps, t_max]
    y = [0.0,   0.0,        1.0,  1.0,   0.0,          0.0]
    return np.array(t), np.array(y)


def _style_trace_ax(ax):
    """Remove all spines and ticks — waveform rows need no axes chrome."""
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_yticks([])
    ax.tick_params(bottom=False, labelbottom=False)


def plot_timing_diagram(
    visual_start: float = 0,
    visual_end:   float = 500,
    estim_start:  float = 100,
    estim_end:    float = 500,
    pre_time:     float = -100,
    post_time:    float = 600,
    save_path:    str   = None,
):
    """
    Parameters
    ----------
    visual_start/end : onset / offset of visual stimulus (ms)
    estim_start/end  : onset / offset of microstimulation (ms)
    pre_time         : time shown before t=0 (negative ms value)
    post_time        : time shown after t=0 (ms)
    save_path        : optional PNG output path
    """
    t_min = pre_time
    t_max = post_time

    rows = [
        ("Visual\nStimulus",       *_square_pulse(visual_start, visual_end, t_min, t_max)),
        ("Micro-\nstimulation",    *_square_pulse(estim_start,  estim_end,  t_min, t_max)),
        # Future row: zoomed estim waveform — insert here
    ]
    n_rows = len(rows)

    fig, axes = plt.subplots(
        n_rows, 1,
        figsize=(6, 1.1 * n_rows + 0.6),
        sharex=True,
        gridspec_kw={"hspace": 0.05},
        constrained_layout=False,
    )
    if n_rows == 1:
        axes = [axes]

    _BLACK    = "#111111"
    _GRAY     = "#888888"
    _LINE_W   = 1.8
    _LABEL_FS = 10

    for ax, (label, t, y) in zip(axes, rows):
        ax.plot(t, y, color=_BLACK, linewidth=_LINE_W,
                solid_joinstyle="miter", solid_capstyle="butt", clip_on=False)
        ax.set_ylim(-0.25, 1.4)
        _style_trace_ax(ax)
        ax.set_ylabel(label, fontsize=_LABEL_FS, rotation=0,
                      ha="right", va="center", labelpad=8,
                      fontfamily="sans-serif")

    # Vertical guide lines at stimulus onset / offset
    for t_event in {visual_start, visual_end, estim_start, estim_end}:
        for ax in axes:
            ax.axvline(t_event, color=_GRAY, linestyle=":", linewidth=0.8, alpha=0.5, zorder=0)

    # Time axis on the bottom row only
    ax_bot = axes[-1]
    ax_bot.spines["bottom"].set_visible(True)
    ax_bot.spines["bottom"].set_color(_GRAY)
    ax_bot.tick_params(bottom=True, labelbottom=True, color=_GRAY, labelcolor=_BLACK,
                       labelsize=9, length=3)
    ax_bot.xaxis.set_major_locator(ticker.MultipleLocator(100))
    ax_bot.xaxis.set_minor_locator(ticker.MultipleLocator(50))
    ax_bot.set_xlabel("Time (ms)", fontsize=_LABEL_FS, labelpad=6)

    # Mark t=0
    ax_bot.axvline(0, color=_GRAY, linestyle=":", linewidth=0.8, alpha=0.5, zorder=0)

    ax_bot.set_xlim(t_min, t_max)

    # Overall title
    fig.suptitle("Stimulus Timing", fontsize=12, fontweight="bold",
                 fontfamily="sans-serif", y=1.01)

    plt.tight_layout(rect=[0.12, 0, 1, 1])

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def main():
    plot_timing_diagram(
        visual_start=0,
        visual_end=500,
        estim_start=100,
        estim_end=500,
        pre_time=-100,
        post_time=650,
        save_path="/home/connorlab/Documents/plots/waveform_diagram/timing.png",
    )


if __name__ == "__main__":
    main()

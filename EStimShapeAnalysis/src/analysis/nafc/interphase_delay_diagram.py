"""
One biphasic microstimulation pulse with an interphase delay, with the first phase
(d1), the interphase delay (dp) and the second phase (d2) marked — a figure for
explaining what the interphase delay is. Same drawing style as waveform_diagram.

Amplitude is schematic (no y-axis). Durations are in µs.
"""

import os
import sys
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from waveform_diagram import _BLACK, _GRAY, _LINE_W, _biphasic_waveform


def plot_interphase_delay_diagram(d1=200.0, d2=200.0, dp=100.0,
                                  polarity="NegativeFirst", pad=100.0,
                                  label_fs=13, save_path=None):
    """d1, d2: phase widths, dp: interphase delay (µs). pad: flat baseline shown
    before and after the pulse (µs)."""
    params = dict(shape="BiphasicWithInterphaseDelay", polarity=polarity,
                  d1=d1, d2=d2, dp=dp, a1=1.0, a2=1.0)
    t, y = _biphasic_waveform(params)
    t = np.concatenate([[-pad], t, [t[-1] + pad]])
    y = np.concatenate([[0.0], y, [0.0]])

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.axhline(0, color=_GRAY, lw=0.8, ls=":", zorder=0)
    ax.plot(t, y, color=_BLACK, linewidth=_LINE_W, solid_joinstyle="miter",
            solid_capstyle="butt")

    # dimension marks below the pulse: d1 | interphase delay | d2
    edges = [0.0, d1, d1 + dp, d1 + dp + d2]
    y_dim = -1.45
    for x in edges:
        ax.plot([x, x], [y_dim - 0.08, 0], color=_GRAY, lw=0.8, ls="--", zorder=0)
    labels = [f"d1\n{d1:g} µs", f"interphase\ndelay\n{dp:g} µs", f"d2\n{d2:g} µs"]
    for (lo, hi), text in zip(zip(edges[:-1], edges[1:]), labels):
        ax.annotate("", xy=(lo, y_dim), xytext=(hi, y_dim),
                    arrowprops=dict(arrowstyle="<->", color=_BLACK, lw=1.0,
                                    shrinkA=0, shrinkB=0))
        ax.text((lo + hi) / 2, y_dim - 0.12, text, ha="center", va="top",
                fontsize=label_fs)

    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(-2.45, 1.3)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(_GRAY)
    ax.spines["bottom"].set_position(("data", -2.45))
    ax.set_yticks([])
    ax.tick_params(axis="x", color=_GRAY, labelcolor=_BLACK, labelsize=label_fs - 2,
                   length=3)
    ax.set_xlabel("Time (µs)", fontsize=label_fs)
    fig.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        fig.savefig(os.path.splitext(save_path)[0] + ".svg", dpi=300, bbox_inches="tight")
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def main():
    d1 = 200.0   # first phase width (µs)
    d2 = 200.0   # second phase width (µs)
    dp = 100.0   # interphase delay (µs)
    polarity = "NegativeFirst"   # or "PositiveFirst"
    plot_interphase_delay_diagram(
        d1=d1, d2=d2, dp=dp, polarity=polarity,
        save_path="/home/connorlab/Documents/plots/waveform_diagram/interphase_delay.png",
    )


if __name__ == "__main__":
    main()

"""
Waveforms of spike.dat threshold crossings around choices_on, EStim ON vs OFF.

Question: are the extra crossings right after choices_on on EStim ON trials
spikes (neural, e.g. a rebound after EStim ends) or voltage-artifact threshold
crossings? Spikes have a stereotyped ~1 ms shape that matches the channel's
ordinary spikes; artifact crossings don't.

Methods
-------
For one session, a random subset of EStim ON and OFF trials is drawn
(n_trials_per_condition each, fixed seed). For each trial the raw amplifier
data (amplifier.dat) of the chosen channels is read, high-pass filtered
(highpass_hz, 4th-order Butterworth, as in src/lfp/spike_waveform_features.py)
and a snippet from -pre_ms to +post_ms is cut around every spike.dat crossing
that falls in each comparison window. Windows are relative to a trial event
(choices_on or sample_off). The "late choice" window is the reference for
ordinary spikes; the "sample" window on ON trials is the reference for
artifact.

Shape similarity: each snippet is correlated (Pearson r) with its channel's
template, the mean snippet of OFF-trial crossings in the late-choice window.
Spikes give r near 1; artifact crossings give low or negative r.

Only reads the sampled trials, so it runs in minutes on one session.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.nafc.neural.choice_period_response import ESTIM_COLORS, ESTIM_LABELS


def highpass(signal: np.ndarray, sample_rate: float, highpass_hz: float) -> np.ndarray:
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, highpass_hz / (sample_rate / 2), btype="high", output="sos")
    return sosfiltfilt(sos, np.asarray(signal, dtype=np.float64))


def snippets_in_window(filtered: np.ndarray, spike_times_s, sample_rate: float,
                       t_lo: float, t_hi: float, pre_ms: float, post_ms: float) -> np.ndarray:
    pre = int(round(pre_ms * sample_rate / 1000))
    post = int(round(post_ms * sample_rate / 1000))
    out = []
    for t in spike_times_s:
        if not t_lo <= t < t_hi:
            continue
        idx = int(round(t * sample_rate))
        if idx - pre < 0 or idx + post >= len(filtered):
            continue
        out.append(filtered[idx - pre: idx + post + 1])
    return np.array(out) if out else np.empty((0, pre + post + 1))


def collect_snippets(trials: pd.DataFrame, recording_dirs: dict, channels: list, windows: dict,
                     highpass_hz: float, pre_ms: float, post_ms: float) -> pd.DataFrame:
    """One row per snippet: estim_on, window, channel, waveform (filtered uV)."""
    from clat.intan.amplifiers import read_amplifier_data_with_memmap
    from clat.intan.rhs.load_intan_rhs_format import read_data

    rows = []
    for i, (_, trial) in enumerate(trials.iterrows()):
        neural = trial["NeuralData"]
        rec_dir = recording_dirs.get(str(neural["task_id"]))
        if rec_dir is None:
            continue
        rhs = read_data(os.path.join(rec_dir, "info.rhs"))
        sample_rate = float(rhs["frequency_parameters"]["amplifier_sample_rate"])
        raw = read_amplifier_data_with_memmap(os.path.join(rec_dir, "amplifier.dat"),
                                              rhs["amplifier_channels"])
        raw = {ch.value: data for ch, data in raw.items() if ch.value in channels}
        for channel, data in raw.items():
            filtered = highpass(data, sample_rate, highpass_hz)
            spikes = neural["spikes_by_channel"].get(channel, [])
            for name, (event, lo, hi) in windows.items():
                t0 = neural.get(event)
                if t0 is None:
                    continue
                for w in snippets_in_window(filtered, spikes, sample_rate, t0 + lo, t0 + hi,
                                            pre_ms, post_ms):
                    rows.append({"estim_on": bool(trial["EStimEnabled"]), "window": name,
                                 "channel": channel, "waveform": w})
        print(f"  trial {i + 1}/{len(trials)}: {len(rows)} snippets so far")
    return pd.DataFrame(rows, columns=["estim_on", "window", "channel", "waveform"])


def add_template_r(snips: pd.DataFrame, template_window: str) -> pd.DataFrame:
    """Pearson r of each snippet with its channel's OFF template-window mean."""
    snips = snips.copy()
    templates = {}
    ref = snips[(~snips["estim_on"]) & (snips["window"] == template_window)]
    for channel, grp in ref.groupby("channel"):
        templates[channel] = np.mean(np.vstack(grp["waveform"]), axis=0)

    def r(row):
        t = templates.get(row["channel"])
        if t is None or np.std(row["waveform"]) == 0:
            return np.nan
        return float(np.corrcoef(row["waveform"], t)[0, 1])

    snips["template_r"] = snips.apply(r, axis=1)
    return snips


def plot_waveforms(snips: pd.DataFrame, windows: dict, pre_ms: float, post_ms: float,
                   max_overlay: int, title: str, y_limit_uv: float = None):
    fig, axes = plt.subplots(len(windows), 2, figsize=(13, 3.6 * len(windows)),
                             sharex=True, sharey=True, squeeze=False)
    rng = np.random.default_rng(0)
    for r, name in enumerate(windows):
        for c, estim_on in enumerate((False, True)):
            ax = axes[r, c]
            grp = snips[(snips["window"] == name) & (snips["estim_on"] == estim_on)]
            if len(grp):
                arr = np.vstack(grp["waveform"])
                t = np.linspace(-pre_ms, post_ms, arr.shape[1])
                pick = rng.choice(len(arr), min(max_overlay, len(arr)), replace=False)
                ax.plot(t, arr[pick].T, color=ESTIM_COLORS[estim_on], alpha=0.06, linewidth=0.6)
                ax.plot(t, arr.mean(axis=0), color="black", linewidth=2.2)
            ax.set_title(f"{ESTIM_LABELS[estim_on]}, {name} (n={len(grp)})", fontsize=13)
            ax.axvline(0, color="#999999", linewidth=0.8)
            ax.tick_params(labelsize=11)
            ax.spines[["top", "right"]].set_visible(False)
            if c == 0:
                ax.set_ylabel("Filtered voltage (uV)", fontsize=12)
            if r == len(windows) - 1:
                ax.set_xlabel("Time from crossing (ms)", fontsize=12)
    if y_limit_uv:
        axes[0, 0].set_ylim(-y_limit_uv, y_limit_uv)  # shared y; artifacts run off-scale
    fig.suptitle(title, fontsize=15)
    fig.tight_layout()
    return fig


def plot_template_r(snips: pd.DataFrame, windows: dict, title: str):
    fig, axes = plt.subplots(1, len(windows), figsize=(5.5 * len(windows), 4.8), sharey=False,
                             squeeze=False)
    edges = np.linspace(-1, 1, 41)
    for ax, name in zip(axes[0], windows):
        for estim_on in (False, True):
            r = snips[(snips["window"] == name) & (snips["estim_on"] == estim_on)][
                "template_r"].dropna()
            if len(r):
                ax.hist(r, bins=edges, density=True, alpha=0.55, color=ESTIM_COLORS[estim_on],
                        label=f"{ESTIM_LABELS[estim_on]} (median {r.median():.2f})")
        ax.set_title(name, fontsize=13)
        ax.set_xlabel("Correlation with spike template", fontsize=12)
        ax.set_ylabel("Density", fontsize=12)
        ax.legend(fontsize=10, frameon=False, loc="upper left")
        ax.tick_params(labelsize=11)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(title, fontsize=15)
    fig.tight_layout()
    return fig


def main():
    # ---- parameters ----
    session_id = "260518_0"
    channels = None                  # None = all 32; or e.g. ["A-012", "A-013"]
    n_trials_per_condition = 30      # random ON and OFF trials to read raw data for
    windows = {                      # name: (event, start_s, stop_s) relative to the event
        "early choice 0-50 ms": ("choices_on", 0.0, 0.05),
        "late choice 250-600 ms": ("choices_on", 0.25, 0.6),
        "sample (artifact ref)": ("sample_off", -0.3, 0.0),
    }
    template_window = "late choice 250-600 ms"
    highpass_hz = 300.0
    pre_ms, post_ms = 0.5, 1.5
    max_overlay = 300                # snippets drawn per panel (mean uses all)
    y_limit_uv = 400                 # +- y range so spikes are visible (None = fit everything)
    seed = 0
    output_root = "/home/connorlab/Documents/plots/nafc_choice_period_waveforms"
    show_plots = True
    # --------------------

    from src.analysis import get_all_channels
    from src.analysis.nafc.neural.choice_period_response import ChoicePeriodEStimAnalysis
    from src.analysis.nafc.nafc_neural_database_fields import NafcNeuralDataField
    from src.startup import context
    from src.startup.apply_session_context import apply_session_context
    from clat.util.connection import Connection

    channels = channels or get_all_channels()
    apply_session_context(session_id)
    analysis = ChoicePeriodEStimAnalysis(export=False, save_plots=False, skip_existing=False,
                                         artifact_mask=None)
    data = analysis.compile()
    if data.empty:
        return
    recording_dirs = NafcNeuralDataField(analysis.nafc_intan_path(),
                                         Connection(context.nafc_database))._index

    rng = np.random.default_rng(seed)
    picked = []
    for estim_on in (False, True):
        idx = np.flatnonzero(data["EStimEnabled"].astype(bool).to_numpy() == estim_on)
        picked.extend(rng.choice(idx, min(n_trials_per_condition, len(idx)), replace=False))
    trials = data.iloc[sorted(picked)]
    print(f"Reading raw data for {len(trials)} trials, {len(channels)} channels")

    snips = collect_snippets(trials, recording_dirs, channels, windows, highpass_hz,
                             pre_ms, post_ms)
    if snips.empty:
        print("No crossings found in the windows.")
        return
    snips = add_template_r(snips, template_window)
    summary = snips.groupby(["window", "estim_on"]).agg(
        n=("template_r", "size"), median_template_r=("template_r", "median")).reset_index()
    print(summary.to_string(index=False))

    out_dir = os.path.join(output_root, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump({"session_id": session_id, "channels": channels,
                   "n_trials_per_condition": n_trials_per_condition,
                   "windows": windows, "template_window": template_window,
                   "highpass_hz": highpass_hz, "pre_ms": pre_ms, "post_ms": post_ms,
                   "seed": seed}, f, indent=2)
    summary.to_csv(os.path.join(out_dir, "template_r_summary.csv"), index=False)

    fig = plot_waveforms(snips, windows, pre_ms, post_ms, max_overlay, f"{session_id} crossings",
                         y_limit_uv=y_limit_uv)
    fig.savefig(os.path.join(out_dir, "waveforms.png"), dpi=150, bbox_inches="tight")
    fig = plot_template_r(snips, windows, f"{session_id} shape vs spike template")
    fig.savefig(os.path.join(out_dir, "template_r.png"), dpi=150, bbox_inches="tight")
    print(f"Saved to {out_dir}")
    if show_plots:
        plt.show()


if __name__ == "__main__":
    main()

"""
response_onset.py
-----------------
Reusable utilities for computing response onset latency and consistency from spike data.

Method: per-trial Spike Density Function (SDF) threshold crossing.

For each trial:
  1. Convolve spike times with a Gaussian kernel (σ ≈ 20 ms) → smooth per-trial SDF (Hz).
  2. Compute a per-trial threshold from that trial's own pre-stimulus baseline
     (SDF_baseline_mean + N * SDF_baseline_std).  This adapts to each trial's
     spontaneous firing rate.
  3. Require the SDF to stay above threshold for ≥ sustain_ms continuously.
     This gates out isolated spontaneous bumps — a single stray spike produces a
     ~40 ms wide bump at σ=20 ms, but requiring sustained ≥ 15 ms crossing means
     the SDF must remain elevated, which typically demands a burst of driven spikes.
  4. Return the time of the first qualifying crossing as that trial's onset, or NaN.

Collecting per-trial onsets gives both:
  mean_onset_ms  — latency estimate
  std_onset_ms   — consistency (low std = reliable, repeatable onset)

Public API
----------
    get_channel_spikes(trial, spike_data_col, channel)
        → List[float]  (spike times in seconds, epoch-relative)

    compute_sdf_onset_for_trial(spike_times, ...)
        → float  (onset in ms for this trial, or NaN)

    compute_onset_stats_for_channel(data, spike_data_col, channel, ...)
        → OnsetStats

    compute_onset_stats_for_all_channels(data, spike_data_col, channels, ...)
        → dict[str, OnsetStats]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class OnsetStats:
    """Per-channel onset latency and consistency summary (both from per-trial SDF)."""
    mean_onset_ms: float      # mean of per-trial SDF onset times (NaN if no trials driven)
    std_onset_ms: float       # std across trials — the consistency measure
    n_trials: int             # total trials used
    n_trials_with_onset: int  # trials whose SDF crossed threshold (sustained)


# ---------------------------------------------------------------------------
# Low-level spike extractor (reusable by other modules)
# ---------------------------------------------------------------------------

def get_channel_spikes(trial: pd.Series, spike_data_col: str, channel: str) -> List[float]:
    """Return spike times (seconds, epoch-relative) for *channel* in *trial*.

    Handles dict-valued cells (keyed by channel name) and plain list-valued cells.
    Returns an empty list when no data is present.
    """
    raw = trial.get(spike_data_col)
    if isinstance(raw, dict):
        times = raw.get(channel, [])
    elif isinstance(raw, list):
        times = raw
    else:
        times = []
    return times if times is not None else []


# ---------------------------------------------------------------------------
# Per-trial SDF onset
# ---------------------------------------------------------------------------

def compute_sdf_onset_for_trial(
        spike_times: List[float],
        sigma_ms: float = 20.0,
        time_resolution_ms: float = 1.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        threshold_n_std: float = 2.5,
        sustain_ms: float = 15.0,
) -> float:
    """Compute onset latency for a single trial via SDF threshold crossing.

    Args:
        spike_times:       Spike times in seconds (epoch-relative) for one trial.
        sigma_ms:          Gaussian kernel sigma in milliseconds.
        time_resolution_ms: Time axis resolution in milliseconds.
        baseline_window:   (start, end) seconds; SDF baseline computed here.
        response_window:   (start, end) seconds; searched for threshold crossing.
        threshold_n_std:   Threshold = baseline_mean + N * baseline_std.
        sustain_ms:        SDF must stay above threshold for this many ms continuously.

    Returns:
        Onset latency in milliseconds, or NaN if the threshold is never sustained.
    """
    dt = time_resolution_ms / 1000.0  # seconds
    t_start = baseline_window[0]
    t_end = response_window[1]

    # Build time axis
    t_axis = np.arange(t_start, t_end + dt, dt)

    # Build SDF: sum of Gaussians centred on each spike
    sigma_s = sigma_ms / 1000.0
    sdf = np.zeros(len(t_axis))
    for spike_t in spike_times:
        sdf += np.exp(-0.5 * ((t_axis - spike_t) / sigma_s) ** 2)
    # Normalise to Hz
    sdf /= (sigma_s * np.sqrt(2 * np.pi))

    # Per-trial baseline threshold
    baseline_mask = (t_axis >= baseline_window[0]) & (t_axis < baseline_window[1])
    if baseline_mask.sum() == 0:
        return np.nan
    bl = sdf[baseline_mask]
    threshold = bl.mean() + threshold_n_std * bl.std()

    # Find first sustained crossing in response window
    response_mask = (t_axis >= response_window[0]) & (t_axis <= response_window[1])
    response_indices = np.where(response_mask)[0]
    sustain_bins = int(np.ceil(sustain_ms / time_resolution_ms))

    above = sdf > threshold
    consecutive = 0
    for idx in response_indices:
        if above[idx]:
            if consecutive == 0:
                first_idx = idx  # mark start of crossing
            consecutive += 1
            if consecutive >= sustain_bins:
                return float(t_axis[first_idx] * 1000.0)
        else:
            consecutive = 0

    return np.nan


# ---------------------------------------------------------------------------
# Per-channel wrappers
# ---------------------------------------------------------------------------

def compute_onset_stats_for_channel(
        data: pd.DataFrame,
        spike_data_col: str,
        channel: str,
        sigma_ms: float = 20.0,
        time_resolution_ms: float = 1.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        threshold_n_std: float = 2.5,
        sustain_ms: float = 15.0,
) -> OnsetStats:
    """Compute per-trial SDF onset latency and consistency for *channel*.

    Args:
        data:               DataFrame where each row is one trial.
        spike_data_col:     Column holding spike-timestamp dicts keyed by channel.
        channel:            Channel name (e.g. "A-007").
        sigma_ms:           Gaussian kernel sigma in ms.
        time_resolution_ms: SDF time axis resolution in ms.
        baseline_window:    Pre-stimulus window (seconds) for per-trial baseline.
        response_window:    Post-stimulus window (seconds) to search for onset.
        threshold_n_std:    Baseline std multiplier for threshold.
        sustain_ms:         Required sustained crossing duration in ms.

    Returns:
        OnsetStats with mean/std onset in ms and trial counts.
    """
    onset_times_ms: List[float] = []
    n_trials = 0

    for _, trial in data.iterrows():
        spike_times = get_channel_spikes(trial, spike_data_col, channel)
        n_trials += 1
        onset = compute_sdf_onset_for_trial(
            spike_times,
            sigma_ms=sigma_ms,
            time_resolution_ms=time_resolution_ms,
            baseline_window=baseline_window,
            response_window=response_window,
            threshold_n_std=threshold_n_std,
            sustain_ms=sustain_ms,
        )
        if not np.isnan(onset):
            onset_times_ms.append(onset)

    n_with = len(onset_times_ms)
    if n_with >= 2:
        mean_onset = float(np.mean(onset_times_ms))
        std_onset = float(np.std(onset_times_ms))
    elif n_with == 1:
        mean_onset = float(onset_times_ms[0])
        std_onset = np.nan
    else:
        mean_onset = np.nan
        std_onset = np.nan

    return OnsetStats(
        mean_onset_ms=mean_onset,
        std_onset_ms=std_onset,
        n_trials=n_trials,
        n_trials_with_onset=n_with,
    )


def compute_onset_stats_for_all_channels(
        data: pd.DataFrame,
        spike_data_col: str,
        channels: List[str],
        sigma_ms: float = 20.0,
        time_resolution_ms: float = 1.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        threshold_n_std: float = 2.5,
        sustain_ms: float = 15.0,
) -> dict[str, OnsetStats]:
    """Run compute_onset_stats_for_channel for every channel.

    Returns:
        Dict mapping channel name → OnsetStats.
    """
    return {
        ch: compute_onset_stats_for_channel(
            data, spike_data_col, ch,
            sigma_ms=sigma_ms,
            time_resolution_ms=time_resolution_ms,
            baseline_window=baseline_window,
            response_window=response_window,
            threshold_n_std=threshold_n_std,
            sustain_ms=sustain_ms,
        )
        for ch in channels
    }

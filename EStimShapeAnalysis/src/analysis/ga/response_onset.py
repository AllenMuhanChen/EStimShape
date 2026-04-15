"""
response_onset.py
-----------------
Reusable utilities for computing response onset latency and consistency from spike data.

Method: PSTH 10%–90% rise time.

  1. Build the population PSTH by binning and averaging spikes across all trials.
  2. Smooth with a Gaussian kernel.
  3. Find the peak of the smoothed PSTH in the response window.
  4. Compute 10% and 90% levels relative to baseline:
       level = baseline_mean + fraction * (peak - baseline_mean)
  5. onset_ms    = first time the PSTH crosses the 10% level (response start)
  6. rise_time_ms = time from 10% to 90% crossing (consistency proxy)

Why rise time works as a consistency measure:
  - Channels where every trial fires at nearly the same time produce a sharp,
    narrow PSTH peak → short rise time.
  - Channels with variable or scattered firing produce a broad, gradual PSTH
    rise → long rise time.
  - This is exactly what you would read off a raster plot, expressed as a single
    number, without needing per-trial estimates at all.

Public API
----------
    get_channel_spikes(trial, spike_data_col, channel)
        → List[float]  (spike times in seconds, epoch-relative)

    compute_psth_onset_and_rise(spike_times_by_trial, ...)
        → (onset_ms, rise_time_ms)

    compute_onset_stats_for_channel(data, spike_data_col, channel, ...)
        → OnsetStats

    compute_onset_stats_for_all_channels(data, spike_data_col, channels, ...)
        → dict[str, OnsetStats]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class OnsetStats:
    """Per-channel onset latency and rise-time (consistency) from the PSTH."""
    onset_ms: float       # time to 10% of PSTH peak above baseline (NaN if no response)
    rise_time_ms: float   # time from 10% to 90% of peak — shorter = more consistent
    n_trials: int         # total trials used to build the PSTH


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
# PSTH rise-time computation
# ---------------------------------------------------------------------------

def compute_psth_onset_and_rise(
        spike_times_by_trial: List[List[float]],
        bin_size_ms: float = 5.0,
        smooth_sigma_ms: float = 10.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        low_fraction: float = 0.10,
        high_fraction: float = 0.90,
) -> Tuple[float, float]:
    """Compute PSTH onset and rise time via fractional peak levels.

    Args:
        spike_times_by_trial: One list of spike times (seconds) per trial.
        bin_size_ms:          PSTH bin width in milliseconds.
        smooth_sigma_ms:      Gaussian kernel sigma in milliseconds.
        baseline_window:      (start, end) seconds; defines baseline mean.
        response_window:      (start, end) seconds; searched for peak and crossings.
        low_fraction:         Peak fraction for onset crossing (default 0.10 = 10%).
        high_fraction:        Peak fraction for rise-time endpoint (default 0.90 = 90%).

    Returns:
        (onset_ms, rise_time_ms) — both NaN if no peak exceeds baseline.
    """
    n_trials = len(spike_times_by_trial)
    if n_trials == 0:
        return np.nan, np.nan

    bin_size_s = bin_size_ms / 1000.0
    t_start = baseline_window[0]
    t_end = response_window[1]
    bin_edges = np.arange(t_start, t_end + bin_size_s, bin_size_s)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    # Build PSTH and convert to Hz
    psth_counts = np.zeros(len(bin_centers))
    for spike_times in spike_times_by_trial:
        counts, _ = np.histogram(spike_times, bins=bin_edges)
        psth_counts += counts
    psth_hz = psth_counts / n_trials / bin_size_s

    # Gaussian smoothing
    psth_smooth = gaussian_filter1d(psth_hz, sigma=smooth_sigma_ms / bin_size_ms)

    # Baseline mean
    baseline_mask = (bin_centers >= baseline_window[0]) & (bin_centers < baseline_window[1])
    if baseline_mask.sum() == 0:
        return np.nan, np.nan
    baseline_mean = psth_smooth[baseline_mask].mean()

    # Find peak in response window
    response_mask = (bin_centers >= response_window[0]) & (bin_centers <= response_window[1])
    response_psth = psth_smooth[response_mask]
    response_times = bin_centers[response_mask]
    if len(response_psth) == 0:
        return np.nan, np.nan

    peak = response_psth.max()
    drive = peak - baseline_mean
    if drive <= 0:
        return np.nan, np.nan

    level_low  = baseline_mean + low_fraction  * drive
    level_high = baseline_mean + high_fraction * drive

    # First crossing of level_low → onset
    onset_ms = np.nan
    for t, v in zip(response_times, response_psth):
        if v >= level_low:
            onset_ms = float(t * 1000.0)
            break

    if np.isnan(onset_ms):
        return np.nan, np.nan

    # First crossing of level_high → rise endpoint
    high_ms = np.nan
    for t, v in zip(response_times, response_psth):
        if v >= level_high:
            high_ms = float(t * 1000.0)
            break

    if np.isnan(high_ms):
        return onset_ms, np.nan

    return onset_ms, high_ms - onset_ms


# ---------------------------------------------------------------------------
# Per-channel wrappers
# ---------------------------------------------------------------------------

def compute_onset_stats_for_channel(
        data: pd.DataFrame,
        spike_data_col: str,
        channel: str,
        bin_size_ms: float = 5.0,
        smooth_sigma_ms: float = 10.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        low_fraction: float = 0.10,
        high_fraction: float = 0.90,
) -> OnsetStats:
    """Compute PSTH onset and rise time for *channel* across all trials in *data*.

    Args:
        data:             DataFrame where each row is one trial.
        spike_data_col:   Column holding spike-timestamp dicts keyed by channel.
        channel:          Channel name (e.g. "A-007").
        bin_size_ms:      PSTH bin width in ms.
        smooth_sigma_ms:  Gaussian kernel sigma in ms.
        baseline_window:  Pre-stimulus window (seconds) for baseline mean.
        response_window:  Post-stimulus window (seconds) to search for peak.
        low_fraction:     Peak fraction for onset (default 0.10).
        high_fraction:    Peak fraction for rise endpoint (default 0.90).

    Returns:
        OnsetStats with onset_ms, rise_time_ms, and trial count.
    """
    spike_times_by_trial: List[List[float]] = [
        get_channel_spikes(trial, spike_data_col, channel)
        for _, trial in data.iterrows()
    ]

    onset_ms, rise_time_ms = compute_psth_onset_and_rise(
        spike_times_by_trial,
        bin_size_ms=bin_size_ms,
        smooth_sigma_ms=smooth_sigma_ms,
        baseline_window=baseline_window,
        response_window=response_window,
        low_fraction=low_fraction,
        high_fraction=high_fraction,
    )

    return OnsetStats(
        onset_ms=onset_ms,
        rise_time_ms=rise_time_ms,
        n_trials=len(spike_times_by_trial),
    )


def compute_onset_stats_for_all_channels(
        data: pd.DataFrame,
        spike_data_col: str,
        channels: List[str],
        bin_size_ms: float = 5.0,
        smooth_sigma_ms: float = 10.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        low_fraction: float = 0.10,
        high_fraction: float = 0.90,
) -> dict[str, OnsetStats]:
    """Run compute_onset_stats_for_channel for every channel.

    Returns:
        Dict mapping channel name → OnsetStats.
    """
    return {
        ch: compute_onset_stats_for_channel(
            data, spike_data_col, ch,
            bin_size_ms=bin_size_ms,
            smooth_sigma_ms=smooth_sigma_ms,
            baseline_window=baseline_window,
            response_window=response_window,
            low_fraction=low_fraction,
            high_fraction=high_fraction,
        )
        for ch in channels
    }

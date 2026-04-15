"""
response_onset.py
-----------------
Reusable utilities for computing response onset latency from spike timestamp data.

Onset is detected via PSTH threshold crossing:
  1. Build a PSTH (spikes/s) binned across all trials.
  2. Smooth with a Gaussian kernel.
  3. Compute baseline mean + N*std from the pre-stimulus window.
  4. Report the first post-stimulus bin that exceeds the threshold.

Public API
----------
    get_channel_spikes(trial, spike_data_col, channel)
        → List[float]  (spike times in seconds, epoch-relative)

    compute_psth_onset(spike_times_by_trial, ...)
        → float  (onset latency in ms, or NaN if threshold not crossed)

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
from scipy.ndimage import gaussian_filter1d


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class OnsetStats:
    """Per-channel PSTH onset summary."""
    onset_ms: float  # threshold-crossing latency in ms (NaN if not found)
    n_trials: int    # number of trials used to build the PSTH


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
# PSTH threshold-crossing onset
# ---------------------------------------------------------------------------

def compute_psth_onset(
        spike_times_by_trial: List[List[float]],
        bin_size_ms: float = 5.0,
        smooth_sigma_ms: float = 10.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        threshold_n_std: float = 2.5,
) -> float:
    """Detect onset latency from a population PSTH threshold crossing.

    Args:
        spike_times_by_trial: One list of spike times (seconds) per trial.
        bin_size_ms:          PSTH bin width in milliseconds.
        smooth_sigma_ms:      Sigma of the Gaussian smoothing kernel in milliseconds.
        baseline_window:      (start, end) in seconds; used to compute mean/std baseline.
        response_window:      (start, end) in seconds; the window searched for threshold crossing.
        threshold_n_std:      Threshold = baseline_mean + threshold_n_std * baseline_std.

    Returns:
        Onset latency in milliseconds, or NaN if the threshold is never crossed.
    """
    n_trials = len(spike_times_by_trial)
    if n_trials == 0:
        return np.nan

    bin_size_s = bin_size_ms / 1000.0
    t_start = baseline_window[0]
    t_end = response_window[1]
    bin_edges = np.arange(t_start, t_end + bin_size_s, bin_size_s)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    n_bins = len(bin_centers)

    # Accumulate spike counts across trials
    psth_counts = np.zeros(n_bins)
    for spike_times in spike_times_by_trial:
        counts, _ = np.histogram(spike_times, bins=bin_edges)
        psth_counts += counts

    # Average and convert to firing rate (Hz)
    psth_hz = psth_counts / n_trials / bin_size_s

    # Gaussian smoothing
    smooth_sigma_bins = smooth_sigma_ms / bin_size_ms
    psth_smooth = gaussian_filter1d(psth_hz, sigma=smooth_sigma_bins)

    # Baseline stats from the pre-stimulus window
    baseline_mask = (bin_centers >= baseline_window[0]) & (bin_centers < baseline_window[1])
    if baseline_mask.sum() == 0:
        return np.nan
    baseline_mean = psth_smooth[baseline_mask].mean()
    baseline_std = psth_smooth[baseline_mask].std()
    threshold = baseline_mean + threshold_n_std * baseline_std

    # First response bin above threshold
    response_mask = (bin_centers >= response_window[0]) & (bin_centers <= response_window[1])
    for idx in np.where(response_mask)[0]:
        if psth_smooth[idx] > threshold:
            return float(bin_centers[idx] * 1000.0)

    return np.nan


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
        threshold_n_std: float = 2.5,
) -> OnsetStats:
    """Compute PSTH onset latency for *channel* across all trials in *data*.

    Args:
        data:             DataFrame where each row is one trial.
        spike_data_col:   Column holding spike-timestamp dicts keyed by channel.
        channel:          Channel name (e.g. "A-007").
        bin_size_ms:      PSTH bin width in ms.
        smooth_sigma_ms:  Gaussian kernel sigma in ms.
        baseline_window:  Pre-stimulus window (seconds) for baseline stats.
        response_window:  Post-stimulus window (seconds) to search for threshold crossing.
        threshold_n_std:  Number of baseline std deviations above mean for threshold.

    Returns:
        OnsetStats with PSTH threshold-crossing latency in ms and trial count.
    """
    spike_times_by_trial: List[List[float]] = [
        get_channel_spikes(trial, spike_data_col, channel)
        for _, trial in data.iterrows()
    ]

    onset_ms = compute_psth_onset(
        spike_times_by_trial,
        bin_size_ms=bin_size_ms,
        smooth_sigma_ms=smooth_sigma_ms,
        baseline_window=baseline_window,
        response_window=response_window,
        threshold_n_std=threshold_n_std,
    )

    return OnsetStats(onset_ms=onset_ms, n_trials=len(spike_times_by_trial))


def compute_onset_stats_for_all_channels(
        data: pd.DataFrame,
        spike_data_col: str,
        channels: List[str],
        bin_size_ms: float = 5.0,
        smooth_sigma_ms: float = 10.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        threshold_n_std: float = 2.5,
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
            threshold_n_std=threshold_n_std,
        )
        for ch in channels
    }

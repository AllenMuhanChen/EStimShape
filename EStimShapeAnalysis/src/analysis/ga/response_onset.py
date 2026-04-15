"""
response_onset.py
-----------------
Reusable utilities for computing response onset latency and jitter from spike data.

Two distinct measures are provided:

  onset_ms   – population-level latency via PSTH threshold crossing.
               Robust to single-trial noise because spikes are averaged across trials.
               Steps: bin → Gaussian-smooth → find first post-stimulus bin above
               (baseline_mean + N * baseline_std).

  jitter_std_ms – per-trial timing consistency, measured as the std of each trial's
               first spike within a narrow window centred on the detected PSTH onset.
               This is NOT used to estimate latency (too noisy), but the spread of
               first-spike times around a known onset is a legitimate jitter metric.
               NaN when onset_ms is NaN (channel not driven).

Public API
----------
    get_channel_spikes(trial, spike_data_col, channel)
        → List[float]  (spike times in seconds, epoch-relative)

    compute_psth_onset(spike_times_by_trial, ...)
        → float  (PSTH threshold-crossing latency in ms, or NaN)

    compute_onset_jitter(spike_times_by_trial, onset_s, ...)
        → (jitter_std_ms: float, n_trials_with_onset: int)

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
    """Per-channel onset latency and jitter summary."""
    onset_ms: float        # PSTH threshold-crossing latency in ms (NaN if not driven)
    jitter_std_ms: float   # std of per-trial first-spike times around onset (NaN if not driven)
    n_trials: int          # total trials used to build the PSTH
    n_trials_with_onset: int  # trials that had a spike in the jitter window


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
    """Detect population-level onset latency via PSTH threshold crossing.

    Args:
        spike_times_by_trial: One list of spike times (seconds) per trial.
        bin_size_ms:          PSTH bin width in milliseconds.
        smooth_sigma_ms:      Sigma of the Gaussian smoothing kernel in milliseconds.
        baseline_window:      (start, end) seconds; defines mean/std baseline.
        response_window:      (start, end) seconds; window searched for threshold crossing.
        threshold_n_std:      Threshold = baseline_mean + threshold_n_std * baseline_std.

    Returns:
        PSTH threshold-crossing latency in milliseconds, or NaN if never crossed.
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

    # Baseline stats
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
# Per-trial jitter around the detected onset
# ---------------------------------------------------------------------------

def compute_onset_jitter(
        spike_times_by_trial: List[List[float]],
        onset_s: float,
        pre_window_s: float = 0.020,
        post_window_s: float = 0.100,
) -> Tuple[float, int]:
    """Compute timing jitter as the std of per-trial first-spike times near the onset.

    The window [onset_s - pre_window_s, onset_s + post_window_s] is centred on the
    already-detected PSTH onset, so we are not using first-spike to estimate latency
    (which would be corrupted by spontaneous activity). Instead we measure how tightly
    the per-trial first spikes cluster around the population onset.

    Args:
        spike_times_by_trial: One list of spike times (seconds) per trial.
        onset_s:              PSTH-detected onset in seconds. If NaN, returns (NaN, 0).
        pre_window_s:         How far before the onset to start the jitter window (s).
        post_window_s:        How far after the onset to end the jitter window (s).

    Returns:
        (jitter_std_ms, n_trials_with_onset) — std in milliseconds and trial count.
        jitter_std_ms is NaN when fewer than 2 trials had a spike in the window.
    """
    if np.isnan(onset_s):
        return np.nan, 0

    win_start = onset_s - pre_window_s
    win_end = onset_s + post_window_s

    first_spikes_s: List[float] = []
    for spike_times in spike_times_by_trial:
        in_window = [s for s in spike_times if win_start <= s <= win_end]
        if in_window:
            first_spikes_s.append(min(in_window))

    n = len(first_spikes_s)
    if n < 2:
        return np.nan, n

    return float(np.std(first_spikes_s) * 1000.0), n


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
        jitter_pre_window_s: float = 0.020,
        jitter_post_window_s: float = 0.100,
) -> OnsetStats:
    """Compute PSTH onset latency and per-trial jitter for *channel* across all trials.

    Args:
        data:                  DataFrame where each row is one trial.
        spike_data_col:        Column holding spike-timestamp dicts keyed by channel.
        channel:               Channel name (e.g. "A-007").
        bin_size_ms:           PSTH bin width in ms.
        smooth_sigma_ms:       Gaussian kernel sigma in ms.
        baseline_window:       Pre-stimulus window (seconds) for baseline stats.
        response_window:       Post-stimulus window (seconds) to search for onset.
        threshold_n_std:       Baseline std multiplier for threshold.
        jitter_pre_window_s:   Start of jitter window relative to onset (seconds before).
        jitter_post_window_s:  End of jitter window relative to onset (seconds after).

    Returns:
        OnsetStats with PSTH onset, per-trial jitter, and trial counts.
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

    onset_s = onset_ms / 1000.0 if not np.isnan(onset_ms) else np.nan
    jitter_std_ms, n_with_onset = compute_onset_jitter(
        spike_times_by_trial,
        onset_s=onset_s,
        pre_window_s=jitter_pre_window_s,
        post_window_s=jitter_post_window_s,
    )

    return OnsetStats(
        onset_ms=onset_ms,
        jitter_std_ms=jitter_std_ms,
        n_trials=len(spike_times_by_trial),
        n_trials_with_onset=n_with_onset,
    )


def compute_onset_stats_for_all_channels(
        data: pd.DataFrame,
        spike_data_col: str,
        channels: List[str],
        bin_size_ms: float = 5.0,
        smooth_sigma_ms: float = 10.0,
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        threshold_n_std: float = 2.5,
        jitter_pre_window_s: float = 0.020,
        jitter_post_window_s: float = 0.100,
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
            jitter_pre_window_s=jitter_pre_window_s,
            jitter_post_window_s=jitter_post_window_s,
        )
        for ch in channels
    }

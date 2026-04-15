"""
response_onset.py
-----------------
Reusable utilities for computing response onset latency from spike timestamp data.

The central public API is:

    compute_onset_stats_for_channel(data, spike_data_col, channel, window_start, window_end)
        → OnsetStats(mean_ms, std_ms, n_trials_with_onset, all_onset_times_ms)

    get_channel_spikes(trial, spike_data_col, channel)
        → List[float]  (spike times in seconds, epoch-relative)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class OnsetStats:
    """Per-channel onset latency summary."""
    mean_ms: float           # mean first-spike latency in milliseconds (NaN if no spikes)
    std_ms: float            # std  of first-spike latency in milliseconds (NaN if no spikes)
    n_trials_with_onset: int # number of trials that had at least one spike in [window_start, window_end]
    all_onset_times_ms: List[float] = field(default_factory=list)  # raw latency values (ms)


# ---------------------------------------------------------------------------
# Low-level spike extractor (reusable by other modules)
# ---------------------------------------------------------------------------

def get_channel_spikes(trial: pd.Series, spike_data_col: str, channel: str) -> List[float]:
    """Return the list of spike times (seconds, epoch-relative) for *channel* in *trial*.

    Handles both dict-valued cells (keyed by channel name) and plain list-valued cells.
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
# Core computation
# ---------------------------------------------------------------------------

def first_spike_latency(
        spike_times: List[float],
        window_start: float = 0.0,
        window_end: float = 0.7,
) -> Optional[float]:
    """Return the time of the first spike within (window_start, window_end] in seconds.

    Returns None if there are no spikes in the window.
    """
    post = [s for s in spike_times if window_start < s <= window_end]
    return min(post) if post else None


def compute_onset_stats_for_channel(
        data: pd.DataFrame,
        spike_data_col: str,
        channel: str,
        window_start: float = 0.0,
        window_end: float = 0.7,
) -> OnsetStats:
    """Compute first-spike onset latency statistics across all trials for one channel.

    Args:
        data:            DataFrame where each row is one trial.
        spike_data_col:  Column name holding spike-timestamp dicts keyed by channel.
        channel:         Channel name (e.g. "A-007").
        window_start:    Lower bound of the response window in seconds (exclusive).
        window_end:      Upper bound of the response window in seconds (inclusive).

    Returns:
        OnsetStats with mean/std latency in **milliseconds** and trial counts.
    """
    onset_times_s: List[float] = []

    for _, trial in data.iterrows():
        spikes = get_channel_spikes(trial, spike_data_col, channel)
        lat = first_spike_latency(spikes, window_start=window_start, window_end=window_end)
        if lat is not None:
            onset_times_s.append(lat)

    if onset_times_s:
        onset_times_ms = [t * 1000.0 for t in onset_times_s]
        return OnsetStats(
            mean_ms=float(np.mean(onset_times_ms)),
            std_ms=float(np.std(onset_times_ms)),
            n_trials_with_onset=len(onset_times_ms),
            all_onset_times_ms=onset_times_ms,
        )
    else:
        return OnsetStats(
            mean_ms=np.nan,
            std_ms=np.nan,
            n_trials_with_onset=0,
            all_onset_times_ms=[],
        )


def compute_onset_stats_for_all_channels(
        data: pd.DataFrame,
        spike_data_col: str,
        channels: List[str],
        window_start: float = 0.0,
        window_end: float = 0.7,
) -> dict[str, OnsetStats]:
    """Convenience wrapper that runs compute_onset_stats_for_channel for every channel.

    Returns:
        Dict mapping channel name → OnsetStats.
    """
    return {
        ch: compute_onset_stats_for_channel(
            data, spike_data_col, ch, window_start=window_start, window_end=window_end
        )
        for ch in channels
    }

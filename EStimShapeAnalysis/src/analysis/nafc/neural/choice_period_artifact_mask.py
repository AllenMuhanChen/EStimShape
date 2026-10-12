"""
Amplitude-based artifact mask for NAFC trials.

Spike-sized deflections are tens to a few hundred uV; the stimulation /
charge-recovery artifacts seen around choices_on are thousands of uV and hit
many channels at once. So a time point is flagged as artifact when, in the
high-passed signal, at least min_channels channels exceed amp_threshold_uv
(absolute value) within the same bin_s bin (or the next one). Flagged bins
are merged into intervals and widened by pad_s on each side (the amplifier
needs time to settle, and spikes right next to an artifact can't be trusted).

Downstream (choice_period_response.py) spikes inside these intervals are
dropped, the interval time is removed from each trial's choice-period
duration, and each PSTH bin's rate is computed over its unmasked time (a bin
more than half masked is left out, NaN, for that trial).

Only the span [choices_on - span_before_s, choices_off + span_after_s] of each
trial is examined (raw amplifier.dat, read once per trial). Results are
pickled per trial and parameter set, so reruns are cheap.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from typing import Optional

import numpy as np

DEFAULT_ARTIFACT_PARAMS = {
    "amp_threshold_uv": 500.0,   # |high-passed voltage| above this = artifact-sized
    "min_channels": 4,           # ... on at least this many channels at once
    "bin_s": 0.0005,             # coincidence bin
    "pad_s": 0.002,              # widen each interval by this on both sides
    "highpass_hz": 300.0,
    "span_before_s": 1.0,        # examine choices_on - span_before_s ...
    "span_after_s": 0.1,         # ... to choices_off + span_after_s
}


def params_key(params: dict) -> str:
    return hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]


def detect_artifact_intervals(raw_by_channel: dict, sample_rate: float, t_start: float,
                              t_stop: float, *, amp_threshold_uv: float, min_channels: int,
                              bin_s: float, pad_s: float, highpass_hz: float,
                              **_ignored) -> list[tuple[float, float]]:
    """Artifact intervals (recording seconds) within [t_start, t_stop)."""
    from scipy.signal import butter, sosfiltfilt

    guard = 0.05  # extra signal on each side so filter edges don't fall in the span
    i0 = max(0, int((t_start - guard) * sample_rate))
    first = next(iter(raw_by_channel.values()))
    i1 = min(len(first), int((t_stop + guard) * sample_rate))
    if i1 - i0 < 10:
        return []
    sos = butter(4, highpass_hz / (sample_rate / 2), btype="high", output="sos")
    bin_n = max(1, int(round(bin_s * sample_rate)))
    n_bins = (i1 - i0) // bin_n

    counts = np.zeros(n_bins, dtype=int)
    for data in raw_by_channel.values():
        seg = sosfiltfilt(sos, np.asarray(data[i0:i1], dtype=np.float64))
        big = np.abs(seg[:n_bins * bin_n]).reshape(n_bins, bin_n).max(axis=1) > amp_threshold_uv
        near = big.copy()
        near[:-1] |= big[1:]
        counts += near
    flagged = counts >= min_channels
    if not flagged.any():
        return []

    # Runs of flagged bins -> intervals in seconds, padded and merged.
    edges = np.diff(np.concatenate([[0], flagged.astype(int), [0]]))
    starts, stops = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    t0 = i0 / sample_rate
    intervals = []
    for a, b in zip(starts, stops):
        lo = t0 + a * bin_n / sample_rate - pad_s
        hi = t0 + b * bin_n / sample_rate + pad_s
        if intervals and lo <= intervals[-1][1]:
            intervals[-1] = (intervals[-1][0], max(intervals[-1][1], hi))
        else:
            intervals.append((lo, hi))
    return [(max(lo, t_start), min(hi, t_stop)) for lo, hi in intervals
            if hi > t_start and lo < t_stop]


def trial_artifact_intervals(recording_dir: str, neural: dict, params: dict,
                             cache_dir: Optional[str]) -> Optional[list]:
    """Read one trial's amplifier.dat (or the cache) and return its intervals."""
    c_on = neural.get("choices_on")
    if c_on is None:
        return None
    cache_path = None
    if cache_dir is not None:
        cache_path = os.path.join(cache_dir, f"{neural['task_id']}_{params_key(params)}.pkl")
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return pickle.load(f)

    from clat.intan.amplifiers import read_amplifier_data_with_memmap
    from clat.intan.rhs.load_intan_rhs_format import read_data
    rhs = read_data(os.path.join(recording_dir, "info.rhs"))
    sample_rate = float(rhs["frequency_parameters"]["amplifier_sample_rate"])
    raw = read_amplifier_data_with_memmap(os.path.join(recording_dir, "amplifier.dat"),
                                          rhs["amplifier_channels"])
    c_off = neural.get("choices_off")
    t_stop = (c_off if c_off is not None else c_on + 2.0) + params["span_after_s"]
    intervals = detect_artifact_intervals(raw, sample_rate, c_on - params["span_before_s"],
                                          t_stop, **params)

    if cache_path is not None:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(intervals, f)
    return intervals


def overlap_s(lo: float, hi: float, intervals) -> float:
    """Seconds of [lo, hi) covered by intervals."""
    if not intervals:
        return 0.0
    return float(sum(max(0.0, min(hi, b) - max(lo, a)) for a, b in intervals))


def in_intervals(times: np.ndarray, intervals) -> np.ndarray:
    mask = np.zeros(len(times), dtype=bool)
    for a, b in intervals or []:
        mask |= (times >= a) & (times < b)
    return mask


def bin_coverage(bins_rel: np.ndarray, t0: float, intervals) -> np.ndarray:
    """Fraction of each bin (relative to t0) covered by intervals."""
    width = bins_rel[1:] - bins_rel[:-1]
    cov = np.array([overlap_s(t0 + lo, t0 + hi, intervals)
                    for lo, hi in zip(bins_rel[:-1], bins_rel[1:])])
    return cov / width

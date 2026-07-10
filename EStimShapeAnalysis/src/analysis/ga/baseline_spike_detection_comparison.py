"""
Compare baseline response-per-generation profiles across spike-detection methods.

Motivation
----------
Baseline stimuli are re-shown every generation to track how the neural
population's response to a fixed stimulus set drifts over an experiment. That
drift is used as a proxy for global excitability. But some of the drift may be
an artifact of the spike-detection threshold rather than true excitability
change: Intan's spike.dat uses a -4x RMS threshold computed early in the GA and
seldom updated, so slow noise-floor changes or small electrode drift can silently
add/remove units from the count.

This module renders the same baseline profile plot (one line per generation,
x = each baseline parent's Gen-1 response, y = that baseline's response in
Gen-N) side by side for several spike-detection methods, so the drift can be
compared across detectors.

Methods
-------
  Column A - "Raw Intan spikes": the per-trial per-channel spike rates already
             stored in the repository (RawSpikeResponses), i.e. Intan's spike.dat.
  Column B - "-4x RMS / N trials": re-detected from the raw wideband
             (amplifier.dat), recomputing the negative -threshold_rms x RMS
             threshold once per block of `block_size` consecutive trials WITHIN
             each recording file.
  Column C - "NEO / N trials": re-detected from the same wideband using the
             nonlinear (Teager) energy operator, threshold = C x mean(NEO)
             refreshed on the same per-block cadence.

Both columns share the exact same trials and metadata (StimType, GenId,
ParentId, StimSpecId) pulled from the repository; only the per-trial response
value differs, so any difference in the profiles is attributable to the
detector, not to trial selection.

Later steps can register additional detectors (NEO, drift-robust variants) by
appending to the `methods` list in `run_comparison`.
"""

from __future__ import annotations

import hashlib
import os
import pickle
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd
from matplotlib import cm
from matplotlib import pyplot as plt

from src.intan.MultiFileParser import find_files_containing_task_ids
from src.lfp.spike_waveform_features import highpass_filter
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context

ChannelSpec = str | list


# ===========================================================================
# Wideband re-detection: negative -N x RMS, threshold recomputed per trial-block
# ===========================================================================

def _detect_negative_crossings(segment: np.ndarray, threshold: float,
                               refractory_samples: int) -> np.ndarray:
    """Detect negative-going crossings of `threshold` (threshold < 0).

    Snaps each crossing to the local trough within the refractory window and
    enforces the refractory period between successive spikes. Returns sample
    indices into `segment`.
    """
    if segment.size < 2:
        return np.empty(0, dtype=int)

    below = segment < threshold
    crossings = np.where(np.diff(below.astype(np.int8)) == 1)[0] + 1
    if len(crossings) == 0:
        return np.empty(0, dtype=int)

    n = len(segment)
    troughs = []
    for c in crossings:
        window_end = min(c + refractory_samples, n)
        troughs.append(c + int(np.argmin(segment[c:window_end])))
    troughs = np.asarray(troughs, dtype=int)

    kept = [troughs[0]]
    for s in troughs[1:]:
        if s - kept[-1] >= refractory_samples:
            kept.append(s)
    return np.asarray(kept, dtype=int)


def _detect_positive_peaks(signal: np.ndarray, threshold: float,
                           refractory_samples: int) -> np.ndarray:
    """Detect upward crossings of `threshold` (threshold > 0) in a one-sided
    signal (e.g. the NEO energy trace).

    Snaps each crossing to the local peak within the refractory window and
    enforces the refractory period. Returns sample indices into `signal`.
    """
    if signal.size < 2:
        return np.empty(0, dtype=int)

    above = signal > threshold
    crossings = np.where(np.diff(above.astype(np.int8)) == 1)[0] + 1
    if len(crossings) == 0:
        return np.empty(0, dtype=int)

    n = len(signal)
    peaks = []
    for c in crossings:
        window_end = min(c + refractory_samples, n)
        peaks.append(c + int(np.argmax(signal[c:window_end])))
    peaks = np.asarray(peaks, dtype=int)

    kept = [peaks[0]]
    for s in peaks[1:]:
        if s - kept[-1] >= refractory_samples:
            kept.append(s)
    return np.asarray(kept, dtype=int)


def _peak_to_peak(signal: np.ndarray, index: int, half_window: int) -> float:
    """Peak-to-peak amplitude of `signal` in a window centered on `index`."""
    lo = max(0, index - half_window)
    hi = min(len(signal), index + half_window + 1)
    if hi <= lo:
        return 0.0
    window = signal[lo:hi]
    return float(window.max() - window.min())


def _neo(x: np.ndarray) -> np.ndarray:
    """Nonlinear (Teager) energy operator: psi[n] = x[n]^2 - x[n-1]*x[n+1].

    Large where the signal has simultaneously high amplitude AND high
    instantaneous frequency, which is what a spike is; low for slow, low-
    amplitude background even when the raw amplitude drifts. Endpoints set to 0.
    """
    psi = np.zeros_like(x)
    psi[1:-1] = x[1:-1] ** 2 - x[:-2] * x[2:]
    return psi


def _smooth_neo(psi: np.ndarray, window_samples: int) -> np.ndarray:
    """Smooth the NEO trace with a normalized Bartlett (triangular) window.

    Mukhopadhyay & Ray (1998) smooth the raw NEO output over roughly a spike
    width so a single spike produces one energy bump rather than a jagged burst.
    """
    if window_samples < 2:
        return psi
    win = np.bartlett(window_samples)
    win = win / win.sum()
    return np.convolve(psi, win, mode='same')


def _normalize_channel(ch) -> str:
    """Normalize a channel name to the repository/cluster 'A-0XX' form.

    Handles Channel-enum values ('A-002'), underscore variants ('A_002'), and
    plain cluster strings uniformly so lookups match across sources.
    """
    return str(ch).replace('_', '-').upper()


class BlockDetectionStrategy:
    """How to turn a high-pass-filtered channel into spikes, given a per-block
    threshold refresh.

    Three hooks, all operating on the (per-channel) filtered signal:
      - transform_channel: map filtered wideband -> a 'detection signal' the
        threshold and detector run on (identity for amplitude methods; the NEO
        energy trace for NEO).
      - block_threshold: compute the scalar threshold for one block's slice of
        the detection signal (refreshed every `block_size` trials).
      - detect_segment: find spike sample-indices within one trial's slice.
    """

    name = "block"

    def cache_key(self) -> str:
        return self.name

    @property
    def multiplier(self) -> float:
        """The scalar swept by run_threshold_multiplier_sweep (the N in -N x RMS,
        or C in C x mean(NEO))."""
        raise NotImplementedError

    def transform_channel(self, filtered: np.ndarray) -> np.ndarray:
        return filtered

    def block_noise(self, detection_block: np.ndarray) -> float:
        """The per-block noise/scale estimate, independent of the multiplier
        (RMS, MAD sigma, or mean(NEO)). Factored out so a multiplier sweep can
        compute it once and reuse it for every candidate multiplier."""
        raise NotImplementedError

    def scaled_threshold(self, noise: float, multiplier: float) -> float:
        """Combine a noise estimate with a multiplier into a threshold (sign
        and scaling are strategy-specific)."""
        raise NotImplementedError

    def block_threshold(self, detection_block: np.ndarray) -> float:
        return self.scaled_threshold(self.block_noise(detection_block), self.multiplier)

    def detect_segment(self, detection_segment: np.ndarray, threshold: float,
                       refractory_samples: int) -> np.ndarray:
        raise NotImplementedError


class NegativeRmsStrategy(BlockDetectionStrategy):
    """Classic -N x RMS on the filtered amplitude, negative crossings only
    (matches how Intan's spike.dat is usually configured)."""

    name = "neg_rms"

    def __init__(self, threshold_rms: float = 4.0):
        self.threshold_rms = threshold_rms

    @property
    def multiplier(self) -> float:
        return self.threshold_rms

    def cache_key(self) -> str:
        return f"neg_rms_{self.threshold_rms}"

    def block_noise(self, detection_block: np.ndarray) -> float:
        return float(np.sqrt(np.mean(detection_block ** 2)))

    def scaled_threshold(self, noise: float, multiplier: float) -> float:
        return -multiplier * noise

    def detect_segment(self, detection_segment, threshold, refractory_samples):
        return _detect_negative_crossings(detection_segment, threshold, refractory_samples)


class MadStrategy(NegativeRmsStrategy):
    """Negative amplitude threshold, but with the noise level estimated by the
    median absolute deviation, sigma = median(|x|) / 0.6745 (Quiroga et al. 2004),
    instead of RMS.

    Same detector as -N x RMS (negative crossings); only the noise estimate
    differs. MAD is far less inflated by the spikes themselves than RMS, so the
    bar doesn't rise during high-firing stretches — it removes the 'a big unit
    censors itself / heavy firing raises the threshold' bias that RMS suffers.
    """

    name = "neg_mad"

    def __init__(self, threshold_mad: float = 4.0):
        self.threshold_mad = threshold_mad

    @property
    def multiplier(self) -> float:
        return self.threshold_mad

    def cache_key(self) -> str:
        return f"neg_mad_{self.threshold_mad}"

    def block_noise(self, detection_block: np.ndarray) -> float:
        return float(np.median(np.abs(detection_block))) / 0.6745


class NeoStrategy(BlockDetectionStrategy):
    """Nonlinear energy operator (Teager). Detection runs on the smoothed NEO
    trace; threshold = coefficient x mean(NEO) over the block (Mukhopadhyay &
    Ray 1998). Energy is one-sided, so detection uses positive peaks."""

    name = "neo"

    def __init__(self, coefficient: float = 8.0, smooth_ms: float = 0.3,
                 sample_rate_hint: float = 30000.0):
        self.coefficient = coefficient
        self.smooth_ms = smooth_ms
        # smoothing window is set from the true sample rate at parse time
        self._window_samples = max(2, int(smooth_ms * sample_rate_hint / 1000.0))

    @property
    def multiplier(self) -> float:
        return self.coefficient

    def cache_key(self) -> str:
        return f"neo_c{self.coefficient}_sm{self.smooth_ms}"

    def configure(self, sample_rate: float) -> None:
        self._window_samples = max(2, int(self.smooth_ms * sample_rate / 1000.0))

    def transform_channel(self, filtered: np.ndarray) -> np.ndarray:
        return _smooth_neo(_neo(filtered), self._window_samples)

    def block_noise(self, detection_block: np.ndarray) -> float:
        return float(np.mean(detection_block))

    def scaled_threshold(self, noise: float, multiplier: float) -> float:
        return multiplier * noise

    def detect_segment(self, detection_segment, threshold, refractory_samples):
        return _detect_positive_peaks(detection_segment, threshold, refractory_samples)


class PeriodicBlockMUAParser:
    """
    Re-detect MUA spikes from raw wideband (amplifier.dat), refreshing the
    detection threshold once per block of `block_size` consecutive trials
    *within each recording file*. The detection statistic itself is supplied by
    a `BlockDetectionStrategy` (e.g. -N x RMS amplitude, or NEO energy), so the
    only thing that changes between methods is the statistic — the trial set,
    filtering, blocking and epoching are identical.

    Produces the same shape as `MultiFileParser.parse`:
        spikes_by_channel_by_task_id : {task_id: {Channel: [abs spike times, s]}}
        epochs_by_task_id            : {task_id: (start_s, end_s)}
        sample_rate                  : float

    The threshold for each block is computed on the high-pass-filtered wideband
    (transformed by the strategy) spanning that block (first trial start -> last
    trial end), mimicking how Intan estimates its noise floor over a stretch of
    streaming data, but refreshed every `block_size` trials instead of once.
    """

    def __init__(self,
                 strategy: BlockDetectionStrategy,
                 block_size: int = 100,
                 highpass_hz: float = 300.0,
                 refractory_sec: float = 0.001,
                 to_cache: bool = True,
                 cache_dir: Optional[str] = None):
        self.strategy = strategy
        self.block_size = block_size
        self.highpass_hz = highpass_hz
        self.refractory_sec = refractory_sec
        self.to_cache = to_cache
        self.cache_dir = cache_dir
        self.sample_rate: Optional[float] = None

    # ---- parameter signature so caches from different settings never collide --
    def _param_key(self, task_ids: list[int]) -> str:
        payload = (
            f"strategy={self.strategy.cache_key()}|block={self.block_size}|"
            f"hp={self.highpass_hz}|refrac={self.refractory_sec}|"
            f"tasks={sorted(int(t) for t in task_ids)}"
        )
        return hashlib.md5(payload.encode()).hexdigest()[:16]

    def parse(self, task_ids: list[int], intan_files_dir: str):
        """Return (spikes_by_channel_by_task_id, epochs_by_task_id, sample_rate)."""
        spikes, epochs, _amps, sr = self._parse_all(
            task_ids, intan_files_dir, need_amplitudes=False)
        return spikes, epochs, sr

    def parse_with_amplitudes(self, task_ids: list[int], intan_files_dir: str):
        """Like `parse`, but also returns per-spike peak-to-peak amplitudes:
        (spikes_by_channel_by_task_id, epochs_by_task_id,
         amplitudes_by_channel_by_task_id, sample_rate).

        `amplitudes_by_channel_by_task_id[task_id][channel]` is a list parallel
        to the spike-time list, giving each spike's peak-to-peak amplitude (uV)
        measured on the high-pass-filtered trace.
        """
        return self._parse_all(task_ids, intan_files_dir, need_amplitudes=True)

    def _parse_all(self, task_ids: list[int], intan_files_dir: str,
                   *, need_amplitudes: bool = False):
        task_ids = [int(t) for t in task_ids]
        task_id_set = set(task_ids)

        if self.to_cache and self.cache_dir is not None:
            cached = self._load_cache(task_ids)
            # A cache written before per-spike amplitudes existed lacks the
            # 'amplitudes_by_channel_by_task_id' key entirely (-> None). Treat
            # that as a miss only when amplitudes are actually needed, so the
            # profile path still uses the existing spike cache untouched.
            if cached is not None:
                cached_amps = cached.get('amplitudes_by_channel_by_task_id')
                if not (need_amplitudes and cached_amps is None):
                    self.sample_rate = cached['sample_rate']
                    return (cached['spikes_by_channel_by_task_id'],
                            cached['epochs_by_task_id'],
                            cached_amps if cached_amps is not None else {},
                            cached['sample_rate'])

        matching_dirs = find_files_containing_task_ids(task_id_set, intan_files_dir)
        if not matching_dirs:
            raise ValueError(f"No Intan files found containing task IDs {task_ids}")

        spikes_by_channel_by_task_id: dict[int, dict] = {}
        epochs_by_task_id: dict[int, tuple] = {}
        amplitudes_by_channel_by_task_id: dict[int, dict] = {}

        for dir_path in sorted(matching_dirs):
            file_spikes, file_epochs, file_amps, file_sr = self._parse_one_dir(
                dir_path, task_id_set)
            if self.sample_rate is None:
                self.sample_rate = file_sr
            elif file_sr != self.sample_rate:
                raise ValueError(
                    f"Inconsistent sample rates: {self.sample_rate} vs {file_sr}")

            for task_id, channel_spikes in file_spikes.items():
                spikes_by_channel_by_task_id[task_id] = channel_spikes
                epochs_by_task_id[task_id] = file_epochs[task_id]
                amplitudes_by_channel_by_task_id[task_id] = file_amps[task_id]

        if self.to_cache and self.cache_dir is not None and spikes_by_channel_by_task_id:
            self._save_cache(task_ids, spikes_by_channel_by_task_id,
                             epochs_by_task_id, amplitudes_by_channel_by_task_id)

        return (spikes_by_channel_by_task_id, epochs_by_task_id,
                amplitudes_by_channel_by_task_id, self.sample_rate)

    def _parse_one_dir(self, dir_path: str, task_id_set: set[int]):
        # Lazy clat imports: the module should import even where clat is absent.
        from clat.intan.amplifiers import read_amplifier_data_with_memmap
        from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
        from clat.intan.marker_channels import epoch_using_combined_marker_channels

        sample_rate, amplifier_channels = self._read_header(dir_path)
        # Let strategies that depend on sample rate (e.g. NEO smoothing) adjust.
        if hasattr(self.strategy, 'configure'):
            self.strategy.configure(sample_rate)

        amplifier_path = os.path.join(dir_path, "amplifier.dat")
        digital_in_path = os.path.join(dir_path, "digitalin.dat")
        notes_path = os.path.join(dir_path, "notes.txt")

        # Epoch boundaries (raw sample indices) keyed by task_id
        stim_epochs = epoch_using_combined_marker_channels(
            digital_in_path, false_negative_correction_duration=2)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(
            notes_path, stim_epochs,
            require_trial_complete=False,
            is_output_first_instance=False)

        # Ordered list of (task_id, start_idx, end_idx) for trials we care about
        trials = []
        for task_id, epoch_indices in epochs_for_task_ids.items():
            if epoch_indices is None or task_id not in task_id_set:
                continue
            trials.append((task_id, int(epoch_indices[0]), int(epoch_indices[1])))
        trials.sort(key=lambda t: t[1])

        spikes_by_channel_by_task_id: dict[int, dict] = {
            t[0]: {} for t in trials}
        amps_by_channel_by_task_id: dict[int, dict] = {
            t[0]: {} for t in trials}
        epochs_by_task_id: dict[int, tuple] = {
            t[0]: (t[1] / sample_rate, t[2] / sample_rate) for t in trials}

        if not trials:
            return (spikes_by_channel_by_task_id, epochs_by_task_id,
                    amps_by_channel_by_task_id, sample_rate)

        # Contiguous blocks of `block_size` trials (within this file)
        blocks = [trials[i:i + self.block_size]
                  for i in range(0, len(trials), self.block_size)]

        refractory_samples = max(1, int(self.refractory_sec * sample_rate))
        # Half-window (samples) for measuring each spike's peak-to-peak amplitude
        amp_half_w = max(1, int(0.0005 * sample_rate))  # 0.5 ms
        channel_to_raw = read_amplifier_data_with_memmap(amplifier_path, amplifier_channels)

        for channel, raw in channel_to_raw.items():
            filtered = highpass_filter(np.asarray(raw, dtype=np.float64),
                                       sample_rate, self.highpass_hz)
            detection_signal = self.strategy.transform_channel(filtered)
            n = len(detection_signal)

            for block in blocks:
                b_start = max(0, block[0][1])
                b_end = min(n, block[-1][2])
                if b_end <= b_start:
                    continue
                threshold = self.strategy.block_threshold(detection_signal[b_start:b_end])

                for task_id, s_idx, e_idx in block:
                    s = max(0, s_idx)
                    e = min(n, e_idx)
                    if e <= s:
                        spikes_by_channel_by_task_id[task_id][channel] = []
                        amps_by_channel_by_task_id[task_id][channel] = []
                        continue
                    segment = detection_signal[s:e]
                    local = self.strategy.detect_segment(
                        segment, threshold, refractory_samples)
                    abs_idx = s + local
                    spikes_by_channel_by_task_id[task_id][channel] = list(abs_idx / sample_rate)
                    # Amplitude is measured on the filtered trace (not the
                    # detection signal, so it is comparable across strategies).
                    amps_by_channel_by_task_id[task_id][channel] = [
                        _peak_to_peak(filtered, ai, amp_half_w) for ai in abs_idx]

        return (spikes_by_channel_by_task_id, epochs_by_task_id,
                amps_by_channel_by_task_id, sample_rate)

    # ------------------------------------------------------------------
    # Fast threshold-MULTIPLIER sweep (filter + noise estimate computed once)
    # ------------------------------------------------------------------
    def sweep_multipliers(self, task_ids: list[int], intan_files_dir: str,
                          multipliers, channel_filter=None) -> dict:
        """Sweep the detection MULTIPLIER at the parser's fixed block_size,
        filtering each channel and computing the per-block noise estimate ONCE
        and reusing them for every candidate multiplier.

        The multiplier (the N in -N x RMS / MAD, or C in C x mean(NEO)) changes
        only the threshold, never the filtering or the noise estimate — the two
        expensive steps — so this is dramatically cheaper than re-detecting per
        multiplier. `channel_filter` (iterable of channel names) restricts work
        to just those channels for a further speedup.

        Returns {multiplier: {task_id: {channel_value: rate_hz}}}.
        """
        multipliers = [float(m) for m in multipliers]
        task_ids = [int(t) for t in task_ids]
        task_id_set = set(task_ids)
        norm_filter = (None if channel_filter is None
                       else {_normalize_channel(c) for c in channel_filter})

        cached = self._load_sweep_cache(task_ids, multipliers, norm_filter)
        if cached is not None:
            return cached

        matching_dirs = find_files_containing_task_ids(task_id_set, intan_files_dir)
        if not matching_dirs:
            raise ValueError(f"No Intan files found containing task IDs {task_ids}")

        rates_by_mult: dict = {m: {} for m in multipliers}
        for dir_path in sorted(matching_dirs):
            self._sweep_one_dir(dir_path, task_id_set, multipliers,
                                norm_filter, rates_by_mult)

        self._save_sweep_cache(task_ids, multipliers, norm_filter, rates_by_mult)
        return rates_by_mult

    def _sweep_one_dir(self, dir_path, task_id_set, multipliers,
                       norm_filter, rates_by_mult) -> None:
        from clat.intan.amplifiers import read_amplifier_data_with_memmap
        from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
        from clat.intan.marker_channels import epoch_using_combined_marker_channels

        sample_rate, amplifier_channels = self._read_header(dir_path)
        if hasattr(self.strategy, 'configure'):
            self.strategy.configure(sample_rate)

        amplifier_path = os.path.join(dir_path, "amplifier.dat")
        digital_in_path = os.path.join(dir_path, "digitalin.dat")
        notes_path = os.path.join(dir_path, "notes.txt")

        stim_epochs = epoch_using_combined_marker_channels(
            digital_in_path, false_negative_correction_duration=2)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(
            notes_path, stim_epochs,
            require_trial_complete=False, is_output_first_instance=False)

        trials = []
        for task_id, epoch_indices in epochs_for_task_ids.items():
            if epoch_indices is None or task_id not in task_id_set:
                continue
            trials.append((task_id, int(epoch_indices[0]), int(epoch_indices[1])))
        trials.sort(key=lambda t: t[1])
        if not trials:
            return

        for m in multipliers:
            for tid, _, _ in trials:
                rates_by_mult[m].setdefault(tid, {})

        blocks = [trials[i:i + self.block_size]
                  for i in range(0, len(trials), self.block_size)]
        refractory_samples = max(1, int(self.refractory_sec * sample_rate))
        channel_to_raw = read_amplifier_data_with_memmap(amplifier_path, amplifier_channels)

        for channel, raw in channel_to_raw.items():
            cval = _normalize_channel(getattr(channel, 'value', channel))
            if norm_filter is not None and cval not in norm_filter:
                continue  # skip filtering channels we don't need -> big speedup

            filtered = highpass_filter(np.asarray(raw, dtype=np.float64),
                                       sample_rate, self.highpass_hz)
            detection_signal = self.strategy.transform_channel(filtered)
            n = len(detection_signal)

            for block in blocks:
                b_start = max(0, block[0][1])
                b_end = min(n, block[-1][2])
                if b_end <= b_start:
                    continue
                noise = self.strategy.block_noise(detection_signal[b_start:b_end])
                thr = {m: self.strategy.scaled_threshold(noise, m) for m in multipliers}

                for task_id, s_idx, e_idx in block:
                    duration = (e_idx - s_idx) / sample_rate
                    s = max(0, s_idx)
                    e = min(n, e_idx)
                    if e <= s or duration <= 0:
                        for m in multipliers:
                            rates_by_mult[m][task_id][cval] = 0.0
                        continue
                    segment = detection_signal[s:e]
                    for m in multipliers:
                        local = self.strategy.detect_segment(
                            segment, thr[m], refractory_samples)
                        rates_by_mult[m][task_id][cval] = len(local) / duration

    def _sweep_key(self, task_ids, multipliers, norm_filter) -> str:
        chans = 'all' if norm_filter is None else ','.join(sorted(norm_filter))
        payload = (
            f"strategy={self.strategy.name}|block={self.block_size}|"
            f"hp={self.highpass_hz}|refrac={self.refractory_sec}|"
            f"mults={sorted(multipliers)}|chans={chans}|"
            f"tasks={sorted(int(t) for t in task_ids)}"
        )
        return hashlib.md5(payload.encode()).hexdigest()[:16]

    def _load_sweep_cache(self, task_ids, multipliers, norm_filter):
        if not (self.to_cache and self.cache_dir is not None):
            return None
        path = os.path.join(self.cache_dir, f"sweep_{self._sweep_key(task_ids, multipliers, norm_filter)}.pkl")
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception as exc:
            print(f"Failed to load multiplier-sweep cache {path}: {exc}")
            return None

    def _save_sweep_cache(self, task_ids, multipliers, norm_filter, rates_by_mult):
        if not (self.to_cache and self.cache_dir is not None):
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, f"sweep_{self._sweep_key(task_ids, multipliers, norm_filter)}.pkl")
        with open(path, 'wb') as f:
            pickle.dump(rates_by_mult, f)

    # ------------------------------------------------------------------
    # Fast BLOCK-SIZE sweep (filter + NEO transform computed once, reused
    # across every block size AND every strategy)
    # ------------------------------------------------------------------
    def sweep_block_sizes(self, task_ids: list[int], intan_files_dir: str,
                          strategies: list, block_sizes, channel_filter=None) -> dict:
        """Sweep block size across several strategies at once, filtering (and, for
        NEO, energy-transforming) each channel ONLY ONCE and reusing it for every
        block size and strategy. Block size changes only how trials are grouped
        for the noise estimate — not the filtering — so nothing expensive repeats.

        Returns {(strategy.name, block_size_entry): {task_id: {channel: rate_hz}}}
        keyed by the original block_size entries (ints or 'file').
        """
        task_ids = [int(t) for t in task_ids]
        task_id_set = set(task_ids)
        block_sizes = list(block_sizes)
        norm_filter = (None if channel_filter is None
                       else {_normalize_channel(c) for c in channel_filter})

        cached = self._load_blocksweep_cache(task_ids, strategies, block_sizes, norm_filter)
        if cached is not None:
            return cached

        matching_dirs = find_files_containing_task_ids(task_id_set, intan_files_dir)
        if not matching_dirs:
            raise ValueError(f"No Intan files found containing task IDs {task_ids}")

        results: dict = {(s.name, b): {} for s in strategies for b in block_sizes}
        for dir_path in sorted(matching_dirs):
            self._sweep_blocks_one_dir(dir_path, task_id_set, strategies,
                                       block_sizes, norm_filter, results)

        self._save_blocksweep_cache(task_ids, strategies, block_sizes, norm_filter, results)
        return results

    def _sweep_blocks_one_dir(self, dir_path, task_id_set, strategies,
                              block_sizes, norm_filter, results) -> None:
        from clat.intan.amplifiers import read_amplifier_data_with_memmap
        from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
        from clat.intan.marker_channels import epoch_using_combined_marker_channels

        sample_rate, amplifier_channels = self._read_header(dir_path)
        for s in strategies:
            if hasattr(s, 'configure'):
                s.configure(sample_rate)

        amplifier_path = os.path.join(dir_path, "amplifier.dat")
        digital_in_path = os.path.join(dir_path, "digitalin.dat")
        notes_path = os.path.join(dir_path, "notes.txt")

        stim_epochs = epoch_using_combined_marker_channels(
            digital_in_path, false_negative_correction_duration=2)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(
            notes_path, stim_epochs,
            require_trial_complete=False, is_output_first_instance=False)

        trials = []
        for task_id, epoch_indices in epochs_for_task_ids.items():
            if epoch_indices is None or task_id not in task_id_set:
                continue
            trials.append((task_id, int(epoch_indices[0]), int(epoch_indices[1])))
        trials.sort(key=lambda t: t[1])
        if not trials:
            return

        for s in strategies:
            for b in block_sizes:
                for tid, _, _ in trials:
                    results[(s.name, b)].setdefault(tid, {})

        # Pre-chunk trials for each block-size entry once (indices into `trials`).
        blocks_by_size = {b: [trials[i:i + _resolve_block_size(b)]
                              for i in range(0, len(trials), _resolve_block_size(b))]
                          for b in block_sizes}

        refractory_samples = max(1, int(self.refractory_sec * sample_rate))
        channel_to_raw = read_amplifier_data_with_memmap(amplifier_path, amplifier_channels)

        for channel, raw in channel_to_raw.items():
            cval = _normalize_channel(getattr(channel, 'value', channel))
            if norm_filter is not None and cval not in norm_filter:
                continue

            filtered = highpass_filter(np.asarray(raw, dtype=np.float64),
                                       sample_rate, self.highpass_hz)

            for s in strategies:
                detection_signal = s.transform_channel(filtered)  # NEO: computed once
                n = len(detection_signal)
                for b in block_sizes:
                    for block in blocks_by_size[b]:
                        b_start = max(0, block[0][1])
                        b_end = min(n, block[-1][2])
                        if b_end <= b_start:
                            continue
                        noise = s.block_noise(detection_signal[b_start:b_end])
                        thr = s.scaled_threshold(noise, s.multiplier)
                        for task_id, s_idx, e_idx in block:
                            duration = (e_idx - s_idx) / sample_rate
                            ss = max(0, s_idx)
                            ee = min(n, e_idx)
                            if ee <= ss or duration <= 0:
                                results[(s.name, b)][task_id][cval] = 0.0
                                continue
                            local = s.detect_segment(
                                detection_signal[ss:ee], thr, refractory_samples)
                            results[(s.name, b)][task_id][cval] = len(local) / duration

    def _blocksweep_key(self, task_ids, strategies, block_sizes, norm_filter) -> str:
        chans = 'all' if norm_filter is None else ','.join(sorted(norm_filter))
        strat_sig = ';'.join(f'{s.name}:{s.multiplier}' for s in strategies)
        payload = (
            f"strategies={strat_sig}|blocks={list(block_sizes)}|"
            f"hp={self.highpass_hz}|refrac={self.refractory_sec}|chans={chans}|"
            f"tasks={sorted(int(t) for t in task_ids)}"
        )
        return hashlib.md5(payload.encode()).hexdigest()[:16]

    def _load_blocksweep_cache(self, task_ids, strategies, block_sizes, norm_filter):
        if not (self.to_cache and self.cache_dir is not None):
            return None
        path = os.path.join(self.cache_dir,
                            f"blocksweep_{self._blocksweep_key(task_ids, strategies, block_sizes, norm_filter)}.pkl")
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception as exc:
            print(f"Failed to load block-size-sweep cache {path}: {exc}")
            return None

    def _save_blocksweep_cache(self, task_ids, strategies, block_sizes, norm_filter, results):
        if not (self.to_cache and self.cache_dir is not None):
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir,
                            f"blocksweep_{self._blocksweep_key(task_ids, strategies, block_sizes, norm_filter)}.pkl")
        with open(path, 'wb') as f:
            pickle.dump(results, f)

    @staticmethod
    def _read_header(dir_path: str) -> tuple[float, list]:
        """Read amplifier sample rate + channel metadata from info.rhd (or .rhs)."""
        rhd_path = os.path.join(dir_path, "info.rhd")
        rhs_path = os.path.join(dir_path, "info.rhs")
        if os.path.exists(rhd_path):
            from clat.intan.rhd.load_intan_rhd_format import read_data
            header_path = rhd_path
        elif os.path.exists(rhs_path):
            from clat.intan.rhs.load_intan_rhs_format import read_data
            header_path = rhs_path
        else:
            raise FileNotFoundError(
                f"No info.rhd or info.rhs header found in {dir_path}")
        data = read_data(header_path)
        sample_rate = data['frequency_parameters']['amplifier_sample_rate']
        amplifier_channels = data['amplifier_channels']
        return sample_rate, amplifier_channels

    # ---- caching -----------------------------------------------------------
    def _cache_path(self, task_ids: list[int]) -> str:
        return os.path.join(self.cache_dir,
                            f"periodic_{self._param_key(task_ids)}.pkl")

    def _load_cache(self, task_ids: list[int]):
        path = self._cache_path(task_ids)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception as exc:
            print(f"Failed to load periodic-detection cache {path}: {exc}")
            return None

    def _save_cache(self, task_ids, spikes_by_channel_by_task_id, epochs_by_task_id,
                    amplitudes_by_channel_by_task_id):
        os.makedirs(self.cache_dir, exist_ok=True)
        path = self._cache_path(task_ids)
        with open(path, 'wb') as f:
            pickle.dump({
                'spikes_by_channel_by_task_id': spikes_by_channel_by_task_id,
                'epochs_by_task_id': epochs_by_task_id,
                'amplitudes_by_channel_by_task_id': amplitudes_by_channel_by_task_id,
                'sample_rate': self.sample_rate,
            }, f)


def compute_rates_by_task(spikes_by_channel_by_task_id: dict,
                          epochs_by_task_id: dict) -> dict[int, dict[str, float]]:
    """Per-trial per-channel spike RATE (Hz) counted within the epoch window.

    Mirrors `IntanSpikeRateByChannelField`: count spikes with times in
    [epoch_start, epoch_end] and divide by the epoch duration. Channel keys are
    normalized to the repository 'A-0XX' form.
    """
    rates_by_task: dict[int, dict[str, float]] = {}
    for task_id, spikes_by_channel in spikes_by_channel_by_task_id.items():
        epoch = epochs_by_task_id.get(task_id)
        if epoch is None:
            continue
        start_s, end_s = epoch
        duration = end_s - start_s
        if duration <= 0:
            continue
        rates: dict[str, float] = {}
        for channel, times in spikes_by_channel.items():
            t = np.asarray(times, dtype=float)
            count = int(np.sum((t >= start_s) & (t <= end_s)))
            key = _normalize_channel(getattr(channel, 'value', channel))
            rates[key] = count / duration
        rates_by_task[task_id] = rates
    return rates_by_task


# ===========================================================================
# Shared response extraction + baseline profile computation
# ===========================================================================

def add_response_column(df: pd.DataFrame, channel: ChannelSpec) -> pd.DataFrame:
    """Attach a scalar 'Response' column summed over the requested channel(s)."""
    channels = channel if isinstance(channel, list) else [channel]
    norm_channels = [_normalize_channel(c) for c in channels]

    def extract(x):
        if not isinstance(x, dict):
            return 0.0
        norm_x = {_normalize_channel(k): v for k, v in x.items()}
        return float(sum(norm_x.get(c, 0.0) or 0.0 for c in norm_channels))

    out = df.copy()
    out['Response'] = out['Spike Rate by channel'].apply(extract)
    return out


def compute_baseline_profile(df: pd.DataFrame):
    """Compute the per-(ParentId, GenId) baseline responses and the Gen-1 reference.

    Returns (avg_baseline, gen1_avg, avg_catch). `avg_baseline` has columns
    ParentId, GenId, Response, Gen1Response.
    """
    baseline = df[df['StimType'] == 'BASELINE'].copy()
    if baseline.empty:
        raise ValueError("No BASELINE stimuli found in the data.")
    if 'ParentId' not in baseline.columns:
        raise ValueError("ParentId column missing — cannot link baselines to Gen-1 parents.")

    avg_baseline = (baseline
                    .groupby(['ParentId', 'GenId'])['Response']
                    .mean()
                    .reset_index())

    gen1_avg = (df[df['GenId'] == 1]
                .groupby('StimSpecId')['Response']
                .mean()
                .rename('Gen1Response'))
    avg_baseline['Gen1Response'] = avg_baseline['ParentId'].map(gen1_avg)

    catch = df[df['StimType'] == 'CATCH']
    avg_catch = (catch
                 .groupby('GenId')['Response']
                 .mean()
                 .rename('AvgCatch')
                 .reset_index())

    return avg_baseline, gen1_avg, avg_catch


def plot_baseline_profile_onto(ax: plt.Axes,
                               avg_baseline: pd.DataFrame,
                               avg_catch: pd.DataFrame,
                               gen_color: dict,
                               title: str) -> None:
    """Baseline / catch response profiles per generation, on a single Axes.

    x = each baseline parent's Gen-1 response value; y = that baseline's mean
    response in Gen-N. One line per generation. The dashed black line is the
    Gen-1 reference (y = x). Mirrors subplot 1 of
    `BaselineAnalysis._plot_baseline_curves`.
    """
    avg_baseline = avg_baseline.copy()
    parent_gen1 = (avg_baseline[['ParentId', 'Gen1Response']]
                   .drop_duplicates('ParentId')
                   .sort_values('Gen1Response')
                   .reset_index(drop=True))
    x_map = parent_gen1.set_index('ParentId')['Gen1Response']
    avg_baseline['StimX'] = avg_baseline['ParentId'].map(x_map)

    gen1_catch_val = avg_catch.loc[avg_catch['GenId'] == 1, 'AvgCatch']
    if len(gen1_catch_val):
        catch_x = gen1_catch_val.values[0]
    elif len(parent_gen1):
        catch_x = parent_gen1['Gen1Response'].min() - parent_gen1['Gen1Response'].std()
    else:
        catch_x = 0.0

    all_generations = sorted(set(avg_baseline['GenId'].unique()) |
                             set(avg_catch['GenId'].unique()))

    # Gen-1 reference: y = gen-1 response, x = gen-1 response -> diagonal
    gen1_catch_y = gen1_catch_val.values[0] if len(gen1_catch_val) else np.nan
    ax.plot([catch_x] + list(parent_gen1['Gen1Response']),
            [gen1_catch_y] + list(parent_gen1['Gen1Response']),
            marker='o', linewidth=2, markersize=5,
            color='black', linestyle='--', label='Gen 1 (reference)', zorder=3)

    for gen_id in [g for g in all_generations if g > 1]:
        catch_row = avg_catch[avg_catch['GenId'] == gen_id]
        catch_val = catch_row['AvgCatch'].values[0] if len(catch_row) else np.nan
        gen_data = avg_baseline[avg_baseline['GenId'] == gen_id].sort_values('StimX')
        ax.plot([catch_x] + list(gen_data['StimX']),
                [catch_val] + list(gen_data['Response']),
                marker='o', linewidth=1.5, markersize=4,
                color=gen_color.get(gen_id, 'gray'), label=f'Gen {gen_id}')

    if len(parent_gen1):
        tick_xs = [catch_x] + list(parent_gen1['Gen1Response'])
        tick_labels = ([f'{catch_x:.1f}\n(catch)'] +
                       [f'{v:.1f}' for v in parent_gen1['Gen1Response']])
        ax.set_xticks(tick_xs)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
    ax.set_xlabel('Gen-1 response (Hz)')
    ax.set_ylabel('Avg Response (Hz)')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)


def _unify_ylim(axes_row: list) -> None:
    """Set a common y-limit across a row of axes (the union of their limits)."""
    lo = min(ax.get_ylim()[0] for ax in axes_row)
    hi = max(ax.get_ylim()[1] for ax in axes_row)
    for ax in axes_row:
        ax.set_ylim(lo, hi)


def compute_correction_score(avg_baseline: pd.DataFrame) -> float:
    """Single 'how much correction is needed' score for a detector: the mean
    over generations of |median(gen-1 / gen-N) - 1|. 0 = baselines perfectly
    stable across generations (no correction needed); larger = more rescaling.
    """
    df = avg_baseline.copy()
    df = df[(df['Response'] > 0) & df['Gen1Response'].notna()]
    if df.empty:
        return float('nan')
    df['Factor'] = df['Gen1Response'] / df['Response']
    med = df.groupby('GenId')['Factor'].median()
    return float(np.mean(np.abs(med.values - 1.0)))


def plot_correction_factors_onto(ax: plt.Axes, avg_baseline: pd.DataFrame,
                                 gen_color: dict) -> list:
    """Per-generation baseline correction factor (gen-1 / gen-N), paired by
    baseline-stim identity (ParentId).

    A factor of 1 means gen-N baselines already match gen 1 -> no correction
    needed; the farther from 1, the more the normalizer has to rescale that
    generation. Draws faint per-baseline factors, the per-generation median
    trend, and annotates the mean |median - 1| as a single 'how much correction'
    score (lower = a more stable detector). Returns the median factors so the
    caller can put all methods on a common y-axis.
    """
    df = avg_baseline.copy()
    df = df[(df['Response'] > 0) & df['Gen1Response'].notna()].copy()
    if df.empty:
        ax.set_title('no data')
        return []
    df['Factor'] = df['Gen1Response'] / df['Response']
    gens = sorted(df['GenId'].unique())

    ax.axhline(1.0, color='black', linestyle='--', linewidth=1.0, alpha=0.7,
               label='factor = 1 (no correction)')
    for g in gens:
        fs = df.loc[df['GenId'] == g, 'Factor']
        ax.scatter([g] * len(fs), fs, color=gen_color.get(g, 'gray'),
                   s=12, alpha=0.35, zorder=2)

    medians = df.groupby('GenId')['Factor'].median()
    med_values = [float(medians[g]) for g in gens]
    ax.plot(gens, med_values, '-o', color='black', linewidth=1.4,
            markersize=4, zorder=4, label='median factor')

    dev = compute_correction_score(avg_baseline)
    ax.annotate(f'mean |median − 1| = {dev:.2f}', (0.03, 0.97),
                xycoords='axes fraction', ha='left', va='top', fontsize=8,
                bbox=dict(boxstyle='round', fc='white', ec='gray', alpha=0.75))

    ax.set_xticks(gens)
    ax.set_xlabel('Generation')
    ax.set_ylabel('Correction factor\n(gen-1 / gen-N)')
    ax.grid(True, alpha=0.3)
    return med_values


# ===========================================================================
# Detection-method definitions + comparison runner
# ===========================================================================

@dataclass
class DetectionMethod:
    """A named spike-detection method that yields a response-bearing DataFrame.

    `build` receives (session_id, base_df, channel) and must return a copy of
    base_df with a scalar 'Response' column populated. `base_df` already carries
    the trial metadata (StimType, GenId, ParentId, StimSpecId, TaskId) and the
    raw-Intan 'Spike Rate by channel' column.
    """
    name: str
    build: Callable[[str, pd.DataFrame, ChannelSpec], pd.DataFrame]


def _method_raw_intan(session_id: str, base_df: pd.DataFrame,
                      channel: ChannelSpec) -> pd.DataFrame:
    """Column A: use the repository's spike.dat-derived per-channel rates."""
    return add_response_column(base_df, channel)


def _make_wideband_method(name: str,
                          strategy: BlockDetectionStrategy,
                          block_size: int,
                          highpass_hz: float) -> DetectionMethod:
    """Build a DetectionMethod that re-detects from wideband with `strategy`."""

    def build(session_id: str, base_df: pd.DataFrame,
              channel: ChannelSpec) -> pd.DataFrame:
        task_ids = [int(t) for t in base_df['TaskId'].tolist()]
        cache_dir = os.path.join(context.ga_parsed_spikes_path, "periodic_block_mua")
        parser = PeriodicBlockMUAParser(
            strategy=strategy,
            block_size=block_size,
            highpass_hz=highpass_hz,
            to_cache=True,
            cache_dir=cache_dir,
        )
        spikes_by_task, epochs_by_task, _sr = parser.parse(
            task_ids, context.ga_intan_path)
        rates_by_task = compute_rates_by_task(spikes_by_task, epochs_by_task)

        df = base_df.copy()
        df['Spike Rate by channel'] = df['TaskId'].map(
            lambda tid: rates_by_task.get(int(tid), {}))
        return add_response_column(df, channel)

    return DetectionMethod(name=name, build=build)


def make_periodic_rms_method(block_size: int = 100,
                             threshold_rms: float = 4.0,
                             highpass_hz: float = 300.0) -> DetectionMethod:
    """Column B: re-detect from wideband with -N x RMS recomputed per trial-block."""
    return _make_wideband_method(
        name=f"-{threshold_rms:g}x RMS (negative)\nrecomputed / {block_size} trials",
        strategy=NegativeRmsStrategy(threshold_rms=threshold_rms),
        block_size=block_size,
        highpass_hz=highpass_hz,
    )


def make_periodic_mad_method(block_size: int = 100,
                             threshold_mad: float = 4.0,
                             highpass_hz: float = 300.0) -> DetectionMethod:
    """-N x MAD (median noise estimate) recomputed per trial-block. Same
    detector as the RMS method; only the noise estimate is more spike-robust."""
    return _make_wideband_method(
        name=f"-{threshold_mad:g}x MAD (median noise)\nrecomputed / {block_size} trials",
        strategy=MadStrategy(threshold_mad=threshold_mad),
        block_size=block_size,
        highpass_hz=highpass_hz,
    )


def make_neo_method(block_size: int = 100,
                    coefficient: float = 8.0,
                    smooth_ms: float = 0.3,
                    highpass_hz: float = 300.0) -> DetectionMethod:
    """Column C: NEO (Teager energy) detection, threshold = C x mean(NEO)
    recomputed per trial-block."""
    return _make_wideband_method(
        name=f"NEO energy\n(C={coefficient:g} x mean, / {block_size} trials)",
        strategy=NeoStrategy(coefficient=coefficient, smooth_ms=smooth_ms),
        block_size=block_size,
        highpass_hz=highpass_hz,
    )


def run_comparison(session_id: Optional[str] = None,
                   channel: Optional[ChannelSpec] = None,
                   methods: Optional[list[DetectionMethod]] = None,
                   block_size: int = 100,
                   save_path: Optional[str] = None):
    """Render baseline profiles for each detection method, one column per method.

    Defaults: current session (from context.ga_database), cluster channels
    summed, and three methods (raw Intan; -4x RMS per `block_size` trials; NEO
    per `block_size` trials).
    """
    if session_id is None:
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    if channel is None:
        channel = read_cluster_channels(session_id)
    if methods is None:
        methods = [
            DetectionMethod("Raw Intan spikes\n(spike.dat, -4x RMS seldom updated)",
                            _method_raw_intan),
            make_periodic_rms_method(block_size=block_size, threshold_rms=5.0),
            make_periodic_mad_method(block_size=block_size),
            make_neo_method(block_size=block_size),
        ]

    print(f"Loading repository trial data for session {session_id} ...")
    base_df = import_from_repository(session_id, "ga", "GAStimInfo", "RawSpikeResponses")

    channel_label = ', '.join(channel) if isinstance(channel, list) else channel
    channel_str = '_'.join(channel) if isinstance(channel, list) else channel

    # Build each method's response DataFrame + baseline profile
    method_results = []
    all_generations: set = set()
    for method in methods:
        print(f"Building method: {method.name!r}")
        df = method.build(session_id, base_df, channel)
        avg_baseline, _gen1_avg, avg_catch = compute_baseline_profile(df)
        all_generations |= set(avg_baseline['GenId'].unique())
        all_generations |= set(avg_catch['GenId'].unique())
        method_results.append((method.name, avg_baseline, avg_catch))

    # Shared generation color map across all columns for comparability
    gens_sorted = sorted(all_generations)
    colors = cm.viridis(np.linspace(0, 1, max(len(gens_sorted), 1)))
    gen_color = {g: colors[i] for i, g in enumerate(gens_sorted)}

    n = len(method_results)
    # Row 0: baseline profiles.  Row 1: per-generation correction factor.
    fig, axes = plt.subplots(2, n, figsize=(7 * n, 9), squeeze=False,
                             gridspec_kw={'height_ratios': [3, 2]})
    fig.suptitle(
        f'Baseline response-per-generation profiles by spike-detection method\n'
        f'Session: {session_id}  |  Channel(s): {channel_label}',
        fontsize=13)

    bottom_medians: list = []
    for i, (name, avg_baseline, avg_catch) in enumerate(method_results):
        plot_baseline_profile_onto(axes[0][i], avg_baseline, avg_catch,
                                   gen_color, title=name)
        meds = plot_correction_factors_onto(axes[1][i], avg_baseline, gen_color)
        bottom_medians.extend(meds)

    # Row 0 shares a y-axis (Hz); apply a common limit across the profiles.
    _unify_ylim(list(axes[0]))
    # Row 1 shares a y-axis (correction factor); scale from the median trends
    # (plus the reference at 1) so a single tiny-response outlier can't blow it up.
    if bottom_medians:
        lo = min(bottom_medians + [1.0])
        hi = max(bottom_medians + [1.0])
        pad = 0.15 * (hi - lo) if hi > lo else 0.2
        for ax in axes[1]:
            ax.set_ylim(lo - pad, hi + pad)

    # One shared legend (generations) to the right
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=7, loc='center right',
               bbox_to_anchor=(1.0, 0.5))
    fig.tight_layout(rect=(0, 0, 0.92, 1))

    if save_path is None:
        save_dir = f"/home/connorlab/Documents/plots/{session_id}"
        os.makedirs(save_dir, exist_ok=True)
        save_path = f"{save_dir}/{channel_str}_baseline_detection_comparison.png"
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved detection-comparison plot to {save_path}")

    plt.show()
    return fig


# ===========================================================================
# Threshold-refresh block-size sweep
# ===========================================================================

_WHOLE_FILE_BLOCK = 10 ** 9  # block larger than any file -> one threshold per file


def _resolve_block_size(bs) -> int:
    """Map a sweep entry to an integer block size ('file' -> whole-file)."""
    return _WHOLE_FILE_BLOCK if bs == 'file' else int(bs)


def _strategy_label(s: BlockDetectionStrategy) -> str:
    """Human-readable legend label for a strategy instance."""
    if s.name == 'neg_rms':
        return f'-{s.multiplier:g}x RMS (negative)'
    if s.name == 'neg_mad':
        return f'-{s.multiplier:g}x MAD (median noise)'
    if s.name == 'neo':
        return f'NEO energy (C={s.multiplier:g})'
    return s.name


def run_block_size_sweep(session_id: Optional[str] = None,
                         channel: Optional[ChannelSpec] = None,
                         block_sizes: tuple = (25, 50, 100, 200, 'file'),
                         highpass_hz: float = 300.0,
                         save_path: Optional[str] = None):
    """Sweep the threshold-refresh block size for each wideband detector and plot
    the correction score (mean |median factor - 1|; lower = less correction) vs
    block size, one line per detector, with the raw-Intan (no re-thresholding)
    score as a dashed reference to beat.

    Reveals both the best refresh cadence (the knee) and which detector is least
    sensitive to it. Each (detector, block size) re-detects from wideband, so the
    first run is slow; results are cached per (strategy, block size).
    """
    if session_id is None:
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    if channel is None:
        channel = read_cluster_channels(session_id)
    channels = channel if isinstance(channel, list) else [channel]

    strategies = [NegativeRmsStrategy(4.0), MadStrategy(4.0), NeoStrategy(8.0)]

    print(f"Loading repository trial data for session {session_id} ...")
    base_df = import_from_repository(session_id, "ga", "GAStimInfo", "RawSpikeResponses")
    channel_label = ', '.join(channels)
    channel_str = '_'.join(channels)

    task_ids = [int(t) for t in base_df['TaskId'].tolist()]
    cache_dir = os.path.join(context.ga_parsed_spikes_path, "periodic_block_mua")
    parser = PeriodicBlockMUAParser(
        strategy=strategies[0], block_size=100, highpass_hz=highpass_hz,
        to_cache=True, cache_dir=cache_dir)
    print(f"Sweeping block sizes {list(block_sizes)} x {len(strategies)} detectors "
          f"over {len(channels)} channel(s) (single filter pass) ...")
    rates = parser.sweep_block_sizes(
        task_ids, context.ga_intan_path, strategies, block_sizes,
        channel_filter=channels)

    # Raw-Intan reference (no per-block re-thresholding)
    raw_ab, _g, _c = compute_baseline_profile(_method_raw_intan(session_id, base_df, channel))
    raw_score = compute_correction_score(raw_ab)

    x = list(range(len(block_sizes)))
    labels = [str(b) for b in block_sizes]

    fig, ax = plt.subplots(figsize=(9, 6))
    for s in strategies:
        scores = []
        for b in block_sizes:
            df = base_df.copy()
            df['Spike Rate by channel'] = df['TaskId'].map(
                lambda tid, key=(s.name, b): rates[key].get(int(tid), {}))
            ab, _gg, _cc = compute_baseline_profile(add_response_column(df, channel))
            scores.append(compute_correction_score(ab))
        ax.plot(x, scores, '-o', linewidth=1.6, markersize=5, label=_strategy_label(s))

    ax.axhline(raw_score, linestyle='--', color='gray', linewidth=1.2,
               label=f'Raw Intan (no re-thresh) = {raw_score:.2f}')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel('Threshold-refresh block size (trials per file;  "file" = whole file)')
    ax.set_ylabel('Correction needed:  mean |median factor − 1|\n(lower = less correction)')
    ax.set_title(f'Threshold-refresh block-size sweep  |  Session: {session_id}  |  '
                 f'Channel(s): {channel_label}')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()

    if save_path is None:
        save_dir = f"/home/connorlab/Documents/plots/{session_id}"
        os.makedirs(save_dir, exist_ok=True)
        save_path = f"{save_dir}/{channel_str}_block_size_sweep.png"
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved block-size sweep plot to {save_path}")

    plt.show()
    return fig


# ===========================================================================
# Threshold-multiplier sweep (fast: filter + noise estimate computed once)
# ===========================================================================

def run_threshold_multiplier_sweep(session_id: Optional[str] = None,
                                   channel: Optional[ChannelSpec] = None,
                                   block_size: int = 50,
                                   strategy: Optional[BlockDetectionStrategy] = None,
                                   multipliers: tuple = (2.0, 2.5, 3.0, 3.5, 4.0,
                                                         4.5, 5.0, 5.5, 6.0),
                                   highpass_hz: float = 300.0,
                                   save_path: Optional[str] = None):
    """Sweep the detection multiplier (default: the N in -N x RMS) at a fixed
    block size, plotting the correction score vs multiplier.

    Fast: each channel is filtered and its per-block noise estimated only once;
    only the (cheap) thresholding + crossing detection is repeated per
    multiplier, and work is restricted to the requested channels. Pass a
    different `strategy` (MadStrategy(), NeoStrategy()) to sweep MAD's or NEO's
    multiplier instead; its own multiplier value is ignored during the sweep.
    """
    if session_id is None:
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    if channel is None:
        channel = read_cluster_channels(session_id)
    if strategy is None:
        strategy = NegativeRmsStrategy()
    channels = channel if isinstance(channel, list) else [channel]
    multipliers = [float(m) for m in multipliers]

    print(f"Loading repository trial data for session {session_id} ...")
    base_df = import_from_repository(session_id, "ga", "GAStimInfo", "RawSpikeResponses")
    channel_label = ', '.join(channels)
    channel_str = '_'.join(channels)

    task_ids = [int(t) for t in base_df['TaskId'].tolist()]
    cache_dir = os.path.join(context.ga_parsed_spikes_path, "periodic_block_mua")
    parser = PeriodicBlockMUAParser(
        strategy=strategy, block_size=block_size, highpass_hz=highpass_hz,
        to_cache=True, cache_dir=cache_dir)
    print(f"Sweeping {strategy.name} multipliers {multipliers} at block={block_size} "
          f"over {len(channels)} channel(s) ...")
    rates_by_mult = parser.sweep_multipliers(
        task_ids, context.ga_intan_path, multipliers, channel_filter=channels)

    # Raw-Intan reference (no re-thresholding)
    raw_ab, _g, _c = compute_baseline_profile(_method_raw_intan(session_id, base_df, channel))
    raw_score = compute_correction_score(raw_ab)

    scores = []
    for m in multipliers:
        df = base_df.copy()
        df['Spike Rate by channel'] = df['TaskId'].map(
            lambda tid, mm=m: rates_by_mult[mm].get(int(tid), {}))
        ab, _gg, _cc = compute_baseline_profile(add_response_column(df, channel))
        scores.append(compute_correction_score(ab))

    best_i = int(np.nanargmin(scores))

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(multipliers, scores, '-o', linewidth=1.6, markersize=5,
            color='steelblue', label=strategy.name)
    ax.scatter([multipliers[best_i]], [scores[best_i]], s=140, facecolors='none',
               edgecolors='red', linewidths=2, zorder=5,
               label=f'best = {multipliers[best_i]:g}  ({scores[best_i]:.3f})')
    ax.axhline(raw_score, linestyle='--', color='gray', linewidth=1.2,
               label=f'Raw Intan (no re-thresh) = {raw_score:.2f}')
    ax.set_xlabel(f'Threshold multiplier  (block size = {block_size} trials/file)')
    ax.set_ylabel('Correction needed:  mean |median factor − 1|\n(lower = less correction)')
    ax.set_title(f'{strategy.name} threshold-multiplier sweep  |  '
                 f'Session: {session_id}  |  Channel(s): {channel_label}')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()

    if save_path is None:
        save_dir = f"/home/connorlab/Documents/plots/{session_id}"
        os.makedirs(save_dir, exist_ok=True)
        save_path = f"{save_dir}/{channel_str}_{strategy.name}_multiplier_sweep.png"
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved multiplier-sweep plot to {save_path}")

    plt.show()
    return fig


# ===========================================================================
# Waveform-amplitude-per-generation diagnostic
# ===========================================================================
# This is the tiebreaker between "threshold artifact" and "true excitability".
# Baseline stimuli are the same set every generation, so if a detector's spike
# COUNT rises across generations we ask WHAT the spikes look like:
#   - a growing pile of small, near-threshold events (low-amplitude tail grows,
#     median amplitude drops) => the threshold is admitting more noise/small
#     units => artifact.
#   - the whole amplitude distribution shifts up coherently => the unit(s) are
#     genuinely firing/appearing larger => real gain.

def collect_baseline_spike_amplitudes(base_df: pd.DataFrame,
                                      strategy: BlockDetectionStrategy,
                                      channel: ChannelSpec,
                                      *,
                                      block_size: int = 100,
                                      highpass_hz: float = 300.0) -> dict:
    """Pool per-spike peak-to-peak amplitudes of the baseline reference set by
    generation, for the selected channel(s). Returns {GenId: [amplitudes_uV]}.

    Generations 2..N come from BASELINE-typed trials. Generation 1 has no
    BASELINE trials (the stimuli exist there as their original regime-zero
    stims), so it is included via the gen-1 trials whose StimSpecId matches a
    baseline's ParentId — the same physical stimuli — giving the reference
    anchor the later generations are compared against.
    """
    channels = channel if isinstance(channel, list) else [channel]
    norm_channels = {_normalize_channel(c) for c in channels}

    task_ids = [int(t) for t in base_df['TaskId'].tolist()]
    cache_dir = os.path.join(context.ga_parsed_spikes_path, "periodic_block_mua")
    parser = PeriodicBlockMUAParser(
        strategy=strategy, block_size=block_size, highpass_hz=highpass_hz,
        to_cache=True, cache_dir=cache_dir)
    _spikes, _epochs, amps_by_task, _sr = parser.parse_with_amplitudes(
        task_ids, context.ga_intan_path)

    task_to_gen = dict(zip(base_df['TaskId'].astype(int), base_df['GenId']))
    baseline_mask = base_df['StimType'] == 'BASELINE'
    baseline_tasks = set(base_df.loc[baseline_mask, 'TaskId'].astype(int))

    # Gen 1 has no BASELINE-typed trials: those same physical stimuli appear in
    # gen 1 as their original regime-zero stims. Include them (labelled gen 1)
    # as the reference anchor by matching the baselines' ParentId (== the gen-1
    # StimSpecId) among gen-1 trials.
    baseline_parent_ids = set(base_df.loc[baseline_mask, 'ParentId'].dropna())
    gen1_ref_mask = ((base_df['GenId'] == 1)
                     & (base_df['StimSpecId'].isin(baseline_parent_ids)))
    gen1_ref_tasks = set(base_df.loc[gen1_ref_mask, 'TaskId'].astype(int))

    amps_by_gen: dict = defaultdict(list)
    for task_id, ch_amps in amps_by_task.items():
        tid = int(task_id)
        if tid in gen1_ref_tasks:
            gen = 1
        elif tid in baseline_tasks:
            gen = task_to_gen.get(tid)
        else:
            continue
        if gen is None:
            continue
        for ch, alist in ch_amps.items():
            if _normalize_channel(getattr(ch, 'value', ch)) in norm_channels:
                amps_by_gen[gen].extend(alist)
    return dict(amps_by_gen)


def plot_amplitude_distributions_onto(ax: plt.Axes, amps_by_gen: dict,
                                      gen_color: dict, title: str) -> None:
    """Violin of baseline spike amplitudes per generation, with the median
    amplitude trend and per-generation spike counts overlaid."""
    gens = sorted(amps_by_gen)
    data = [np.asarray(amps_by_gen[g], dtype=float) for g in gens]
    positions = list(range(1, len(gens) + 1))

    nonempty = [(p, g, d) for p, g, d in zip(positions, gens, data) if d.size > 1]
    if nonempty:
        parts = ax.violinplot([d for _, _, d in nonempty],
                              positions=[p for p, _, _ in nonempty],
                              showextrema=False, widths=0.85)
        for body, (_, g, _) in zip(parts['bodies'], nonempty):
            body.set_facecolor(gen_color.get(g, 'gray'))
            body.set_alpha(0.6)
            body.set_edgecolor('gray')

    medians = [float(np.median(d)) if d.size else np.nan for d in data]
    ax.plot(positions, medians, '-o', color='black', linewidth=1.5,
            markersize=4, label='median amplitude', zorder=5)

    # Per-generation spike counts along the top
    for p, d in zip(positions, data):
        ax.annotate(f'{d.size}', (p, 0.99), xycoords=ax.get_xaxis_transform(),
                    ha='center', va='top', fontsize=6, color='dimgray')

    ax.set_xticks(positions)
    ax.set_xticklabels([f'{g}' for g in gens])
    ax.set_xlabel('Generation  (top row = spike count)')
    ax.set_ylabel('Spike peak-to-peak amplitude (uV)')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7, loc='upper right')


def run_amplitude_diagnostic(session_id: Optional[str] = None,
                             channel: Optional[ChannelSpec] = None,
                             block_size: int = 100,
                             strategies: Optional[list] = None,
                             save_path: Optional[str] = None):
    """Render, per detector, the baseline-stim spike-amplitude distribution for
    each generation. One column per detection strategy.

    `strategies` is a list of (label, BlockDetectionStrategy); defaults to
    -4x RMS, -4x MAD, and NEO so it lines up with the profile comparison. The
    raw-Intan method is omitted here because spike.dat carries no per-spike
    waveforms to measure.
    """
    if session_id is None:
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    if channel is None:
        channel = read_cluster_channels(session_id)
    if strategies is None:
        strategies = [
            ("-4x RMS (negative)", NegativeRmsStrategy(threshold_rms=4.0)),
            ("-4x MAD (median noise)", MadStrategy(threshold_mad=4.0)),
            ("NEO energy (C=8)", NeoStrategy(coefficient=8.0)),
        ]

    print(f"Loading repository trial data for session {session_id} ...")
    base_df = import_from_repository(session_id, "ga", "GAStimInfo", "RawSpikeResponses")

    channel_label = ', '.join(channel) if isinstance(channel, list) else channel
    channel_str = '_'.join(channel) if isinstance(channel, list) else channel

    results = []
    all_gens: set = set()
    for name, strat in strategies:
        print(f"Collecting baseline spike amplitudes for: {name!r}")
        amps_by_gen = collect_baseline_spike_amplitudes(
            base_df, strat, channel, block_size=block_size)
        all_gens |= set(amps_by_gen)
        results.append((name, amps_by_gen))

    gens_sorted = sorted(all_gens)
    colors = cm.viridis(np.linspace(0, 1, max(len(gens_sorted), 1)))
    gen_color = {g: colors[i] for i, g in enumerate(gens_sorted)}

    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(7 * n, 6), squeeze=False, sharey=True)
    fig.suptitle(
        f'Baseline-stim spike-amplitude distribution per generation  |  '
        f'Session: {session_id}  |  Channel(s): {channel_label}\n'
        'Growing low-amplitude tail / falling median => threshold admitting '
        'smaller events (artifact);  whole distribution rising => true gain',
        fontsize=11)

    for ax, (name, amps_by_gen) in zip(axes[0], results):
        plot_amplitude_distributions_onto(ax, amps_by_gen, gen_color, name)

    fig.tight_layout()

    if save_path is None:
        save_dir = f"/home/connorlab/Documents/plots/{session_id}"
        os.makedirs(save_dir, exist_ok=True)
        save_path = f"{save_dir}/{channel_str}_baseline_amplitude_diagnostic.png"
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved amplitude-diagnostic plot to {save_path}")

    plt.show()
    return fig


def main():
    # run_comparison(block_size=50)
    # run_amplitude_diagnostic(block_size=50)
    # run_block_size_sweep()
    run_threshold_multiplier_sweep(block_size=100, strategy=NegativeRmsStrategy(), multipliers=(2, 3, 4, 5, 6))


if __name__ == "__main__":
    main()

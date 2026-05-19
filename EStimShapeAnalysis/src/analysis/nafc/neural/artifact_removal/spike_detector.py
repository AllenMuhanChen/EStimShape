"""
Spike (MUA) detection strategies, run *after* artifact removal.

Two interchangeable implementations:

  - RmsThresholdSpikeDetector : negative threshold at -N * RMS (or MAD) of
    the bandpass-filtered trace. Simple and fast; can be biased by baseline
    shifts left over from imperfect artifact removal.

  - NeoSpikeDetector : Nonlinear Energy Operator (Teager-Kaiser).
        psi[x(n)] = x(n)^2 - x(n-1) * x(n+1)
    Emphasizes signals that are simultaneously high-amplitude and
    high-frequency (spikes), suppressing slow baseline drift. Threshold
    at C * mean(psi). More robust than amplitude thresholding when
    estim-induced baseline shifts contaminate the trace.
    See Mukhopadhyay & Ray (1998), Choi et al. (2006).
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
from scipy.signal import butter, sosfilt


class SpikeDetector(ABC):
    """Detect spike sample indices in a 1-D voltage trace."""

    @abstractmethod
    def detect(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        ...

    def bandpass(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        """Return the bandpass-filtered trace used before thresholding.
        Default is a pass-through; override in subclasses that filter."""
        return signal

    def compute_threshold(
        self,
        filtered: np.ndarray,
        noise_mask: Optional[np.ndarray] = None,
    ) -> float:
        """
        Return the detection threshold for the (possibly already-filtered)
        trace. ``noise_mask`` (bool array, same length as ``filtered``)
        selects which samples contribute to the noise estimate; use it to
        exclude artifact-blanked regions. Default returns NaN; subclasses
        that have a notion of threshold should override.
        """
        return float('nan')

    def detect_on_filtered(
        self,
        filtered: np.ndarray,
        sample_rate: float,
        noise_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Detect spikes on an already-bandpass-filtered trace, optionally
        excluding ``noise_mask=False`` samples from the noise estimate.
        Default falls back to ``detect()``.
        """
        return self.detect(filtered, sample_rate)


class RmsThresholdSpikeDetector(SpikeDetector):
    """
    MUA spike detection by negative-threshold crossing.

    Pipeline:
      1. Band-pass filter the signal in the MUA band
         (default 300-6000 Hz, zero-phase Butterworth).
      2. Estimate noise: ``"rms"`` (default) or ``"mad"`` (robust to spikes).
      3. Mark crossings where ``signal < -threshold_factor * noise``.
         Take the local negative peak within ``peak_search_s`` as the spike.
      4. Enforce refractory period.

    ``detect_on_filtered()`` skips step 1 and accepts an optional
    ``noise_mask`` to exclude artifact windows from the noise estimate (step 2).
    """

    def __init__(
        self,
        threshold_factor: float = 4.0,
        noise_scale: str = "rms",
        bandpass_low_hz: float = 300.0,
        bandpass_high_hz: float = 6000.0,
        filter_order: int = 4,
        refractory_s: float = 0.001,
        peak_search_s: float = 0.0005,
    ):
        if noise_scale not in {"rms", "mad", "std"}:
            raise ValueError(f"unknown noise_scale: {noise_scale!r}")
        self.threshold_factor = threshold_factor
        self.noise_scale = noise_scale
        self.bandpass_low_hz = bandpass_low_hz
        self.bandpass_high_hz = bandpass_high_hz
        self.filter_order = filter_order
        self.refractory_s = refractory_s
        self.peak_search_s = peak_search_s

    def bandpass(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        nyq = sample_rate / 2.0
        high = min(self.bandpass_high_hz, 0.99 * nyq)
        sos = butter(
            self.filter_order,
            [self.bandpass_low_hz, high],
            btype='band', fs=sample_rate, output='sos',
        )
        return sosfilt(sos, np.asarray(signal, dtype=np.float64))

    def compute_threshold(
        self,
        filtered: np.ndarray,
        noise_mask: Optional[np.ndarray] = None,
    ) -> float:
        """
        Estimate the noise floor and return the detection threshold.

        Parameters
        ----------
        noise_mask : np.ndarray of bool, optional
            If given, only ``filtered[noise_mask]`` samples contribute.
            Use this to exclude artifact-blanked regions from the noise
            estimate so their zeros don't pull down the RMS.
        """
        x = filtered if noise_mask is None else filtered[noise_mask]
        if len(x) == 0:
            x = filtered
        if self.noise_scale == "mad":
            scale = 1.4826 * np.median(np.abs(x - np.median(x)))
        elif self.noise_scale == "rms":
            scale = float(np.sqrt(np.mean(x * x)))
        else:  # "std"
            scale = float(np.std(x))
        return self.threshold_factor * max(scale, 1e-12)

    def detect(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        filtered = self.bandpass(signal, sample_rate)
        return self.detect_on_filtered(filtered, sample_rate, noise_mask=None)

    def detect_on_filtered(
        self,
        filtered: np.ndarray,
        sample_rate: float,
        noise_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        threshold = self.compute_threshold(filtered, noise_mask=noise_mask)
        below = filtered < -threshold
        if not below.any():
            return np.array([], dtype=int)

        edges = np.diff(below.astype(np.int8))
        crossings = np.where(edges == 1)[0] + 1
        if below[0]:
            crossings = np.insert(crossings, 0, 0)

        peak_window = max(int(round(self.peak_search_s * sample_rate)), 1)
        refractory_samples = max(int(round(self.refractory_s * sample_rate)), 1)
        n = len(filtered)

        spikes: list[int] = []
        for c in crossings:
            seg_end = min(c + peak_window, n)
            seg = filtered[c:seg_end]
            if len(seg) == 0:
                continue
            peak_idx = c + int(np.argmin(seg))
            if spikes and (peak_idx - spikes[-1]) < refractory_samples:
                continue
            spikes.append(peak_idx)

        return np.array(spikes, dtype=int)


class NeoSpikeDetector(SpikeDetector):
    """
    Spike detection using the Nonlinear Energy Operator (NEO / Teager-Kaiser).

        psi[x(n)] = x(n)^2 - x(n-1) * x(n+1)

    NEO is large only when the signal is simultaneously high-amplitude and
    high-frequency, so slow baseline shifts (e.g. post-estim drift) are
    suppressed and don't bias the threshold the way RMS does.

    Pipeline:
      1. Bandpass-filter (default 300-6000 Hz) — still useful even with NEO
         to keep the operator from amplifying low-frequency drift squared.
      2. Compute NEO sample-by-sample.
      3. Smooth NEO with a Bartlett window of width ``smoothing_window_s``
         (default 1 ms) to integrate energy over a spike's duration.
      4. Threshold = ``threshold_factor * noise(smoothed_neo)`` where
         ``noise`` is ``mean`` (Mukhopadhyay & Ray 1998 style, C ~ 8) or
         ``median`` (default; more robust when many spikes inflate the mean).
      5. Take the local negative peak of the bandpass-filtered trace
         within ``peak_search_s`` of each rising threshold crossing.
         Refractory enforced.

    With ``noise_scale="median"`` good defaults are C ~ 4-6; with
    ``noise_scale="mean"`` use C ~ 8-24 (literature).
    """

    def __init__(
        self,
        threshold_factor: float = 5.0,
        noise_scale: str = "median",
        bandpass_low_hz: float = 300.0,
        bandpass_high_hz: float = 6000.0,
        filter_order: int = 4,
        smoothing_window_s: float = 0.001,
        refractory_s: float = 0.001,
        peak_search_s: float = 0.0005,
        baseline_window_s: float = 0.0,
        min_spike_amplitude_uv: float = 0.0,
        max_spike_amplitude_uv: float = float('inf'),
    ):
        """
        ``baseline_window_s`` > 0 subtracts a running median of the
        smoothed NEO with that window length before thresholding. Kills
        post-pulse artifact-recovery drift that survives the upstream
        bandpass. The median is robust to short spike peaks, so a window
        a couple of ms wide tracks the recovery envelope without
        flattening real spikes. Try 0.002-0.005 s. 0 disables.
        """
        if noise_scale not in {"mean", "median"}:
            raise ValueError(f"unknown noise_scale: {noise_scale!r}")
        self.threshold_factor = threshold_factor
        self.noise_scale = noise_scale
        self.bandpass_low_hz = bandpass_low_hz
        self.bandpass_high_hz = bandpass_high_hz
        self.filter_order = filter_order
        self.smoothing_window_s = smoothing_window_s
        self.refractory_s = refractory_s
        self.peak_search_s = peak_search_s
        self.baseline_window_s = baseline_window_s
        self.min_spike_amplitude_uv = float(min_spike_amplitude_uv)
        self.max_spike_amplitude_uv = float(max_spike_amplitude_uv)

    def bandpass(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        nyq = sample_rate / 2.0
        high = min(self.bandpass_high_hz, 0.99 * nyq)
        sos = butter(
            self.filter_order,
            [self.bandpass_low_hz, high],
            btype='band', fs=sample_rate, output='sos',
        )
        return sosfilt(sos, np.asarray(signal, dtype=np.float64))

    @staticmethod
    def neo(filtered: np.ndarray) -> np.ndarray:
        """Sample-wise NEO. Endpoints set to 0."""
        x = np.asarray(filtered, dtype=np.float64)
        out = np.zeros_like(x)
        out[1:-1] = x[1:-1] ** 2 - x[:-2] * x[2:]
        return out

    def smooth(self, neo: np.ndarray, sample_rate: float) -> np.ndarray:
        win_samples = max(int(round(self.smoothing_window_s * sample_rate)), 1)
        if win_samples < 3:
            return neo
        window = np.bartlett(win_samples)
        window = window / window.sum()
        return np.convolve(neo, window, mode='same')

    def smoothed_neo(
        self, filtered: np.ndarray, sample_rate: float,
    ) -> np.ndarray:
        smoothed = self.smooth(self.neo(filtered), sample_rate)
        if self.baseline_window_s > 0:
            from scipy.ndimage import median_filter
            win = max(int(round(self.baseline_window_s * sample_rate)), 3)
            if win % 2 == 0:
                win += 1
            baseline = median_filter(smoothed, size=win, mode='reflect')
            smoothed = np.maximum(smoothed - baseline, 0.0)
        return smoothed

    def compute_threshold(
        self,
        filtered: np.ndarray,
        noise_mask: Optional[np.ndarray] = None,
        smoothed: Optional[np.ndarray] = None,
    ) -> float:
        """
        Threshold = ``threshold_factor * mean(smoothed_neo[noise_mask])``.

        Pass ``smoothed`` directly to avoid recomputing it (e.g. inside
        ``detect_on_filtered``).
        """
        if smoothed is None:
            # Derive smoothed NEO from the filtered signal. We do not know
            # the sample rate here, so use a fixed 5-sample Bartlett as a
            # cheap fallback; callers that care should pass `smoothed`.
            neo = self.neo(filtered)
            window = np.bartlett(5)
            window = window / window.sum()
            smoothed = np.convolve(neo, window, mode='same')
        x = smoothed if noise_mask is None else smoothed[noise_mask]
        if len(x) == 0:
            x = smoothed
        if self.noise_scale == "median":
            noise = float(np.median(x))
        else:  # "mean"
            noise = float(np.mean(x))
        return self.threshold_factor * max(noise, 1e-12)

    def detect(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        filtered = self.bandpass(signal, sample_rate)
        return self.detect_on_filtered(filtered, sample_rate, noise_mask=None)

    def detect_on_filtered(
        self,
        filtered: np.ndarray,
        sample_rate: float,
        noise_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        smoothed = self.smoothed_neo(filtered, sample_rate)
        threshold = self.compute_threshold(
            filtered, noise_mask=noise_mask, smoothed=smoothed,
        )

        above = smoothed > threshold
        if not above.any():
            return np.array([], dtype=int)

        edges = np.diff(above.astype(np.int8))
        crossings = np.where(edges == 1)[0] + 1
        if above[0]:
            crossings = np.insert(crossings, 0, 0)

        peak_window = max(int(round(self.peak_search_s * sample_rate)), 1)
        refractory_samples = max(int(round(self.refractory_s * sample_rate)), 1)
        n = len(filtered)

        spikes: list[int] = []
        for c in crossings:
            seg_end = min(c + peak_window, n)
            seg = filtered[c:seg_end]
            if len(seg) == 0:
                continue
            # Spike time = local negative peak of the bandpass-filtered trace.
            peak_idx = c + int(np.argmin(seg))
            # Amplitude check: examine max |signal| in a window around the
            # peak so a small negative trough sitting on a huge artifact
            # excursion gets rejected.
            wlo = max(peak_idx - peak_window, 0)
            whi = min(peak_idx + peak_window, n)
            window_amp = float(np.max(np.abs(filtered[wlo:whi])))
            if window_amp < self.min_spike_amplitude_uv:
                continue
            if window_amp > self.max_spike_amplitude_uv:
                continue
            if spikes and (peak_idx - spikes[-1]) < refractory_samples:
                continue
            spikes.append(peak_idx)

        return np.array(spikes, dtype=int)

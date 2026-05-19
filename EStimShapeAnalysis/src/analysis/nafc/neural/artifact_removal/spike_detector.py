"""
Spike (MUA) detection strategies, run *after* artifact removal.

The default implementation uses a fixed negative threshold at
``-N * RMS`` of the MUA-band-filtered trace. The threshold strategy is
deliberately separated from the parser so alternative detectors can be
swapped in.
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
from scipy.signal import butter, sosfiltfilt


class SpikeDetector(ABC):
    """Detect spike sample indices in a 1-D voltage trace."""

    @abstractmethod
    def detect(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        ...

    def bandpass(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        """Return the bandpass-filtered trace used before thresholding.
        Default implementation is a pass-through; override in subclasses."""
        return signal

    def detect_on_filtered(
        self,
        filtered: np.ndarray,
        sample_rate: float,
        noise_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Detect spikes on an already-bandpass-filtered trace.

        Parameters
        ----------
        noise_mask : np.ndarray of bool, optional
            Samples to *include* in the noise/threshold estimate.
            Pass a mask that excludes artifact-removal windows so their
            zeroed samples don't artificially lower the RMS.
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
        return sosfiltfilt(sos, np.asarray(signal, dtype=np.float64))

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

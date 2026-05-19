"""
Pre-artifact-removal signal conditioning.

Heffer & Fallon (2008) describe a light preprocessing stage applied
before artifact detection: DC offset removal followed by a 5 Hz digital
high-pass filter to correct for baseline drift. This level of filtering
was found to cause negligible changes to action-potential waveforms.
"""

from abc import ABC, abstractmethod

import numpy as np
from scipy.signal import butter, sosfiltfilt


class SignalPreprocessor(ABC):
    """Preprocess a raw 1-D voltage trace prior to artifact detection."""

    @abstractmethod
    def preprocess(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        ...


class BaselineDriftPreprocessor(SignalPreprocessor):
    """
    DC-offset removal + zero-phase high-pass filter at a low cutoff
    (default 5 Hz, per Heffer & Fallon 2008) to correct for baseline drift
    while leaving action-potential waveforms essentially undistorted.
    """

    def __init__(self, highpass_hz: float = 5.0, filter_order: int = 3):
        self.highpass_hz = highpass_hz
        self.filter_order = filter_order

    def preprocess(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        x = np.asarray(signal, dtype=np.float64)
        x = x - np.mean(x)
        sos = butter(
            self.filter_order, self.highpass_hz,
            btype='high', fs=sample_rate, output='sos',
        )
        return sosfiltfilt(sos, x)

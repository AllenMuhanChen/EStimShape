"""
Stimulus-artifact event detection.

Heffer & Fallon (2008) identify artifact event times by amplitude
threshold-level crossings on the preprocessed signal. The artifact
amplitude is typically one to two orders of magnitude greater than the
recorded action potentials, so a sufficiently high threshold isolates
artifacts from spikes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class ArtifactEvent:
    """A detected stimulus-artifact event.

    Attributes
    ----------
    start_sample : int
        First sample at which the signal exceeded threshold.
    end_sample : int
        First sample after ``start_sample`` at which the signal returned
        below threshold. May equal ``start_sample + 1`` for single-sample
        crossings.
    peak_sample : int
        Sample index of the peak (max ``|signal|``) within the event.
    peak_value : float
        Signed signal value at ``peak_sample``.
    """
    start_sample: int
    end_sample: int
    peak_sample: int
    peak_value: float

    @property
    def width_samples(self) -> int:
        return self.end_sample - self.start_sample


class ArtifactDetector(ABC):
    """Identify stimulus-artifact events in a preprocessed signal."""

    @abstractmethod
    def detect(self, signal: np.ndarray, sample_rate: float) -> List[ArtifactEvent]:
        ...


class ThresholdArtifactDetector(ArtifactDetector):
    """
    Amplitude threshold-crossing detector (Heffer & Fallon 2008, step II.ii).

    Threshold is computed as ``threshold_factor * scale`` where ``scale``
    is a robust noise estimate of the input signal:

    - ``"mad"``  : median absolute deviation, scaled to SD
                   (default; robust to the artifacts themselves).
    - ``"rms"``  : root-mean-square of the signal.
    - ``"std"``  : standard deviation.

    Consecutive crossings whose start times fall within
    ``min_event_separation_s`` of one another are merged into a single
    event (so a multi-sample artifact wave is reported once).
    """

    def __init__(
        self,
        threshold_factor: float = 8.0,
        noise_scale: str = "mad",
        min_event_separation_s: float = 0.0005,  # 500 us
    ):
        if noise_scale not in {"mad", "rms", "std"}:
            raise ValueError(f"unknown noise_scale: {noise_scale!r}")
        self.threshold_factor = threshold_factor
        self.noise_scale = noise_scale
        self.min_event_separation_s = min_event_separation_s

    def compute_threshold(self, signal: np.ndarray) -> float:
        x = np.asarray(signal, dtype=np.float64)
        if self.noise_scale == "mad":
            scale = 1.4826 * np.median(np.abs(x - np.median(x)))
        elif self.noise_scale == "rms":
            scale = float(np.sqrt(np.mean(x * x)))
        else:  # "std"
            scale = float(np.std(x))
        return self.threshold_factor * max(scale, 1e-12)

    def detect(self, signal: np.ndarray, sample_rate: float) -> List[ArtifactEvent]:
        x = np.asarray(signal, dtype=np.float64)
        threshold = self.compute_threshold(x)

        above = np.abs(x) > threshold
        if not above.any():
            return []

        # Rising/falling edges of the boolean trace.
        edges = np.diff(above.astype(np.int8))
        starts = np.where(edges == 1)[0] + 1
        ends = np.where(edges == -1)[0] + 1
        if above[0]:
            starts = np.insert(starts, 0, 0)
        if above[-1]:
            ends = np.append(ends, len(x))

        # Merge runs whose starts are closer than min_event_separation_s.
        min_gap = max(int(self.min_event_separation_s * sample_rate), 1)
        merged_starts: List[int] = []
        merged_ends: List[int] = []
        for s, e in zip(starts, ends):
            if merged_starts and s - merged_ends[-1] < min_gap:
                merged_ends[-1] = e
            else:
                merged_starts.append(int(s))
                merged_ends.append(int(e))

        events: List[ArtifactEvent] = []
        for s, e in zip(merged_starts, merged_ends):
            seg = x[s:e]
            peak_off = int(np.argmax(np.abs(seg)))
            events.append(ArtifactEvent(
                start_sample=s,
                end_sample=e,
                peak_sample=s + peak_off,
                peak_value=float(seg[peak_off]),
            ))
        return events

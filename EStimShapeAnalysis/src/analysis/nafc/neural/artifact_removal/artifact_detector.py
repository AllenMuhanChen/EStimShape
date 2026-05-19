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


class TriggerBasedArtifactDetector(ArtifactDetector):
    """
    Build artifact events from known stimulation trigger times rather than
    detecting them by amplitude. Robust across experiments — no threshold
    tuning, immune to baseline drift, immune to HP-filter ringing.

    Matches Intan HOLD-mode stimulation: while the trigger TTL is held
    high, pulses fire repeatedly at ``pulse_period_s`` intervals starting
    at ``rising + post_trigger_delay_s``, until the falling edge.

    Each pulse produces a forward-asymmetric ArtifactEvent spanning::

        [onset - padding_before_s, onset + pulse_width_s + padding_after_s]

    Gaps between pulses are NOT blanked, so spike detection can run on
    inter-pulse intervals. Set ``pulse_period_s = 0`` to blank the whole
    TTL-high span as a single event (useful when individual pulse
    semantics are unknown).
    """

    def __init__(
        self,
        trigger_rising_samples,
        trigger_falling_samples,
        post_trigger_delay_s: float,
        pulse_width_s: float,
        padding_after_s: float = 0.0,
        padding_before_s: float = 0.0,
        pulse_period_s: float = 0.0,
    ):
        self.trigger_rising_samples = np.asarray(
            trigger_rising_samples, dtype=np.int64,
        )
        self.trigger_falling_samples = np.asarray(
            trigger_falling_samples, dtype=np.int64,
        )
        self.post_trigger_delay_s = float(post_trigger_delay_s)
        self.pulse_width_s = float(pulse_width_s)
        self.padding_after_s = float(padding_after_s)
        self.padding_before_s = float(padding_before_s)
        self.pulse_period_s = float(pulse_period_s)

    def detect(self, signal: np.ndarray, sample_rate: float) -> List[ArtifactEvent]:
        n = len(signal)
        x = np.asarray(signal, dtype=np.float64)
        delay = int(round(self.post_trigger_delay_s * sample_rate))
        width = max(int(round(self.pulse_width_s * sample_rate)), 1)
        pad_before = max(int(round(self.padding_before_s * sample_rate)), 0)
        pad_after = max(int(round(self.padding_after_s * sample_rate)), 0)
        period = int(round(self.pulse_period_s * sample_rate))

        risings = self.trigger_rising_samples
        fallings = self.trigger_falling_samples
        events: List[ArtifactEvent] = []
        for rise in risings:
            rise = int(rise)
            after = fallings[fallings > rise]
            fall = int(after[0]) if len(after) else n

            if period <= 0:
                # No period — blank the whole TTL-high span as one event.
                start = max(rise + delay - pad_before, 0)
                end = min(fall + pad_after, n)
                if end <= start:
                    continue
                center = (start + end) // 2
                events.append(ArtifactEvent(
                    start_sample=start, end_sample=end,
                    peak_sample=center,
                    peak_value=float(x[center]) if 0 <= center < n else 0.0,
                ))
                continue

            # Per-pulse blanking: one forward-asymmetric event per pulse.
            k = 0
            while True:
                onset = rise + delay + k * period
                if onset >= fall or onset >= n:
                    break
                start = max(onset - pad_before, 0)
                end = min(onset + width + pad_after, n)
                if end > start:
                    events.append(ArtifactEvent(
                        start_sample=start, end_sample=end,
                        peak_sample=onset,
                        peak_value=float(x[onset])
                        if 0 <= onset < n else 0.0,
                    ))
                k += 1
        return events

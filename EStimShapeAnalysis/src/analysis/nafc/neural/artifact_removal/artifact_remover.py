"""
Stimulus-artifact removal strategies.

Two interchangeable implementations:

  - SampleInterpolateRemover : Heffer & Fallon (2008) sample-and-interpolate.
        Linear interpolation across a fixed-duration window.
  - FlatBaselineRemover      : replace contaminated samples with a flat baseline
        (either zero or the median of a pre-artifact reference window).
        Useful when artifacts are wide enough that linear interpolation
        introduces obvious ramps.
"""

from abc import ABC, abstractmethod
from typing import Iterable

import numpy as np

from src.analysis.nafc.neural.artifact_removal.artifact_detector import ArtifactEvent


class ArtifactRemover(ABC):
    """Replace artifact-contaminated samples with cleaned values."""

    @abstractmethod
    def remove(
        self,
        signal: np.ndarray,
        events: Iterable[ArtifactEvent],
        sample_rate: float,
    ) -> np.ndarray:
        ...


class SampleInterpolateRemover(ArtifactRemover):
    """
    Sample-and-interpolate removal (Heffer & Fallon 2008, step III).

    For each detected event the removal window is
    ``[event.start_sample - pre_pad, event.start_sample + duration]``
    where ``duration`` is ``artifact_duration_s * sample_rate`` samples
    (default 170 us, per the paper). The samples inside the window are
    overwritten with a straight line drawn between the sample immediately
    before the window and the sample at the end of the window.

    ``pre_pad_s`` and ``post_pad_s`` add a small margin on either side
    of the nominal artifact, useful when the threshold-crossing slightly
    lags the true onset or when ringing extends past the assumed
    duration.
    """

    def __init__(
        self,
        artifact_duration_s: float = 170e-6,
        pre_pad_s: float = 0.0,
        post_pad_s: float = 0.0,
    ):
        self.artifact_duration_s = artifact_duration_s
        self.pre_pad_s = pre_pad_s
        self.post_pad_s = post_pad_s

    def remove(
        self,
        signal: np.ndarray,
        events: Iterable[ArtifactEvent],
        sample_rate: float,
    ) -> np.ndarray:
        cleaned = np.array(signal, dtype=np.float64, copy=True)
        n = len(cleaned)
        if n == 0:
            return cleaned

        duration = max(int(round(self.artifact_duration_s * sample_rate)), 1)
        pre_pad = max(int(round(self.pre_pad_s * sample_rate)), 0)
        post_pad = max(int(round(self.post_pad_s * sample_rate)), 0)

        for ev in events:
            window_start = max(ev.start_sample - pre_pad, 0)
            window_end = min(ev.start_sample + duration + post_pad, n - 1)
            if window_end <= window_start:
                continue

            anchor_left_idx = max(window_start - 1, 0)
            anchor_right_idx = window_end
            y_left = cleaned[anchor_left_idx]
            y_right = cleaned[anchor_right_idx]

            fill_len = anchor_right_idx - window_start
            if fill_len <= 0:
                continue
            # endpoint=False so the linspace does not overwrite the right anchor.
            ramp = np.linspace(y_left, y_right, fill_len + 1, endpoint=False)[1:]
            cleaned[window_start:anchor_right_idx] = ramp

        return cleaned


class FlatBaselineRemover(ArtifactRemover):
    """
    Replace artifact-contaminated samples with a flat constant baseline.

    For each detected event the removal window is

        [event.start_sample - pre_pad,  event.end_sample + post_pad]

    where ``event.end_sample`` is the detector's measured end-of-event.
    If ``min_duration_s`` is set, the window is extended to at least that
    duration after ``event.start_sample`` (useful when the threshold
    crossing returns before the artifact has actually died down).

    The fill value is determined by ``baseline``:
        "zero"       : replace with 0.0.
        "pre_median" : median of ``reference_window_s`` worth of samples
                       immediately before the (padded) window. Falls back
                       to 0.0 if the reference window is empty.
    """

    def __init__(
        self,
        pre_pad_s: float = 0.0,
        post_pad_s: float = 0.0,
        min_duration_s: float = 0.0,
        baseline: str = "zero",
        reference_window_s: float = 1e-3,
    ):
        if baseline not in {"zero", "pre_median"}:
            raise ValueError(f"unknown baseline: {baseline!r}")
        self.pre_pad_s = pre_pad_s
        self.post_pad_s = post_pad_s
        self.min_duration_s = min_duration_s
        self.baseline = baseline
        self.reference_window_s = reference_window_s

    def remove(
        self,
        signal: np.ndarray,
        events: Iterable[ArtifactEvent],
        sample_rate: float,
    ) -> np.ndarray:
        cleaned = np.array(signal, dtype=np.float64, copy=True)
        n = len(cleaned)
        if n == 0:
            return cleaned

        pre_pad = max(int(round(self.pre_pad_s * sample_rate)), 0)
        post_pad = max(int(round(self.post_pad_s * sample_rate)), 0)
        min_duration = max(int(round(self.min_duration_s * sample_rate)), 0)
        ref_len = max(int(round(self.reference_window_s * sample_rate)), 1)

        for ev in events:
            window_start = max(ev.start_sample - pre_pad, 0)
            event_end = max(ev.end_sample, ev.start_sample + min_duration)
            window_end = min(event_end + post_pad, n)
            if window_end <= window_start:
                continue

            if self.baseline == "zero":
                fill = 0.0
            else:  # "pre_median"
                ref_lo = max(window_start - ref_len, 0)
                if ref_lo < window_start:
                    fill = float(np.median(cleaned[ref_lo:window_start]))
                else:
                    fill = 0.0

            cleaned[window_start:window_end] = fill

        return cleaned

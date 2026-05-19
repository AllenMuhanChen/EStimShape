"""
Stimulus-artifact removal strategies.

Heffer & Fallon (2008) "sample-and-interpolate": for each artifact event,
replace the contaminated samples with values drawn from a straight line
between the sample just before artifact onset and the sample at the end
of the artifact (a fixed duration after onset, e.g. 170 us).
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

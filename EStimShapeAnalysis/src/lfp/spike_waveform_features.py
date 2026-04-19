from typing import Optional

import numpy as np
from scipy.signal import butter, sosfilt


def highpass_filter(wideband: np.ndarray, sample_rate: float, highpass_hz: float = 300.0) -> np.ndarray:
    """4th-order zero-phase Butterworth highpass filter."""
    nyq = sample_rate / 2.0
    sos = butter(4, highpass_hz / nyq, btype='high', output='sos')
    return sosfilt(sos, wideband)


def extract_spike_waveforms(
    filtered: np.ndarray,
    spike_indices: np.ndarray,
    pre_ms: float = 0.5,
    post_ms: float = 1.5,
    sample_rate: float = 20_000.0,
) -> np.ndarray:
    """
    Extract waveform snippets around each spike index.

    Returns array of shape (n_valid_spikes, pre_samples + post_samples + 1).
    Spikes too close to signal edges are dropped.
    """
    pre  = int(pre_ms  * sample_rate / 1000)
    post = int(post_ms * sample_rate / 1000)
    n = len(filtered)

    snippets = []
    for idx in spike_indices:
        if idx - pre < 0 or idx + post >= n:
            continue
        snippets.append(filtered[idx - pre : idx + post + 1])

    return np.array(snippets) if snippets else np.empty((0, pre + post + 1))


def classify_spike_polarity(waveform: np.ndarray) -> str:
    """Return 'positive' if the positive peak exceeds the absolute negative trough, else 'negative'."""
    return 'positive' if np.max(waveform) > np.abs(np.min(waveform)) else 'negative'


def compute_polarity_ratio(waveforms: np.ndarray) -> Optional[float]:
    """Fraction of waveforms that are positive-leading. Returns None if no waveforms."""
    if len(waveforms) == 0:
        return None
    n_positive = sum(1 for w in waveforms if classify_spike_polarity(w) == 'positive')
    return n_positive / len(waveforms)

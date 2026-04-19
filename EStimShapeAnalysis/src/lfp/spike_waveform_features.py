from typing import Optional

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import butter, sosfilt, find_peaks


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


def count_waveform_peaks(
    waveform: np.ndarray,
    prominence_fraction: float = 0.15,
    smooth_ms: float = 0.3,
    sample_rate: float = 20_000.0,
) -> int:
    """
    Count the number of distinct peaks (positive and negative) in a waveform snippet.

    Applies a Gaussian smooth before peak detection to remove sub-ms noise oscillations
    (which otherwise inflate the count to 5-10). Real spike phases are ≥0.5ms wide and
    are preserved; noise at 1-3kHz is attenuated.

    Parameters
    ----------
    prominence_fraction : peak must exceed this fraction of peak-to-peak to be counted.
    smooth_ms : Gaussian sigma in ms for pre-smoothing (tune to filter noise vs real phases).
    sample_rate : samples per second, needed to convert smooth_ms to samples.
    """
    sigma = smooth_ms * sample_rate / 1000
    smoothed = gaussian_filter1d(waveform.astype(float), sigma=sigma)

    ptp = np.max(smoothed) - np.min(smoothed)
    if ptp == 0:
        return 0
    prominence = prominence_fraction * ptp
    pos_peaks, _ = find_peaks( smoothed, prominence=prominence)
    neg_peaks, _ = find_peaks(-smoothed, prominence=prominence)
    return len(pos_peaks) + len(neg_peaks)


def compute_mean_peak_count(
    waveforms: np.ndarray,
    prominence_fraction: float = 0.15,
    smooth_ms: float = 0.3,
    sample_rate: float = 20_000.0,
    negative_only: bool = True,
) -> Optional[float]:
    """
    Mean number of peaks across waveforms.

    Parameters
    ----------
    negative_only : if True, exclude positive-leading spikes from the mean.
    prominence_fraction : prominence threshold as fraction of peak-to-peak (post-smoothing).
    smooth_ms : Gaussian smooth sigma in ms applied before peak detection.
    sample_rate : needed to convert smooth_ms to samples.

    Returns None if no qualifying waveforms.
    """
    if len(waveforms) == 0:
        return None
    counts = [
        count_waveform_peaks(w, prominence_fraction, smooth_ms, sample_rate)
        for w in waveforms
        if not negative_only or classify_spike_polarity(w) == 'negative'
    ]
    return float(np.mean(counts)) if counts else None

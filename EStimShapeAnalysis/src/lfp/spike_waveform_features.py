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
    """
    'positive' if the maximum (hyperpolarization peak) precedes the minimum
    (depolarization trough); 'negative' if the trough comes first.
    """
    return 'positive' if int(np.argmax(waveform)) < int(np.argmin(waveform)) else 'negative'


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


def compute_trough_to_peak_ms(
    waveform: np.ndarray,
    smooth_ms: float = 0.1,
    sample_rate: float = 20_000.0,
) -> Optional[float]:
    """
    Trough-to-peak duration in ms for a single spike waveform.

    Finds the trough (global minimum), then finds the FIRST local maximum in
    the post-trough portion (repolarisation peak). Using argmax would grab the
    window end when there is no strong positive deflection. Returns None if no
    local maximum is found after the trough.
    """
    sigma = smooth_ms * sample_rate / 1000
    smoothed = gaussian_filter1d(waveform.astype(float), sigma=sigma) if sigma > 0 else waveform.astype(float)

    trough_idx = int(np.argmin(smoothed))
    post_trough = smoothed[trough_idx:]
    if len(post_trough) < 2:
        return None

    peaks, _ = find_peaks(post_trough)
    if len(peaks) == 0:
        return None
    return int(peaks[0]) / sample_rate * 1000.0


def compute_mean_trough_to_peak_ms(
    waveforms: np.ndarray,
    smooth_ms: float = 0.1,
    sample_rate: float = 20_000.0,
    negative_only: bool = True,
) -> Optional[float]:
    """
    Mean trough-to-peak duration in ms across waveforms.

    Parameters
    ----------
    negative_only : if True, exclude positive-leading spikes.
    smooth_ms : Gaussian smooth sigma in ms before measurement.
    sample_rate : samples per second.
    """
    if len(waveforms) == 0:
        return None
    durations = [
        compute_trough_to_peak_ms(w, smooth_ms, sample_rate)
        for w in waveforms
        if not negative_only or classify_spike_polarity(w) == 'negative'
    ]
    durations = [d for d in durations if d is not None]
    return float(np.mean(durations)) if durations else None


def compute_waveform_amplitude(
    waveform: np.ndarray,
    smooth_ms: float = 0.0,
    sample_rate: float = 20_000.0,
) -> float:
    """Peak-to-peak amplitude of a single waveform snippet."""
    if smooth_ms > 0:
        sigma = smooth_ms * sample_rate / 1000
        waveform = gaussian_filter1d(waveform.astype(float), sigma=sigma)
    return float(np.max(waveform) - np.min(waveform))


def compute_mean_spike_amplitude(
    waveforms: np.ndarray,
    smooth_ms: float = 0.0,
    sample_rate: float = 20_000.0,
    negative_only: bool = True,
) -> Optional[float]:
    """
    Mean peak-to-peak spike amplitude across waveforms.

    Parameters
    ----------
    negative_only : if True, exclude positive-leading spikes.
    smooth_ms : Gaussian smooth sigma in ms before measurement (default 0 = no smoothing,
                preserving true amplitude; smoothing reduces apparent amplitude).
    """
    if len(waveforms) == 0:
        return None
    amps = [
        compute_waveform_amplitude(w, smooth_ms, sample_rate)
        for w in waveforms
        if not negative_only or classify_spike_polarity(w) == 'negative'
    ]
    return float(np.mean(amps)) if amps else None

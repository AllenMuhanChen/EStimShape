import numpy as np
from scipy.signal import butter, sosfilt


def detect_mua_spikes(
    wideband: np.ndarray,
    sample_rate: float,
    highpass_hz: float = 300.0,
    threshold_rms: float = 4.0,
    refractory_sec: float = 0.001,
) -> np.ndarray:
    """
    Detect MUA spikes using the -N×RMS threshold method.

    Steps:
      1. High-pass filter at highpass_hz (4th-order Butterworth, zero-phase).
      2. Compute RMS over the entire signal as the noise estimate.
      3. Detect negative-going threshold crossings at -threshold_rms × RMS.
      4. Snap each crossing to the trough within the refractory window.
      5. Enforce refractory period between successive spikes.

    Returns
    -------
    spike_samples : np.ndarray
        Sample indices of detected spikes.
    """
    nyq = sample_rate / 2.0
    sos = butter(4, highpass_hz / nyq, btype='high', output='sos')
    filtered = sosfilt(sos, wideband)

    rms = np.sqrt(np.mean(filtered ** 2))
    threshold = -threshold_rms * rms

    below = filtered < threshold
    crossings = np.where(np.diff(below.astype(np.int8)) == 1)[0] + 1

    if len(crossings) == 0:
        return np.array([], dtype=int)

    refractory_samples = max(1, int(refractory_sec * sample_rate))
    n = len(filtered)
    spike_samples = []
    for c in crossings:
        window_end = min(c + refractory_samples, n)
        trough = c + int(np.argmin(filtered[c:window_end]))
        spike_samples.append(trough)

    spike_samples = np.array(spike_samples, dtype=int)

    if len(spike_samples) > 1:
        kept = [spike_samples[0]]
        for s in spike_samples[1:]:
            if s - kept[-1] >= refractory_samples:
                kept.append(s)
        spike_samples = np.array(kept, dtype=int)

    return spike_samples

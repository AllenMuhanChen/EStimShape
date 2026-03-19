"""
Streaming LFP Processor
========================
Real-time LFP extraction and spectral analysis pipeline.

Mirrors the offline analysis chain from the project:
    OneFileLFPParser  → lowpass + decimate raw wideband to LFP
    LFPSpectrum       → Welch PSD on LFP segments
    RelativePowerSpectrum → normalize across channels per frequency bin
    LFPBandPowerPlotter   → extract band powers (delta-theta, alpha-beta, gamma)

This module operates on streaming data via rolling circular buffers,
producing updated spectra and band powers each analysis cycle.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt, decimate, welch


@dataclass
class LFPProcessorConfig:
    """Configuration matching existing analysis parameters."""
    # LFP extraction (from OneFileLFPParser)
    lowpass_cutoff: float = 250.0
    filter_order: int = 3
    target_lfp_rate: int = 1000  # Hz, downsample target

    # Welch PSD (from LFPSpectrum)
    nperseg: int = 2048         # ~2s at 1kHz → ~0.5 Hz resolution
    noverlap: Optional[int] = None  # defaults to nperseg // 2
    welch_window: str = 'hann'

    # Band definitions (from LFPBandPowerPlotter)
    bands: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "delta-theta": (1, 8),
        "alpha-beta": (10, 19),
        "gamma": (40, 150),
    })

    # Relative power normalization (from RelativePowerSpectrum)
    noise_threshold_sd: float = 2.0

    # Streaming parameters
    analysis_window_seconds: float = 4.0   # seconds of LFP to use for each PSD
    freq_range: Tuple[float, float] = (0, 150)  # display range


class StreamingLFPProcessor:
    """
    Processes streaming wideband data into LFP spectra and band powers.

    Data flow:
        1. append_wideband() — add new raw samples per channel
        2. process() — lowpass → decimate → Welch PSD → normalize → band powers
        3. Read results from .spectra, .band_powers, .normalized_spectra

    The processor maintains a circular buffer of wideband data per channel.
    On each process() call, it filters and analyzes the most recent window.
    """

    def __init__(self, sample_rate: float, channel_names: List[str],
                 config: LFPProcessorConfig = None):
        self.sample_rate = sample_rate
        self.channel_names = list(channel_names)
        self.config = config or LFPProcessorConfig()

        # Compute decimation factor
        self.decimate_factor = max(1, int(sample_rate / self.config.target_lfp_rate))
        self.lfp_rate = sample_rate / self.decimate_factor

        # Design lowpass filter (Butterworth, same as OneFileLFPParser)
        self._sos = butter(
            self.config.filter_order,
            self.config.lowpass_cutoff,
            btype='low',
            fs=sample_rate,
            output='sos'
        )

        # Circular buffer: enough wideband samples for analysis window + filter padding
        padding_seconds = 1.0  # extra for filter edge effects
        buf_samples = int((self.config.analysis_window_seconds + padding_seconds) * sample_rate)
        self._buffer_size = buf_samples
        self._buffers: Dict[str, np.ndarray] = {
            ch: np.zeros(buf_samples) for ch in channel_names
        }
        self._write_pos = 0
        self._total_samples_received = 0

        # Filter state for streaming (causal filtering)
        n_sections = self._sos.shape[0]
        self._filter_states: Dict[str, np.ndarray] = {
            ch: np.zeros((n_sections, 2)) for ch in channel_names
        }

        # Results (updated on each process() call)
        self.spectra: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self.normalized_spectra: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self.band_powers: Dict[str, Dict[str, float]] = {}
        self.freqs: Optional[np.ndarray] = None

    @property
    def has_enough_data(self) -> bool:
        """True when we have at least one full analysis window."""
        min_samples = int(self.config.analysis_window_seconds * self.sample_rate)
        return self._total_samples_received >= min_samples

    def append_wideband(self, channel_data: Dict[str, np.ndarray]):
        """
        Append new wideband samples to the circular buffers.

        Args:
            channel_data: Dict mapping channel name → 1D array of new samples (µV).
                          Channels must match self.channel_names in order.
        """
        if not channel_data:
            return

        # All channels should have the same number of new samples
        first_key = next(iter(channel_data))
        n_new = len(channel_data[first_key])

        for ch_name in self.channel_names:
            if ch_name not in channel_data:
                continue
            samples = channel_data[ch_name]

            if n_new <= self._buffer_size:
                # Fits in one write (possibly wrapping)
                end_pos = self._write_pos + n_new
                if end_pos <= self._buffer_size:
                    self._buffers[ch_name][self._write_pos:end_pos] = samples
                else:
                    first_part = self._buffer_size - self._write_pos
                    self._buffers[ch_name][self._write_pos:] = samples[:first_part]
                    self._buffers[ch_name][:n_new - first_part] = samples[first_part:]
            else:
                # More data than buffer — keep only the last buffer_size samples
                self._buffers[ch_name][:] = samples[-self._buffer_size:]

        self._write_pos = (self._write_pos + n_new) % self._buffer_size
        self._total_samples_received += n_new

    def process(self) -> bool:
        """
        Run the full LFP analysis pipeline on the current buffer contents.

        Returns True if processing succeeded, False if not enough data.
        Updates self.spectra, self.normalized_spectra, and self.band_powers.
        """
        if not self.has_enough_data:
            return False

        # Step 1: Extract the most recent analysis_window from each buffer
        window_samples = int(self.config.analysis_window_seconds * self.sample_rate)
        window_samples = min(window_samples, self._buffer_size)

        raw_windows = {}
        for ch_name in self.channel_names:
            raw_windows[ch_name] = self._get_recent_samples(ch_name, window_samples)

        # Step 2: Lowpass filter + decimate → LFP (mirrors OneFileLFPParser)
        lfp_windows = {}
        for ch_name, raw in raw_windows.items():
            # Use sosfiltfilt for zero-phase filtering on the window
            # (offline-style, since we have the full window)
            filtered = sosfiltfilt(self._sos, raw)

            # Decimate (same approach as OneFileLFPParser)
            if self.decimate_factor > 1:
                lfp = decimate(filtered, self.decimate_factor, ftype='fir', zero_phase=True)
            else:
                lfp = filtered
            lfp_windows[ch_name] = lfp

        # Step 3: Welch PSD (mirrors LFPSpectrum)
        self.spectra = {}
        for ch_name, lfp in lfp_windows.items():
            # === ADD DEBUG PRINTS HERE ===
            actual_nperseg = min(self.config.nperseg, len(lfp))
            print(f"Channel: {ch_name}")
            print(f"  LFP length: {len(lfp)}")
            print(f"  Config nperseg: {self.config.nperseg}")
            print(f"  Actual nperseg used: {actual_nperseg}")
            print(f"  Freq resolution: {self.lfp_rate / actual_nperseg:.2f} Hz")
            # === END DEBUG ===
            freqs, power = welch(
                lfp,
                fs=self.lfp_rate,
                nperseg=min(self.config.nperseg, len(lfp)),
                noverlap=self.config.noverlap,
                window=self.config.welch_window,
            )
            self.spectra[ch_name] = (freqs, power)

        self.freqs = freqs

        # Step 4: Relative power normalization (mirrors RelativePowerSpectrum)
        self.normalized_spectra = self._normalize_spectra(self.spectra)

        # Step 5: Band power extraction (mirrors LFPBandPowerPlotter)
        self.band_powers = {}
        for ch_name in self.channel_names:
            if ch_name not in self.normalized_spectra:
                continue
            f, norm_power = self.normalized_spectra[ch_name]
            ch_bands = {}
            for band_name, (fmin, fmax) in self.config.bands.items():
                mask = (f >= fmin) & (f <= fmax)
                ch_bands[band_name] = float(np.mean(norm_power[mask])) if np.any(mask) else 0.0
            self.band_powers[ch_name] = ch_bands

        return True

    def get_gamma_alpha_beta_ratios(self) -> Dict[str, float]:
        """
        Compute gamma / alpha-beta power ratio per channel from raw spectra.
        Mirrors LFPPowerLawPlotter._compute_gamma_alpha_beta_ratio.
        """
        ratios = {}
        for ch_name in self.channel_names:
            if ch_name not in self.spectra:
                continue
            freqs, power = self.spectra[ch_name]

            ab_mask = (freqs >= 10) & (freqs <= 30)
            gamma_mask = (freqs >= 50) & (freqs <= 150)

            ab_power = np.mean(power[ab_mask]) if np.any(ab_mask) else np.nan
            gamma_power = np.mean(power[gamma_mask]) if np.any(gamma_mask) else np.nan

            if ab_power > 0:
                ratios[ch_name] = gamma_power / ab_power
            else:
                ratios[ch_name] = np.nan

        return ratios

    def _get_recent_samples(self, ch_name: str, n_samples: int) -> np.ndarray:
        """Extract the most recent n_samples from the circular buffer."""
        buf = self._buffers[ch_name]
        end = self._write_pos
        start = end - n_samples

        if start >= 0:
            return buf[start:end].copy()
        else:
            # Wraps around
            return np.concatenate([buf[start:], buf[:end]])

    def _normalize_spectra(self, spectra: Dict[str, Tuple[np.ndarray, np.ndarray]]
                           ) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """
        Normalize power spectra across channels per frequency bin.
        Mirrors RelativePowerSpectrum.compute():
            1. Detect noisy channels (mean power > threshold_sd * SD above mean)
            2. Interpolate noisy channels from spatial neighbors
            3. Normalize each frequency bin by max across channels
        """
        if not spectra:
            return {}

        ordered_keys = [ch for ch in self.channel_names if ch in spectra]
        if not ordered_keys:
            return {}

        freqs = spectra[ordered_keys[0]][0]
        power_matrix = np.array([spectra[k][1] for k in ordered_keys])

        # Detect noisy channels
        mean_power = np.mean(power_matrix, axis=1)
        global_mean = np.mean(mean_power)
        global_sd = np.std(mean_power)
        threshold = global_mean + self.config.noise_threshold_sd * global_sd
        noisy_indices = np.where(mean_power > threshold)[0]

        # Interpolate noisy channels
        if len(noisy_indices) > 0:
            power_matrix = self._interpolate_noisy(power_matrix, noisy_indices)

        # Normalize per frequency bin
        max_per_freq = np.max(power_matrix, axis=0)
        max_per_freq[max_per_freq == 0] = 1.0
        normalized = power_matrix / max_per_freq

        result = {}
        for i, key in enumerate(ordered_keys):
            result[key] = (freqs, normalized[i])
        return result

    @staticmethod
    def _interpolate_noisy(power_matrix: np.ndarray,
                           noisy_indices: np.ndarray) -> np.ndarray:
        """Replace noisy channels with mean of nearest non-noisy neighbors."""
        n = power_matrix.shape[0]
        noisy_set = set(noisy_indices.tolist())
        result = power_matrix.copy()

        for idx in noisy_indices:
            neighbors = []
            # Search up
            for offset in range(1, n):
                neighbor = idx - offset
                if neighbor >= 0 and neighbor not in noisy_set:
                    neighbors.append(neighbor)
                    break
            # Search down
            for offset in range(1, n):
                neighbor = idx + offset
                if neighbor < n and neighbor not in noisy_set:
                    neighbors.append(neighbor)
                    break
            if neighbors:
                result[idx] = np.mean(power_matrix[neighbors], axis=0)

        return result

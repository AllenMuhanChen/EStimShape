from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np


@dataclass
class RelativePowerSpectrum:
    """
    Computes relative power spectra across channels with noisy channel interpolation.

    channel_order defines the spatial layout of channels (top to bottom on the probe).
    Noisy channels (mean power > noise_threshold_sd s.d. above the mean) are replaced
    with interpolations from their nearest neighbors in channel_order before normalization.
    """
    channel_order: List[int]
    channel_prefix: str = "A"
    noise_threshold_sd: float = 2.0
    exclude_channels: List[int] = field(default_factory=list)

    @property
    def _effective_channel_order(self) -> List[int]:
        return [ch for ch in self.channel_order if ch not in self.exclude_channels]

    def compute(self, avg_spectrum_by_channel: Dict) -> Dict:
        """
        Takes Dict[Channel, (freqs, power)] and returns Dict[Channel, (freqs, normalized_power)]
        with noisy channels interpolated and power normalized per frequency bin.
        """
        # Build ordered list of (channel_key, power) pairs
        ordered_keys, ordered_powers = self._get_ordered_channel_data(avg_spectrum_by_channel)
        freqs = avg_spectrum_by_channel[ordered_keys[0]][0]

        # Detect and interpolate noisy channels
        power_matrix = np.array(ordered_powers)  # (n_channels, n_freqs)
        noisy_indices = self._find_noisy_channels(power_matrix)
        if len(noisy_indices) > 0:
            power_matrix = self._interpolate_noisy_channels(power_matrix, noisy_indices)

        # Normalize per frequency bin
        max_per_freq = np.max(power_matrix, axis=0)
        max_per_freq[max_per_freq == 0] = 1.0
        normalized = power_matrix / max_per_freq

        # Rebuild dict
        result = {}
        for i, key in enumerate(ordered_keys):
            result[key] = (freqs, normalized[i])

        return result

    def get_noisy_channels(self, avg_spectrum_by_channel: Dict) -> List:
        """Returns the channel keys identified as noisy."""
        ordered_keys, ordered_powers = self._get_ordered_channel_data(avg_spectrum_by_channel)
        power_matrix = np.array(ordered_powers)
        noisy_indices = self._find_noisy_channels(power_matrix)
        return [ordered_keys[i] for i in noisy_indices]

    def _get_ordered_channel_data(self, avg_spectrum_by_channel: Dict) -> Tuple[List, List]:
        """Extract channel keys and power arrays in channel_order."""
        ordered_keys = []
        ordered_powers = []
        for ch_num in self._effective_channel_order:
            key = self._find_channel_key(ch_num, avg_spectrum_by_channel)
            if key is None:
                continue
            _, power = avg_spectrum_by_channel[key]
            ordered_keys.append(key)
            ordered_powers.append(power)
        return ordered_keys, ordered_powers

    def _find_noisy_channels(self, power_matrix: np.ndarray) -> List[int]:
        """
        Identify noisy channels as those whose mean power across all frequencies
        is greater than noise_threshold_sd standard deviations above the mean.
        """
        mean_power_per_channel = np.mean(power_matrix, axis=1)
        global_mean = np.mean(mean_power_per_channel)
        global_sd = np.std(mean_power_per_channel)
        threshold = global_mean + self.noise_threshold_sd * global_sd
        noisy = np.where(mean_power_per_channel > threshold)[0].tolist()
        return noisy

    def _interpolate_noisy_channels(self, power_matrix: np.ndarray, noisy_indices: List[int]) -> np.ndarray:
        """
        Replace noisy channels with the mean of their nearest non-noisy neighbors
        in channel_order (spatial neighbors on the probe).
        """
        n_channels = power_matrix.shape[0]
        noisy_set = set(noisy_indices)
        result = power_matrix.copy()

        for idx in noisy_indices:
            neighbors = []

            # Search upward for nearest non-noisy neighbor
            for offset in range(1, n_channels):
                neighbor = idx - offset
                if neighbor >= 0 and neighbor not in noisy_set:
                    neighbors.append(neighbor)
                    break

            # Search downward for nearest non-noisy neighbor
            for offset in range(1, n_channels):
                neighbor = idx + offset
                if neighbor < n_channels and neighbor not in noisy_set:
                    neighbors.append(neighbor)
                    break

            if len(neighbors) > 0:
                result[idx] = np.mean(power_matrix[neighbors], axis=0)

        return result

    def _find_channel_key(self, ch_num: int, channel_dict: Dict):
        target_str = f"{self.channel_prefix}_{ch_num:03d}"
        for key in channel_dict:
            if str(key).endswith(target_str):
                return key
        return None
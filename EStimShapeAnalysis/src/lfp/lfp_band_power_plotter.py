from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt


@dataclass
class LFPBandPowerPlotter:
    """
    Plots relative power per channel as a line profile for each frequency band.
    X-axis: relative power (0-1), Y-axis: channels in spatial order.
    """
    channel_order: List[int]
    channel_prefix: str = "A"
    bands: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "delta-theta": (1, 8),
        "alpha-beta": (10, 19),
        "gamma": (40, 150),
    })

    def plot(self, normalized_spectrum_by_channel: Dict, ax=None) -> plt.Figure:
        """
        Args:
            normalized_spectrum_by_channel: Dict[Channel, (freqs, normalized_power)]
                Output from RelativePowerSpectrum.compute().
            ax: optional matplotlib Axes.
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 8))
        else:
            fig = ax.figure

        channel_labels = []
        band_powers = {band: [] for band in self.bands}

        for ch_num in self.channel_order:
            key = self._find_channel_key(ch_num, normalized_spectrum_by_channel)
            if key is None:
                continue
            freqs, power = normalized_spectrum_by_channel[key]
            channel_labels.append(f"{self.channel_prefix}-{ch_num:03d}")

            for band_name, (fmin, fmax) in self.bands.items():
                mask = (freqs >= fmin) & (freqs <= fmax)
                band_powers[band_name].append(np.mean(power[mask]))

        y_positions = np.arange(len(channel_labels))

        colors = {"delta-theta": "tab:blue", "alpha-beta": "tab:orange", "gamma": "tab:green"}
        for band_name, powers in band_powers.items():
            color = colors.get(band_name, None)
            ax.plot(powers, y_positions, marker='o', markersize=4, label=band_name, color=color)

        ax.set_yticks(y_positions)
        ax.set_yticklabels(channel_labels)
        ax.invert_yaxis()
        ax.set_xlim(0, 1)
        ax.set_xlabel("Relative Power")
        ax.set_ylabel("Channel")
        ax.legend(loc="lower right")

        return fig

    def _find_channel_key(self, ch_num: int, channel_dict: Dict):
        target_str = f"{self.channel_prefix}_{ch_num:03d}"
        for key in channel_dict:
            if str(key).endswith(target_str):
                return key
        return None
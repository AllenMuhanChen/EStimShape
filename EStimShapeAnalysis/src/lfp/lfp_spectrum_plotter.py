from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm


@dataclass
class LFPSpectrumPlotter:
    channel_order: List[int]
    freq_range: Tuple[float, float] = (0, 150)
    channel_prefix: str = "A"

    def plot(self, channel_to_spectrum: Dict, ax=None) -> plt.Figure:
        """
        Plot a heatmap of power spectra across channels.

        Args:
            channel_to_spectrum: Dict[Channel, (frequencies, power)]
                Power spectrum per channel.
            ax: optional matplotlib Axes to plot on.

        Returns:
            The matplotlib Figure.
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        else:
            fig = ax.figure

        # Build the 2D power matrix in channel_order
        first_key = next(iter(channel_to_spectrum))
        freqs, _ = channel_to_spectrum[first_key]

        # Mask to freq_range
        freq_mask = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
        freqs_masked = freqs[freq_mask]

        power_matrix = []
        channel_labels = []
        for ch_num in self.channel_order:
            channel_key = self._find_channel_key(ch_num, channel_to_spectrum)
            if channel_key is None:
                print(f"Warning: no match for channel {self.channel_prefix}-{ch_num:03d}")
                continue
            _, power = channel_to_spectrum[channel_key]
            power_matrix.append(power[freq_mask])
            channel_labels.append(f"{self.channel_prefix}-{ch_num:03d}")

        if len(power_matrix) == 0:
            # Debug: show what keys actually exist
            print(f"Available keys: {[str(k) for k in channel_to_spectrum.keys()]}")
            raise ValueError("No channels matched. Check channel_prefix and channel_order.")

        power_matrix = np.array(power_matrix)

        im = ax.imshow(
            power_matrix, aspect='auto', origin='upper',
            interpolation='nearest',
            extent=[freqs_masked[0], freqs_masked[-1], len(channel_labels) - 0.5, -0.5]
        )
        ax.set_yticks(np.arange(len(channel_labels)))
        ax.set_yticklabels(channel_labels)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Channel")
        fig.colorbar(im, ax=ax, label="Power (µV²/Hz)")

        return fig

    def _find_channel_key(self, ch_num: int, channel_to_spectrum: Dict):
        """Find the matching channel key for a given channel number."""
        for key in channel_to_spectrum:
            s = str(key)
            if (s.endswith(f"{self.channel_prefix}_{ch_num:03d}") or
                    s.endswith(f"{self.channel_prefix}-{ch_num:03d}")):
                return key
        return None
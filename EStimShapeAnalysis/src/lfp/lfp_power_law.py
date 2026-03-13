from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt


@dataclass
class PowerLawFit:
    """Result of a power law fit: P(f) = A * f^χ"""
    exponent: float   # χ (slope in log-log, the layer-identifying parameter)
    amplitude: float  # A (intercept, affected by normalization)
    freqs: np.ndarray
    power: np.ndarray
    fit_power: np.ndarray
    r_squared: float


@dataclass
class LFPPowerLaw:
    """
    Fits P(f) = A * f^χ to LFP power spectra via linear regression in log-log space.
    The exponent χ is invariant to multiplicative scaling (e.g. impedance differences).
    """
    freq_range: Tuple[float, float] = (10, 100)

    def fit_one(self, freqs: np.ndarray, power: np.ndarray) -> PowerLawFit:
        mask = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
        f = freqs[mask]
        p = power[mask]

        valid = (p > 0) & (f > 0)
        f = f[valid]
        p = p[valid]

        log_f = np.log10(f)
        log_p = np.log10(p)

        try:
            coeffs = np.polyfit(log_f, log_p, 1)
            chi = coeffs[0]
            A = 10 ** coeffs[1]

            log_fit = np.polyval(coeffs, log_f)
            fit_power = 10 ** log_fit

            ss_res = np.sum((log_p - log_fit) ** 2)
            ss_tot = np.sum((log_p - np.mean(log_p)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        except Exception:
            A, chi = np.nan, np.nan
            fit_power = np.full_like(f, np.nan)
            r_squared = 0.0

        return PowerLawFit(
            exponent=chi, amplitude=A,
            freqs=f, power=p, fit_power=fit_power,
            r_squared=r_squared
        )

    def fit_dict(self, spectrum_by_channel: Dict) -> Dict:
        result = {}
        for channel, (freqs, power) in spectrum_by_channel.items():
            result[channel] = self.fit_one(freqs, power)
        return result

    @staticmethod
    def normalize_spectra(spectrum_by_channel: Dict) -> Dict:
        """
        Normalize each channel's power spectrum by its total power (area under curve).
        This removes absolute magnitude differences (e.g. from impedance) and
        preserves only the spectral shape for fitting.
        """
        result = {}
        for channel, (freqs, power) in spectrum_by_channel.items():
            total_power = np.trapz(power, freqs)
            if total_power > 0:
                result[channel] = (freqs, power / total_power)
            else:
                result[channel] = (freqs, power)
        return result


@dataclass
class LFPPowerLawPlotter:
    """
    Plots power law fits across channels.

    - Stacked subplots: one per channel, spectrum + fit in log-log.
    - Overlay: all channels on one plot, colored by depth.
    - Parameters: χ, A, c each vs channel.
    """
    channel_order: List[int]
    channel_prefix: str = "A"

    def plot(self, fits_by_channel: Dict) -> Tuple[plt.Figure, plt.Figure, plt.Figure]:
        """
        Returns:
            (fig_stacked, fig_overlay, fig_params)
        """
        ordered_keys, ordered_fits, channel_labels = self._get_ordered_fits(fits_by_channel)

        fig_stacked = self._plot_stacked(ordered_fits, channel_labels)
        fig_overlay = self._plot_overlay(ordered_fits, channel_labels)
        fig_params = self._plot_params(ordered_fits, channel_labels)

        return fig_stacked, fig_overlay, fig_params

    # ---- Stacked: one subplot per channel ----
    def _plot_stacked(self, ordered_fits: List[PowerLawFit], channel_labels: List[str]) -> plt.Figure:
        n = len(ordered_fits)
        fig, axes = plt.subplots(n, 1, figsize=(8, 1.5 * n), sharex=True)
        if n == 1:
            axes = [axes]

        for ax, fit, label in zip(axes, ordered_fits, channel_labels):
            ax.loglog(fit.freqs, fit.power, 'k-', linewidth=0.5, alpha=0.7)
            ax.loglog(fit.freqs, fit.fit_power, 'r-', linewidth=1.5,
                      label=f'χ={fit.exponent:.2f}, R²={fit.r_squared:.2f}')
            ax.set_ylabel(label, fontsize=7, rotation=0, ha='right', va='center')
            ax.legend(fontsize=6, loc='upper right')
            ax.tick_params(labelsize=6)

        axes[-1].set_xlabel("Frequency (Hz)")
        fig.suptitle("1/f Power Law Fits by Channel (log-log)")
        fig.tight_layout()
        return fig

    # ---- Overlay: all channels on one plot, colored by depth ----
    def _plot_overlay(self, ordered_fits: List[PowerLawFit], channel_labels: List[str]) -> plt.Figure:
        n = len(ordered_fits)
        cmap = plt.cm.viridis
        colors = [cmap(i / (n - 1)) for i in range(n)]

        fig, (ax_data, ax_fit) = plt.subplots(1, 2, figsize=(14, 6))

        for i, (fit, label) in enumerate(zip(ordered_fits, channel_labels)):
            ax_data.loglog(fit.freqs, fit.power, color=colors[i], linewidth=0.8, alpha=0.8)
            ax_fit.loglog(fit.freqs, fit.fit_power, color=colors[i], linewidth=0.8, alpha=0.8)

        ax_data.set_xlabel("Frequency (Hz)")
        ax_data.set_ylabel("Power (µV²/Hz)")
        ax_data.set_title("Data")

        ax_fit.set_xlabel("Frequency (Hz)")
        ax_fit.set_title("Fits")

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=n - 1))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=[ax_data, ax_fit], label="Depth (shallow → deep)",
                            ticks=[0, n - 1])
        cbar.ax.set_yticklabels([channel_labels[0], channel_labels[-1]])

        fig.suptitle("All Channels by Depth")
        fig.tight_layout()
        return fig

    # ---- Parameters: χ and A vs channel ----
    def _plot_params(self, ordered_fits: List[PowerLawFit], channel_labels: List[str]) -> plt.Figure:
        y_positions = np.arange(len(channel_labels))
        exponents = [f.exponent for f in ordered_fits]
        amplitudes = [f.amplitude for f in ordered_fits]

        fig, (ax_chi, ax_a) = plt.subplots(1, 2, figsize=(10, 8), sharey=True)

        ax_chi.plot(exponents, y_positions, 'o-', markersize=5, color='tab:blue')
        ax_chi.set_xlabel("χ (exponent)")
        ax_chi.set_ylabel("Channel")
        ax_chi.set_title("χ")
        ax_chi.set_yticks(y_positions)
        ax_chi.set_yticklabels(channel_labels)
        ax_chi.invert_yaxis()

        ax_a.plot(amplitudes, y_positions, 'o-', markersize=5, color='tab:orange')
        ax_a.set_xlabel("A (amplitude)")
        ax_a.set_title("A")

        fig.suptitle("Power Law Parameters: P(f) = A·f^χ")
        fig.tight_layout()
        return fig

    # ---- Helpers ----
    def _get_ordered_fits(self, fits_by_channel: Dict) -> Tuple[List, List[PowerLawFit], List[str]]:
        ordered_keys = []
        ordered_fits = []
        channel_labels = []
        for ch_num in self.channel_order:
            key = self._find_channel_key(ch_num, fits_by_channel)
            if key is None:
                continue
            ordered_keys.append(key)
            ordered_fits.append(fits_by_channel[key])
            channel_labels.append(f"{self.channel_prefix}-{ch_num:03d}")
        return ordered_keys, ordered_fits, channel_labels

    def _find_channel_key(self, ch_num: int, channel_dict: Dict):
        target_str = f"{self.channel_prefix}_{ch_num:03d}"
        for key in channel_dict:
            if str(key).endswith(target_str):
                return key
        return None
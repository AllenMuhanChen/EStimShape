from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class PowerLawFit:
    """Result of a power law fit: P(f) = A * f^χ"""
    exponent: float    # χ  — slope in log-log; the layer-identifying parameter
    amplitude: float   # A  — intercept; affected by normalization
    freqs: np.ndarray
    power: np.ndarray
    fit_power: np.ndarray
    r_squared: float


# ============================================================================
# Fitting
# ============================================================================

@dataclass
class LFPPowerLaw:
    """
    Fits P(f) = A * f^χ to LFP power spectra via linear regression in log-log
    space.  The exponent χ is invariant to multiplicative scaling (e.g.
    impedance differences between channels).
    """
    freq_range: Tuple[float, float] = (20, 100)

    def fit_one(self, freqs: np.ndarray, power: np.ndarray) -> PowerLawFit:
        mask = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
        f = freqs[mask]
        p = power[mask]

        valid = (p > 0) & (f > 0)
        f, p = f[valid], p[valid]

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
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        except Exception:
            A, chi = np.nan, np.nan
            fit_power = np.full_like(f, np.nan)
            r_squared = 0.0

        return PowerLawFit(
            exponent=chi, amplitude=A,
            freqs=f, power=p, fit_power=fit_power,
            r_squared=r_squared,
        )

    def fit_dict(self, spectrum_by_channel: Dict) -> Dict:
        """Fit every channel in a {channel: (freqs, power)} dict."""
        return {ch: self.fit_one(freqs, power)
                for ch, (freqs, power) in spectrum_by_channel.items()}

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_spectra(spectrum_by_channel: Dict) -> Dict:
        """
        Normalise each channel by its total power (area under curve).
        Removes absolute magnitude differences while preserving spectral shape.
        """
        result = {}
        for ch, (freqs, power) in spectrum_by_channel.items():
            total = np.trapz(power, freqs)
            result[ch] = (freqs, power / total) if total > 0 else (freqs, power)
        return result

    def normalize_spectra_peak(self, spectrum_by_channel: Dict) -> Dict:
        """
        Normalise so that the peak power within *self.freq_range* equals 1.
        Matches the fitting range, making plots directly comparable across channels.
        """
        result = {}
        for ch, (freqs, power) in spectrum_by_channel.items():
            mask = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
            peak = np.max(power[mask]) if np.any(mask) else 1.0
            result[ch] = (freqs, power / peak) if peak > 0 else (freqs, power)
        return result


# ============================================================================
# Shared channel-ordering mixin
# ============================================================================

@dataclass
class _ChannelOrderMixin:
    """Lookup and ordering utilities shared between plotters."""
    channel_order: List[int]
    channel_prefix: str = "A"

    def _find_channel_key(self, ch_num: int, channel_dict: Dict):
        target = f"{self.channel_prefix}_{ch_num:03d}"
        for key in channel_dict:
            if str(key).endswith(target):
                return key
        return None

    def _get_ordered_fits(
        self, fits_by_channel: Dict
    ) -> Tuple[List, List[PowerLawFit], List[str]]:
        ordered_keys, ordered_fits, labels = [], [], []
        for ch_num in self.channel_order:
            key = self._find_channel_key(ch_num, fits_by_channel)
            if key is None:
                continue
            ordered_keys.append(key)
            ordered_fits.append(fits_by_channel[key])
            labels.append(f"{self.channel_prefix}-{ch_num:03d}")
        return ordered_keys, ordered_fits, labels

    def _get_ordered_channels(
        self, channel_dict: Dict
    ) -> Tuple[List, List[str]]:
        ordered_keys, labels = [], []
        for ch_num in self.channel_order:
            key = self._find_channel_key(ch_num, channel_dict)
            if key is None:
                continue
            ordered_keys.append(key)
            labels.append(f"{self.channel_prefix}-{ch_num:03d}")
        return ordered_keys, labels


# ============================================================================
# LFPPowerLawSpectrumPlotter
# ============================================================================

@dataclass
class LFPPowerLawSpectrumPlotter(_ChannelOrderMixin):
    """
    Plots spectrum-derived power-law parameters as horizontal depth profiles
    (one row per channel, shallow → deep).

    Designed to be stitched directly onto an existing figure via
    :meth:`plot_onto_axes` — no spike data required.

    Panel toggles (all default True)
    ---------------------------------
    show_exponent       : χ per channel                            (always useful)
    show_amplitude      : A per channel                            (scale check)
    show_r_squared      : R² goodness-of-fit per channel           (QC)
    show_gamma_ratio    : γ (50–150 Hz) / αβ (10–30 Hz) ratio     (needs spectra)
    show_residual_gamma : mean residual γ above the 1/f baseline   (needs spectra)

    Concat onto an existing figure
    --------------------------------
    >>> pl = LFPPowerLawSpectrumPlotter(channel_order=ORDER)
    >>> width_ratios = [2, 1] + [1] * pl.n_axes
    >>> fig, axes = plt.subplots(1, 2 + pl.n_axes,
    ...                          gridspec_kw={'width_ratios': width_ratios})
    >>> heatmap_plotter.plot(data, ax=axes[0])
    >>> band_plotter.plot(data, ax=axes[1])
    >>> pl.plot_onto_axes(fits, axes[2:], avg_spectrum_by_channel=spectra)

    Standalone figure
    -----------------
    >>> fig = pl.plot(fits, avg_spectrum_by_channel=spectra)

    Diagnostic figures (for QC — not concatenation)
    ------------------------------------------------
    >>> fig_stacked = pl.plot_stacked(fits)
    >>> fig_overlay = pl.plot_overlay(fits)
    """

    show_exponent:            bool = True
    show_amplitude:           bool = True
    show_r_squared:           bool = True
    show_gamma_ratio:         bool = True
    show_residual_gamma:      bool = True
    show_residual_alpha_beta: bool = True

    @property
    def n_axes(self) -> int:
        """Number of axes required by :meth:`plot_onto_axes`."""
        return sum([
            self.show_exponent,
            self.show_amplitude,
            self.show_r_squared,
            self.show_gamma_ratio,
            self.show_residual_gamma,
            self.show_residual_alpha_beta,
        ])

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def plot_onto_axes(
        self,
        fits_by_channel: Dict,
        axes,
        avg_spectrum_by_channel: Optional[Dict] = None,
        label_y_axis: bool = True,
    ) -> None:
        """
        Draw all enabled panels onto the provided axes sequence.

        Parameters
        ----------
        fits_by_channel : Dict[channel_key, PowerLawFit]
        axes : sequence of matplotlib Axes, length == self.n_axes
        avg_spectrum_by_channel : Dict[channel_key, (freqs, power)], optional
            Required for gamma_ratio and residual_gamma panels; those panels
            render as NaN placeholders if omitted.
        label_y_axis : bool
            If True, the leftmost panel shows channel tick labels and a
            "Channel" y-label.  Set False when an adjacent axis already
            carries the labels (e.g. when appending to a sharey figure).
        """
        axes = list(axes)
        if len(axes) != self.n_axes:
            raise ValueError(
                f"Expected {self.n_axes} axes (based on enabled panels), "
                f"got {len(axes)}."
            )

        ordered_keys, ordered_fits, labels = self._get_ordered_fits(fits_by_channel)
        y = np.arange(len(labels))

        gamma_ratios, residual_gammas, residual_alpha_betas = self._compute_spectrum_metrics(
            ordered_keys, ordered_fits, avg_spectrum_by_channel
        )

        ax_idx = 0
        first_panel = True  # track whether to show y-tick labels

        if self.show_exponent:
            ax = axes[ax_idx]; ax_idx += 1
            self._draw_panel(
                ax, [f.exponent for f in ordered_fits], y, labels,
                xlabel="χ (exponent)", title="1/f Exponent",
                color="tab:blue",
                show_yticks=first_panel and label_y_axis,
            )
            first_panel = False

        if self.show_amplitude:
            ax = axes[ax_idx]; ax_idx += 1
            self._draw_panel(
                ax, [f.amplitude for f in ordered_fits], y, labels,
                xlabel="A (amplitude)", title="Amplitude",
                color="tab:orange",
                show_yticks=first_panel and label_y_axis,
            )
            first_panel = False

        if self.show_r_squared:
            ax = axes[ax_idx]; ax_idx += 1
            self._draw_panel(
                ax, [f.r_squared for f in ordered_fits], y, labels,
                xlabel="R²", title="Fit Quality (R²)",
                color="tab:gray",
                show_yticks=first_panel and label_y_axis,
                xlim=(0.0, 1.0),
            )
            first_panel = False

        if self.show_gamma_ratio:
            ax = axes[ax_idx]; ax_idx += 1
            vals = gamma_ratios if gamma_ratios is not None else [np.nan] * len(y)
            self._draw_panel(
                ax, vals, y, labels,
                xlabel="γ / αβ", title="Gamma / Alpha-Beta\nRatio",
                color="tab:purple",
                show_yticks=first_panel and label_y_axis,
            )
            first_panel = False

        if self.show_residual_gamma:
            ax = axes[ax_idx]; ax_idx += 1
            vals = residual_gammas if residual_gammas is not None else [np.nan] * len(y)
            self._draw_panel(
                ax, vals, y, labels,
                xlabel="Residual γ (µV²/Hz)", title="Residual Gamma\n(above 1/f)",
                color="tab:green",
                show_yticks=first_panel and label_y_axis,
            )
            first_panel = False

        if self.show_residual_alpha_beta:
            ax = axes[ax_idx]; ax_idx += 1
            vals = residual_alpha_betas if residual_alpha_betas is not None else [np.nan] * len(y)
            self._draw_panel(
                ax, vals, y, labels,
                xlabel="Residual αβ (µV²/Hz)", title="Residual Alpha-Beta\n(above 1/f)",
                color="tab:brown",
                show_yticks=first_panel and label_y_axis,
            )

    def plot(
        self,
        fits_by_channel: Dict,
        avg_spectrum_by_channel: Optional[Dict] = None,
    ) -> plt.Figure:
        """Create a standalone figure and delegate to :meth:`plot_onto_axes`."""
        n = self.n_axes
        fig, axes = plt.subplots(1, n, figsize=(4 * n, 8), sharey=True)
        axes = [axes] if n == 1 else list(axes)
        self.plot_onto_axes(
            fits_by_channel, axes,
            avg_spectrum_by_channel=avg_spectrum_by_channel,
            label_y_axis=True,
        )
        fig.suptitle("Power Law Parameters: P(f) = A·f^χ")
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # Diagnostic figures
    # ------------------------------------------------------------------

    def plot_stacked(self, fits_by_channel: Dict) -> plt.Figure:
        """
        One log-log subplot per channel showing raw spectrum + power-law fit.
        Useful for per-channel QC; not intended for concatenation.
        """
        _, ordered_fits, labels = self._get_ordered_fits(fits_by_channel)
        n = len(ordered_fits)
        fig, axes = plt.subplots(n, 1, figsize=(8, 1.5 * n), sharex=True)
        if n == 1:
            axes = [axes]
        for ax, fit, label in zip(axes, ordered_fits, labels):
            ax.loglog(fit.freqs, fit.power, 'k-', linewidth=0.5, alpha=0.7)
            ax.loglog(fit.freqs, fit.fit_power, 'r-', linewidth=1.5,
                      label=f"χ={fit.exponent:.2f}, R²={fit.r_squared:.2f}")
            ax.set_ylabel(label, fontsize=7, rotation=0, ha='right', va='center')
            ax.legend(fontsize=6, loc='upper right')
            ax.tick_params(labelsize=6)
        axes[-1].set_xlabel("Frequency (Hz)")
        fig.suptitle("1/f Power Law Fits by Channel (log-log)")
        fig.tight_layout()
        return fig

    def plot_overlay(self, fits_by_channel: Dict) -> plt.Figure:
        """
        All channels overlaid on a single log-log plot, coloured by depth
        (shallow → deep via viridis).  Not intended for concatenation.
        """
        _, ordered_fits, labels = self._get_ordered_fits(fits_by_channel)
        n = len(ordered_fits)
        cmap = plt.cm.viridis
        colors = [cmap(i / max(n - 1, 1)) for i in range(n)]

        fig, (ax_data, ax_fit) = plt.subplots(1, 2, figsize=(14, 6))
        for i, (fit, label) in enumerate(zip(ordered_fits, labels)):
            ax_data.loglog(fit.freqs, fit.power,
                           color=colors[i], linewidth=0.8, alpha=0.8)
            ax_fit.loglog(fit.freqs, fit.fit_power,
                          color=colors[i], linewidth=0.8, alpha=0.8)

        ax_data.set_xlabel("Frequency (Hz)")
        ax_data.set_ylabel("Power (µV²/Hz)")
        ax_data.set_title("Data")
        ax_fit.set_xlabel("Frequency (Hz)")
        ax_fit.set_title("Fits")

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, n - 1))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=[ax_data, ax_fit],
                            label="Depth (shallow → deep)", ticks=[0, n - 1])
        cbar.ax.set_yticklabels([labels[0], labels[-1]])

        fig.suptitle("All Channels by Depth")
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_spectrum_metrics(
        self,
        ordered_keys: List,
        ordered_fits: List[PowerLawFit],
        avg_spectrum_by_channel: Optional[Dict],
    ) -> Tuple[Optional[List[float]], Optional[List[float]], Optional[List[float]]]:
        """Return (gamma_ratios, residual_gammas, residual_alpha_betas).  All None if no spectra given."""
        if avg_spectrum_by_channel is None:
            return None, None, None

        gamma_ratios, residual_gammas, residual_alpha_betas = [], [], []
        for key, fit in zip(ordered_keys, ordered_fits):
            if key in avg_spectrum_by_channel:
                freqs, power = avg_spectrum_by_channel[key]
                gamma_ratios.append(self._gamma_alpha_beta_ratio(freqs, power))
                residual_gammas.append(self._residual_gamma(freqs, power, fit))
                residual_alpha_betas.append(self._residual_alpha_beta(freqs, power, fit))
            else:
                gamma_ratios.append(np.nan)
                residual_gammas.append(np.nan)
                residual_alpha_betas.append(np.nan)

        return gamma_ratios, residual_gammas, residual_alpha_betas

    @staticmethod
    def _gamma_alpha_beta_ratio(freqs: np.ndarray, power: np.ndarray) -> float:
        """γ (50–150 Hz) / αβ (10–30 Hz) mean-power ratio."""
        ab_mask = (freqs >= 10) & (freqs <= 30)
        g_mask  = (freqs >= 50) & (freqs <= 150)
        ab_pow = np.mean(power[ab_mask]) if np.any(ab_mask) else np.nan
        g_pow  = np.mean(power[g_mask])  if np.any(g_mask)  else np.nan
        if np.isnan(ab_pow) or ab_pow <= 0:
            return np.nan
        return float(g_pow / ab_pow)

    @staticmethod
    def _residual_gamma(
        freqs: np.ndarray, power: np.ndarray, fit: PowerLawFit
    ) -> float:
        """
        Mean residual power in γ (50–150 Hz) after subtracting the extrapolated
        1/f baseline.  Positive = oscillatory γ above the aperiodic background.
        """
        g_mask = (freqs >= 50) & (freqs <= 150)
        f_g = freqs[g_mask]
        p_g = power[g_mask]
        if len(f_g) == 0 or np.isnan(fit.exponent):
            return np.nan
        predicted = fit.amplitude * np.power(f_g, fit.exponent)
        return float(np.mean(p_g - predicted))

    @staticmethod
    def _residual_alpha_beta(
        freqs: np.ndarray, power: np.ndarray, fit: PowerLawFit
    ) -> float:
        """
        Mean residual power in αβ (10–30 Hz) after subtracting the extrapolated
        1/f baseline.  Positive = oscillatory αβ above the aperiodic background.
        """
        ab_mask = (freqs >= 10) & (freqs <= 30)
        f_ab = freqs[ab_mask]
        p_ab = power[ab_mask]
        if len(f_ab) == 0 or np.isnan(fit.exponent):
            return np.nan
        predicted = fit.amplitude * np.power(f_ab, fit.exponent)
        return float(np.mean(p_ab - predicted))

    @staticmethod
    def _draw_panel(
        ax: plt.Axes,
        values: List[float],
        y_positions: np.ndarray,
        labels: List[str],
        xlabel: str,
        title: str,
        color: str,
        show_yticks: bool = False,
        xlim: Optional[Tuple[float, float]] = None,
    ) -> None:
        ax.plot(values, y_positions, 'o-', markersize=5, color=color)
        ax.set_xlabel(xlabel)
        ax.set_title(title)
        ax.invert_yaxis()
        ax.set_yticks(y_positions)
        if show_yticks:
            ax.set_yticklabels(labels)
            ax.set_ylabel("Channel")
        else:
            ax.set_yticklabels([])
        if xlim is not None:
            ax.set_xlim(*xlim)


# ============================================================================
# LFPSpikeRatePlotter
# ============================================================================

@dataclass
class LFPSpikeRatePlotter(_ChannelOrderMixin):
    """
    Plots spike-rate–derived panels as horizontal depth profiles.

    Shares the same ``plot_onto_axes`` / ``n_axes`` contract as
    :class:`LFPPowerLawSpectrumPlotter`, so both can be appended to the same
    figure in sequence.

    Panel toggles (all default True)
    ---------------------------------
    show_spike_rate       : mean firing rate per channel
    show_rate_vs_exponent : spike rate vs χ scatter (requires fits_by_channel)

    Append after spectrum panels
    ----------------------------
    >>> sp = LFPSpikeRatePlotter(channel_order=ORDER)
    >>> n_total = 2 + pl.n_axes + sp.n_axes
    >>> fig, axes = plt.subplots(1, n_total, ...)
    >>> pl.plot_onto_axes(fits, axes[2 : 2 + pl.n_axes], ...)
    >>> sp.plot_onto_axes(rates, axes[2 + pl.n_axes :], fits_by_channel=fits)

    Standalone figure
    -----------------
    >>> fig = sp.plot(spike_rates, fits_by_channel=fits)
    """

    show_spike_rate:       bool = False
    show_rate_vs_exponent: bool = True

    @property
    def n_axes(self) -> int:
        return sum([self.show_spike_rate, self.show_rate_vs_exponent])

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def plot_onto_axes(
        self,
        spike_rates_by_channel: Dict,
        axes,
        fits_by_channel: Optional[Dict] = None,
        label_y_axis: bool = True,
    ) -> None:
        """
        Draw all enabled panels onto the provided axes sequence.

        Parameters
        ----------
        spike_rates_by_channel : Dict[channel_key, float]  (mean Hz per channel)
        axes : sequence of matplotlib Axes, length == self.n_axes
        fits_by_channel : Dict[channel_key, PowerLawFit], optional
            Required for the rate-vs-exponent scatter panel.
        label_y_axis : bool
            Whether the depth-profile panel shows channel tick labels.
        """
        axes = list(axes)
        if len(axes) != self.n_axes:
            raise ValueError(
                f"Expected {self.n_axes} axes (based on enabled panels), "
                f"got {len(axes)}."
            )

        ordered_keys, labels = self._get_ordered_channels(spike_rates_by_channel)
        y = np.arange(len(labels))
        rates = [spike_rates_by_channel.get(k, np.nan) for k in ordered_keys]

        ax_idx = 0
        first_panel = True

        if self.show_spike_rate:
            ax = axes[ax_idx]; ax_idx += 1
            ax.plot(rates, y, 'o-', markersize=5, color='tab:red')
            ax.set_xlabel("Spike Rate (Hz)")
            ax.set_title("Avg Spike Rate")
            ax.invert_yaxis()
            ax.set_yticks(y)
            if first_panel and label_y_axis:
                ax.set_yticklabels(labels)
                ax.set_ylabel("Channel")
            else:
                ax.set_yticklabels([])
            first_panel = False

        if self.show_rate_vs_exponent:
            ax = axes[ax_idx]; ax_idx += 1
            if fits_by_channel is not None:
                exponents, valid_rates = [], []
                for k, rate in zip(ordered_keys, rates):
                    fit = fits_by_channel.get(k)
                    if fit is not None and not np.isnan(rate) and not np.isnan(fit.exponent):
                        exponents.append(fit.exponent)
                        valid_rates.append(rate)
                ax.scatter(exponents, valid_rates,
                           c='tab:red', s=40, alpha=0.8, zorder=3)
                if len(exponents) > 1:
                    m, b = np.polyfit(exponents, valid_rates, 1)
                    x_line = np.linspace(min(exponents), max(exponents), 50)
                    ax.plot(x_line, m * x_line + b, 'k--', linewidth=1, alpha=0.6)
            else:
                ax.text(0.5, 0.5, "No fits provided",
                        transform=ax.transAxes, ha='center', va='center', color='gray')
            ax.set_xlabel("χ (exponent)")
            ax.set_ylabel("Spike Rate (Hz)")
            ax.set_title("Spike Rate\nvs χ")

    def plot(
        self,
        spike_rates_by_channel: Dict,
        fits_by_channel: Optional[Dict] = None,
    ) -> plt.Figure:
        """Create a standalone figure and delegate to :meth:`plot_onto_axes`."""
        n = self.n_axes
        fig, axes = plt.subplots(1, n, figsize=(4 * n, 8))
        axes = [axes] if n == 1 else list(axes)
        self.plot_onto_axes(
            spike_rates_by_channel, axes,
            fits_by_channel=fits_by_channel,
            label_y_axis=True,
        )
        fig.suptitle("Spike Rate Profile")
        fig.tight_layout()
        return fig
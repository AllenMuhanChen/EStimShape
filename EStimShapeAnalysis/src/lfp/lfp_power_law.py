from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import warnings

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

warnings.filterwarnings("ignore", category=DeprecationWarning, module="fooof")


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class OscillatorPeak:
    """A single Gaussian oscillatory peak fit in log-frequency space."""
    center_freq: float   # CF  — peak center frequency (Hz)
    bandwidth:   float   # BW  — std dev in log10(Hz); ~0.1–0.4 is typical
    height:      float   # H   — peak height above the aperiodic floor (log10 units)


@dataclass
class PowerLawFit:
    """
    Result of an aperiodic + oscillatory peak model fit.

    The full model in log10 space:
        log10 P(f) = log10 A  +  χ · log10 f
                     + Σ_k  H_k · exp(-(log10 f − log10 CF_k)² / (2·BW_k²))

    The aperiodic component alone (peaks removed) gives an uncontaminated
    estimate of χ, which is what we care about for laminar analysis.
    """
    exponent:   float          # χ — aperiodic slope (pure, peak-free)
    amplitude:  float          # A — aperiodic intercept
    peaks:      List[OscillatorPeak]  # oscillatory perturbations
    freqs:      np.ndarray
    power:      np.ndarray
    fit_power:  np.ndarray     # full model (aperiodic + peaks)
    aperiodic_power: np.ndarray  # aperiodic component only
    r_squared:  float


# ============================================================================
# Fitting
# ============================================================================

@dataclass
class SimplePowerLaw:
    """
    Fits an aperiodic (1/f) power law with optional Gaussian oscillatory peak
    perturbations to LFP power spectra.

    Model (log10 space):
        log10 P(f) = log10 A + χ·log10 f
                     + Σ_k H_k · exp(-(log10 f - log10 CF_k)² / (2·BW_k²))

    Fitting strategy
    ----------------
    1. Initial aperiodic-only polyfit (fast, ignores peaks).
    2. If ``peak_regions`` is non-empty: nonlinear least squares adds one
       Gaussian per region, seeded from the residual peak and constrained to
       stay within the region.  The aperiodic params are re-estimated jointly
       so they are not biased by the oscillatory power.
    3. The returned ``exponent`` is always from the joint fit (or the simple
       fit if no peaks are requested), giving an uncontaminated χ.

    Note: for a proper iterative peak-finding approach use FOOOFPowerLaw.

    Parameters
    ----------
    freq_range : (lo, hi)
        Frequency range used for fitting (Hz).
    peak_regions : list of (lo, hi) tuples
        Each entry defines a band where an oscillatory peak is expected.
        A Gaussian is seeded and constrained to that band.
        Example: ``[(8, 30)]`` to model the alpha-beta peak.
        Leave empty (default) for a pure aperiodic fit.
    min_peak_height : float
        Minimum residual height (log10 units) for a peak to be included.
        Peaks smaller than this are dropped from the model.
    """
    freq_range:       Tuple[float, float]       = (2, 150)
    peak_regions:     List[Tuple[float, float]] = field(default_factory=list)
    min_peak_height:  float                     = 0.05

    def fit_one(self, freqs: np.ndarray, power: np.ndarray) -> PowerLawFit:
        mask  = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
        f     = freqs[mask]
        p     = power[mask]
        valid = (p > 0) & (f > 0)
        f, p  = f[valid], p[valid]

        log_f = np.log10(f)
        log_p = np.log10(p)

        try:
            coeffs_init = np.polyfit(log_f, log_p, 1)
        except Exception:
            return self._nan_fit(f, p)

        if not self.peak_regions:
            return self._build_fit(f, p, log_f, log_p, coeffs_init, peaks=[])

        aperiodic_init = np.polyval(coeffs_init, log_f)
        residual       = log_p - aperiodic_init

        peak_params_init = []
        peak_bounds_lo   = []
        peak_bounds_hi   = []

        for (lo, hi) in self.peak_regions:
            region_mask = (f >= lo) & (f <= hi)
            if not np.any(region_mask):
                continue
            peak_idx = np.argmax(residual[region_mask])
            cf_seed  = f[region_mask][peak_idx]
            h_seed   = max(residual[region_mask][peak_idx], self.min_peak_height)
            bw_seed  = 0.2

            peak_params_init += [h_seed, np.log10(cf_seed), bw_seed]
            peak_bounds_lo += [0.0, np.log10(lo), 0.05]
            peak_bounds_hi += [np.inf, np.log10(hi), 1.0]

        if not peak_params_init:
            return self._build_fit(f, p, log_f, log_p, coeffs_init, peaks=[])

        n_peaks   = len(peak_params_init) // 3
        p0        = [coeffs_init[1], coeffs_init[0]] + peak_params_init
        bounds_lo = [-np.inf, -np.inf] + peak_bounds_lo
        bounds_hi = [ np.inf,  0.0  ] + peak_bounds_hi

        def model(lf, log_A, chi, *peak_args):
            y = log_A + chi * lf
            for k in range(n_peaks):
                H, log_cf, bw = peak_args[3*k], peak_args[3*k+1], peak_args[3*k+2]
                y = y + H * np.exp(-((lf - log_cf) ** 2) / (2 * bw ** 2))
            return y

        try:
            popt, _ = curve_fit(
                model, log_f, log_p, p0=p0,
                bounds=(bounds_lo, bounds_hi),
                maxfev=5000,
            )
        except Exception:
            return self._build_fit(f, p, log_f, log_p, coeffs_init, peaks=[])

        log_A_fit, chi_fit = popt[0], popt[1]
        coeffs_fit = [chi_fit, log_A_fit]

        peaks = []
        for k in range(n_peaks):
            H, log_cf, bw = popt[2 + 3*k], popt[3 + 3*k], popt[4 + 3*k]
            if H >= self.min_peak_height:
                peaks.append(OscillatorPeak(
                    center_freq=10 ** log_cf,
                    bandwidth=bw,
                    height=H,
                ))

        return self._build_fit(f, p, log_f, log_p, coeffs_fit, peaks=peaks)

    def fit_dict(self, spectrum_by_channel: Dict) -> Dict:
        """Fit every channel in a {channel: (freqs, power)} dict."""
        return {ch: self.fit_one(freqs, power)
                for ch, (freqs, power) in spectrum_by_channel.items()}

    @staticmethod
    def normalize_spectra(spectrum_by_channel: Dict) -> Dict:
        """Normalise each channel by total power (area under curve)."""
        result = {}
        for ch, (freqs, power) in spectrum_by_channel.items():
            total = np.trapz(power, freqs)
            result[ch] = (freqs, power / total) if total > 0 else (freqs, power)
        return result

    def normalize_spectra_peak(self, spectrum_by_channel: Dict) -> Dict:
        """Normalise so that the peak power within freq_range equals 1."""
        result = {}
        for ch, (freqs, power) in spectrum_by_channel.items():
            mask = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
            peak = np.max(power[mask]) if np.any(mask) else 1.0
            result[ch] = (freqs, power / peak) if peak > 0 else (freqs, power)
        return result

    @staticmethod
    def _build_fit(
        f: np.ndarray, p: np.ndarray,
        log_f: np.ndarray, log_p: np.ndarray,
        coeffs: list, peaks: List[OscillatorPeak],
    ) -> PowerLawFit:
        log_A = coeffs[1]
        chi   = coeffs[0]
        A     = 10 ** log_A

        log_aperiodic   = log_A + chi * log_f
        aperiodic_power = 10 ** log_aperiodic

        log_full = log_aperiodic.copy()
        for pk in peaks:
            log_full += pk.height * np.exp(
                -((log_f - np.log10(pk.center_freq)) ** 2) / (2 * pk.bandwidth ** 2)
            )
        fit_power = 10 ** log_full

        ss_res    = np.sum((log_p - log_full) ** 2)
        ss_tot    = np.sum((log_p - np.mean(log_p)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return PowerLawFit(
            exponent=chi, amplitude=A, peaks=peaks,
            freqs=f, power=p,
            fit_power=fit_power, aperiodic_power=aperiodic_power,
            r_squared=r_squared,
        )

    @staticmethod
    def _nan_fit(f: np.ndarray, p: np.ndarray) -> PowerLawFit:
        nan_arr = np.full_like(f, np.nan)
        return PowerLawFit(
            exponent=np.nan, amplitude=np.nan, peaks=[],
            freqs=f, power=p,
            fit_power=nan_arr, aperiodic_power=nan_arr,
            r_squared=0.0,
        )


@dataclass
class FOOOFPowerLaw:
    """
    Wraps the FOOOF (specparam) spectral parameterization library to produce
    PowerLawFit objects with the same interface as SimplePowerLaw.

    FOOOF's algorithm:
        1. Fit aperiodic component on the raw log-power spectrum.
        2. Subtract aperiodic → flattened residual.
        3. Iteratively find and fit Gaussian peaks in the residual, one at a
           time (greedy), each time subtracting the found peak before looking
           for the next.
        4. Re-fit aperiodic on the peak-removed spectrum for a clean estimate.
        5. Return aperiodic params + all peaks jointly.

    This gives an uncontaminated χ even when peaks overlap the fit range,
    which SimplePowerLaw cannot guarantee.

    FOOOF convention: exponent is stored as positive (slope of falling
    spectrum).  We negate it so χ follows the standard sign convention
    (χ < 0 for a 1/f spectrum).

    Peak params from FOOOF: [CF, PW, BW]
        CF  — center frequency (Hz)
        PW  — peak power / height above aperiodic (log10 units)
        BW  — bandwidth = std dev of Gaussian in Hz (linear frequency)

    Parameters
    ----------
    freq_range : (lo, hi)
        Frequency range passed to FOOOF for fitting (Hz).
    max_n_peaks : int
        Maximum number of oscillatory peaks to fit per channel.
    min_peak_height : float
        Minimum peak height in log10 units for a peak to be retained.
    peak_width_limits : (min_hz, max_hz)
        Bounds on the Gaussian std dev (Hz) for each peak.
    aperiodic_mode : str
        'fixed' (default) or 'knee'.  'fixed' gives the classic 1/f model.
    """
    freq_range:         Tuple[float, float] = (2, 150)
    max_n_peaks:        int                 = 6
    min_peak_height:    float               = 0.05
    peak_width_limits:  Tuple[float, float] = (2.0, 20.0)
    aperiodic_mode:     str                 = 'fixed'

    def fit_one(self, freqs: np.ndarray, power: np.ndarray) -> PowerLawFit:
        try:
            from fooof import FOOOF
        except ImportError:
            raise ImportError("fooof is required: pip install fooof")

        # Restrict to fit range and require positive power
        mask  = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
        f     = freqs[mask]
        p     = power[mask]
        valid = (p > 0) & (f > 0)
        f, p  = f[valid], p[valid]

        if len(f) < 10:
            return self._nan_fit(f, p)

        fm = FOOOF(
            max_n_peaks=self.max_n_peaks,
            min_peak_height=self.min_peak_height,
            peak_width_limits=self.peak_width_limits,
            aperiodic_mode=self.aperiodic_mode,
            verbose=False,
        )

        try:
            fm.fit(f, p, self.freq_range)
        except Exception:
            return self._nan_fit(f, p)

        # --- Aperiodic params --------------------------------------------
        # FOOOF fixed: log10 P = offset - exponent * log10(f)
        # → our convention: χ = -exponent  (χ < 0 for falling spectrum)
        offset   = fm.aperiodic_params_[0]
        exponent = fm.aperiodic_params_[1]
        chi      = -exponent
        A        = 10 ** offset

        # Reconstruct aperiodic and full-model power on f
        # fm._ap_fit and fm.fooofed_spectrum_ live on fm.freqs_
        # Use interp in case freq grids differ
        aperiodic_power = 10 ** np.interp(f, fm.freqs, fm._ap_fit)
        fit_power       = 10 ** np.interp(f, fm.freqs, fm.fooofed_spectrum_)

        # R² in log10 space
        log_p    = np.log10(p)
        log_full = np.interp(f, fm.freqs, fm.fooofed_spectrum_)
        ss_res   = np.sum((log_p - log_full) ** 2)
        ss_tot   = np.sum((log_p - np.mean(log_p)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # --- Peaks -------------------------------------------------------
        # FOOOF peak_params_: rows of [CF, PW, BW]
        # PW = height in log10; BW = std dev in Hz (linear frequency)
        peaks = []
        if fm.peak_params_.ndim == 2 and len(fm.peak_params_) > 0:
            for cf, pw, bw in fm.peak_params_:
                peaks.append(OscillatorPeak(
                    center_freq=float(cf),
                    height=float(pw),
                    bandwidth=float(bw),   # Hz, linear (not log10)
                ))

        return PowerLawFit(
            exponent=chi, amplitude=A, peaks=peaks,
            freqs=f, power=p,
            fit_power=fit_power, aperiodic_power=aperiodic_power,
            r_squared=r_squared,
        )

    def fit_dict(self, spectrum_by_channel: Dict) -> Dict:
        """Fit every channel in a {channel: (freqs, power)} dict."""
        return {ch: self.fit_one(freqs, power)
                for ch, (freqs, power) in spectrum_by_channel.items()}

    @staticmethod
    def normalize_spectra(spectrum_by_channel: Dict) -> Dict:
        """Normalise each channel by total power (area under curve)."""
        result = {}
        for ch, (freqs, power) in spectrum_by_channel.items():
            total = np.trapz(power, freqs)
            result[ch] = (freqs, power / total) if total > 0 else (freqs, power)
        return result

    def normalize_spectra_peak(self, spectrum_by_channel: Dict) -> Dict:
        """Normalise so that the peak power within freq_range equals 1."""
        result = {}
        for ch, (freqs, power) in spectrum_by_channel.items():
            mask = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
            peak = np.max(power[mask]) if np.any(mask) else 1.0
            result[ch] = (freqs, power / peak) if peak > 0 else (freqs, power)
        return result

    @staticmethod
    def _nan_fit(f: np.ndarray, p: np.ndarray) -> PowerLawFit:
        nan_arr = np.full_like(f, np.nan)
        return PowerLawFit(
            exponent=np.nan, amplitude=np.nan, peaks=[],
            freqs=f, power=p,
            fit_power=nan_arr, aperiodic_power=nan_arr,
            r_squared=0.0,
        )


# Backward-compatible alias
LFPPowerLaw = FOOOFPowerLaw


# ============================================================================
# Shared channel-ordering mixin
# ============================================================================

@dataclass
class _ChannelOrderMixin:
    """Lookup and ordering utilities shared between plotters."""
    channel_order: List[int]
    channel_prefix: str = "A"

    def _find_channel_key(self, ch_num: int, channel_dict: Dict):
        for key in channel_dict:
            s = str(key)
            if (s.endswith(f"{self.channel_prefix}_{ch_num:03d}") or
                    s.endswith(f"{self.channel_prefix}-{ch_num:03d}")):
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
    show_alpha_beta_peak:     bool = True   # fitted αβ Gaussian: height + CF (needs peak_regions fit)

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
            self.show_alpha_beta_peak * 2,  # height + CF = 2 panels
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

        # Extract αβ peak params directly from the fits
        ab_peak_heights = [self._alpha_beta_peak_height(fit) for fit in ordered_fits]
        ab_peak_cfs     = [self._alpha_beta_peak_cf(fit)     for fit in ordered_fits]

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
            first_panel = False

        if self.show_alpha_beta_peak:
            ax = axes[ax_idx]; ax_idx += 1
            self._draw_panel(
                ax, ab_peak_heights, y, labels,
                xlabel="αβ peak / aperiodic (ratio)", title="αβ Peak\n(power / aperiodic at CF)",
                color="tab:pink",
                show_yticks=first_panel and label_y_axis,
            )
            first_panel = False

            ax = axes[ax_idx]; ax_idx += 1
            self._draw_panel(
                ax, ab_peak_cfs, y, labels,
                xlabel="αβ peak CF (Hz)", title="αβ Peak Center Freq",
                color="tab:red",
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

    def plot_spectrum_fits(
        self,
        fits_by_channel: Dict,
        avg_spectrum_by_channel: Optional[Dict] = None,
        n_cols: int = 4,
        freq_range: Tuple[float, float] = (1, 150),
    ) -> plt.Figure:
        """
        Grid of per-channel log-log spectrum plots with FOOOF decomposition.

        Each subplot shows:
          - Raw spectrum (full ``freq_range``, grey)
          - Aperiodic component only (blue dashed)
          - Full model fit = aperiodic + peaks (red)
          - Vertical dotted lines at each fitted peak's CF

        Parameters
        ----------
        fits_by_channel : Dict[channel_key, PowerLawFit]
        avg_spectrum_by_channel : Dict[channel_key, (freqs, power)], optional
            If provided, raw spectra are drawn over the full ``freq_range``
            rather than just the fit's restricted frequency vector.
        n_cols : int
            Number of columns in the subplot grid (default 4).
        freq_range : (lo, hi)
            Frequency range to display in each subplot (Hz).
        """
        ordered_keys, ordered_fits, labels = self._get_ordered_fits(fits_by_channel)
        n = len(ordered_fits)
        n_rows = int(np.ceil(n / n_cols))

        fig, axes = plt.subplots(
            n_rows, n_cols,
            figsize=(4 * n_cols, 3 * n_rows),
            sharex=True, sharey=False,
        )
        axes_flat = np.array(axes).flatten()

        for i, (key, fit, label) in enumerate(zip(ordered_keys, ordered_fits, labels)):
            ax = axes_flat[i]

            # --- Raw spectrum (full range if available) ---
            if avg_spectrum_by_channel is not None and key in avg_spectrum_by_channel:
                raw_freqs, raw_power = avg_spectrum_by_channel[key]
                mask = (raw_freqs >= freq_range[0]) & (raw_freqs <= freq_range[1])
                ax.semilogy(raw_freqs[mask], raw_power[mask],
                            color='0.6', linewidth=0.8, alpha=0.9, label='raw')
            else:
                # Fall back to the spectrum stored in the fit
                ax.semilogy(fit.freqs, fit.power,
                            color='0.6', linewidth=0.8, alpha=0.9, label='raw')

            # --- Aperiodic component (fit range only) ---
            ax.semilogy(fit.freqs, fit.aperiodic_power,
                        'b--', linewidth=1.2, alpha=0.9, label='aperiodic')

            # --- Full model fit ---
            ax.semilogy(fit.freqs, fit.fit_power,
                        'r-', linewidth=1.5, alpha=0.9, label='model')

            # --- Peak CF markers ---
            for pk in fit.peaks:
                ax.axvline(pk.center_freq, color='orange', linewidth=0.9,
                           linestyle=':', alpha=0.85)
                ax.text(pk.center_freq, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1,
                        f'{pk.center_freq:.0f}Hz',
                        fontsize=5, color='darkorange', ha='center', va='bottom',
                        clip_on=True)

            # --- Fit range shading ---
            ax.axvspan(fit.freqs[0], fit.freqs[-1], alpha=0.04, color='red')

            # --- Labels ---
            n_peaks = len(fit.peaks)
            peak_str = f"  {n_peaks}pk" if n_peaks > 0 else ""
            ax.set_title(
                f"{label}  χ={fit.exponent:.2f}  R²={fit.r_squared:.2f}{peak_str}",
                fontsize=7, pad=2,
            )
            ax.set_xlim(*freq_range)
            ax.tick_params(labelsize=6)
            ax.set_xlabel("Hz", fontsize=6)

            if i % n_cols == 0:
                ax.set_ylabel("Power (µV²/Hz)", fontsize=6)

        # Add a single shared legend on the first axis
        axes_flat[0].legend(
            fontsize=6, loc='upper right',
            handles=[
                plt.Line2D([0], [0], color='0.6', linewidth=1.0, label='raw'),
                plt.Line2D([0], [0], color='blue', linestyle='--', linewidth=1.2, label='aperiodic'),
                plt.Line2D([0], [0], color='red', linewidth=1.5, label='model'),
                plt.Line2D([0], [0], color='orange', linestyle=':', linewidth=0.9, label='peak CF'),
            ]
        )

        # Hide unused axes
        for j in range(n, len(axes_flat)):
            axes_flat[j].set_visible(False)

        fig.suptitle("FOOOF Spectral Fits by Channel", fontsize=10)
        fig.tight_layout()
        return fig

    def plot_stacked(self, fits_by_channel: Dict,
                     avg_spectrum_by_channel: Optional[Dict] = None) -> plt.Figure:
        """Thin wrapper around plot_spectrum_fits for backward compatibility."""
        return self.plot_spectrum_fits(fits_by_channel, avg_spectrum_by_channel)

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
    def _alpha_beta_peak(fit: PowerLawFit) -> Optional['OscillatorPeak']:
        """Return the fitted peak whose CF falls in the αβ band (8–30 Hz), or None."""
        ab_peaks = [pk for pk in fit.peaks if 8 <= pk.center_freq <= 30]
        if not ab_peaks:
            return None
        # If multiple somehow landed in range, take the tallest
        return max(ab_peaks, key=lambda pk: pk.height)

    @classmethod
    def _alpha_beta_peak_height(cls, fit: PowerLawFit) -> float:
        """
        αβ peak power as a ratio to the aperiodic baseline at the same CF.
        Computed as 10^PW where PW is FOOOF's log₁₀ peak height — amplitude-invariant
        across channels because the aperiodic floor is divided out.
        Returns NaN if no αβ peak was fitted.
        """
        pk = cls._alpha_beta_peak(fit)
        return float(10 ** pk.height) if pk is not None else np.nan

    @classmethod
    def _alpha_beta_peak_cf(cls, fit: PowerLawFit) -> float:
        """Center frequency (Hz) of the αβ Gaussian peak, or NaN if none was fit."""
        pk = cls._alpha_beta_peak(fit)
        return pk.center_freq if pk is not None else np.nan

    @staticmethod
    def _residual_in_band(
        freqs: np.ndarray, power: np.ndarray, fit: PowerLawFit,
        f_lo: float, f_hi: float,
    ) -> float:
        """
        Mean residual power in [f_lo, f_hi] Hz after subtracting the fitted
        aperiodic baseline, interpolated onto the spectrum's frequency axis.
        Positive = oscillatory power above the aperiodic background.
        """
        band_mask = (freqs >= f_lo) & (freqs <= f_hi)
        f_band = freqs[band_mask]
        p_band = power[band_mask]
        if len(f_band) == 0 or np.isnan(fit.exponent):
            return np.nan
        # Interpolate the aperiodic component (defined on fit.freqs) onto f_band
        aperiodic_interp = np.interp(f_band, fit.freqs, fit.aperiodic_power)
        return float(np.mean(p_band - aperiodic_interp))

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

    def _residual_gamma(
        self, freqs: np.ndarray, power: np.ndarray, fit: PowerLawFit
    ) -> float:
        """Mean residual γ (50–150 Hz) above the aperiodic baseline."""
        return self._residual_in_band(freqs, power, fit, 50, 150)

    def _residual_alpha_beta(
        self, freqs: np.ndarray, power: np.ndarray, fit: PowerLawFit
    ) -> float:
        """Mean residual αβ (10–30 Hz) above the aperiodic baseline."""
        return self._residual_in_band(freqs, power, fit, 10, 30)

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

    show_spike_rate:       bool = True
    show_rate_vs_exponent: bool = False

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
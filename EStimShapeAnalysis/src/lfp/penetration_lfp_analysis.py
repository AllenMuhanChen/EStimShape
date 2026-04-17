#!/usr/bin/env python3
"""
Penetration LFP Analysis
========================
Post-hoc script that combines all idle LFP recordings from a single
penetration into a unified depth-profile visualization.

Recording discovery:
    Scans ga_intan_path for directories matching:
        idle_{session_id}_{depth}_{date}_{time}
    and pairs them with impedance CSVs:
        idle_{session_id}_{depth}.csv

Probe geometry (confirmed):
    CHANNEL_ORDER[0]  = most superficial channel
    CHANNEL_ORDER[31] = deepest (tip)
    Channel at probe position i: depth_um = driven_depth_um + (i - 31) * 65
    Depth under chamber (mm): tip_start_mm + depth_um / 1000
"""

import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d

from clat.intan.amplifiers import read_amplifier_data
from clat.intan.rhs.load_intan_rhs_format import read_data

from lfp_spectrum import LFPSpectrum
from lfp_power_law import (
    FOOOFPowerLaw, LFPPowerLawSpectrumPlotter, PowerLawFit, OscillatorPeak,
)
from mua_detection import detect_mua_spikes
from intan_lfp import (
    extract_lfp, CHANNEL_ORDER, POWER_LAW_PANELS,
    LFP_LOWPASS, LFP_TARGET_RATE,
    MUA_HIGHPASS_HZ, MUA_THRESHOLD_RMS, MUA_REFRACTORY_SEC,
)

from src.startup.context import ga_intan_path, ga_database
from src.repository.export_to_repository import read_session_id_from_db_name


# ============================================================================
# CONFIGURATION
# ============================================================================

CHANNEL_SPACING_UM = 65       # µm between adjacent channels on probe
N_CHANNELS = len(CHANNEL_ORDER)  # 32
TIP_TO_BOTTOM_CHANNEL_UM = 600  # µm from probe tip to deepest recording channel
FREQ_RANGE = (0, 150)

BANDS = {
    "delta-theta": (1, 8),
    "alpha-beta":  (10, 19),
    "gamma":       (40, 150),
}
BAND_COLORS = {
    "delta-theta": "tab:blue",
    "alpha-beta":  "tab:orange",
    "gamma":       "tab:green",
}


# ============================================================================
# RECORDING DISCOVERY
# ============================================================================

def discover_recordings(
    intan_path: str,
    session_id: str,
) -> List[Tuple[int, str, Optional[str]]]:
    """
    Scan intan_path for idle recording directories and impedance CSVs.

    Returns list of (driven_depth_um, recording_dir, impedance_csv_or_None)
    sorted by depth ascending.  When multiple dirs exist for the same depth,
    the most recently modified one is used.
    """
    dir_pattern = re.compile(
        rf'^idle_{re.escape(session_id)}_(\d+)_\d{{6}}_\d{{6}}$'
    )
    csv_pattern = re.compile(
        rf'^idle_{re.escape(session_id)}_(\d+)\.csv$'
    )

    depth_to_dirs: Dict[int, List[Tuple[str, float]]] = defaultdict(list)
    depth_to_csv:  Dict[int, str] = {}

    try:
        entries = os.listdir(intan_path)
    except OSError as exc:
        raise RuntimeError(f"Cannot list {intan_path}: {exc}")

    for entry in entries:
        m = dir_pattern.match(entry)
        if m:
            depth = int(m.group(1))
            full = os.path.join(intan_path, entry)
            depth_to_dirs[depth].append((full, os.path.getmtime(full)))
            continue
        m = csv_pattern.match(entry)
        if m:
            depth = int(m.group(1))
            depth_to_csv[depth] = os.path.join(intan_path, entry)

    recordings = []
    for depth in sorted(depth_to_dirs):
        latest_dir = max(depth_to_dirs[depth], key=lambda x: x[1])[0]
        recordings.append((depth, latest_dir, depth_to_csv.get(depth)))
    return recordings


# ============================================================================
# PER-RECORDING LOADING
# ============================================================================

def _ch_num_from_key(key) -> Optional[int]:
    """Extract integer channel number from a Channel object or string."""
    m = re.search(r'[A-Za-z][-_](\d{3})', str(key))
    return int(m.group(1)) if m else None


def _nan_fit() -> PowerLawFit:
    empty = np.array([])
    return PowerLawFit(
        exponent=np.nan, amplitude=np.nan, peaks=[],
        freqs=empty, power=empty,
        fit_power=empty, aperiodic_power=empty,
        r_squared=0.0,
    )


def load_recording(
    rec_dir: str,
) -> Tuple[Dict, Dict, Dict, float]:
    """
    Load a saved Intan idle recording and compute LFP spectra, power-law
    fits, and MUA spike rates.

    Returns:
        spectra      : Dict[ch_name, (freqs, power)]
        fits         : Dict[ch_name, PowerLawFit]
        spike_rates  : Dict[ch_name, float]  (Hz)
        duration     : float  (seconds)
    """
    info_path = os.path.join(rec_dir, "info.rhs")
    amp_path  = os.path.join(rec_dir, "amplifier.dat")

    rhs = read_data(info_path)
    sample_rate        = rhs['frequency_parameters']['amplifier_sample_rate']
    amplifier_channels = rhs['amplifier_channels']

    channel_to_raw = read_amplifier_data(amp_path, amplifier_channels)

    channel_order_set = set(CHANNEL_ORDER)
    raw_by_name: Dict[str, np.ndarray] = {}
    for key, data in channel_to_raw.items():
        ch_num = _ch_num_from_key(key)
        if ch_num is not None and ch_num in channel_order_set:
            raw_by_name[f"A_{ch_num:03d}"] = data

    if not raw_by_name:
        raise RuntimeError(f"No matching channels found in {rec_dir}")

    duration = len(next(iter(raw_by_name.values()))) / sample_rate

    lfp_by_name: Dict[str, np.ndarray] = {}
    lfp_rate: Optional[float] = None
    for name, wideband in raw_by_name.items():
        lfp, lfp_rate = extract_lfp(wideband, sample_rate, LFP_LOWPASS, LFP_TARGET_RATE)
        lfp_by_name[name] = lfp

    spectrum_calc = LFPSpectrum(sample_rate=lfp_rate, nperseg=1000)
    spectra = {ch: spectrum_calc.compute(lfp) for ch, lfp in lfp_by_name.items()}
    fits    = FOOOFPowerLaw().fit_dict(spectra)

    spike_rates: Dict[str, float] = {}
    for name, wideband in raw_by_name.items():
        spikes = detect_mua_spikes(
            wideband, sample_rate,
            highpass_hz=MUA_HIGHPASS_HZ,
            threshold_rms=MUA_THRESHOLD_RMS,
            refractory_sec=MUA_REFRACTORY_SEC,
        )
        spike_rates[name] = len(spikes) / duration

    return spectra, fits, spike_rates, duration


def load_impedance(csv_path: str) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Parse an Intan impedance CSV (tab-separated).

    Returns (magnitude_ohms, phase_degrees), both keyed by A_NNN channel name.
    Handles UTF-8 BOM, whitespace in column names, and tab vs comma separators.
    """
    for sep in ('\t', ','):
        df = pd.read_csv(csv_path, sep=sep, encoding='utf-8-sig')
        if len(df.columns) > 2:
            break

    df.columns = [c.strip() for c in df.columns]

    ch_col = next(
        (c for c in df.columns if 'channel' in c.lower() and 'number' in c.lower()),
        df.columns[0],
    )
    imp_col = next(
        (c for c in df.columns if 'impedance' in c.lower() and 'magnitude' in c.lower()),
        None,
    )
    if imp_col is None:
        raise ValueError(
            f"Cannot find impedance magnitude column in {csv_path}.\n"
            f"Columns found: {list(df.columns)}"
        )
    phase_col = next(
        (c for c in df.columns if 'phase' in c.lower()),
        None,
    )

    magnitude: Dict[str, float] = {}
    phase:     Dict[str, float] = {}
    for _, row in df.iterrows():
        raw  = str(row[ch_col]).strip()
        name = re.sub(r'([A-Za-z])-(\d+)', r'\1_\2', raw)
        magnitude[name] = float(row[imp_col])
        if phase_col is not None:
            phase[name] = float(row[phase_col])
    return magnitude, phase


# ============================================================================
# DEPTH ASSIGNMENT & BINNING
# ============================================================================

def _probe_positions() -> Dict[str, int]:
    """Map channel name → probe position index (0=superficial, 31=deep)."""
    return {f"A_{ch_num:03d}": i for i, ch_num in enumerate(CHANNEL_ORDER)}


def _depth_mm(driven_depth_um: int, probe_pos: int, tip_start_mm: float) -> float:
    # Deepest channel (probe_pos=31) is TIP_TO_BOTTOM_CHANNEL_UM above the tip
    tip_corrected_um = driven_depth_um - TIP_TO_BOTTOM_CHANNEL_UM
    depth_um = tip_corrected_um + (probe_pos - (N_CHANNELS - 1)) * CHANNEL_SPACING_UM
    return round(tip_start_mm + depth_um / 1000.0, 4)


def bin_recordings(
    recordings_data: List[Tuple[int, Dict, Dict, Dict, Dict, Dict]],
    tip_start_mm: float,
) -> Tuple[np.ndarray, Dict, Dict, Dict, Dict, Dict]:
    """
    Combine per-recording data into depth bins.

    recordings_data: [(driven_depth_um, spectra, fits, spike_rates, magnitudes, phases), ...]

    Returns:
        bin_depths           : np.ndarray shape (n_bins,)  sorted depth values in mm
        binned_spectra       : Dict[bin_idx, (freqs, avg_power)]
        binned_fits          : Dict[bin_idx, PowerLawFit]  (averaged exponent/amplitude)
        binned_spike_rates   : Dict[bin_idx, float]
        binned_imp_raw       : Dict[(bin_idx, ch_name), float]  raw impedance magnitude
        binned_phase_raw     : Dict[(bin_idx, ch_name), float]  raw impedance phase (degrees)
    """
    probe_pos = _probe_positions()

    spec_acc:  Dict[float, List] = defaultdict(list)
    fits_acc:  Dict[float, List] = defaultdict(list)
    spike_acc: Dict[float, List] = defaultdict(list)
    imp_acc:   Dict[Tuple[float, str], List[float]] = defaultdict(list)
    phase_acc: Dict[Tuple[float, str], List[float]] = defaultdict(list)

    for driven_um, spectra, fits, spike_rates, magnitudes, phases in recordings_data:
        for ch_name, pos in probe_pos.items():
            if ch_name not in spectra:
                continue
            depth = _depth_mm(driven_um, pos, tip_start_mm)
            spec_acc[depth].append(spectra[ch_name])
            if ch_name in fits:
                fits_acc[depth].append(fits[ch_name])
            if ch_name in spike_rates:
                spike_acc[depth].append(spike_rates[ch_name])
            if ch_name in magnitudes:
                imp_acc[(depth, ch_name)].append(magnitudes[ch_name])
            if ch_name in phases:
                phase_acc[(depth, ch_name)].append(phases[ch_name])

    bin_depths = np.array(sorted(spec_acc.keys()))
    n_bins = len(bin_depths)

    binned_spectra:    Dict[int, Tuple]  = {}
    binned_fits:       Dict[int, PowerLawFit] = {}
    binned_spike_rates: Dict[int, float] = {}
    binned_imp_raw:    Dict[Tuple[int, str], float] = {}
    binned_phase_raw:  Dict[Tuple[int, str], float] = {}

    for idx, depth in enumerate(bin_depths):
        contribs = spec_acc[depth]
        freqs    = contribs[0][0]
        avg_pow  = np.mean([p for _, p in contribs], axis=0)
        binned_spectra[idx] = (freqs, avg_pow)

        fl = fits_acc[depth]
        if fl:
            exps = [f.exponent  for f in fl if not np.isnan(f.exponent)]
            amps = [f.amplitude for f in fl if not np.isnan(f.amplitude)]
            r2s  = [f.r_squared for f in fl]
            ref  = fl[0]
            binned_fits[idx] = PowerLawFit(
                exponent  = float(np.mean(exps)) if exps else np.nan,
                amplitude = float(np.mean(amps)) if amps else np.nan,
                peaks=ref.peaks,
                freqs=ref.freqs, power=ref.power,
                fit_power=ref.fit_power, aperiodic_power=ref.aperiodic_power,
                r_squared=float(np.mean(r2s)) if r2s else 0.0,
            )

        sl = spike_acc[depth]
        if sl:
            binned_spike_rates[idx] = float(np.mean(sl))

        for (dep, ch_name), imps in imp_acc.items():
            if dep == depth:
                binned_imp_raw[(idx, ch_name)] = float(np.mean(imps))

        for (dep, ch_name), phs in phase_acc.items():
            if dep == depth:
                binned_phase_raw[(idx, ch_name)] = float(np.mean(phs))

    return bin_depths, binned_spectra, binned_fits, binned_spike_rates, binned_imp_raw, binned_phase_raw


def smooth_spectra(
    binned_spectra: Dict[int, Tuple],
    n_bins: int,
    sigma_bins: float,
) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
    """
    Gaussian smoothing along the depth axis to reduce channel-to-channel
    noise from minor probe drift between recordings.

    sigma_bins: smoothing width in depth bins (1 bin ≈ 65 µm).
    """
    if sigma_bins <= 0:
        return binned_spectra
    freqs        = binned_spectra[0][0]
    power_matrix = np.array([binned_spectra[i][1] for i in range(n_bins)])
    smoothed     = gaussian_filter1d(power_matrix, sigma=sigma_bins, axis=0)
    return {i: (freqs, smoothed[i]) for i in range(n_bins)}


def smooth_scalars(
    values: Dict[int, float],
    n_bins: int,
    sigma_bins: float,
) -> Dict[int, float]:
    """Gaussian smoothing of per-bin scalar values along the depth axis."""
    if sigma_bins <= 0:
        return values
    arr = np.array([values.get(i, np.nan) for i in range(n_bins)])
    # Replace NaNs with nearest valid value before filtering so they don't
    # bleed into neighbouring bins, then restore NaN positions afterwards.
    nan_mask = np.isnan(arr)
    if nan_mask.all():
        return values
    # Simple forward-fill / back-fill for NaN positions
    filled = arr.copy()
    idx    = np.where(~nan_mask)[0]
    filled = np.interp(np.arange(n_bins), idx, arr[idx])
    smoothed = gaussian_filter1d(filled, sigma=sigma_bins)
    smoothed[nan_mask] = np.nan
    return {i: float(smoothed[i]) for i in range(n_bins)}


def smooth_fits(
    binned_fits: Dict[int, PowerLawFit],
    n_bins: int,
    sigma_bins: float,
) -> Dict[int, PowerLawFit]:
    """
    Smooth the scalar parameters (exponent, amplitude, r_squared) of the
    power-law fits along the depth axis.  Waveform arrays (freqs, power, etc.)
    are left unchanged since they are only used for per-channel diagnostics.
    """
    if sigma_bins <= 0:
        return binned_fits

    exps  = smooth_scalars({i: f.exponent   for i, f in binned_fits.items()}, n_bins, sigma_bins)
    amps  = smooth_scalars({i: f.amplitude  for i, f in binned_fits.items()}, n_bins, sigma_bins)
    r2s   = smooth_scalars({i: f.r_squared  for i, f in binned_fits.items()}, n_bins, sigma_bins)

    result: Dict[int, PowerLawFit] = {}
    for i, fit in binned_fits.items():
        result[i] = PowerLawFit(
            exponent  = exps.get(i, fit.exponent),
            amplitude = amps.get(i, fit.amplitude),
            peaks     = fit.peaks,
            freqs     = fit.freqs,
            power     = fit.power,
            fit_power = fit.fit_power,
            aperiodic_power = fit.aperiodic_power,
            r_squared = r2s.get(i, fit.r_squared),
        )
    return result


def compute_relative_power(
    binned_spectra: Dict[int, Tuple],
    n_bins: int,
) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
    """
    Normalise power across all depth bins so each frequency bin's max = 1.
    Noisy depth bins (mean power > 2 SD above mean) are interpolated from
    spatial neighbours before normalisation, mirroring RelativePowerSpectrum.
    """
    freqs        = binned_spectra[0][0]
    power_matrix = np.array([binned_spectra[i][1] for i in range(n_bins)])

    mean_per_bin = np.mean(power_matrix, axis=1)
    threshold    = np.mean(mean_per_bin) + 2.0 * np.std(mean_per_bin)
    noisy        = set(np.where(mean_per_bin > threshold)[0])
    if noisy:
        clean = power_matrix.copy()
        for idx in sorted(noisy):
            neighbors = []
            for off in range(1, n_bins):
                if idx - off >= 0 and idx - off not in noisy:
                    neighbors.append(idx - off); break
            for off in range(1, n_bins):
                if idx + off < n_bins and idx + off not in noisy:
                    neighbors.append(idx + off); break
            if neighbors:
                clean[idx] = np.mean(power_matrix[list(neighbors)], axis=0)
        power_matrix = clean

    max_per_freq = np.max(power_matrix, axis=0)
    max_per_freq[max_per_freq == 0] = 1.0
    normalized = power_matrix / max_per_freq

    return {i: (freqs, normalized[i]) for i in range(n_bins)}


def compute_relative_impedance(
    binned_imp_raw: Dict[Tuple[int, str], float],
) -> Dict[int, float]:
    """
    For each physical channel, compute its mean impedance across all recordings.
    relative_impedance = recorded_value / channel_mean.
    Returns the mean relative impedance per depth bin.
    """
    ch_vals: Dict[str, List[float]] = defaultdict(list)
    for (_, ch_name), imp in binned_imp_raw.items():
        ch_vals[ch_name].append(imp)
    ch_mean = {ch: float(np.mean(v)) for ch, v in ch_vals.items()}

    bin_rel: Dict[int, List[float]] = defaultdict(list)
    for (bin_idx, ch_name), imp in binned_imp_raw.items():
        mean = ch_mean.get(ch_name, imp)
        if mean > 0:
            bin_rel[bin_idx].append(imp / mean)

    return {idx: float(np.mean(vals)) for idx, vals in bin_rel.items() if vals}


def compute_relative_phase(
    binned_phase_raw: Dict[Tuple[int, str], float],
) -> Dict[int, float]:
    """
    For each physical channel, compute its mean phase across all recordings.
    relative_phase = recorded_phase / channel_mean_phase.
    Both are negative (capacitive), so the ratio is positive: >1 means more
    capacitive than that channel's baseline, <1 means less capacitive.
    Returns the mean relative phase per depth bin.
    """
    ch_vals: Dict[str, List[float]] = defaultdict(list)
    for (_, ch_name), ph in binned_phase_raw.items():
        ch_vals[ch_name].append(ph)
    ch_mean = {ch: float(np.mean(v)) for ch, v in ch_vals.items()}

    bin_rel: Dict[int, List[float]] = defaultdict(list)
    for (bin_idx, ch_name), ph in binned_phase_raw.items():
        mean = ch_mean.get(ch_name, ph)
        if mean != 0:
            bin_rel[bin_idx].append(ph / mean)

    return {idx: float(np.mean(vals)) for idx, vals in bin_rel.items() if vals}


# ============================================================================
# PLOTTING HELPERS
# ============================================================================

def _setup_depth_axis(
    ax: plt.Axes,
    bin_depths: np.ndarray,
    label: bool = True,
    max_labels: int = 25,
) -> None:
    """Y-axis: depth in mm, shallow at top, deep at bottom."""
    n = len(bin_depths)
    step = max(1, n // max_labels)
    ticks = np.arange(0, n, step)
    ax.set_yticks(ticks)
    if label:
        ax.set_yticklabels([f"{bin_depths[i]:.2f}" for i in ticks], fontsize=6)
        ax.set_ylabel("Depth under chamber (mm)")
    else:
        ax.set_yticklabels([])
    if not ax.yaxis_inverted():
        ax.invert_yaxis()


def plot_heatmap(
    normalized: Dict[int, Tuple],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    freqs, _ = normalized[0]
    mask = (freqs >= FREQ_RANGE[0]) & (freqs <= FREQ_RANGE[1])
    freqs_m = freqs[mask]
    mat = np.array([normalized[i][1][mask] for i in range(n_bins)])

    im = ax.imshow(
        mat, aspect='auto', origin='upper', interpolation='nearest',
        extent=[freqs_m[0], freqs_m[-1], n_bins - 0.5, -0.5],
        vmin=0, vmax=1,
    )
    plt.colorbar(im, ax=ax, label="Relative Power")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_title("Relative Power\n(full penetration)")
    _setup_depth_axis(ax, bin_depths, label=True)


def plot_band_power(
    normalized: Dict[int, Tuple],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    y = np.arange(n_bins)
    for band, (flo, fhi) in BANDS.items():
        powers = []
        for i in range(n_bins):
            freqs, power = normalized[i]
            mask = (freqs >= flo) & (freqs <= fhi)
            powers.append(float(np.mean(power[mask])) if np.any(mask) else np.nan)
        ax.plot(powers, y, 'o-', markersize=3, color=BAND_COLORS[band], label=band)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Relative Power")
    ax.set_title("Band Power")
    ax.legend(loc="lower right", fontsize=6)
    _setup_depth_axis(ax, bin_depths, label=False)


def _spectral_metrics(
    binned_fits: Dict[int, PowerLawFit],
    binned_spectra: Dict[int, Tuple],
    n_bins: int,
) -> Tuple[List, List, List]:
    """Compute gamma ratio and residual power per depth bin."""
    gamma_ratios, res_gamma, res_ab = [], [], []
    for i in range(n_bins):
        fit = binned_fits.get(i)
        freqs, power = binned_spectra[i]
        if fit is None or np.isnan(fit.exponent):
            gamma_ratios.append(np.nan)
            res_gamma.append(np.nan)
            res_ab.append(np.nan)
            continue
        gamma_ratios.append(LFPPowerLawSpectrumPlotter._gamma_alpha_beta_ratio(freqs, power))
        res_gamma.append(LFPPowerLawSpectrumPlotter._residual_in_band(freqs, power, fit, 50, 150))
        res_ab.append(LFPPowerLawSpectrumPlotter._residual_in_band(freqs, power, fit, 10, 30))
    return gamma_ratios, res_gamma, res_ab


def _draw(ax, values, y, bin_depths, xlabel, title, color, xlim=None):
    ax.plot(values, y, 'o-', markersize=3, color=color)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_title(title, fontsize=8)
    if xlim:
        ax.set_xlim(*xlim)
    _setup_depth_axis(ax, bin_depths, label=False)


def plot_power_law_panels(
    binned_fits: Dict[int, PowerLawFit],
    binned_spectra: Dict[int, Tuple],
    bin_depths: np.ndarray,
    axes: List[plt.Axes],
    cfg: dict,
) -> None:
    n_bins = len(bin_depths)
    y = np.arange(n_bins)
    fits = [binned_fits.get(i) for i in range(n_bins)]

    gamma_ratios, res_gamma, res_ab = _spectral_metrics(binned_fits, binned_spectra, n_bins)

    ax_idx = 0
    if cfg.get('show_exponent', True):
        _draw(axes[ax_idx], [f.exponent if f else np.nan for f in fits],
              y, bin_depths, "χ (exponent)", "1/f Exponent", "tab:blue"); ax_idx += 1
    if cfg.get('show_amplitude', True):
        _draw(axes[ax_idx], [f.amplitude if f else np.nan for f in fits],
              y, bin_depths, "A (amplitude)", "Amplitude", "tab:orange"); ax_idx += 1
    if cfg.get('show_r_squared', False):
        _draw(axes[ax_idx], [f.r_squared if f else 0.0 for f in fits],
              y, bin_depths, "R²", "Fit Quality", "tab:gray", xlim=(0, 1)); ax_idx += 1
    if cfg.get('show_gamma_ratio', False):
        _draw(axes[ax_idx], gamma_ratios,
              y, bin_depths, "γ / αβ", "Gamma/Alpha-Beta", "tab:purple"); ax_idx += 1
    if cfg.get('show_residual_gamma', False):
        _draw(axes[ax_idx], res_gamma,
              y, bin_depths, "Residual γ", "Residual Gamma", "tab:green"); ax_idx += 1
    if cfg.get('show_residual_alpha_beta', False):
        _draw(axes[ax_idx], res_ab,
              y, bin_depths, "Residual αβ", "Residual Alpha-Beta", "tab:brown"); ax_idx += 1


def plot_spike_rates(
    binned_spike_rates: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    y     = np.arange(n_bins)
    rates = [binned_spike_rates.get(i, np.nan) for i in range(n_bins)]
    ax.plot(rates, y, 'o-', markersize=3, color='tab:red')
    ax.set_xlabel("Spike Rate (Hz)")
    ax.set_title("Avg Spike Rate")
    _setup_depth_axis(ax, bin_depths, label=False)


def plot_relative_impedance(
    binned_rel_imp: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins  = len(bin_depths)
    y       = np.arange(n_bins)
    rel_imp = [binned_rel_imp.get(i, np.nan) for i in range(n_bins)]
    ax.plot(rel_imp, y, 'o-', markersize=3, color='tab:purple')
    ax.axvline(1.0, color='gray', linewidth=0.8, linestyle='--', alpha=0.6)
    ax.set_xlabel("Rel. Impedance\n(recording / ch. mean)")
    ax.set_title("Relative Impedance")
    _setup_depth_axis(ax, bin_depths, label=False)


def plot_relative_phase(
    binned_rel_phase: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins    = len(bin_depths)
    y         = np.arange(n_bins)
    rel_phase = [binned_rel_phase.get(i, np.nan) for i in range(n_bins)]
    ax.plot(rel_phase, y, 'o-', markersize=3, color='tab:cyan')
    ax.axvline(1.0, color='gray', linewidth=0.8, linestyle='--', alpha=0.6)
    ax.set_xlabel("Rel. Phase\n(recording / ch. mean)")
    ax.set_title("Relative Phase")
    _setup_depth_axis(ax, bin_depths, label=False)


# ============================================================================
# MAIN ANALYSIS CLASS
# ============================================================================

class PenetrationLFPAnalysis:
    def __init__(self, tip_start_mm: float, spatial_smooth_sigma: float = 1.5):
        self.tip_start_mm        = tip_start_mm
        self.spatial_smooth_sigma = spatial_smooth_sigma  # depth bins (1 bin = 65 µm)
        self.session_id, _ = read_session_id_from_db_name(ga_database)
        self.intan_path    = ga_intan_path

    def run(self) -> None:
        print(f"Scanning {self.intan_path}  (session {self.session_id}) ...")
        recordings = discover_recordings(self.intan_path, self.session_id)
        if not recordings:
            print("No idle recordings found."); return

        depths_str = [str(d) for d, _, _ in recordings]
        print(f"Found {len(recordings)} recording(s) at depths: {', '.join(depths_str)} µm")

        recordings_data = []
        for driven_um, rec_dir, csv_path in recordings:
            print(f"\n  depth {driven_um} µm  →  {os.path.basename(rec_dir)}")
            try:
                spectra, fits, spike_rates, duration = load_recording(rec_dir)
                if csv_path:
                    magnitudes, phases = load_impedance(csv_path)
                else:
                    magnitudes, phases = {}, {}
                    print(f"    Warning: no impedance CSV for depth {driven_um}")
                print(f"    {duration:.1f}s  |  {len(spectra)} ch  "
                      f"|  {len(magnitudes)} imp  |  {len(phases)} phase values")
                recordings_data.append((driven_um, spectra, fits, spike_rates, magnitudes, phases))
            except Exception as exc:
                print(f"    Error: {exc}"); continue

        if not recordings_data:
            print("No recordings loaded successfully."); return

        print(f"\nBinning {len(recordings_data)} recordings ...")
        bin_depths, b_spec, b_fits, b_spike, b_imp_raw, b_phase_raw = bin_recordings(
            recordings_data, self.tip_start_mm
        )
        n_bins = len(bin_depths)
        print(f"  {n_bins} depth bins  [{bin_depths[0]:.2f} – {bin_depths[-1]:.2f} mm]")

        sigma = self.spatial_smooth_sigma
        if sigma > 0:
            print(f"Applying spatial smoothing  (sigma = {sigma} bins = {sigma * CHANNEL_SPACING_UM:.0f} µm) ...")
            b_spec  = smooth_spectra(b_spec,  n_bins, sigma)
            b_fits  = smooth_fits(b_fits,   n_bins, sigma)
            b_spike = smooth_scalars(b_spike, n_bins, sigma)

        print("Computing penetration-wide relative power ...")
        normalized = compute_relative_power(b_spec, n_bins)

        print("Computing relative impedance and phase ...")
        b_rel_imp   = compute_relative_impedance(b_imp_raw)
        b_rel_phase = compute_relative_phase(b_phase_raw)
        if sigma > 0:
            if b_rel_imp:
                b_rel_imp   = smooth_scalars(b_rel_imp,   n_bins, sigma)
            if b_rel_phase:
                b_rel_phase = smooth_scalars(b_rel_phase, n_bins, sigma)

        print("Plotting ...")
        self._plot(bin_depths, normalized, b_spec, b_fits, b_spike, b_rel_imp, b_rel_phase)

    def _plot(self, bin_depths, normalized, b_spec, b_fits, b_spike, b_rel_imp, b_rel_phase):
        cfg  = POWER_LAW_PANELS
        n_pl = sum([
            cfg.get('show_exponent', True),
            cfg.get('show_amplitude', True),
            cfg.get('show_r_squared', False),
            cfg.get('show_gamma_ratio', False),
            cfg.get('show_residual_gamma', False),
            cfg.get('show_residual_alpha_beta', False),
        ])
        n_bins = len(bin_depths)

        # Layout: heatmap | band power | [power-law] | spike rate | impedance | phase
        n_total      = 1 + 1 + n_pl + 1 + 1 + 1
        width_ratios = [3, 1] + [1] * n_pl + [1, 1, 1]

        fig_h = max(8, min(20, n_bins * 0.15))
        fig, axes = plt.subplots(
            1, n_total,
            figsize=(3.5 * n_total, fig_h),
            gridspec_kw={'width_ratios': width_ratios},
            sharey=True,
        )

        plot_heatmap(normalized, bin_depths, axes[0])
        plot_band_power(normalized, bin_depths, axes[1])
        plot_power_law_panels(b_fits, b_spec, bin_depths, axes[2:2 + n_pl], cfg)
        plot_spike_rates(b_spike, bin_depths, axes[2 + n_pl])
        plot_relative_impedance(b_rel_imp, bin_depths, axes[2 + n_pl + 1])
        plot_relative_phase(b_rel_phase, bin_depths, axes[2 + n_pl + 2])

        # Lock y limits to the heatmap's extent so all panels align exactly
        axes[0].set_ylim(n_bins - 0.5, -0.5)

        sigma     = self.spatial_smooth_sigma
        smooth_str = f"  |  smooth σ={sigma}×65µm" if sigma > 0 else "  |  no smoothing"
        has_imp   = bool(b_rel_imp)
        fig.suptitle(
            f"Penetration LFP  |  {self.session_id}  |  "
            f"tip_start = {self.tip_start_mm:.1f} mm  |  "
            f"{len(bin_depths)} depth bins  "
            f"({bin_depths[0]:.2f} – {bin_depths[-1]:.2f} mm)"
            + smooth_str
            + ("" if has_imp else "  [no impedance data]"),
            fontsize=10,
        )
        plt.tight_layout()
        plt.show()
        savepath = f"/home/connorlab/Documents/plots/{self.session_id}/penetration_analysis.png"
        fig.savefig(savepath, dpi=300)


if __name__ == '__main__':
    tip   = float(input("Enter tip start depth (mm): ").strip())
    sigma_str = input("Spatial smoothing sigma in depth bins [default 1.5, 0 = off]: ").strip()
    sigma = float(sigma_str) if sigma_str else 1.5
    PenetrationLFPAnalysis(tip_start_mm=tip, spatial_smooth_sigma=sigma).run()

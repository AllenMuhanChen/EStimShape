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
from clat.util.connection import Connection

from lfp_spectrum import LFPSpectrum
from lfp_power_law import (
    FOOOFPowerLaw, LFPPowerLawSpectrumPlotter, PowerLawFit, OscillatorPeak,
)
from mua_detection import detect_mua_spikes
from spike_waveform_features import (
    highpass_filter, extract_spike_waveforms,
    compute_polarity_ratio, compute_mean_peak_count,
    compute_mean_trough_to_peak_ms, compute_mean_spike_amplitude,
)

from src.startup.context import ga_intan_path, ga_database
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup.startup_system import ExperimentManager

INTAN_SFTP_PREFIX = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape"

# ============================================================================
# CONFIGURATION
# ============================================================================

CHANNEL_SPACING_UM = 65       # µm between adjacent channels on probe

# Spike waveform feature parameters
PEAK_COUNT_PROMINENCE_FRACTION = 0.15  # prominence threshold as fraction of peak-to-peak (post-smoothing)
PEAK_COUNT_SMOOTH_MS           = 0.3   # Gaussian smooth sigma in ms before peak detection (filters sub-ms noise)
PEAK_COUNT_NEGATIVE_ONLY       = False  # if True, exclude positive-leading spikes from peak count mean
TROUGH_PEAK_SMOOTH_MS          = 0.1   # Gaussian smooth sigma in ms before trough-to-peak measurement
TROUGH_PEAK_NEGATIVE_ONLY      = True  # if True, exclude positive-leading spikes from trough-to-peak mean
SPIKE_AMPLITUDE_SMOOTH_MS      = 0.0   # smooth before amplitude measurement (0 = no smoothing, preserves true amplitude)
SPIKE_AMPLITUDE_NEGATIVE_ONLY  = False  # if True, exclude positive-leading spikes from amplitude mean

# Per-channel quality gating (applied in load_recording before binning)
BAD_CHANNEL_R2_THRESHOLD = 0.7   # exclude channels with FOOOF r² below this (artifact/noise spectrum)
BAD_CHANNEL_RMS_HI_FACTOR = 5.0  # exclude channels with LFP RMS > factor × median (saturated)
BAD_CHANNEL_RMS_LO_FACTOR = 0.1  # exclude channels with LFP RMS < factor × median (dead/disconnected)
CHANNEL_ORDER = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
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

# Band power/phase method: True=FOOOF-robust, False=legacy relative normalization
USE_FOOOF_BAND_POWERS = False   # False: use legacy compute_relative_power normalization
USE_ABSOLUTE_PHASE    = False   # False: use legacy compute_relative_phase normalization

# Local depth-wise LFP spectral-dissimilarity metric (narrow-sulcus / CSF detector).
# In a thin sulcus the electrode passes through CSF, an excellent conductor, so the
# relative-power spectrum barely changes over depth (the "blur" bands in the
# relative-power heat-map). This metric is low there and high in real tissue whose
# spectrum shifts bin-to-bin, giving the PCA a feature to separate sulcus from tissue.
SPECTRAL_DISSIM_WINDOW_MM = 0.25   # ± depth window over which neighbouring spectra are compared
SPECTRAL_DISSIM_METRIC    = "l1"   # 'l1' | 'l2' | 'corr'

# ---------------------------------------------------------------------------
# Per-metric spatial (depth) smoothing.
# ---------------------------------------------------------------------------
# Smoothing exists only to absorb depth jitter from slightly inconsistent probe
# positions across drives — it should be the *minimum* that keeps a metric
# well-behaved. Anything beyond that erases real structure (e.g. a thin sulcus
# gets smeared into its neighbours). Different metrics have different natural
# smoothness, so each gets its own σ (in depth bins; 1 bin ≈ CHANNEL_SPACING_UM).
#
#   * LFP-family metrics (band power, 1/f fit, spike rate, impedance, phase) are
#     already spatially smooth, so a small σ suffices.
#   * Spike-*waveform* metrics are per-spike estimates and much noisier, so they
#     need a larger σ to be stable.
#   * spectral_dissimilarity is a *difference* operator whose whole job is to
#     resolve narrow (~1 mm) sulci — it must stay sharp, so it gets the least
#     smoothing. Its σ is applied to the spectra the metric is computed from
#     (not an output smoothing), since that is what sets its depth resolution;
#     the ±window average already provides jitter robustness on top of that.
LFP_SMOOTH_SIGMA_BINS      = 1.5   # LFP-family metrics (naturally smooth)
WAVEFORM_SMOOTH_SIGMA_BINS = 3.0   # spike-waveform metrics (noisy per-spike estimates)
DISSIM_SMOOTH_SIGMA_BINS   = 0.5   # spectral dissimilarity — keep sharp so small sulci survive

DEFAULT_SMOOTH_SIGMA_BINS = {
    'lfp_spectra':            LFP_SMOOTH_SIGMA_BINS,   # heatmap + band powers (via relative power)
    'power_law':              LFP_SMOOTH_SIGMA_BINS,   # exponent, amplitude
    'spike_rate':             LFP_SMOOTH_SIGMA_BINS,
    'relative_impedance':     LFP_SMOOTH_SIGMA_BINS,
    'relative_phase':         LFP_SMOOTH_SIGMA_BINS,
    'polarity_ratio':         WAVEFORM_SMOOTH_SIGMA_BINS,
    'mean_peak_count':        WAVEFORM_SMOOTH_SIGMA_BINS,
    'trough_to_peak_ms':      WAVEFORM_SMOOTH_SIGMA_BINS,
    'mean_spike_amplitude':   WAVEFORM_SMOOTH_SIGMA_BINS,
    'spectral_dissimilarity': DISSIM_SMOOTH_SIGMA_BINS,
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
    from intan_lfp import (
        extract_lfp, CHANNEL_ORDER, POWER_LAW_PANELS,
        LFP_LOWPASS, LFP_TARGET_RATE,
        MUA_HIGHPASS_HZ, MUA_THRESHOLD_RMS, MUA_REFRACTORY_SEC,
    )

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
    spectra_all   = {ch: spectrum_calc.compute(lfp) for ch, lfp in lfp_by_name.items()}
    fits_all      = FOOOFPowerLaw().fit_dict(spectra_all)

    # ── Per-channel quality gate ─────────────────────────────────────────────
    channel_rms = {ch: float(np.sqrt(np.mean(lfp ** 2))) for ch, lfp in lfp_by_name.items()}
    median_rms  = float(np.median(list(channel_rms.values()))) if channel_rms else 1.0

    good_channels: set = set()
    n_rejected = 0
    for ch in lfp_by_name:
        fit = fits_all.get(ch)
        rms = channel_rms.get(ch, 0.0)
        r2_ok   = fit is not None and fit.r_squared >= BAD_CHANNEL_R2_THRESHOLD
        rms_ok  = (median_rms <= 0
                   or (rms <= BAD_CHANNEL_RMS_HI_FACTOR * median_rms
                       and rms >= BAD_CHANNEL_RMS_LO_FACTOR * median_rms))
        if r2_ok and rms_ok:
            good_channels.add(ch)
        else:
            n_rejected += 1
    if n_rejected:
        print(f"    Rejected {n_rejected}/{len(lfp_by_name)} channels "
              f"(r²<{BAD_CHANNEL_R2_THRESHOLD} or RMS outlier)")

    spectra = {ch: v for ch, v in spectra_all.items() if ch in good_channels}
    fits    = {ch: v for ch, v in fits_all.items()    if ch in good_channels}
    # ────────────────────────────────────────────────────────────────────────

    spike_rates:              Dict[str, float]          = {}
    spike_polarity_ratios:    Dict[str, Optional[float]] = {}
    spike_peak_counts:        Dict[str, Optional[float]] = {}
    spike_trough_to_peak_ms:  Dict[str, Optional[float]] = {}
    spike_amplitudes:         Dict[str, Optional[float]] = {}
    for name, wideband in raw_by_name.items():
        if name not in good_channels:
            continue
        spikes = detect_mua_spikes(
            wideband, sample_rate,
            highpass_hz=MUA_HIGHPASS_HZ,
            threshold_rms=MUA_THRESHOLD_RMS,
            refractory_sec=MUA_REFRACTORY_SEC,
        )
        spike_rates[name] = len(spikes) / duration

        filtered  = highpass_filter(wideband, sample_rate, MUA_HIGHPASS_HZ)
        waveforms = extract_spike_waveforms(filtered, spikes, sample_rate=sample_rate)
        spike_polarity_ratios[name]   = compute_polarity_ratio(waveforms)
        spike_peak_counts[name]       = compute_mean_peak_count(
            waveforms,
            prominence_fraction=PEAK_COUNT_PROMINENCE_FRACTION,
            smooth_ms=PEAK_COUNT_SMOOTH_MS,
            sample_rate=sample_rate,
            negative_only=PEAK_COUNT_NEGATIVE_ONLY,
        )
        spike_trough_to_peak_ms[name] = compute_mean_trough_to_peak_ms(
            waveforms,
            smooth_ms=TROUGH_PEAK_SMOOTH_MS,
            sample_rate=sample_rate,
            negative_only=TROUGH_PEAK_NEGATIVE_ONLY,
        )
        spike_amplitudes[name] = compute_mean_spike_amplitude(
            waveforms,
            smooth_ms=SPIKE_AMPLITUDE_SMOOTH_MS,
            sample_rate=sample_rate,
            negative_only=SPIKE_AMPLITUDE_NEGATIVE_ONLY,
        )

    return spectra, fits, spike_rates, spike_polarity_ratios, spike_peak_counts, spike_trough_to_peak_ms, spike_amplitudes, duration


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
    from intan_lfp import (
        extract_lfp, CHANNEL_ORDER, POWER_LAW_PANELS,
        LFP_LOWPASS, LFP_TARGET_RATE,
        MUA_HIGHPASS_HZ, MUA_THRESHOLD_RMS, MUA_REFRACTORY_SEC,
    )
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
) -> Tuple[np.ndarray, Dict, Dict, Dict, Dict, Dict, Dict, Dict, Dict, Dict]:
    """
    Combine per-recording data into depth bins.

    recordings_data: [(driven_depth_um, spectra, fits, spike_rates, spike_polarity_ratios,
                       spike_peak_counts, spike_trough_to_peak_ms, spike_amplitudes, magnitudes, phases), ...]

    Returns:
        bin_depths                : np.ndarray shape (n_bins,)  sorted depth values in mm
        binned_spectra            : Dict[bin_idx, (freqs, avg_power)]
        binned_fits               : Dict[bin_idx, PowerLawFit]  (averaged exponent/amplitude)
        binned_spike_rates        : Dict[bin_idx, float]
        binned_polarity_ratios    : Dict[bin_idx, float]
        binned_peak_counts        : Dict[bin_idx, float]
        binned_trough_to_peak_ms  : Dict[bin_idx, float]
        binned_spike_amplitudes   : Dict[bin_idx, float]
        binned_imp_raw            : Dict[(bin_idx, ch_name), float]  raw impedance magnitude
        binned_phase_raw          : Dict[(bin_idx, ch_name), float]  raw impedance phase (degrees)
    """
    probe_pos = _probe_positions()

    spec_acc:            Dict[float, List] = defaultdict(list)
    fits_acc:            Dict[float, List] = defaultdict(list)
    spike_acc:           Dict[float, List] = defaultdict(list)
    polarity_acc:        Dict[float, List] = defaultdict(list)
    peak_count_acc:      Dict[float, List] = defaultdict(list)
    trough_to_peak_acc:  Dict[float, List] = defaultdict(list)
    amplitude_acc:       Dict[float, List] = defaultdict(list)
    imp_acc:             Dict[Tuple[float, str], List[float]] = defaultdict(list)
    phase_acc:           Dict[Tuple[float, str], List[float]] = defaultdict(list)

    for driven_um, spectra, fits, spike_rates, spike_polarity_ratios, spike_peak_counts, spike_trough_to_peak_ms, spike_amplitudes, magnitudes, phases in recordings_data:
        for ch_name, pos in probe_pos.items():
            if ch_name not in spectra:
                continue
            depth = _depth_mm(driven_um, pos, tip_start_mm)
            spec_acc[depth].append(spectra[ch_name])
            if ch_name in fits:
                fits_acc[depth].append(fits[ch_name])
            if ch_name in spike_rates:
                spike_acc[depth].append(spike_rates[ch_name])
            ratio = spike_polarity_ratios.get(ch_name)
            if ratio is not None:
                polarity_acc[depth].append(ratio)
            pc = spike_peak_counts.get(ch_name)
            if pc is not None:
                peak_count_acc[depth].append(pc)
            ttp = spike_trough_to_peak_ms.get(ch_name)
            if ttp is not None:
                trough_to_peak_acc[depth].append(ttp)
            amp = spike_amplitudes.get(ch_name)
            if amp is not None:
                amplitude_acc[depth].append(amp)
            if ch_name in magnitudes:
                imp_acc[(depth, ch_name)].append(magnitudes[ch_name])
            if ch_name in phases:
                phase_acc[(depth, ch_name)].append(phases[ch_name])

    bin_depths = np.array(sorted(spec_acc.keys()))
    n_bins = len(bin_depths)

    binned_spectra:            Dict[int, Tuple]             = {}
    binned_fits:               Dict[int, PowerLawFit]       = {}
    binned_spike_rates:        Dict[int, float]             = {}
    binned_polarity_ratios:    Dict[int, float]             = {}
    binned_peak_counts:        Dict[int, float]             = {}
    binned_trough_to_peak_ms:  Dict[int, float]             = {}
    binned_spike_amplitudes:   Dict[int, float]             = {}
    binned_imp_raw:            Dict[Tuple[int, str], float] = {}
    binned_phase_raw:          Dict[Tuple[int, str], float] = {}

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

        pl = polarity_acc[depth]
        if pl:
            binned_polarity_ratios[idx] = float(np.mean(pl))

        pcl = peak_count_acc[depth]
        if pcl:
            binned_peak_counts[idx] = float(np.mean(pcl))

        ttpl = trough_to_peak_acc[depth]
        if ttpl:
            binned_trough_to_peak_ms[idx] = float(np.mean(ttpl))

        al = amplitude_acc[depth]
        if al:
            binned_spike_amplitudes[idx] = float(np.mean(al))

        for (dep, ch_name), imps in imp_acc.items():
            if dep == depth:
                binned_imp_raw[(idx, ch_name)] = float(np.mean(imps))

        for (dep, ch_name), phs in phase_acc.items():
            if dep == depth:
                binned_phase_raw[(idx, ch_name)] = float(np.mean(phs))

    return bin_depths, binned_spectra, binned_fits, binned_spike_rates, binned_polarity_ratios, binned_peak_counts, binned_trough_to_peak_ms, binned_spike_amplitudes, binned_imp_raw, binned_phase_raw


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


def compute_spectral_dissimilarity(
    normalized: Dict[int, Tuple],
    bin_depths: np.ndarray,
    n_bins: int,
    neighbor_window_mm: float = SPECTRAL_DISSIM_WINDOW_MM,
    freq_range: Tuple[float, float] = FREQ_RANGE,
    metric: str = SPECTRAL_DISSIM_METRIC,
) -> Dict[int, float]:
    """
    Per-depth-bin measure of how much the *relative* LFP power spectrum changes
    between a bin and its depth neighbours — a narrow-sulcus / CSF detector.

    Motivation
    ----------
    In a thin sulcus the electrode travels through CSF, an excellent conductor,
    so the local field potential is spatially smeared: the relative-power
    spectrum barely changes over ~1 mm of depth (the "blur" bands visible in the
    relative-power heat-map). Grey/white matter, by contrast, has locally
    varying LFP, so its spectrum shifts from bin to bin. Because a thin sulcus is
    still close to neural tissue, spikes persist there, so spike metrics alone
    mislabel it as tissue. This feature is *low* in sulcus and *high* in genuine
    tissue, giving the decomposition a signal it can use to separate the two.

    Definition
    ----------
    For each bin i, average the spectral distance between S_i (its relative-power
    spectrum, restricted to ``freq_range``) and each neighbour S_j within
    ±``neighbor_window_mm`` along depth (i itself excluded):

        metric='l1'   : mean_j  mean_f |S_i(f) - S_j(f)|            (default)
        metric='l2'   : mean_j  sqrt(mean_f (S_i(f) - S_j(f))^2)
        metric='corr' : mean_j  (1 - pearson_corr(S_i, S_j))

    Low value  -> spectrum is locally flat vs depth (sulcus / CSF blur).
    High value -> spectrum changes with depth (grey/white-matter structure).

    The mm window is converted to a bin half-width using the median bin spacing.
    Edge bins use whatever neighbours fall inside the window (clamped, never
    wrapped); a bin with no valid neighbour gets NaN.
    """
    freqs = normalized[0][0]
    mask  = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
    S = np.array([normalized[i][1][mask] for i in range(n_bins)])  # (n_bins, n_freqs)

    spacing_mm = float(np.median(np.diff(bin_depths))) if n_bins > 1 else 1.0
    half = max(1, int(round(neighbor_window_mm / max(spacing_mm, 1e-9))))

    out: Dict[int, float] = {}
    for i in range(n_bins):
        lo = max(0, i - half)
        hi = min(n_bins, i + half + 1)
        dists: List[float] = []
        for j in range(lo, hi):
            if j == i:
                continue
            diff = S[i] - S[j]
            if metric == "l1":
                dists.append(float(np.mean(np.abs(diff))))
            elif metric == "l2":
                dists.append(float(np.sqrt(np.mean(diff ** 2))))
            elif metric == "corr":
                if S[i].std() < 1e-12 or S[j].std() < 1e-12:
                    dists.append(1.0)
                else:
                    dists.append(1.0 - float(np.corrcoef(S[i], S[j])[0, 1]))
            else:
                raise ValueError(
                    f"Unknown metric {metric!r}; use 'l1', 'l2', or 'corr'.")
        out[i] = float(np.mean(dists)) if dists else np.nan
    return out


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


def compute_mean_phase(
    binned_phase_raw: Dict[Tuple[int, str], float],
) -> Dict[int, float]:
    """Mean absolute phase angle per depth bin (degrees). No per-channel normalization."""
    bin_vals: Dict[int, List[float]] = defaultdict(list)
    for (bin_idx, _ch_name), ph in binned_phase_raw.items():
        bin_vals[bin_idx].append(ph)
    return {idx: float(np.mean(vals)) for idx, vals in bin_vals.items() if vals}


# ============================================================================
# PLOTTING HELPERS
# ============================================================================

def _setup_depth_axis(
    ax: plt.Axes,
    bin_depths: np.ndarray,
    show_ylabel: bool = False,
    max_labels: int = 40,
) -> None:
    """Y-axis: depth in mm, shallow at top, deep at bottom.
    Tick mark at every bin; labels shown every ~max_labels-th bin."""
    n = len(bin_depths)
    step = max(1, n // max_labels)
    ax.set_yticks(np.arange(n))
    ax.set_yticklabels(
        [f"{bin_depths[i]:.2f}" if i % step == 0 else "" for i in range(n)],
        fontsize=6,
    )
    ax.tick_params(axis='y', which='major', length=4)
    # Override sharey tick-label suppression so every panel shows depths
    ax.tick_params(labelleft=True)
    if show_ylabel:
        ax.set_ylabel("Depth under chamber (mm)")
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
    _setup_depth_axis(ax, bin_depths, show_ylabel=True)


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
    _setup_depth_axis(ax, bin_depths)


def plot_fooof_band_power(
    b_spec: Dict[int, Tuple],
    b_fits: Dict[int, PowerLawFit],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    y = np.arange(n_bins)
    for band, (flo, fhi) in BANDS.items():
        powers = [_band_power_fooof(b_spec, b_fits, i, flo, fhi) for i in range(n_bins)]
        powers = [p if p is not None else np.nan for p in powers]
        ax.plot(powers, y, 'o-', markersize=3, color=BAND_COLORS[band], label=band)
    ax.axvline(0.0, color='gray', linewidth=0.8, linestyle='--', alpha=0.6)
    ax.set_xlabel("log\u2081\u2080(P / aperiodic)")
    ax.set_title("FOOOF Band Power")
    ax.legend(fontsize=6)
    _setup_depth_axis(ax, bin_depths)


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
    _setup_depth_axis(ax, bin_depths)


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
    _setup_depth_axis(ax, bin_depths)


def plot_polarity_ratio(
    binned_polarity_ratios: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins  = len(bin_depths)
    y       = np.arange(n_bins)
    ratios  = [binned_polarity_ratios.get(i, np.nan) for i in range(n_bins)]
    ax.plot(ratios, y, 'o-', markersize=3, color='tab:orange')
    ax.axvline(0.5, color='gray', linewidth=0.8, linestyle='--', alpha=0.6)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Fraction Positive\nSpikes")
    ax.set_title("Spike Polarity Ratio")
    _setup_depth_axis(ax, bin_depths)


def plot_mean_peak_count(
    binned_peak_counts: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    y      = np.arange(n_bins)
    counts = [binned_peak_counts.get(i, np.nan) for i in range(n_bins)]
    ax.plot(counts, y, 'o-', markersize=3, color='tab:brown')
    ax.set_xlabel("Mean Peak Count\n(neg. spikes only)")
    ax.set_title("Spike Peak Count")
    _setup_depth_axis(ax, bin_depths)


def plot_spike_amplitude(
    binned_spike_amplitudes: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    y      = np.arange(n_bins)
    vals   = [binned_spike_amplitudes.get(i, np.nan) for i in range(n_bins)]
    ax.plot(vals, y, 'o-', markersize=3, color='tab:pink')
    ax.set_xlabel("Amplitude (µV)")
    ax.set_title("Spike Amplitude")
    _setup_depth_axis(ax, bin_depths)


def plot_trough_to_peak_ms(
    binned_trough_to_peak_ms: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    y      = np.arange(n_bins)
    vals   = [binned_trough_to_peak_ms.get(i, np.nan) for i in range(n_bins)]
    ax.plot(vals, y, 'o-', markersize=3, color='tab:green')
    ax.set_xlabel("Trough-to-Peak (ms)")
    ax.set_title("T-P Duration")
    _setup_depth_axis(ax, bin_depths)


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
    _setup_depth_axis(ax, bin_depths)


def plot_spectral_dissimilarity(
    binned_dissim: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    y      = np.arange(n_bins)
    vals   = [binned_dissim.get(i, np.nan) for i in range(n_bins)]
    ax.plot(vals, y, 'o-', markersize=3, color='tab:olive')
    ax.set_xlabel("Spectral change\nvs neighbours")
    ax.set_title("LFP Spectral\nDissimilarity")
    _setup_depth_axis(ax, bin_depths)


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
    _setup_depth_axis(ax, bin_depths)


def plot_absolute_phase(
    binned_phase: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    n_bins = len(bin_depths)
    y      = np.arange(n_bins)
    phase  = [binned_phase.get(i, np.nan) for i in range(n_bins)]
    ax.plot(phase, y, 'o-', markersize=3, color='tab:cyan')
    ax.set_xlabel("Phase (\u00b0)")
    ax.set_title("Abs. Phase")
    _setup_depth_axis(ax, bin_depths)


def _compute_driven_per_bin(
    recordings_data: list,
    bin_depths: np.ndarray,
    tip_start_mm: float,
) -> Dict[int, float]:
    """
    For each depth-bin index, return the mean driven depth (µm) that
    produced data for that bin.  Useful for the right-side driven-depth axis.
    """
    probe_pos_map = _probe_positions()
    depth_to_idx  = {round(d, 4): i for i, d in enumerate(bin_depths)}
    driven_per_bin: Dict[int, List[float]] = defaultdict(list)

    for driven_um, spectra, *_ in recordings_data:
        for ch_name, pos in probe_pos_map.items():
            if ch_name not in spectra:
                continue
            depth_r = round(_depth_mm(driven_um, pos, tip_start_mm), 4)
            if depth_r in depth_to_idx:
                idx = depth_to_idx[depth_r]
                if driven_um not in driven_per_bin[idx]:
                    driven_per_bin[idx].append(float(driven_um))

    return {idx: float(np.mean(vals)) for idx, vals in driven_per_bin.items() if vals}


def plot_driven_depth(
    driven_per_bin: Dict[int, float],
    bin_depths: np.ndarray,
    ax: plt.Axes,
) -> None:
    """Step plot of driven depth (mm) vs depth-bin index."""
    n_bins = len(bin_depths)
    y      = np.arange(n_bins)
    driven_mm = [driven_per_bin.get(i, np.nan) / 1000.0 for i in range(n_bins)]
    ax.step(driven_mm, y, where='mid', color='tab:gray', linewidth=1.5)
    ax.plot(driven_mm, y, 'o', markersize=3, color='tab:gray')
    ax.set_xlabel("Driven depth (mm)")
    ax.set_title("Amount\nDriven")
    _setup_depth_axis(ax, bin_depths)




_PENETRATION_TIP_START_TABLE = "PenetrationTipStart"

_CREATE_PENETRATION_TIP_START_SQL = f"""
CREATE TABLE IF NOT EXISTS {_PENETRATION_TIP_START_TABLE} (
    session_id      VARCHAR(32)     NOT NULL,
    tip_start_mm    DOUBLE          NOT NULL,
    PRIMARY KEY (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_UPSERT_PENETRATION_TIP_START_SQL = f"""
INSERT INTO {_PENETRATION_TIP_START_TABLE} (session_id, tip_start_mm)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE tip_start_mm = VALUES(tip_start_mm)
"""


def save_tip_start(session_id: str, tip_start_mm: float) -> None:
    """Upsert the tip start depth for a session into allen_data_repository."""
    conn = Connection("allen_data_repository")
    conn.execute(_CREATE_PENETRATION_TIP_START_SQL)
    conn.execute(_UPSERT_PENETRATION_TIP_START_SQL, (session_id, tip_start_mm))


def get_tip_start(session_id: str) -> Optional[float]:
    """Return tip_start_mm for a session, or None if not found."""
    conn = Connection("allen_data_repository")
    conn.execute(_CREATE_PENETRATION_TIP_START_SQL)
    conn.execute(
        f"SELECT tip_start_mm FROM {_PENETRATION_TIP_START_TABLE} WHERE session_id = %s",
        (session_id,),
    )
    rows = conn.fetch_all()
    return float(rows[0][0]) if rows else None


_PENETRATION_METRICS_TABLE = "PenetrationMetrics"

_CREATE_PENETRATION_METRICS_SQL = f"""
CREATE TABLE IF NOT EXISTS {_PENETRATION_METRICS_TABLE} (
    session_id                  VARCHAR(32)     NOT NULL,
    depth_under_chamber_mm      DOUBLE          NOT NULL,
    band_power_delta_theta      DOUBLE          DEFAULT NULL,
    band_power_alpha_beta       DOUBLE          DEFAULT NULL,
    band_power_gamma            DOUBLE          DEFAULT NULL,
    exponent                    DOUBLE          DEFAULT NULL,
    amplitude                   DOUBLE          DEFAULT NULL,
    r_squared                   DOUBLE          DEFAULT NULL,
    spike_rate_hz               DOUBLE          DEFAULT NULL,
    polarity_ratio              DOUBLE          DEFAULT NULL,
    mean_peak_count             DOUBLE          DEFAULT NULL,
    trough_to_peak_ms           DOUBLE          DEFAULT NULL,
    mean_spike_amplitude        DOUBLE          DEFAULT NULL,
    relative_impedance          DOUBLE          DEFAULT NULL,
    relative_phase              DOUBLE          DEFAULT NULL,
    lfp_spectral_dissimilarity  DOUBLE          DEFAULT NULL,
    PRIMARY KEY (session_id, depth_under_chamber_mm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_UPSERT_PENETRATION_METRICS_SQL = f"""
INSERT INTO {_PENETRATION_METRICS_TABLE}
    (session_id, depth_under_chamber_mm,
     band_power_delta_theta, band_power_alpha_beta, band_power_gamma,
     exponent, amplitude, r_squared,
     spike_rate_hz, polarity_ratio, mean_peak_count, trough_to_peak_ms, mean_spike_amplitude, relative_impedance, relative_phase,
     lfp_spectral_dissimilarity)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    band_power_delta_theta  = VALUES(band_power_delta_theta),
    band_power_alpha_beta   = VALUES(band_power_alpha_beta),
    band_power_gamma        = VALUES(band_power_gamma),
    exponent                = VALUES(exponent),
    amplitude               = VALUES(amplitude),
    r_squared               = VALUES(r_squared),
    spike_rate_hz           = VALUES(spike_rate_hz),
    polarity_ratio          = VALUES(polarity_ratio),
    mean_peak_count         = VALUES(mean_peak_count),
    trough_to_peak_ms       = VALUES(trough_to_peak_ms),
    mean_spike_amplitude    = VALUES(mean_spike_amplitude),
    relative_impedance      = VALUES(relative_impedance),
    relative_phase          = VALUES(relative_phase),
    lfp_spectral_dissimilarity = VALUES(lfp_spectral_dissimilarity)
"""


def _ensure_column(conn: Connection, column: str, col_type: str = "DOUBLE DEFAULT NULL") -> None:
    """Add column to PenetrationMetrics if it does not already exist."""
    conn.execute(f"DESCRIBE {_PENETRATION_METRICS_TABLE}")
    existing = {row[0] for row in conn.fetch_all()}
    if column not in existing:
        conn.execute(
            f"ALTER TABLE {_PENETRATION_METRICS_TABLE} ADD COLUMN {column} {col_type}"
        )


def _band_power_at_bin(normalized: Dict[int, Tuple], bin_idx: int, flo: float, fhi: float) -> Optional[float]:
    if bin_idx not in normalized:
        return None
    freqs, power = normalized[bin_idx]
    mask = (freqs >= flo) & (freqs <= fhi)
    return float(np.mean(power[mask])) if np.any(mask) else None


def _band_power_fooof(
    b_spec: Dict[int, Tuple],
    b_fits: Dict[int, PowerLawFit],
    bin_idx: int,
    flo: float,
    fhi: float,
) -> Optional[float]:
    """
    Mean log10(P(f) / aperiodic(f)) for f in [flo, fhi].
    Uses smoothed per-bin spectrum and fit parameters.
    Returns None if data missing or power <= 0.
    """
    if bin_idx not in b_spec or bin_idx not in b_fits:
        return None
    freqs, power = b_spec[bin_idx]
    fit = b_fits[bin_idx]
    mask = (freqs >= flo) & (freqs <= fhi)
    if not np.any(mask):
        return None
    power_band = power[mask]
    freq_band  = freqs[mask]
    if np.any(power_band <= 0) or fit.amplitude <= 0:
        return None
    aperiodic = fit.amplitude * (freq_band ** fit.exponent)
    return float(np.mean(np.log10(power_band) - np.log10(aperiodic)))


def save_to_repository(
    session_id: str,
    bin_depths: np.ndarray,
    normalized: Dict[int, Tuple],
    binned_fits: Dict[int, PowerLawFit],
    binned_spike_rates: Dict[int, float],
    binned_polarity_ratios: Dict[int, float],
    binned_peak_counts: Dict[int, float],
    binned_trough_to_peak_ms: Dict[int, float],
    binned_spike_amplitudes: Dict[int, float],
    binned_rel_imp: Dict[int, float],
    binned_phase: Dict[int, float],
    binned_spectra: Optional[Dict[int, Tuple]] = None,
    binned_spectral_dissim: Optional[Dict[int, float]] = None,
) -> None:
    """
    Upsert all per-depth-bin penetration metrics into allen_data_repository.
    Creates the PenetrationMetrics table if it doesn't exist.
    Band powers use FOOOF-based method when USE_FOOOF_BAND_POWERS=True and binned_spectra provided.
    """
    conn = Connection("allen_data_repository")

    conn.execute(_CREATE_PENETRATION_METRICS_SQL)
    _ensure_column(conn, 'polarity_ratio')
    _ensure_column(conn, 'mean_peak_count')
    _ensure_column(conn, 'trough_to_peak_ms')
    _ensure_column(conn, 'mean_spike_amplitude')
    _ensure_column(conn, 'lfp_spectral_dissimilarity')
    print(f"Table '{_PENETRATION_METRICS_TABLE}' ready.")

    n_inserted = 0
    for idx, depth_mm in enumerate(bin_depths):
        fit = binned_fits.get(idx)

        if USE_FOOOF_BAND_POWERS and binned_spectra is not None:
            bp_dt = _band_power_fooof(binned_spectra, binned_fits, idx, *BANDS["delta-theta"])
            bp_ab = _band_power_fooof(binned_spectra, binned_fits, idx, *BANDS["alpha-beta"])
            bp_g  = _band_power_fooof(binned_spectra, binned_fits, idx, *BANDS["gamma"])
        else:
            bp_dt = _band_power_at_bin(normalized, idx, *BANDS["delta-theta"])
            bp_ab = _band_power_at_bin(normalized, idx, *BANDS["alpha-beta"])
            bp_g  = _band_power_at_bin(normalized, idx, *BANDS["gamma"])

        row = (
            session_id,
            float(depth_mm),
            bp_dt,
            bp_ab,
            bp_g,
            float(fit.exponent)  if fit and not np.isnan(fit.exponent)  else None,
            float(fit.amplitude) if fit and not np.isnan(fit.amplitude) else None,
            float(fit.r_squared) if fit else None,
            binned_spike_rates.get(idx),
            binned_polarity_ratios.get(idx),
            binned_peak_counts.get(idx),
            binned_trough_to_peak_ms.get(idx),
            binned_spike_amplitudes.get(idx),
            binned_rel_imp.get(idx),
            binned_phase.get(idx),
            binned_spectral_dissim.get(idx) if binned_spectral_dissim else None,
        )
        conn.execute(_UPSERT_PENETRATION_METRICS_SQL, row)
        n_inserted += 1

    print(f"Saved {n_inserted} depth-bin rows to {_PENETRATION_METRICS_TABLE} "
          f"(session {session_id}).")


# ============================================================================
# MAIN ANALYSIS CLASS
# ============================================================================

class PenetrationLFPAnalysis:
    def __init__(self, session_id: str, intan_path: str,
                 spatial_smooth_sigma: float = LFP_SMOOTH_SIGMA_BINS,
                 waveform_smooth_sigma: float = WAVEFORM_SMOOTH_SIGMA_BINS,
                 smooth_sigma_bins: Optional[dict] = None):
        self.session_id            = session_id
        self.intan_path            = intan_path
        # tip_start_mm is never defaulted: it is read from the
        # PenetrationTipStart table in allen_data_repository inside run().
        self.tip_start_mm          = None
        self.spatial_smooth_sigma  = spatial_smooth_sigma
        self.waveform_smooth_sigma = waveform_smooth_sigma  # larger sigma for noisy spike metrics

        # Per-metric smoothing σ (depth bins). Start from the module defaults,
        # let the two legacy sigmas re-seed their families (so old call sites and
        # tuning by family still work), then apply any explicit per-metric
        # overrides passed in via smooth_sigma_bins.
        self.smooth_sigma_bins = dict(DEFAULT_SMOOTH_SIGMA_BINS)
        for k in ('lfp_spectra', 'power_law', 'spike_rate',
                  'relative_impedance', 'relative_phase'):
            self.smooth_sigma_bins[k] = spatial_smooth_sigma
        for k in ('polarity_ratio', 'mean_peak_count',
                  'trough_to_peak_ms', 'mean_spike_amplitude'):
            self.smooth_sigma_bins[k] = waveform_smooth_sigma
        if smooth_sigma_bins:
            unknown = [k for k in smooth_sigma_bins if k not in self.smooth_sigma_bins]
            if unknown:
                print(f"  WARNING: smooth_sigma_bins has unknown metric keys "
                      f"(ignored): {unknown}. Valid keys: "
                      f"{sorted(self.smooth_sigma_bins)}")
            self.smooth_sigma_bins.update(
                {k: v for k, v in smooth_sigma_bins.items()
                 if k in self.smooth_sigma_bins})

    def _sigma(self, metric_key: str) -> float:
        """Smoothing σ (depth bins) for a metric; falls back to the LFP default."""
        return self.smooth_sigma_bins.get(metric_key, self.spatial_smooth_sigma)

    def run(self) -> None:

        # Tip start must come from the database, never a default. If this
        # session has no entry, skip it rather than guessing a value.
        self.tip_start_mm = get_tip_start(self.session_id)
        if self.tip_start_mm is None:
            print(f"No tip start found in {_PENETRATION_TIP_START_TABLE} for "
                  f"session {self.session_id}; skipping.")
            return

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
                spectra, fits, spike_rates, spike_polarity_ratios, spike_peak_counts, spike_trough_to_peak_ms, spike_amplitudes, duration = load_recording(rec_dir)
                if csv_path:
                    magnitudes, phases = load_impedance(csv_path)
                else:
                    magnitudes, phases = {}, {}
                    print(f"    Warning: no impedance CSV for depth {driven_um}")
                print(f"    {duration:.1f}s  |  {len(spectra)} ch  "
                      f"|  {len(magnitudes)} imp  |  {len(phases)} phase values")
                recordings_data.append((driven_um, spectra, fits, spike_rates, spike_polarity_ratios, spike_peak_counts, spike_trough_to_peak_ms, spike_amplitudes, magnitudes, phases))
            except Exception as exc:
                print(f"    Error: {exc}"); continue

        if not recordings_data:
            print("No recordings loaded successfully."); return

        print(f"\nBinning {len(recordings_data)} recordings ...")
        bin_depths, b_spec, b_fits, b_spike, b_polarity, b_peak_count, b_ttp, b_amp, b_imp_raw, b_phase_raw = bin_recordings(
            recordings_data, self.tip_start_mm
        )
        n_bins = len(bin_depths)
        print(f"  {n_bins} depth bins  [{bin_depths[0]:.2f} – {bin_depths[-1]:.2f} mm]")

        # Per-metric smoothing (σ in depth bins). smooth_* treat σ<=0 as no-op.
        # b_spec_raw is kept unsmoothed so metrics that want a different σ than
        # the display spectra (e.g. spectral dissimilarity) can re-smooth it.
        b_spec_raw = b_spec
        sig = self.smooth_sigma_bins
        print("Applying per-metric spatial smoothing (σ, depth bins): "
              + ", ".join(f"{k}={sig[k]}" for k in sorted(sig)))
        b_spec  = smooth_spectra(b_spec_raw, n_bins, self._sigma('lfp_spectra'))
        b_fits  = smooth_fits(b_fits,        n_bins, self._sigma('power_law'))
        b_spike = smooth_scalars(b_spike,    n_bins, self._sigma('spike_rate'))
        # Spike waveform metrics are estimated from individual spikes → noisier → larger σ
        b_polarity   = smooth_scalars(b_polarity,   n_bins, self._sigma('polarity_ratio'))
        b_peak_count = smooth_scalars(b_peak_count, n_bins, self._sigma('mean_peak_count'))
        b_ttp        = smooth_scalars(b_ttp,        n_bins, self._sigma('trough_to_peak_ms'))
        b_amp        = smooth_scalars(b_amp,        n_bins, self._sigma('mean_spike_amplitude'))

        print("Computing penetration-wide relative power ...")
        normalized = compute_relative_power(b_spec, n_bins)

        print("Computing LFP spectral dissimilarity (sulcus detector) ...")
        # Compute the dissimilarity from spectra smoothed at its *own* (lighter)
        # σ so aggressive display smoothing doesn't wipe out narrow sulci. Reuse
        # the display relative power when the σ happens to match.
        dissim_sigma = self._sigma('spectral_dissimilarity')
        if dissim_sigma == self._sigma('lfp_spectra'):
            normalized_dissim = normalized
        else:
            normalized_dissim = compute_relative_power(
                smooth_spectra(b_spec_raw, n_bins, dissim_sigma), n_bins)
        b_spectral_dissim = compute_spectral_dissimilarity(
            normalized_dissim, bin_depths, n_bins)

        print("Computing relative impedance and phase ...")
        b_rel_imp   = compute_relative_impedance(b_imp_raw)
        b_rel_phase = compute_relative_phase(b_phase_raw)
        b_phase_save = compute_mean_phase(b_phase_raw) if USE_ABSOLUTE_PHASE else b_rel_phase
        if b_rel_imp:
            b_rel_imp    = smooth_scalars(b_rel_imp,    n_bins, self._sigma('relative_impedance'))
        if b_rel_phase:
            b_rel_phase  = smooth_scalars(b_rel_phase,  n_bins, self._sigma('relative_phase'))
        if USE_ABSOLUTE_PHASE and b_phase_save:
            b_phase_save = smooth_scalars(b_phase_save, n_bins, self._sigma('relative_phase'))

        driven_ums      = [d for d, *_ in recordings_data]
        driven_analyzed = [d for d, *_ in recordings]
        b_driven        = _compute_driven_per_bin(recordings_data, bin_depths, self.tip_start_mm)

        print("Plotting ...")
        self._plot(
            bin_depths, normalized, b_spec, b_fits, b_spike, b_polarity,
            b_peak_count, b_ttp, b_amp, b_rel_imp, b_phase_save,
            b_spectral_dissim=b_spectral_dissim,
            b_driven=b_driven,
            driven_ums_found=sorted(driven_analyzed),
            driven_ums_used=sorted(driven_ums),
        )

        print("Saving metrics to allen_data_repository ...")
        try:
            # save_tip_start(self.session_id, self.tip_start_mm)
            save_to_repository(
                self.session_id, bin_depths, normalized,
                b_fits, b_spike, b_polarity, b_peak_count, b_ttp, b_amp,
                b_rel_imp, b_phase_save, binned_spectra=b_spec,
                binned_spectral_dissim=b_spectral_dissim,
            )
        except Exception as exc:
            print(f"  Warning: could not save to repository: {exc}")

    def _plot(self, bin_depths, normalized, b_spec, b_fits, b_spike, b_polarity,
              b_peak_count, b_ttp, b_amp, b_rel_imp, b_phase,
              b_spectral_dissim=None,
              b_driven=None, driven_ums_found=None, driven_ums_used=None):
        from intan_lfp import (
            extract_lfp, CHANNEL_ORDER, POWER_LAW_PANELS,
            LFP_LOWPASS, LFP_TARGET_RATE,
            MUA_HIGHPASS_HZ, MUA_THRESHOLD_RMS, MUA_REFRACTORY_SEC,
        )
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

        # Layout: heatmap | band power | [power-law] | spike rate | polarity | peak count | T-P duration | amplitude | impedance | phase | driven | spectral dissimilarity
        n_total      = 1 + 1 + n_pl + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1
        width_ratios = [3, 1] + [1] * n_pl + [1, 1, 1, 1, 1, 1, 1, 1, 1]

        fig_h = max(8, min(20, n_bins * 0.15))
        fig, axes = plt.subplots(
            1, n_total,
            figsize=(3.5 * n_total, fig_h),
            gridspec_kw={'width_ratios': width_ratios},
            sharey=True,
        )

        plot_heatmap(normalized, bin_depths, axes[0])
        if USE_FOOOF_BAND_POWERS:
            plot_fooof_band_power(b_spec, b_fits, bin_depths, axes[1])
        else:
            plot_band_power(normalized, bin_depths, axes[1])
        plot_power_law_panels(b_fits, b_spec, bin_depths, axes[2:2 + n_pl], cfg)
        plot_spike_rates(b_spike, bin_depths, axes[2 + n_pl])
        plot_polarity_ratio(b_polarity, bin_depths, axes[2 + n_pl + 1])
        plot_mean_peak_count(b_peak_count, bin_depths, axes[2 + n_pl + 2])
        plot_trough_to_peak_ms(b_ttp, bin_depths, axes[2 + n_pl + 3])
        plot_spike_amplitude(b_amp, bin_depths, axes[2 + n_pl + 4])
        plot_relative_impedance(b_rel_imp, bin_depths, axes[2 + n_pl + 5])
        if USE_ABSOLUTE_PHASE:
            plot_absolute_phase(b_phase, bin_depths, axes[2 + n_pl + 6])
        else:
            plot_relative_phase(b_phase, bin_depths, axes[2 + n_pl + 6])
        plot_driven_depth(b_driven or {}, bin_depths, axes[2 + n_pl + 7])
        plot_spectral_dissimilarity(b_spectral_dissim or {}, bin_depths, axes[2 + n_pl + 8])

        # Lock y limits to the heatmap's extent so all panels align exactly
        axes[0].set_ylim(n_bins - 0.5, -0.5)

        smooth_str = (f"  |  smooth σ (bins): lfp={self._sigma('lfp_spectra')}, "
                      f"wave={self._sigma('mean_spike_amplitude')}, "
                      f"dissim={self._sigma('spectral_dissimilarity')}")
        has_imp   = bool(b_rel_imp)

        driven_found = driven_ums_found or []
        driven_used  = driven_ums_used  or []
        if driven_found:
            driven_info = (f"  |  driven {min(driven_found)/1000:.1f}–{max(driven_found)/1000:.1f} mm"
                           f" ({len(driven_found)} found, {len(driven_used)} analyzed)")
        else:
            driven_info = ""

        fig.suptitle(
            f"Penetration LFP  |  {self.session_id}  |  "
            f"tip_start = {self.tip_start_mm:.1f} mm  |  "
            f"{len(bin_depths)} depth bins  "
            f"({bin_depths[0]:.2f} – {bin_depths[-1]:.2f} mm)"
            + driven_info
            + smooth_str
            + ("" if has_imp else "  [no impedance data]"),
            fontsize=10,
        )
        plt.tight_layout()
        plt.show()
        savepath = f"/home/connorlab/Documents/plots/{self.session_id}/penetration_analysis.png"
        fig.savefig(savepath, dpi=300)
        savepath = f"/home/connorlab/Documents/penetration_plots/{self.session_id}.png"
        fig.savefig(savepath, dpi=300)

def all_existing_session_ids():
    """Every session_id already present in EStimShapeTrials, in DB order."""
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM Penetrations ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]
if __name__ == '__main__':
    # Tip start for each session is read from the PenetrationTipStart table in
    # allen_data_repository inside run() — never hardcoded here. Sessions without
    # a tip start entry are skipped.
    session_ids = all_existing_session_ids()

    for session_id in session_ids:
        db_name    = f"allen_ga_exp_{session_id}"
        intan_path = f"{INTAN_SFTP_PREFIX}/{db_name}"
        PenetrationLFPAnalysis(session_id=session_id, intan_path=intan_path).run()

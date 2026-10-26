"""
Laminar markers from one session's GA recording at the final probe position.

Pure numpy, no database: laminar_profiles.py feeds it LFP and saves the result,
the calling GUI reads it back.

Probe geometry (same as penetration_lfp_analysis.py / import_penetration.py):
    CHANNEL_ORDER[0]  = most superficial channel, CHANNEL_ORDER[31] = deepest
    deepest channel sits TIP_TO_BOTTOM_CHANNEL_UM above the tip, 65 µm spacing
    depth under chamber (mm) = tip_mm - (600 + (31 - pos) * 65) / 1000
    (tip_mm = tip distance from the top of the chamber, as in the MRI viewer; the same
    depth coordinate as PenetrationMetrics.depth_under_chamber_mm)

CSD (Nicholson & Freeman 1975, 1D):
    phi    = trial-averaged LFP at stimulus onset, baseline-subtracted, channels in
             probe order, noisy channels replaced by their neighbours' mean
    smooth = 3-point Hamming filter across depth (0.23, 0.54, 0.23; Ulbert et al. 2001)
    CSD    = -(phi[z+h] - 2 phi[z] + phi[z-h]) / h^2, h = 0.065 mm, end channels
             duplicated (Vaknin et al. 1988) so the CSD has all 32 channels.
             Conductivity is left out, so units are µV/mm^2. Negative = sink.
    Suggested granular (L4) channel = the strongest sink in SINK_WINDOW_MS after onset.

Spectrolaminar motif (Mendoza-Halliday et al. 2024):
    relative power = power at each frequency divided by its max across channels
    (RelativePowerSpectrum), averaged within the alpha-beta and gamma bands.
    Gamma is highest in superficial layers, alpha-beta in deep ones; the depth where
    (gamma - alpha_beta) crosses from + to - going deeper is near L4.
"""

import re
from typing import Dict, List, Optional, Sequence

import numpy as np

CHANNEL_ORDER = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
N_CHANNELS = len(CHANNEL_ORDER)
CHANNEL_SPACING_UM = 65
TIP_TO_BOTTOM_CHANNEL_UM = 600

LAMINAR_CLASSES = ['superficial', 'middle', 'deep', 'wm', 'sulcus', 'unsure']
CLASS_LABELS = {'superficial': 'Superficial', 'middle': 'Middle (L4)', 'deep': 'Deep',
                'wm': 'White matter', 'sulcus': 'Sulcus / out', 'unsure': 'Unsure'}
CLASS_COLORS = {'superficial': '#e8a33d', 'middle': '#c0392b', 'deep': '#5b3a8c',
                'wm': '#bdbdbd', 'sulcus': '#3a87c8', 'unsure': '#ffffff'}

_CH_RE = re.compile(r'[A-Za-z][-_]?0*(\d+)$')


def channel_number(key) -> Optional[int]:
    """'A-007', 'A_007', 'A007', Channel.A_007 -> 7."""
    m = _CH_RE.search(str(key).strip())
    return int(m.group(1)) if m else None


def channel_name(ch: int) -> str:
    return f"A-{ch:03d}"


def probe_position(ch: int) -> int:
    return CHANNEL_ORDER.index(ch)


def channel_depth_mm(probe_pos, tip_mm: float):
    """Depth under chamber (mm) of a probe position (0 = top) given the tip distance.
    Same offsets as the MRI viewer's channel correction (viewer_trajectory._channel_corrected_dist)."""
    pos = np.asarray(probe_pos, dtype=float)
    return tip_mm - (TIP_TO_BOTTOM_CHANNEL_UM + ((N_CHANNELS - 1) - pos) * CHANNEL_SPACING_UM) / 1000.0


def tip_from_corrected(dist_mm: float, channel: int) -> float:
    """Inverse of the viewer's channel correction: tip distance from a channel's distance."""
    return dist_mm - float(channel_depth_mm(CHANNEL_ORDER.index(channel), 0.0))


# ─────────────────────────────────────────────────────────────────────────────
#  Evoked LFP + CSD
# ─────────────────────────────────────────────────────────────────────────────

def evoked_matrix(trials: Sequence[Dict[int, np.ndarray]], sample_rate: float,
                  pre_s: float, post_s: float, baseline_s: float = 0.1) -> np.ndarray:
    """Trial-averaged LFP (channels in probe order x time), onset at pre_s.

    trials: one dict per trial, channel number -> LFP that starts pre_s before onset.
    Each trial is baseline-subtracted (mean of the last baseline_s before onset).
    """
    n_pre = int(round(pre_s * sample_rate))
    n_post = int(round(post_s * sample_rate))
    n_base = max(1, int(round(baseline_s * sample_rate)))
    total = np.zeros((N_CHANNELS, n_pre + n_post))
    count = np.zeros(N_CHANNELS)
    for trial in trials:
        for pos, ch in enumerate(CHANNEL_ORDER):
            x = trial.get(ch)
            if x is None or len(x) < n_pre + n_post:
                continue
            seg = np.asarray(x[:n_pre + n_post], dtype=float)
            total[pos] += seg - seg[n_pre - n_base:n_pre].mean()
            count[pos] += 1
    with np.errstate(invalid='ignore', divide='ignore'):
        out = total / count[:, None]
    out[count == 0] = np.nan
    return out


def interpolate_channels(matrix: np.ndarray, bad_positions: Sequence[int]) -> np.ndarray:
    """Replace rows (probe positions) with the mean of the nearest good row above and below."""
    out = matrix.copy()
    bad = set(int(p) for p in bad_positions) | {i for i in range(len(matrix)) if np.all(np.isnan(matrix[i]))}
    good = [i for i in range(len(matrix)) if i not in bad]
    if not good:
        return out
    for i in bad:
        above = [g for g in good if g < i]
        below = [g for g in good if g > i]
        nb = ([above[-1]] if above else []) + ([below[0]] if below else [])
        out[i] = np.mean(matrix[nb], axis=0)
    return out


def compute_csd(phi: np.ndarray, spacing_mm: float = CHANNEL_SPACING_UM / 1000.0,
                hamming: bool = True) -> np.ndarray:
    """1D CSD (µV/mm^2, negative = sink) with Vaknin end padding and optional 3-point Hamming smoothing."""
    p = np.vstack([phi[:1], phi, phi[-1:]])
    if hamming:
        p = np.vstack([p[:1], 0.23 * p[:-2] + 0.54 * p[1:-1] + 0.23 * p[2:], p[-1:]])
    return -(p[2:] - 2 * p[1:-1] + p[:-2]) / spacing_mm ** 2


def strongest_sink(csd: np.ndarray, times_ms: np.ndarray, window_ms=(30, 90)) -> dict:
    """Probe position and latency of the most negative CSD inside window_ms."""
    m = (times_ms >= window_ms[0]) & (times_ms <= window_ms[1])
    if not np.any(m) or np.all(np.isnan(csd[:, m])):
        return dict(pos=None, latency_ms=None, value=None)
    sub = np.where(np.isnan(csd[:, m]), np.inf, csd[:, m])
    pos, t = np.unravel_index(np.argmin(sub), sub.shape)
    return dict(pos=int(pos), latency_ms=float(times_ms[m][t]), value=float(sub[pos, t]))


# ─────────────────────────────────────────────────────────────────────────────
#  Spectrolaminar
# ─────────────────────────────────────────────────────────────────────────────

def band_profile(rel_power_by_pos: np.ndarray, freqs: np.ndarray, band) -> np.ndarray:
    m = (freqs >= band[0]) & (freqs <= band[1])
    return np.nanmean(rel_power_by_pos[:, m], axis=1)


def crossover_position(gamma: np.ndarray, alpha_beta: np.ndarray) -> Optional[float]:
    """Fractional probe position where (gamma - alpha_beta) goes from + to - with depth.
    If there are several, the one with the largest drop. None if it never crosses."""
    d = np.asarray(gamma, float) - np.asarray(alpha_beta, float)
    best, best_drop = None, 0.0
    for i in range(len(d) - 1):
        if np.isnan(d[i]) or np.isnan(d[i + 1]):
            continue
        if d[i] > 0 >= d[i + 1]:
            drop = d[i] - d[i + 1]
            if drop > best_drop:
                best, best_drop = i + d[i] / drop, drop
    return best


# ─────────────────────────────────────────────────────────────────────────────
#  Suggested calls
# ─────────────────────────────────────────────────────────────────────────────

def suggest_classes(depths_mm: np.ndarray, middle_depth_mm: Optional[float],
                    tissue_by_pos: Sequence[Optional[str]], middle_half_width_um: float = 100.0,
                    normal_order: bool = True) -> List[str]:
    """Starting calls for the GUI, one per probe position (0 = top).

    tissue_by_pos: 'gm' | 'wm' | 'sulcus' | None per channel (ephys tissue model, or MRI).
    Channels in wm / sulcus get that class. Gray-matter channels in the same contiguous
    gray-matter run as middle_depth_mm are middle (within ±middle_half_width_um), superficial
    above and deep below (swapped if normal_order is False, i.e. the probe moves from
    white matter toward pia). Other gray-matter channels are 'unsure'.
    """
    n = len(depths_mm)
    tissue = [t if t in ('gm', 'wm', 'sulcus') else 'gm' for t in tissue_by_pos]
    out = [t if t in ('wm', 'sulcus') else 'unsure' for t in tissue]
    if middle_depth_mm is None:
        return out
    mid = int(np.argmin(np.abs(np.asarray(depths_mm) - middle_depth_mm)))
    if tissue[mid] != 'gm':
        return out
    lo = mid
    while lo > 0 and tissue[lo - 1] == 'gm':
        lo -= 1
    hi = mid
    while hi < n - 1 and tissue[hi + 1] == 'gm':
        hi += 1
    above, below = ('superficial', 'deep') if normal_order else ('deep', 'superficial')
    for i in range(lo, hi + 1):
        dz_um = (depths_mm[i] - middle_depth_mm) * 1000.0
        if abs(dz_um) <= middle_half_width_um:
            out[i] = 'middle'
        else:
            out[i] = above if dz_um < 0 else below
    return out

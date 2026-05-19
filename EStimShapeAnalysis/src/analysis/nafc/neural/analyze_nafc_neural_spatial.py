"""
Spatial activation analysis: firing rate and z-score across probe channels × EStimSpecId.

For each (channel, estim spec id) pair, computes mean firing rate during the
stimulus window.  Each channel is z-scored against its own no-estim baseline
(mean ± std of per-trial firing rates on no-estim trials), so the map shows
where—along the probe—each estim spec drives activity above spontaneous level.

Analysis window is relative to sample_on (start of stimulus presentation).
ESTIM_BLANK_DURATION_S approximates the total blanked time per estim trial
due to artifact removal, so the effective recording time is
  (WINDOW_END_S - WINDOW_START_S) - ESTIM_BLANK_DURATION_S
Leaving it at 0.0 gives a conservative (slightly underestimated) estim rate.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np
import matplotlib.pyplot as plt

from clat.util import time_util

from src.analysis.nafc.neural.analyze_nafc_neural_raster import load_data
from src.analysis.nafc.neural.nafc_parser_base import NafcParserBase
from src.analysis.nafc.neural.nafc_neural_parser import NafcNeuralParser
from src.analysis.nafc.neural.nafc_artifact_removal_parser import NafcArtifactRemovalParser
from src.analysis.nafc.neural.artifact_removal import (
    BaselineDriftPreprocessor,
    ThresholdArtifactDetector,
    FlatBaselineRemover,
    RmsThresholdSpikeDetector,
    NeoSpikeDetector,
)


# ═══════════════════════════ CONFIG ═════════════════════════════════════════
EXP_DB_NAME     = "allen_estimshape_exp_260514_0"
INTAN_BASE_PATH = f"/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/{EXP_DB_NAME}/2026-05-14/"
SINCE_DATE      = time_util.from_date_to_now(2026, 4, 26)

# ── probe channel ordering (spatial, tip→top or top→tip) ────────────────────
CHANNEL_ORDER: List[int] = [
     7,  8, 25, 22,  0, 15, 24, 23,
     6,  9, 26, 21,  5, 10, 31, 16,
    27, 20,  4, 11, 28, 19,  1, 14,
     3, 12, 29, 18,  2, 13, 30, 17,
]

# ── analysis window (seconds relative to sample_on) ─────────────────────────
WINDOW_START_S          = 0.0    # start of window
WINDOW_END_S            = 0.5    # end of window
# Approximate total blanked time per estim trial from artifact removal.
# Subtract from effective duration so estim and no-estim rates are comparable.
# Set to 0.0 to skip correction (conservative: estim rates slightly underestimated).
ESTIM_BLANK_DURATION_S  = 0.0

# ── parser selection (mirrors analyze_nafc_neural.py) ───────────────────────
USE_ARTIFACT_REMOVAL_PARSER = True

SPIKE_DETECTOR_METHOD     = "neo"
ARTIFACT_THRESHOLD_FACTOR = 100
SPIKE_THRESHOLD_FACTOR    = 4.0
NEO_THRESHOLD_FACTOR      = 5.0
NEO_NOISE_SCALE           = "median"
NEO_SMOOTHING_S           = 0.001
REMOVER_PRE_PAD_S         = 0.0002
REMOVER_POST_PAD_S        = 0.0002
REMOVER_MIN_DURATION_S    = 0.0
REMOVER_BASELINE          = "zero"
PREPROCESSOR_HIGHPASS_HZ  = 5
POST_ARTIFACT_BLANK_S     = 0.001
# ════════════════════════════════════════════════════════════════════════════


def _channel_name(idx: int) -> str:
    return f"A-{idx:03d}"


def _spikes_in_window(neural: dict, channel: str, t_start: float, t_end: float) -> int:
    spikes = neural.get("spikes_by_channel", {}).get(channel, [])
    return sum(1 for s in spikes if t_start <= s <= t_end)


def _trial_rate(neural: dict, channel: str, window_start_s: float, window_end_s: float,
                effective_duration: float) -> Optional[float]:
    if not isinstance(neural, dict):
        return None
    s_on = neural.get("sample_on")
    if s_on is None:
        return None
    n = _spikes_in_window(neural, channel, s_on + window_start_s, s_on + window_end_s)
    return n / effective_duration


def _baseline_stats(
    no_estim_data, channels: List[str], window_start_s: float, window_end_s: float
) -> Dict[str, Tuple[float, float]]:
    """Per-channel (mean, std) firing rate from no-estim trials."""
    duration = window_end_s - window_start_s
    stats: Dict[str, Tuple[float, float]] = {}
    for ch in channels:
        rates = []
        for _, trial in no_estim_data.iterrows():
            r = _trial_rate(trial.get("NeuralData"), ch, window_start_s, window_end_s, duration)
            if r is not None:
                rates.append(r)
        if rates:
            arr = np.array(rates)
            stats[ch] = (float(arr.mean()), float(arr.std()))
        else:
            stats[ch] = (0.0, 0.0)
    return stats


def _estim_mean_rates(
    estim_data, channels: List[str], window_start_s: float, window_end_s: float,
    estim_blank_s: float,
) -> Dict[str, Dict[str, float]]:
    """mean firing rate per estim_id per channel: {estim_id -> {channel -> rate}}."""
    effective_duration = max(window_end_s - window_start_s - estim_blank_s, 1e-9)
    accumulator: Dict[str, Dict[str, List[float]]] = {}
    for _, trial in estim_data.iterrows():
        eid = trial.get("EStimSpecId", None)
        label = str(eid) if eid is not None else "None"
        neural = trial.get("NeuralData")
        for ch in channels:
            r = _trial_rate(neural, ch, window_start_s, window_end_s, effective_duration)
            if r is not None:
                accumulator.setdefault(label, {}).setdefault(ch, []).append(r)
    return {
        eid: {ch: float(np.mean(vals)) for ch, vals in ch_dict.items()}
        for eid, ch_dict in accumulator.items()
    }


def _build_matrices(
    baseline: Dict[str, Tuple[float, float]],
    rates_by_id: Dict[str, Dict[str, float]],
    channels: List[str],
    estim_ids: List[str],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (rate_mat, zscore_baseline_mat, zscore_across_eids_mat)."""
    n_ch, n_ids = len(channels), len(estim_ids)
    rate_mat        = np.full((n_ch, n_ids), np.nan)
    zscore_baseline = np.full((n_ch, n_ids), np.nan)
    zscore_eids     = np.full((n_ch, n_ids), np.nan)

    for c_idx, ch in enumerate(channels):
        b_mean, b_std = baseline.get(ch, (0.0, 0.0))
        b_std_safe = max(b_std, 1e-9)
        for e_idx, eid in enumerate(estim_ids):
            rate = rates_by_id.get(eid, {}).get(ch)
            if rate is not None:
                rate_mat[c_idx, e_idx]        = rate
                zscore_baseline[c_idx, e_idx] = (rate - b_mean) / b_std_safe

    # z-score each channel's rates across the estim-spec distribution
    for c_idx in range(n_ch):
        row = rate_mat[c_idx]
        valid = row[np.isfinite(row)]
        if len(valid) < 2:
            continue
        row_mean = valid.mean()
        row_std  = max(valid.std(), 1e-9)
        for e_idx in range(n_ids):
            if np.isfinite(rate_mat[c_idx, e_idx]):
                zscore_eids[c_idx, e_idx] = (rate_mat[c_idx, e_idx] - row_mean) / row_std

    return rate_mat, zscore_baseline, zscore_eids


def _heatmap_panel(ax, mat, ch_labels, estim_ids, title, cbar_label, cmap, vmin=None, vmax=None):
    im = ax.imshow(mat, aspect="auto", cmap=cmap, origin="upper", vmin=vmin, vmax=vmax)
    plt.colorbar(im, ax=ax, label=cbar_label)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_xticks(range(len(estim_ids)))
    ax.set_xticklabels(estim_ids, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(len(ch_labels)))
    ax.set_yticklabels(ch_labels, fontsize=7)
    ax.set_xlabel("EStimSpecId")
    ax.set_ylabel("Channel (probe order)")


def _plot_heatmaps(
    rate_mat: np.ndarray, zscore_baseline: np.ndarray, zscore_eids: np.ndarray,
    channel_order: List[int], estim_ids: List[str],
    window_start_s: float, window_end_s: float,
) -> None:
    ch_labels = [f"ch{idx}" for idx in channel_order]
    n_ids = len(estim_ids)

    fig_w = max(n_ids * 0.9 + 8, 16)
    fig_h = max(len(ch_labels) * 0.38 + 3, 10)
    fig, axes = plt.subplots(1, 3, figsize=(fig_w, fig_h))

    # ── raw rates ────────────────────────────────────────────────────────────
    _heatmap_panel(axes[0], rate_mat, ch_labels, estim_ids,
                   "Mean firing rate (estim on)", "spikes / s", "hot")

    # ── z-score vs no-estim baseline ─────────────────────────────────────────
    finite = zscore_baseline[np.isfinite(zscore_baseline)]
    vmax1 = max(float(np.percentile(np.abs(finite), 99)) if len(finite) else 1.0, 1.0)
    _heatmap_panel(axes[1], zscore_baseline, ch_labels, estim_ids,
                   "Z-score vs no-estim baseline", "z-score", "RdBu_r",
                   vmin=-vmax1, vmax=vmax1)

    # ── z-score across estim specs per channel ────────────────────────────────
    finite2 = zscore_eids[np.isfinite(zscore_eids)]
    vmax2 = max(float(np.percentile(np.abs(finite2), 99)) if len(finite2) else 1.0, 1.0)
    _heatmap_panel(axes[2], zscore_eids, ch_labels, estim_ids,
                   "Z-score across estim specs (per channel)", "z-score", "RdBu_r",
                   vmin=-vmax2, vmax=vmax2)

    fig.suptitle(
        f"Spatial activation map  ·  window [{window_start_s:.2f}, {window_end_s:.2f}] s after sample_on\n"
        f"Left: raw rates  ·  Centre: z vs no-estim baseline  ·  Right: z across estim specs per channel",
        fontsize=10,
    )
    plt.tight_layout()
    plt.show()


def run_spatial(
    data,
    channel_order: List[int],
    window_start_s: float,
    window_end_s: float,
    estim_blank_s: float = 0.0,
) -> None:
    channels = [_channel_name(idx) for idx in channel_order]

    no_estim = data[data["EStimEnabled"] == False]
    estim    = data[data["EStimEnabled"] == True]

    print(f"Baseline: {len(no_estim)} no-estim trials  |  Estim: {len(estim)} estim trials")

    baseline    = _baseline_stats(no_estim, channels, window_start_s, window_end_s)
    rates_by_id = _estim_mean_rates(estim, channels, window_start_s, window_end_s, estim_blank_s)
    estim_ids   = sorted(rates_by_id.keys())

    if not estim_ids:
        print("No estim trials found — check EStimEnabled column.")
        return

    rate_mat, zscore_baseline, zscore_eids = _build_matrices(baseline, rates_by_id, channels, estim_ids)
    _plot_heatmaps(rate_mat, zscore_baseline, zscore_eids, channel_order, estim_ids, window_start_s, window_end_s)


# ── parser helpers (identical to analyze_nafc_neural.py) ─────────────────────

def build_spike_detector():
    if SPIKE_DETECTOR_METHOD == "neo":
        return NeoSpikeDetector(
            threshold_factor=NEO_THRESHOLD_FACTOR,
            noise_scale=NEO_NOISE_SCALE,
            smoothing_window_s=NEO_SMOOTHING_S,
        )
    return RmsThresholdSpikeDetector(
        threshold_factor=SPIKE_THRESHOLD_FACTOR,
        noise_scale="rms",
    )


def build_parser() -> NafcParserBase:
    if not USE_ARTIFACT_REMOVAL_PARSER:
        return NafcNeuralParser()
    return NafcArtifactRemovalParser(
        preprocessor=BaselineDriftPreprocessor(highpass_hz=PREPROCESSOR_HIGHPASS_HZ),
        artifact_detector=ThresholdArtifactDetector(
            threshold_factor=ARTIFACT_THRESHOLD_FACTOR, noise_scale="mad",
        ),
        artifact_remover=FlatBaselineRemover(
            pre_pad_s=REMOVER_PRE_PAD_S,
            post_pad_s=REMOVER_POST_PAD_S,
            min_duration_s=REMOVER_MIN_DURATION_S,
            baseline=REMOVER_BASELINE,
        ),
        spike_detector=build_spike_detector(),
        post_artifact_blank_s=POST_ARTIFACT_BLANK_S,
    )


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    print(f"Using parser: {type(parser).__name__}")

    data, err = load_data(EXP_DB_NAME, INTAN_BASE_PATH, SINCE_DATE, parser=parser)
    if err or data.empty:
        print(err or "No matching trials — check EXP_DB_NAME / SINCE_DATE.")
        return

    run_spatial(data, CHANNEL_ORDER, WINDOW_START_S, WINDOW_END_S, ESTIM_BLANK_DURATION_S)


if __name__ == "__main__":
    main()

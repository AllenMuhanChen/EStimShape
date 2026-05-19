"""
Combined NAFC neural analysis: runs both raster and PSTH from a single config.
Edit the CONFIG block here; changes apply to both analyses automatically.

The neural parser is selectable: the default NafcNeuralParser reads
spike.dat from each recording directory, while NafcArtifactRemovalParser
loads raw amplifier data, removes stimulus artifacts, and detects MUA
spikes from the cleaned signal. Toggle ``USE_ARTIFACT_REMOVAL_PARSER``
to switch; both implement NafcParserBase so the rest of the pipeline is
identical.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from clat.util import time_util

from src.analysis.nafc.neural.analyze_nafc_neural_raster import load_data, run as run_raster
from src.analysis.nafc.neural.analyze_nafc_neural_psth import run as run_psth, run_by_choice_and_estim_id

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
# ── shared ──────────────────────────────────────────────────────────────────
EXP_DB_NAME     = "allen_estimshape_exp_260514_0"
INTAN_BASE_PATH = f"/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/{EXP_DB_NAME}/2026-05-14/"
CHANNEL_NAME    = "A-027"
SINCE_DATE      = time_util.from_date_to_now(2026, 4, 26)

# ── parser selection ────────────────────────────────────────────────────────
# Flip this to switch between the spike.dat parser and the new
# artifact-removal parser. Both produce NafcTrialEvents with the same shape,
# so everything downstream works unchanged.
USE_ARTIFACT_REMOVAL_PARSER = True

# Artifact-removal parser config (only used when USE_ARTIFACT_REMOVAL_PARSER).
# Matches tests/analysis/nafc/neural/test_nafc_artifact_removal_parser.py.

# Spike-detection backend: "rms" or "neo".
#   "rms" — fixed negative threshold at -SPIKE_THRESHOLD_FACTOR * RMS.
#           Fast, but biased by baseline shifts left over from artifacts.
#   "neo" — Nonlinear Energy Operator. Threshold = NEO_THRESHOLD_FACTOR
#           * mean(smoothed_NEO). Robust to slow baseline drift (e.g.
#           post-estim recovery), which is what we want here.
SPIKE_DETECTOR_METHOD     = "neo"

ARTIFACT_THRESHOLD_FACTOR = 100        # x MAD
SPIKE_THRESHOLD_FACTOR    = 4.0        # used when SPIKE_DETECTOR_METHOD == "rms"
NEO_THRESHOLD_FACTOR      = 5.0        # used when SPIKE_DETECTOR_METHOD == "neo"
NEO_NOISE_SCALE           = "median"   # "median" (robust) or "mean" (literature)
NEO_SMOOTHING_S           = 0.001      # 1 ms Bartlett window
REMOVER_PRE_PAD_S         = 0.0002     # 200 us
REMOVER_POST_PAD_S        = 0.0002     # 200 us
REMOVER_MIN_DURATION_S    = 0.0        # rely on detected event width
REMOVER_BASELINE          = "zero"  # or "zero"
PREPROCESSOR_HIGHPASS_HZ  = 5
# Samples within this many seconds of any artifact window are excluded from
# both the noise-threshold estimate and post-filter-ringing detection.
POST_ARTIFACT_BLANK_S     = 0.001        # 2 ms

# ── raster ──────────────────────────────────────────────────────────────────
RASTER_TIME_BEFORE_S = 0.2   # seconds before sample_on
RASTER_TIME_AFTER_S  = 1.5   # seconds after sample_on

# ── PSTH ────────────────────────────────────────────────────────────────────
PSTH_TIME_BEFORE_S   = 0.6   # seconds before sample_off
PSTH_TIME_AFTER_S    = 3.0   # seconds after sample_off
BIN_SIZE_S           = 0.05  # 50 ms bins
SHOW_STD             = True  # shaded ± 1 SEM band
# ════════════════════════════════════════════════════════════════════════════


def build_spike_detector():
    """Build the spike detector selected by SPIKE_DETECTOR_METHOD."""
    if SPIKE_DETECTOR_METHOD == "neo":
        return NeoSpikeDetector(
            threshold_factor=NEO_THRESHOLD_FACTOR,
            noise_scale=NEO_NOISE_SCALE,
            smoothing_window_s=NEO_SMOOTHING_S,
        )
    elif SPIKE_DETECTOR_METHOD == "rms":
        return RmsThresholdSpikeDetector(
            threshold_factor=SPIKE_THRESHOLD_FACTOR,
            noise_scale="rms",
        )
    else:
        raise ValueError(
            f"unknown SPIKE_DETECTOR_METHOD: {SPIKE_DETECTOR_METHOD!r}"
        )


def build_parser() -> NafcParserBase:
    """Build the parser selected by USE_ARTIFACT_REMOVAL_PARSER."""
    if not USE_ARTIFACT_REMOVAL_PARSER:
        return NafcNeuralParser()

    return NafcArtifactRemovalParser(
        preprocessor=BaselineDriftPreprocessor(
            highpass_hz=PREPROCESSOR_HIGHPASS_HZ,
        ),
        artifact_detector=ThresholdArtifactDetector(
            threshold_factor=ARTIFACT_THRESHOLD_FACTOR,
            noise_scale="mad",
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


def main():
    parser = build_parser()
    print(f"Using parser: {type(parser).__name__}")

    data, err = load_data(EXP_DB_NAME, INTAN_BASE_PATH, SINCE_DATE, parser=parser)
    if err or data.empty:
        print(err or "No matching trials — check EXP_DB_NAME / SINCE_DATE.")
        return

    run_raster(data, CHANNEL_NAME, RASTER_TIME_BEFORE_S, RASTER_TIME_AFTER_S)
    run_psth(data, CHANNEL_NAME, PSTH_TIME_BEFORE_S, PSTH_TIME_AFTER_S, BIN_SIZE_S, SHOW_STD)
    run_by_choice_and_estim_id(data, CHANNEL_NAME, PSTH_TIME_BEFORE_S, PSTH_TIME_AFTER_S, BIN_SIZE_S, SHOW_STD)


if __name__ == "__main__":
    main()

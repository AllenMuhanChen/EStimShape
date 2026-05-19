"""
Visual + sanity test for NafcArtifactRemovalParser.

Point INTAN_BASE_PATH at a directory of NAFC recordings (the same layout
NafcNeuralDataField walks: optionally one date-subdir level, then
{stimSpecId}_{YYMMDD}_{HHMMSS}/ trial dirs). The test will:

  1. Pick the first recording directory under INTAN_BASE_PATH.
  2. Load raw amplifier data for CHANNEL_NAME.
  3. Run the full pipeline (preprocess -> detect -> remove -> spike-detect).
  4. Plot:
       - A wide overview of the cleaned vs raw signal.
       - N short windows around individual artifacts: raw + cleaned + threshold,
         with detected spikes marked.
       - Histograms of artifact peak amplitudes and event widths (these
         help us pick a sensible a-priori artifact duration).
  5. Assert basic invariants (parser ran, returned a NafcTrialEvents,
     spikes_by_channel populated for at least one channel).

Run as a script to skip unittest plumbing:
    python -m tests.analysis.nafc.neural.test_nafc_artifact_removal_parser
"""

import os
import sys
import unittest
from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np

# Make `src.` imports work when running this file directly.
_REPO_SRC_PARENT = Path(__file__).resolve().parents[4]
if str(_REPO_SRC_PARENT) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC_PARENT))

from clat.intan.amplifiers import read_amplifier_data_with_memmap
from clat.intan.rhs.load_intan_rhs_format import read_data

from src.analysis.nafc.neural.artifact_removal import (
    ArtifactEvent, BaselineDriftPreprocessor, RmsThresholdSpikeDetector,
    SampleInterpolateRemover, ThresholdArtifactDetector,
)
from src.analysis.nafc.neural.nafc_artifact_removal_parser import (
    NafcArtifactRemovalParser,
)
from src.analysis.nafc.neural.nafc_trial_events import NafcTrialEvents


# ───────────────────────── CONFIG ──────────────────────────────────────────
# Point this at an Intan base directory. The test picks the first recording
# directory it finds inside (one level deep, or under a date subdir).
INTAN_BASE_PATH = (
    "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/"
    "allen_estimshape_exp_260518_0/2026-05-18/"
)
CHANNEL_NAME = "A-006"

# How many example artifact windows to display.
N_WINDOWS = 6
# Half-width of each artifact display window, in milliseconds.
WINDOW_HALFWIDTH_MS = 2.0

# Artifact-detector tuning (kept loose; refine after viewing the plots).
ARTIFACT_THRESHOLD_FACTOR = 8.0   # x MAD
ARTIFACT_DURATION_S = 170e-6      # paper's a-priori value
SPIKE_THRESHOLD_FACTOR = 4.0      # -N x RMS on the cleaned MUA band

# Optional: limit how much raw data we load to keep the test snappy.
# Set to None to process the full recording.
MAX_SECONDS_TO_LOAD: Optional[float] = 60.0
# ───────────────────────────────────────────────────────────────────────────


# ── recording-dir discovery (mirrors NafcNeuralDataField) ──────────────────

def _is_recording_dir(name: str) -> bool:
    parts = name.split('_')
    return len(parts) >= 3 and len(parts[0]) > 10 and parts[0].isdigit()


def _find_first_recording_dir(base_path: str) -> Optional[str]:
    if not os.path.isdir(base_path):
        return None
    for entry in sorted(os.scandir(base_path), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        if _is_recording_dir(entry.name):
            return entry.path
        # one level deeper (e.g. {base}/{YYYY-MM-DD}/{trial_dir})
        try:
            for sub in sorted(os.scandir(entry.path), key=lambda e: e.name):
                if sub.is_dir() and _is_recording_dir(sub.name):
                    return sub.path
        except OSError:
            continue
    return None


# ── plotting helpers ───────────────────────────────────────────────────────

def _find_channel_key(channel_to_data: dict, channel_name: str):
    for key in channel_to_data:
        if getattr(key, 'value', str(key)) == channel_name:
            return key
    return None


def _plot_overview(
    raw: np.ndarray, cleaned: np.ndarray, sample_rate: float,
    artifacts: List[ArtifactEvent], threshold: Optional[float], channel_name: str,
):
    n = len(raw)
    t = np.arange(n) / sample_rate
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(t, raw, color='tab:gray', linewidth=0.4, alpha=0.7, label='raw (preprocessed)')
    ax.plot(t, cleaned, color='tab:blue', linewidth=0.4, alpha=0.9, label='cleaned')
    if threshold is not None:
        ax.axhline(threshold, color='tab:red', linewidth=0.6, linestyle='--',
                   label=f'+/- artifact threshold ({threshold:.1f} uV)')
        ax.axhline(-threshold, color='tab:red', linewidth=0.6, linestyle='--')
    for ev in artifacts:
        ax.axvline(ev.start_sample / sample_rate,
                   color='tab:orange', alpha=0.15, linewidth=0.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Voltage (uV)')
    ax.set_title(
        f'{channel_name}  -  overview  -  {len(artifacts)} artifact events'
    )
    ax.legend(loc='upper right', fontsize=8)
    plt.tight_layout()


def _plot_artifact_windows(
    raw: np.ndarray, cleaned: np.ndarray, sample_rate: float,
    artifacts: List[ArtifactEvent], spike_samples: np.ndarray,
    threshold: Optional[float], channel_name: str,
    n_windows: int, halfwidth_ms: float,
):
    if not artifacts:
        print("No artifacts detected - skipping per-event windows.")
        return

    # Pick evenly spaced examples so we sample early/middle/late events.
    idxs = np.linspace(0, len(artifacts) - 1, num=min(n_windows, len(artifacts)),
                       dtype=int)
    halfwidth = int(halfwidth_ms * 1e-3 * sample_rate)

    fig, axes = plt.subplots(len(idxs), 1, figsize=(10, 2.0 * len(idxs)),
                             sharex=False)
    if len(idxs) == 1:
        axes = [axes]

    for ax, idx in zip(axes, idxs):
        ev = artifacts[idx]
        c = ev.peak_sample
        lo = max(c - halfwidth, 0)
        hi = min(c + halfwidth, len(raw))
        t_ms = (np.arange(lo, hi) - c) / sample_rate * 1e3

        ax.plot(t_ms, raw[lo:hi], color='tab:gray', linewidth=0.8,
                label='raw (preprocessed)')
        ax.plot(t_ms, cleaned[lo:hi], color='tab:blue', linewidth=1.0,
                label='cleaned')
        ax.axvspan(
            (ev.start_sample - c) / sample_rate * 1e3,
            (ev.end_sample - c) / sample_rate * 1e3,
            color='tab:orange', alpha=0.25, label='detected event'
        )
        if threshold is not None:
            ax.axhline(threshold, color='tab:red', linewidth=0.5, linestyle='--')
            ax.axhline(-threshold, color='tab:red', linewidth=0.5, linestyle='--')
        # Mark any spikes that fall inside this window.
        spike_mask = (spike_samples >= lo) & (spike_samples < hi)
        for s in spike_samples[spike_mask]:
            ax.axvline((s - c) / sample_rate * 1e3,
                       color='tab:green', linewidth=0.8, alpha=0.7)

        ax.set_title(
            f'artifact #{idx}  -  peak {ev.peak_value:+.0f} uV  -  '
            f'width {ev.width_samples} samples '
            f'({ev.width_samples / sample_rate * 1e6:.0f} us)',
            fontsize=9,
        )
        ax.set_ylabel('uV', fontsize=8)
        ax.tick_params(labelsize=7)

    axes[0].legend(loc='upper right', fontsize=7)
    axes[-1].set_xlabel('Time relative to artifact peak (ms)')
    plt.suptitle(f'{channel_name}  -  artifact removal windows', fontsize=10)
    plt.tight_layout()


def _plot_artifact_stats(artifacts: List[ArtifactEvent], sample_rate: float,
                         channel_name: str):
    if not artifacts:
        return
    peaks = np.array([abs(ev.peak_value) for ev in artifacts])
    widths_us = np.array(
        [ev.width_samples / sample_rate * 1e6 for ev in artifacts]
    )

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
    axes[0].hist(peaks, bins=40, color='tab:orange', edgecolor='black')
    axes[0].set_xlabel('|peak| (uV)')
    axes[0].set_ylabel('count')
    axes[0].set_title('Artifact peak amplitudes')

    axes[1].hist(widths_us, bins=40, color='tab:purple', edgecolor='black')
    axes[1].set_xlabel('Event width above threshold (us)')
    axes[1].set_title('Artifact event widths')
    axes[1].axvline(170, color='tab:red', linestyle='--', linewidth=1,
                    label='paper a-priori (170 us)')
    axes[1].legend(fontsize=8)

    plt.suptitle(f'{channel_name}  -  artifact statistics', fontsize=10)
    plt.tight_layout()


# ── the test class ─────────────────────────────────────────────────────────

class TestNafcArtifactRemovalParser(unittest.TestCase):
    """Visual / sanity test against a real Intan recording."""

    @classmethod
    def setUpClass(cls):
        cls.recording_dir = _find_first_recording_dir(INTAN_BASE_PATH)
        if cls.recording_dir is None:
            raise unittest.SkipTest(
                f"No recording dir found under INTAN_BASE_PATH={INTAN_BASE_PATH}"
            )
        print(f"\nUsing recording: {cls.recording_dir}")

    def _build_parser(self) -> NafcArtifactRemovalParser:
        return NafcArtifactRemovalParser(
            preprocessor=BaselineDriftPreprocessor(highpass_hz=5.0),
            artifact_detector=ThresholdArtifactDetector(
                threshold_factor=ARTIFACT_THRESHOLD_FACTOR,
                noise_scale="mad",
            ),
            artifact_remover=SampleInterpolateRemover(
                artifact_duration_s=ARTIFACT_DURATION_S,
            ),
            spike_detector=RmsThresholdSpikeDetector(
                threshold_factor=SPIKE_THRESHOLD_FACTOR,
                noise_scale="rms",
            ),
        )

    # -- the "show me windows around artifacts" visual test ------------------

    def test_visualize_artifact_windows_on_single_channel(self):
        """Load one channel, run the pipeline, and display diagnostic plots."""
        rhs = read_data(os.path.join(self.recording_dir, "info.rhs"))
        sample_rate = float(rhs['frequency_parameters']['amplifier_sample_rate'])
        amplifier_channels = rhs['amplifier_channels']

        channel_to_raw = read_amplifier_data_with_memmap(
            os.path.join(self.recording_dir, "amplifier.dat"),
            amplifier_channels,
        )
        key = _find_channel_key(channel_to_raw, CHANNEL_NAME)
        self.assertIsNotNone(
            key, f"channel {CHANNEL_NAME} not present in recording"
        )

        raw = np.asarray(channel_to_raw[key], dtype=np.float64)
        if MAX_SECONDS_TO_LOAD is not None:
            raw = raw[: int(MAX_SECONDS_TO_LOAD * sample_rate)]
        print(f"Loaded {len(raw)} samples ({len(raw)/sample_rate:.1f} s) "
              f"from channel {CHANNEL_NAME} @ {sample_rate:.0f} Hz")

        parser = self._build_parser()
        result = parser.process_channel(raw, sample_rate)

        artifacts: List[ArtifactEvent] = result['artifacts']
        cleaned = result['cleaned']
        preprocessed = result['preprocessed']
        spike_samples = result['spike_samples']
        threshold = result['artifact_threshold']

        print(f"Detected {len(artifacts)} artifact events "
              f"(threshold = {threshold:.1f} uV)")
        print(f"Detected {len(spike_samples)} spikes after artifact removal")

        # Visual outputs (only block once, at the end).
        _plot_overview(preprocessed, cleaned, sample_rate, artifacts,
                       threshold, CHANNEL_NAME)
        _plot_artifact_windows(preprocessed, cleaned, sample_rate, artifacts,
                               spike_samples, threshold, CHANNEL_NAME,
                               N_WINDOWS, WINDOW_HALFWIDTH_MS)
        _plot_artifact_stats(artifacts, sample_rate, CHANNEL_NAME)
        plt.show()

        # Sanity asserts.
        self.assertEqual(len(cleaned), len(preprocessed))
        self.assertTrue(np.isfinite(cleaned).all())
        if artifacts:
            ev = artifacts[0]
            self.assertGreaterEqual(ev.peak_sample, ev.start_sample)
            self.assertLess(ev.peak_sample, ev.end_sample)

    # -- end-to-end parser test (NafcTrialEvents shape) ----------------------

    def test_parser_returns_nafc_trial_events(self):
        """Parser runs to completion and produces a populated NafcTrialEvents.

        WARNING: this runs the pipeline on every channel and can be slow.
        Comment out or skip if you only care about the visual test.
        """
        if os.environ.get("SKIP_FULL_PARSE") == "1":
            self.skipTest("SKIP_FULL_PARSE=1")

        parser = self._build_parser()
        events = parser.parse(self.recording_dir)

        self.assertIsInstance(events, NafcTrialEvents)
        self.assertGreater(events.sample_rate, 0)
        self.assertTrue(events.spikes_by_channel, "no channels parsed")

        total_spikes = sum(len(v) for v in events.spikes_by_channel.values())
        print(f"task_id={events.task_id}  "
              f"channels={len(events.spikes_by_channel)}  "
              f"total spikes={total_spikes}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Visual + sanity test for NafcArtifactRemovalParser.

Point INTAN_BASE_PATH at a directory of NAFC recordings (the same layout
NafcNeuralDataField walks: optionally one date-subdir level, then
{stimSpecId}_{YYMMDD}_{HHMMSS}/ trial dirs). The test will:

  1. Find up to N_RECORDINGS recording directories under INTAN_BASE_PATH.
  2. For each, load raw amplifier data for CHANNEL_NAME and run the full
     pipeline (preprocess -> detect -> remove -> spike-detect).
  3. Plot:
       - One overview (raw vs. cleaned) per recording.
       - N_WINDOWS short windows around individual artifacts sampled
         across all recordings: raw + cleaned + threshold, with detected
         spikes marked.
       - Pooled histograms of artifact peak amplitudes and event widths
         (these help us pick a sensible a-priori artifact duration).
  4. Assert basic invariants (parser ran, returned a NafcTrialEvents,
     spikes_by_channel populated for at least one channel).

Run as a script to skip unittest plumbing:
    python -m tests.analysis.nafc.neural.test_nafc_artifact_removal_parser
"""

import os
import sys
import unittest
from pathlib import Path
from typing import List, Optional, Tuple

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
# Point this at an Intan base directory. The test scans for recording
# directories one level deep (and one level under a date subdir).
INTAN_BASE_PATH = (
    "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/"
    "allen_estimshape_exp_260518_0/2026-05-18/"
)
CHANNEL_NAME = "A-006"

# How many recordings to sample from INTAN_BASE_PATH.
N_RECORDINGS = 10
# How many example artifact windows to display, sampled across all
# recordings.
N_WINDOWS = 12
# Half-width of each artifact display window, in milliseconds.
WINDOW_HALFWIDTH_MS = 2.0
# How many overview traces to plot (one figure each). Set to 0 to skip.
N_OVERVIEW_PLOTS = 3

# Artifact-detector tuning (kept loose; refine after viewing the plots).
ARTIFACT_THRESHOLD_FACTOR = 8.0   # x MAD
ARTIFACT_DURATION_S = 170e-6      # paper's a-priori value
SPIKE_THRESHOLD_FACTOR = 4.0      # -N x RMS on the cleaned MUA band

# Optional: limit how much raw data we load per recording. NAFC trials
# are short so this is usually a no-op, but useful for sftp-mounted dirs
# during exploration.
MAX_SECONDS_TO_LOAD: Optional[float] = None
# ───────────────────────────────────────────────────────────────────────────


# ── recording-dir discovery (mirrors NafcNeuralDataField) ──────────────────

def _is_recording_dir(name: str) -> bool:
    parts = name.split('_')
    return len(parts) >= 3 and len(parts[0]) > 10 and parts[0].isdigit()


def _find_recording_dirs(base_path: str, limit: Optional[int] = None) -> List[str]:
    """Return recording dirs found one level deep (or under a date subdir)."""
    if not os.path.isdir(base_path):
        return []
    found: List[str] = []
    for entry in sorted(os.scandir(base_path), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        if _is_recording_dir(entry.name):
            found.append(entry.path)
        else:
            try:
                for sub in sorted(os.scandir(entry.path), key=lambda e: e.name):
                    if sub.is_dir() and _is_recording_dir(sub.name):
                        found.append(sub.path)
            except OSError:
                continue
        if limit is not None and len(found) >= limit:
            break
    if limit is not None:
        found = found[:limit]
    return found


def _find_channel_key(channel_to_data: dict, channel_name: str):
    for key in channel_to_data:
        if getattr(key, 'value', str(key)) == channel_name:
            return key
    return None


# ── per-recording pipeline run ─────────────────────────────────────────────

def _process_one_recording(
    recording_dir: str, channel_name: str,
    parser: NafcArtifactRemovalParser,
    max_seconds: Optional[float],
) -> Optional[dict]:
    """Returns a dict with pipeline outputs for one channel of one recording,
    or None if the channel isn't present."""
    rhs = read_data(os.path.join(recording_dir, "info.rhs"))
    sample_rate = float(rhs['frequency_parameters']['amplifier_sample_rate'])
    amplifier_channels = rhs['amplifier_channels']

    channel_to_raw = read_amplifier_data_with_memmap(
        os.path.join(recording_dir, "amplifier.dat"),
        amplifier_channels,
    )
    key = _find_channel_key(channel_to_raw, channel_name)
    if key is None:
        return None

    raw = np.asarray(channel_to_raw[key], dtype=np.float64)
    if max_seconds is not None:
        raw = raw[: int(max_seconds * sample_rate)]

    result = parser.process_channel(raw, sample_rate)
    result['sample_rate'] = sample_rate
    result['recording_dir'] = recording_dir
    return result


# ── plotting helpers ───────────────────────────────────────────────────────

def _plot_overview(result: dict, channel_name: str):
    pp = result['preprocessed']
    cleaned = result['cleaned']
    fs = result['sample_rate']
    artifacts: List[ArtifactEvent] = result['artifacts']
    threshold = result['artifact_threshold']
    name = os.path.basename(result['recording_dir'].rstrip('/\\'))

    t = np.arange(len(pp)) / fs
    fig, ax = plt.subplots(figsize=(14, 3.5))
    ax.plot(t, pp, color='tab:gray', linewidth=0.4, alpha=0.7,
            label='raw (preprocessed)')
    ax.plot(t, cleaned, color='tab:blue', linewidth=0.4, alpha=0.9,
            label='cleaned')
    if threshold is not None:
        ax.axhline(threshold, color='tab:red', linewidth=0.6, linestyle='--',
                   label=f'+/- artifact threshold ({threshold:.1f} uV)')
        ax.axhline(-threshold, color='tab:red', linewidth=0.6, linestyle='--')
    for ev in artifacts:
        ax.axvline(ev.start_sample / fs,
                   color='tab:orange', alpha=0.15, linewidth=0.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Voltage (uV)')
    ax.set_title(f'{channel_name}  -  {name}  -  '
                 f'{len(artifacts)} artifacts')
    ax.legend(loc='upper right', fontsize=8)
    plt.tight_layout()


def _plot_pooled_artifact_windows(
    per_recording_results: List[dict], channel_name: str,
    n_windows: int, halfwidth_ms: float,
):
    # Pool (recording_result, event) pairs, then evenly sample N of them.
    all_pairs: List[Tuple[dict, ArtifactEvent]] = []
    for res in per_recording_results:
        for ev in res['artifacts']:
            all_pairs.append((res, ev))

    if not all_pairs:
        print("No artifacts detected across recordings - skipping windows.")
        return

    idxs = np.linspace(0, len(all_pairs) - 1,
                       num=min(n_windows, len(all_pairs)), dtype=int)

    n_rows = len(idxs)
    fig, axes = plt.subplots(n_rows, 1, figsize=(10, 1.8 * n_rows))
    if n_rows == 1:
        axes = [axes]

    for ax, idx in zip(axes, idxs):
        res, ev = all_pairs[idx]
        fs = res['sample_rate']
        pp = res['preprocessed']
        cleaned = res['cleaned']
        spike_samples = res['spike_samples']
        threshold = res['artifact_threshold']

        halfwidth = int(halfwidth_ms * 1e-3 * fs)
        c = ev.peak_sample
        lo = max(c - halfwidth, 0)
        hi = min(c + halfwidth, len(pp))
        t_ms = (np.arange(lo, hi) - c) / fs * 1e3

        ax.plot(t_ms, pp[lo:hi], color='tab:gray', linewidth=0.8,
                label='raw (preprocessed)')
        ax.plot(t_ms, cleaned[lo:hi], color='tab:blue', linewidth=1.0,
                label='cleaned')
        ax.axvspan(
            (ev.start_sample - c) / fs * 1e3,
            (ev.end_sample - c) / fs * 1e3,
            color='tab:orange', alpha=0.25, label='detected event',
        )
        if threshold is not None:
            ax.axhline(threshold, color='tab:red', linewidth=0.5, linestyle='--')
            ax.axhline(-threshold, color='tab:red', linewidth=0.5, linestyle='--')

        spike_mask = (spike_samples >= lo) & (spike_samples < hi)
        for s in spike_samples[spike_mask]:
            ax.axvline((s - c) / fs * 1e3,
                       color='tab:green', linewidth=0.8, alpha=0.7)

        rec_name = os.path.basename(res['recording_dir'].rstrip('/\\'))
        ax.set_title(
            f'{rec_name}  -  peak {ev.peak_value:+.0f} uV  -  '
            f'width {ev.width_samples} samp '
            f'({ev.width_samples / fs * 1e6:.0f} us)',
            fontsize=8,
        )
        ax.set_ylabel('uV', fontsize=8)
        ax.tick_params(labelsize=7)

    axes[0].legend(loc='upper right', fontsize=7)
    axes[-1].set_xlabel('Time relative to artifact peak (ms)')
    plt.suptitle(
        f'{channel_name}  -  artifact removal windows '
        f'(pooled across {len(per_recording_results)} recordings)',
        fontsize=10,
    )
    plt.tight_layout()


def _plot_pooled_stats(per_recording_results: List[dict], channel_name: str):
    peaks: List[float] = []
    widths_us: List[float] = []
    counts_per_recording: List[int] = []
    for res in per_recording_results:
        fs = res['sample_rate']
        counts_per_recording.append(len(res['artifacts']))
        for ev in res['artifacts']:
            peaks.append(abs(ev.peak_value))
            widths_us.append(ev.width_samples / fs * 1e6)

    if not peaks:
        return

    peaks_arr = np.asarray(peaks)
    widths_arr = np.asarray(widths_us)
    counts_arr = np.asarray(counts_per_recording)

    fig, axes = plt.subplots(1, 3, figsize=(14, 3.4))
    axes[0].hist(peaks_arr, bins=40, color='tab:orange', edgecolor='black')
    axes[0].set_xlabel('|peak| (uV)')
    axes[0].set_ylabel('count')
    axes[0].set_title('Artifact peak amplitudes')

    axes[1].hist(widths_arr, bins=40, color='tab:purple', edgecolor='black')
    axes[1].set_xlabel('Event width above threshold (us)')
    axes[1].set_title(
        f'Artifact widths  (median {np.median(widths_arr):.0f} us, '
        f'p95 {np.percentile(widths_arr, 95):.0f} us)'
    )
    axes[1].axvline(170, color='tab:red', linestyle='--', linewidth=1,
                    label='paper a-priori (170 us)')
    axes[1].legend(fontsize=8)

    axes[2].bar(np.arange(len(counts_arr)), counts_arr,
                color='tab:teal', edgecolor='black')
    axes[2].set_xlabel('Recording index')
    axes[2].set_ylabel('# artifacts')
    axes[2].set_title('Artifacts per recording')

    plt.suptitle(
        f'{channel_name}  -  pooled artifact statistics '
        f'({len(peaks_arr)} events across {len(counts_arr)} recordings)',
        fontsize=10,
    )
    plt.tight_layout()


# ── the test class ─────────────────────────────────────────────────────────

class TestNafcArtifactRemovalParser(unittest.TestCase):
    """Visual / sanity test against real Intan recordings."""

    @classmethod
    def setUpClass(cls):
        cls.recording_dirs = _find_recording_dirs(INTAN_BASE_PATH,
                                                  limit=N_RECORDINGS)
        if not cls.recording_dirs:
            raise unittest.SkipTest(
                f"No recording dirs found under INTAN_BASE_PATH={INTAN_BASE_PATH}"
            )
        print(f"\nFound {len(cls.recording_dirs)} recordings; using all.")

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

    def test_visualize_artifact_windows_across_recordings(self):
        """Run the pipeline on one channel across N recordings and plot
        diagnostic figures pooled across the lot."""
        parser = self._build_parser()
        results: List[dict] = []

        for i, rec in enumerate(self.recording_dirs):
            try:
                res = _process_one_recording(
                    rec, CHANNEL_NAME, parser, MAX_SECONDS_TO_LOAD,
                )
            except Exception as exc:
                print(f"[{i+1}/{len(self.recording_dirs)}] {rec}: FAILED  ({exc})")
                continue
            if res is None:
                print(f"[{i+1}/{len(self.recording_dirs)}] {rec}: "
                      f"channel {CHANNEL_NAME} not present, skipping")
                continue

            n_samples = len(res['preprocessed'])
            rec_name = os.path.basename(rec.rstrip('/\\'))
            print(f"[{i+1}/{len(self.recording_dirs)}] "
                  f"{rec_name}: "
                  f"{n_samples} samples "
                  f"({n_samples/res['sample_rate']:.2f} s), "
                  f"{len(res['artifacts'])} artifacts, "
                  f"{len(res['spike_samples'])} spikes")
            results.append(res)

        self.assertTrue(results, "no recordings processed")

        # Plots: per-recording overview (limited), pooled windows, pooled stats.
        for res in results[:N_OVERVIEW_PLOTS]:
            _plot_overview(res, CHANNEL_NAME)
        _plot_pooled_artifact_windows(results, CHANNEL_NAME,
                                      N_WINDOWS, WINDOW_HALFWIDTH_MS)
        _plot_pooled_stats(results, CHANNEL_NAME)
        plt.show()

        # Sanity asserts on aggregate output.
        total_artifacts = sum(len(r['artifacts']) for r in results)
        print(f"\nTotal artifacts detected: {total_artifacts} "
              f"across {len(results)} recordings")
        for res in results:
            self.assertEqual(len(res['cleaned']), len(res['preprocessed']))
            self.assertTrue(np.isfinite(res['cleaned']).all())

    # -- end-to-end parser test (NafcTrialEvents shape) ----------------------

    def test_parser_returns_nafc_trial_events(self):
        """Parser runs to completion on one recording and produces a populated
        NafcTrialEvents.

        WARNING: this runs the pipeline on every channel and can be slow.
        Set SKIP_FULL_PARSE=1 in the env to skip.
        """
        if os.environ.get("SKIP_FULL_PARSE") == "1":
            self.skipTest("SKIP_FULL_PARSE=1")

        parser = self._build_parser()
        events = parser.parse(self.recording_dirs[0])

        self.assertIsInstance(events, NafcTrialEvents)
        self.assertGreater(events.sample_rate, 0)
        self.assertTrue(events.spikes_by_channel, "no channels parsed")

        total_spikes = sum(len(v) for v in events.spikes_by_channel.values())
        print(f"task_id={events.task_id}  "
              f"channels={len(events.spikes_by_channel)}  "
              f"total spikes={total_spikes}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

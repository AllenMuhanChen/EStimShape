"""
Visual + sanity test for NafcArtifactRemovalParser.

Point INTAN_BASE_PATH at a directory of NAFC recordings and EXP_DB_NAME
at the corresponding experiment database. The test will:

  1. Query the DB for trials with EStim ON; extract stimSpecId and EStimSpecId.
  2. Map each stimSpecId to its recording directory.
  3. Group recordings by EStimSpecId and sample N_PER_ESTIM_SPEC from each.
  4. Run the full pipeline on CHANNEL_NAME for each selected recording.
  5. Plot:
       - Per-EStimSpecId artifact-window examples (raw + cleaned, spike-detection
         threshold, detected spikes, and the artifact blank zone).
       - Pooled histogram of spike times relative to the nearest artifact-
         window edge — to confirm no spikes sneak through the blank zone.
       - Pooled histograms of artifact peak amplitudes and event widths.

Run as a script:
    python -m tests.analysis.nafc.neural.test_nafc_artifact_removal_parser
"""

import os
import sys
import unittest
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

_REPO_SRC_PARENT = Path(__file__).resolve().parents[4]
if str(_REPO_SRC_PARENT) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC_PARENT))

from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.intan.amplifiers import read_amplifier_data_with_memmap
from clat.intan.rhs.load_intan_rhs_format import read_data
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    EStimEnabledField, EStimSpecIdField, StimSpecIdField,
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials
from src.analysis.nafc.neural.artifact_removal import (
    ArtifactEvent, BaselineDriftPreprocessor, FlatBaselineRemover,
    NeoSpikeDetector, RmsThresholdSpikeDetector, ThresholdArtifactDetector,
)
from src.analysis.nafc.neural.nafc_artifact_removal_parser import (
    NafcArtifactRemovalParser,
)
from src.analysis.nafc.neural.nafc_trial_events import NafcTrialEvents


# ───────────────────────── CONFIG ──────────────────────────────────────────
EXP_DB_NAME = "allen_estimshape_exp_260518_0"
INTAN_BASE_PATH = (
    "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/"
    "allen_estimshape_exp_260518_0/2026-05-18/"
)
SINCE_DATE = time_util.from_date_to_now(2026, 5, 18)
CHANNEL_NAME = "A-006"

# Recordings per EStimSpecId to process.
N_PER_ESTIM_SPEC = 3
# Artifact windows to display per EStimSpecId group.
N_WINDOWS_PER_SPEC = 2
# Half-width of each artifact display window, in milliseconds.
WINDOW_HALFWIDTH_MS = 2.0

# Artifact-detector tuning.
ARTIFACT_THRESHOLD_FACTOR = 100   # x MAD

# Spike-detection backend: "neo" or "rms".
#   "neo" — Nonlinear Energy Operator. Robust to slow baseline shifts
#           (e.g. post-estim drift) that bias RMS thresholding.
#   "rms" — fixed negative -N x RMS threshold on the cleaned MUA band.
SPIKE_DETECTOR_METHOD = "neo"
SPIKE_THRESHOLD_FACTOR = 4.0   # for "rms"
NEO_THRESHOLD_FACTOR   = 5.0   # for "neo"; C * noise(smoothed NEO)
NEO_NOISE_SCALE        = "median"  # "median" (robust) or "mean" (literature)
NEO_SMOOTHING_S        = 0.001

# Flat-baseline remover.
REMOVER_PRE_PAD_S      = 0.0002   # 200 us
REMOVER_POST_PAD_S     = 0.0002   # 200 us
REMOVER_MIN_DURATION_S = 0.0
REMOVER_BASELINE       = "pre_median"

# Post-artifact blank: spikes inside this zone are suppressed AND the zone
# is excluded from the noise/threshold estimate.
POST_ARTIFACT_BLANK_S = 0.002     # 2 ms

MAX_SECONDS_TO_LOAD: Optional[float] = None
# ───────────────────────────────────────────────────────────────────────────


# ── recording-dir discovery ───────────────────────────────────────────────

def _is_recording_dir(name: str) -> bool:
    parts = name.split('_')
    return len(parts) >= 3 and len(parts[0]) > 10 and parts[0].isdigit()


def _build_recording_index(base_path: str) -> dict:
    index: dict = {}
    if not os.path.isdir(base_path):
        return index
    try:
        entries = list(os.scandir(base_path))
    except OSError as exc:
        print(f"Cannot scan {base_path}: {exc}")
        return index
    for entry in entries:
        if not entry.is_dir():
            continue
        if _is_recording_dir(entry.name):
            index[entry.name.split('_')[0]] = entry.path
        else:
            try:
                for sub in os.scandir(entry.path):
                    if sub.is_dir() and _is_recording_dir(sub.name):
                        index[sub.name.split('_')[0]] = sub.path
            except OSError:
                pass
    return index


def _query_estim_on_trials(exp_db_name: str, since_date):
    """
    Return a list of dicts:
        {'stim_spec_id': str, 'estim_spec_id': str}
    for all EStim-ON trials found in the DB.
    """
    conn = Connection(exp_db_name)
    trial_tstamps = collect_choice_trials(conn, since_date)
    if not trial_tstamps:
        return []

    fields = CachedFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(EStimEnabledField(conn))
    fields.append(EStimSpecIdField(conn))
    data = fields.to_data(trial_tstamps)

    estim_on = data[data["EStimEnabled"] == True].copy()
    rows = []
    for _, row in estim_on.iterrows():
        stim_spec_id = row.get("StimSpecId")
        estim_spec_id = row.get("EStimSpecId")
        if stim_spec_id is None:
            continue
        rows.append({
            'stim_spec_id': str(int(stim_spec_id)),
            'estim_spec_id': str(estim_spec_id) if estim_spec_id is not None else "unknown",
        })
    return rows


def _select_recordings(
    exp_db_name: str, base_path: str, since_date, n_per_spec: int,
) -> List[dict]:
    """
    Return a list of dicts:
        {'recording_dir': str, 'stim_spec_id': str, 'estim_spec_id': str}
    with up to n_per_spec entries per EStimSpecId.
    """
    print("Building recording index from filesystem...")
    index = _build_recording_index(base_path)
    print(f"  found {len(index)} recording dirs")

    print("Querying DB for EStim-ON trials...")
    trial_rows = _query_estim_on_trials(exp_db_name, since_date)
    print(f"  found {len(trial_rows)} EStim-ON trials")

    # Group stim_spec_ids by estim_spec_id, keeping only those present on disk.
    by_spec: Dict[str, List[str]] = defaultdict(list)
    for row in trial_rows:
        sid = row['stim_spec_id']
        if sid in index:
            by_spec[row['estim_spec_id']].append(sid)

    selected = []
    for estim_spec_id in sorted(by_spec.keys()):
        sids = by_spec[estim_spec_id][:n_per_spec]
        for sid in sids:
            selected.append({
                'recording_dir': index[sid],
                'stim_spec_id': sid,
                'estim_spec_id': estim_spec_id,
            })

    print(f"  selected {len(selected)} recordings across "
          f"{len(by_spec)} EStimSpecIds "
          f"(up to {n_per_spec} each)")
    return selected


# ── per-recording pipeline run ────────────────────────────────────────────

def _find_channel_key(channel_to_data: dict, channel_name: str):
    for key in channel_to_data:
        if getattr(key, 'value', str(key)) == channel_name:
            return key
    return None


def _process_one_recording(
    rec: dict, channel_name: str, parser: NafcArtifactRemovalParser,
    max_seconds: Optional[float],
) -> Optional[dict]:
    recording_dir = rec['recording_dir']
    rhs = read_data(os.path.join(recording_dir, "info.rhs"))
    sample_rate = float(rhs['frequency_parameters']['amplifier_sample_rate'])
    channel_to_raw = read_amplifier_data_with_memmap(
        os.path.join(recording_dir, "amplifier.dat"),
        rhs['amplifier_channels'],
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
    result['estim_spec_id'] = rec['estim_spec_id']
    result['stim_spec_id'] = rec['stim_spec_id']
    return result


# ── plotting helpers ──────────────────────────────────────────────────────

def _artifact_window_bounds(
    artifacts: List[ArtifactEvent], blank_mask: np.ndarray,
) -> List[Tuple[int, int]]:
    """Return (start, end) sample pairs for each contiguous blanked region."""
    if not blank_mask.any():
        return []
    edges = np.diff(blank_mask.astype(np.int8))
    starts = np.where(edges == 1)[0] + 1
    ends = np.where(edges == -1)[0] + 1
    if blank_mask[0]:
        starts = np.insert(starts, 0, 0)
    if blank_mask[-1]:
        ends = np.append(ends, len(blank_mask))
    return list(zip(starts.tolist(), ends.tolist()))


def _plot_per_spec_windows(
    results_by_spec: Dict[str, List[dict]],
    channel_name: str,
    n_windows_per_spec: int,
    halfwidth_ms: float,
):
    """One grid per EStimSpecId; each row is one artifact window."""
    for estim_spec_id, results in sorted(results_by_spec.items()):
        # Collect (result, artifact_event) pairs for this spec.
        pairs: List[Tuple[dict, ArtifactEvent]] = []
        for res in results:
            for ev in res['artifacts']:
                pairs.append((res, ev))
        if not pairs:
            print(f"EStimSpecId {estim_spec_id}: no artifacts detected")
            continue

        idxs = np.linspace(0, len(pairs) - 1,
                           num=min(n_windows_per_spec, len(pairs)), dtype=int)
        n_rows = len(idxs)
        fig, axes = plt.subplots(n_rows, 1, figsize=(10, 2.2 * n_rows),
                                 squeeze=False)
        axes = axes[:, 0]

        for ax, idx in zip(axes, idxs):
            res, ev = pairs[idx]
            fs = res['sample_rate']
            pp = res['preprocessed']
            cleaned = res['cleaned']
            filtered = res['filtered_for_spikes']
            spike_samples = res['spike_samples']
            blank_mask = res['artifact_blank_mask']
            spike_threshold = res['spike_threshold']

            halfwidth = int(halfwidth_ms * 1e-3 * fs)
            c = ev.peak_sample
            lo = max(c - halfwidth, 0)
            hi = min(c + halfwidth, len(pp))
            t_ms = (np.arange(lo, hi) - c) / fs * 1e3

            ax.plot(t_ms, pp[lo:hi], color='tab:gray', lw=0.8, alpha=0.7,
                    label='raw (preprocessed)')
            ax.plot(t_ms, cleaned[lo:hi], color='tab:blue', lw=0.9,
                    label='cleaned')
            ax.plot(t_ms, filtered[lo:hi], color='black', lw=0.7, alpha=0.6,
                    label='filtered (for spikes)')

            # Shade the full blank zone (removal + post_artifact margin).
            blank_seg = blank_mask[lo:hi]
            if blank_seg.any():
                ax.fill_between(t_ms, ax.get_ylim()[0], ax.get_ylim()[1],
                                where=blank_seg,
                                color='tab:orange', alpha=0.18,
                                label='blank zone (no spikes)')

            # Spike threshold lines.
            if np.isfinite(spike_threshold):
                ax.axhline(-spike_threshold, color='tab:red', lw=0.6,
                           linestyle='--', label=f'-threshold ({-spike_threshold:.1f})')

            # Mark detected spikes.
            spike_mask = (spike_samples >= lo) & (spike_samples < hi)
            for s in spike_samples[spike_mask]:
                ax.axvline((s - c) / fs * 1e3,
                           color='tab:green', lw=1.0, alpha=0.85)

            ax.set_title(
                f'EStimSpecId {estim_spec_id}  |  '
                f'peak {ev.peak_value:+.0f} uV  |  '
                f'width {ev.width_samples} samp '
                f'({ev.width_samples/fs*1e6:.0f} us)',
                fontsize=8,
            )
            ax.set_ylabel('uV', fontsize=8)
            ax.tick_params(labelsize=7)

        axes[0].legend(loc='upper right', fontsize=7, ncol=2)
        axes[-1].set_xlabel('Time relative to artifact peak (ms)')
        fig.suptitle(
            f'{channel_name}  |  EStimSpecId: {estim_spec_id}  |  '
            f'orange = blank zone (no spikes possible)',
            fontsize=9,
        )
        plt.tight_layout()


def _plot_spike_near_artifact_diagnostic(
    all_results: List[dict], channel_name: str,
):
    """
    For every detected spike compute the distance to the nearest edge of any
    artifact blank zone. Spikes inside the zone should be zero; spikes very
    close to the zone edge would indicate filter ringing is leaking through.
    """
    distances_ms: List[float] = []

    for res in all_results:
        fs = res['sample_rate']
        spike_samples = res['spike_samples']
        blank_mask = res['artifact_blank_mask']
        if not len(spike_samples) or not blank_mask.any():
            continue

        # Edges of blanked zones (rising = zone start, falling = zone end).
        edges = np.diff(blank_mask.astype(np.int8))
        zone_starts = np.where(edges == 1)[0] + 1
        zone_ends = np.where(edges == -1)[0] + 1
        if blank_mask[0]:
            zone_starts = np.insert(zone_starts, 0, 0)
        if blank_mask[-1]:
            zone_ends = np.append(zone_ends, len(blank_mask))

        boundaries = np.concatenate([zone_starts, zone_ends])
        if not len(boundaries):
            continue

        for s in spike_samples:
            d = np.min(np.abs(s - boundaries)) / fs * 1e3
            distances_ms.append(float(d))

    if not distances_ms:
        return

    arr = np.asarray(distances_ms)
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.hist(arr, bins=60, color='tab:blue', edgecolor='black')
    ax.axvline(POST_ARTIFACT_BLANK_S * 1e3, color='tab:red', lw=1.2,
               linestyle='--',
               label=f'blank zone radius ({POST_ARTIFACT_BLANK_S*1e3:.1f} ms)')
    near = np.sum(arr < POST_ARTIFACT_BLANK_S * 1e3)
    ax.set_xlabel('Distance from nearest blank-zone edge (ms)')
    ax.set_ylabel('Spike count')
    ax.set_title(
        f'{channel_name}  |  spike distance to blank-zone boundary\n'
        f'{near} / {len(arr)} spikes inside blank zone '
        f'(should be 0)',
        fontsize=9,
    )
    ax.legend(fontsize=8)
    plt.tight_layout()


def _plot_pooled_stats(all_results: List[dict], channel_name: str):
    peaks: List[float] = []
    widths_us: List[float] = []
    for res in all_results:
        fs = res['sample_rate']
        for ev in res['artifacts']:
            peaks.append(abs(ev.peak_value))
            widths_us.append(ev.width_samples / fs * 1e6)

    if not peaks:
        return

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    axes[0].hist(peaks, bins=40, color='tab:orange', edgecolor='black')
    axes[0].set_xlabel('|peak| (uV)')
    axes[0].set_ylabel('count')
    axes[0].set_title('Artifact peak amplitudes (pooled)')

    axes[1].hist(widths_us, bins=40, color='tab:purple', edgecolor='black')
    axes[1].axvline(170, color='tab:red', ls='--', lw=1,
                    label='paper a-priori (170 us)')
    axes[1].set_xlabel('Width above threshold (us)')
    axes[1].set_title(
        f'Artifact widths  '
        f'(median {np.median(widths_us):.0f} us, '
        f'p95 {np.percentile(widths_us, 95):.0f} us)'
    )
    axes[1].legend(fontsize=8)
    plt.suptitle(
        f'{channel_name}  |  pooled artifact statistics '
        f'({len(peaks)} events)', fontsize=10,
    )
    plt.tight_layout()


# ── test class ────────────────────────────────────────────────────────────

class TestNafcArtifactRemovalParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.selected = _select_recordings(
            EXP_DB_NAME, INTAN_BASE_PATH, SINCE_DATE, N_PER_ESTIM_SPEC,
        )
        if not cls.selected:
            raise unittest.SkipTest(
                "No EStim-ON recording dirs found. "
                f"Check EXP_DB_NAME={EXP_DB_NAME} and INTAN_BASE_PATH."
            )

    def _build_spike_detector(self):
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

    def _build_parser(self) -> NafcArtifactRemovalParser:
        return NafcArtifactRemovalParser(
            preprocessor=BaselineDriftPreprocessor(highpass_hz=5.0),
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
            spike_detector=self._build_spike_detector(),
            post_artifact_blank_s=POST_ARTIFACT_BLANK_S,
        )

    def test_visualize_artifact_windows_per_estim_spec(self):
        """
        Run the pipeline on each selected recording, then plot:
          - Artifact-window examples grouped by EStimSpecId.
          - Spike-near-artifact diagnostic (should show zero spikes in blank zone).
          - Pooled artifact-amplitude / width histograms.
        """
        parser = self._build_parser()
        all_results: List[dict] = []
        results_by_spec: Dict[str, List[dict]] = defaultdict(list)

        for i, rec in enumerate(self.selected):
            try:
                res = _process_one_recording(
                    rec, CHANNEL_NAME, parser, MAX_SECONDS_TO_LOAD,
                )
            except Exception as exc:
                print(f"[{i+1}] {os.path.basename(rec['recording_dir'])}: "
                      f"FAILED — {exc}")
                continue
            if res is None:
                print(f"[{i+1}] channel {CHANNEL_NAME} not present, skipping")
                continue

            n = len(res['preprocessed'])
            spec = rec['estim_spec_id']
            print(
                f"[{i+1}] EStimSpecId={spec}  "
                f"{n/res['sample_rate']:.2f}s  "
                f"{len(res['artifacts'])} artifacts  "
                f"{len(res['spike_samples'])} spikes  "
                f"spike_thr={res['spike_threshold']:.1f} uV  "
                f"blank={res['artifact_blank_mask'].sum()/res['sample_rate']*1e3:.1f}ms blanked"
            )
            all_results.append(res)
            results_by_spec[spec].append(res)

        self.assertTrue(all_results, "no recordings processed successfully")

        _plot_per_spec_windows(results_by_spec, CHANNEL_NAME,
                               N_WINDOWS_PER_SPEC, WINDOW_HALFWIDTH_MS)
        _plot_spike_near_artifact_diagnostic(all_results, CHANNEL_NAME)
        _plot_pooled_stats(all_results, CHANNEL_NAME)
        plt.show()

        # Verify no spikes fall inside any blank zone.
        for res in all_results:
            blank_mask = res['artifact_blank_mask']
            spikes = res['spike_samples']
            spikes_in_blank = blank_mask[spikes].sum() if len(spikes) else 0
            self.assertEqual(
                spikes_in_blank, 0,
                f"recording {res['recording_dir']}: "
                f"{spikes_in_blank} spikes inside blank zone",
            )

    def test_parser_returns_nafc_trial_events(self):
        """Parse one recording end-to-end. Set SKIP_FULL_PARSE=1 to skip."""
        if os.environ.get("SKIP_FULL_PARSE") == "1":
            self.skipTest("SKIP_FULL_PARSE=1")

        parser = self._build_parser()
        events = parser.parse(self.selected[0]['recording_dir'])

        self.assertIsInstance(events, NafcTrialEvents)
        self.assertGreater(events.sample_rate, 0)
        self.assertTrue(events.spikes_by_channel)

        total = sum(len(v) for v in events.spikes_by_channel.values())
        print(f"task_id={events.task_id}  "
              f"channels={len(events.spikes_by_channel)}  "
              f"total spikes={total}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

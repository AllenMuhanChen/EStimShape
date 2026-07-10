"""
Compare baseline response-per-generation profiles across spike-detection methods.

Motivation
----------
Baseline stimuli are re-shown every generation to track how the neural
population's response to a fixed stimulus set drifts over an experiment. That
drift is used as a proxy for global excitability. But some of the drift may be
an artifact of the spike-detection threshold rather than true excitability
change: Intan's spike.dat uses a -4x RMS threshold computed early in the GA and
seldom updated, so slow noise-floor changes or small electrode drift can silently
add/remove units from the count.

This module renders the same baseline profile plot (one line per generation,
x = each baseline parent's Gen-1 response, y = that baseline's response in
Gen-N) side by side for several spike-detection methods, so the drift can be
compared across detectors.

Step 1 methods
--------------
  Column A - "Raw Intan spikes": the per-trial per-channel spike rates already
             stored in the repository (RawSpikeResponses), i.e. Intan's spike.dat.
  Column B - "-4x RMS / N trials": re-detected from the raw wideband
             (amplifier.dat), recomputing the negative -threshold_rms x RMS
             threshold once per block of `block_size` consecutive trials WITHIN
             each recording file.

Both columns share the exact same trials and metadata (StimType, GenId,
ParentId, StimSpecId) pulled from the repository; only the per-trial response
value differs, so any difference in the profiles is attributable to the
detector, not to trial selection.

Later steps can register additional detectors (NEO, drift-robust variants) by
appending to the `methods` list in `run_comparison`.
"""

from __future__ import annotations

import hashlib
import os
import pickle
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd
from matplotlib import cm
from matplotlib import pyplot as plt

from src.intan.MultiFileParser import find_files_containing_task_ids
from src.lfp.spike_waveform_features import highpass_filter
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context

ChannelSpec = str | list


# ===========================================================================
# Wideband re-detection: negative -N x RMS, threshold recomputed per trial-block
# ===========================================================================

def _detect_negative_crossings(segment: np.ndarray, threshold: float,
                               refractory_samples: int) -> np.ndarray:
    """Detect negative-going crossings of `threshold` (threshold < 0).

    Snaps each crossing to the local trough within the refractory window and
    enforces the refractory period between successive spikes. Returns sample
    indices into `segment`.
    """
    if segment.size < 2:
        return np.empty(0, dtype=int)

    below = segment < threshold
    crossings = np.where(np.diff(below.astype(np.int8)) == 1)[0] + 1
    if len(crossings) == 0:
        return np.empty(0, dtype=int)

    n = len(segment)
    troughs = []
    for c in crossings:
        window_end = min(c + refractory_samples, n)
        troughs.append(c + int(np.argmin(segment[c:window_end])))
    troughs = np.asarray(troughs, dtype=int)

    kept = [troughs[0]]
    for s in troughs[1:]:
        if s - kept[-1] >= refractory_samples:
            kept.append(s)
    return np.asarray(kept, dtype=int)


def _normalize_channel(ch) -> str:
    """Normalize a channel name to the repository/cluster 'A-0XX' form.

    Handles Channel-enum values ('A-002'), underscore variants ('A_002'), and
    plain cluster strings uniformly so lookups match across sources.
    """
    return str(ch).replace('_', '-').upper()


class PeriodicRmsMUAParser:
    """
    Re-detect MUA spikes from raw wideband (amplifier.dat), recomputing the
    negative -threshold_rms x RMS threshold once per block of `block_size`
    consecutive trials *within each recording file*.

    Produces the same shape as `MultiFileParser.parse`:
        spikes_by_channel_by_task_id : {task_id: {Channel: [abs spike times, s]}}
        epochs_by_task_id            : {task_id: (start_s, end_s)}
        sample_rate                  : float

    RMS is computed on the high-pass-filtered wideband spanning each block
    (first trial start -> last trial end), mimicking how Intan estimates the
    noise floor over a stretch of streaming data, but refreshed every
    `block_size` trials instead of once per session.
    """

    def __init__(self,
                 block_size: int = 100,
                 threshold_rms: float = 4.0,
                 highpass_hz: float = 300.0,
                 refractory_sec: float = 0.001,
                 to_cache: bool = True,
                 cache_dir: Optional[str] = None):
        self.block_size = block_size
        self.threshold_rms = threshold_rms
        self.highpass_hz = highpass_hz
        self.refractory_sec = refractory_sec
        self.to_cache = to_cache
        self.cache_dir = cache_dir
        self.sample_rate: Optional[float] = None

    # ---- parameter signature so caches from different settings never collide --
    def _param_key(self, task_ids: list[int]) -> str:
        payload = (
            f"block={self.block_size}|rms={self.threshold_rms}|"
            f"hp={self.highpass_hz}|refrac={self.refractory_sec}|"
            f"tasks={sorted(int(t) for t in task_ids)}"
        )
        return hashlib.md5(payload.encode()).hexdigest()[:16]

    def parse(self, task_ids: list[int], intan_files_dir: str):
        task_ids = [int(t) for t in task_ids]
        task_id_set = set(task_ids)

        if self.to_cache and self.cache_dir is not None:
            cached = self._load_cache(task_ids)
            if cached is not None:
                self.sample_rate = cached['sample_rate']
                return (cached['spikes_by_channel_by_task_id'],
                        cached['epochs_by_task_id'],
                        cached['sample_rate'])

        matching_dirs = find_files_containing_task_ids(task_id_set, intan_files_dir)
        if not matching_dirs:
            raise ValueError(f"No Intan files found containing task IDs {task_ids}")

        spikes_by_channel_by_task_id: dict[int, dict] = {}
        epochs_by_task_id: dict[int, tuple] = {}

        for dir_path in sorted(matching_dirs):
            file_spikes, file_epochs, file_sr = self._parse_one_dir(dir_path, task_id_set)
            if self.sample_rate is None:
                self.sample_rate = file_sr
            elif file_sr != self.sample_rate:
                raise ValueError(
                    f"Inconsistent sample rates: {self.sample_rate} vs {file_sr}")

            for task_id, channel_spikes in file_spikes.items():
                spikes_by_channel_by_task_id[task_id] = channel_spikes
                epochs_by_task_id[task_id] = file_epochs[task_id]

        if self.to_cache and self.cache_dir is not None and spikes_by_channel_by_task_id:
            self._save_cache(task_ids, spikes_by_channel_by_task_id, epochs_by_task_id)

        return spikes_by_channel_by_task_id, epochs_by_task_id, self.sample_rate

    def _parse_one_dir(self, dir_path: str, task_id_set: set[int]):
        # Lazy clat imports: the module should import even where clat is absent.
        from clat.intan.amplifiers import read_amplifier_data_with_memmap
        from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
        from clat.intan.marker_channels import epoch_using_combined_marker_channels

        sample_rate, amplifier_channels = self._read_header(dir_path)

        amplifier_path = os.path.join(dir_path, "amplifier.dat")
        digital_in_path = os.path.join(dir_path, "digitalin.dat")
        notes_path = os.path.join(dir_path, "notes.txt")

        # Epoch boundaries (raw sample indices) keyed by task_id
        stim_epochs = epoch_using_combined_marker_channels(
            digital_in_path, false_negative_correction_duration=2)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(
            notes_path, stim_epochs,
            require_trial_complete=False,
            is_output_first_instance=False)

        # Ordered list of (task_id, start_idx, end_idx) for trials we care about
        trials = []
        for task_id, epoch_indices in epochs_for_task_ids.items():
            if epoch_indices is None or task_id not in task_id_set:
                continue
            trials.append((task_id, int(epoch_indices[0]), int(epoch_indices[1])))
        trials.sort(key=lambda t: t[1])

        spikes_by_channel_by_task_id: dict[int, dict] = {
            t[0]: {} for t in trials}
        epochs_by_task_id: dict[int, tuple] = {
            t[0]: (t[1] / sample_rate, t[2] / sample_rate) for t in trials}

        if not trials:
            return spikes_by_channel_by_task_id, epochs_by_task_id, sample_rate

        # Contiguous blocks of `block_size` trials (within this file)
        blocks = [trials[i:i + self.block_size]
                  for i in range(0, len(trials), self.block_size)]

        refractory_samples = max(1, int(self.refractory_sec * sample_rate))
        channel_to_raw = read_amplifier_data_with_memmap(amplifier_path, amplifier_channels)

        for channel, raw in channel_to_raw.items():
            filtered = highpass_filter(np.asarray(raw, dtype=np.float64),
                                       sample_rate, self.highpass_hz)
            n = len(filtered)

            for block in blocks:
                b_start = max(0, block[0][1])
                b_end = min(n, block[-1][2])
                if b_end <= b_start:
                    continue
                rms = float(np.sqrt(np.mean(filtered[b_start:b_end] ** 2)))
                threshold = -self.threshold_rms * rms

                for task_id, s_idx, e_idx in block:
                    s = max(0, s_idx)
                    e = min(n, e_idx)
                    if e <= s:
                        spikes_by_channel_by_task_id[task_id][channel] = []
                        continue
                    segment = filtered[s:e]
                    local = _detect_negative_crossings(
                        segment, threshold, refractory_samples)
                    abs_times = (s + local) / sample_rate
                    spikes_by_channel_by_task_id[task_id][channel] = list(abs_times)

        return spikes_by_channel_by_task_id, epochs_by_task_id, sample_rate

    @staticmethod
    def _read_header(dir_path: str) -> tuple[float, list]:
        """Read amplifier sample rate + channel metadata from info.rhd (or .rhs)."""
        rhd_path = os.path.join(dir_path, "info.rhd")
        rhs_path = os.path.join(dir_path, "info.rhs")
        if os.path.exists(rhd_path):
            from clat.intan.rhd.load_intan_rhd_format import read_data
            header_path = rhd_path
        elif os.path.exists(rhs_path):
            from clat.intan.rhs.load_intan_rhs_format import read_data
            header_path = rhs_path
        else:
            raise FileNotFoundError(
                f"No info.rhd or info.rhs header found in {dir_path}")
        data = read_data(header_path)
        sample_rate = data['frequency_parameters']['amplifier_sample_rate']
        amplifier_channels = data['amplifier_channels']
        return sample_rate, amplifier_channels

    # ---- caching -----------------------------------------------------------
    def _cache_path(self, task_ids: list[int]) -> str:
        return os.path.join(self.cache_dir,
                            f"periodic_rms_{self._param_key(task_ids)}.pkl")

    def _load_cache(self, task_ids: list[int]):
        path = self._cache_path(task_ids)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception as exc:
            print(f"Failed to load periodic-RMS cache {path}: {exc}")
            return None

    def _save_cache(self, task_ids, spikes_by_channel_by_task_id, epochs_by_task_id):
        os.makedirs(self.cache_dir, exist_ok=True)
        path = self._cache_path(task_ids)
        with open(path, 'wb') as f:
            pickle.dump({
                'spikes_by_channel_by_task_id': spikes_by_channel_by_task_id,
                'epochs_by_task_id': epochs_by_task_id,
                'sample_rate': self.sample_rate,
            }, f)


def compute_rates_by_task(spikes_by_channel_by_task_id: dict,
                          epochs_by_task_id: dict) -> dict[int, dict[str, float]]:
    """Per-trial per-channel spike RATE (Hz) counted within the epoch window.

    Mirrors `IntanSpikeRateByChannelField`: count spikes with times in
    [epoch_start, epoch_end] and divide by the epoch duration. Channel keys are
    normalized to the repository 'A-0XX' form.
    """
    rates_by_task: dict[int, dict[str, float]] = {}
    for task_id, spikes_by_channel in spikes_by_channel_by_task_id.items():
        epoch = epochs_by_task_id.get(task_id)
        if epoch is None:
            continue
        start_s, end_s = epoch
        duration = end_s - start_s
        if duration <= 0:
            continue
        rates: dict[str, float] = {}
        for channel, times in spikes_by_channel.items():
            t = np.asarray(times, dtype=float)
            count = int(np.sum((t >= start_s) & (t <= end_s)))
            key = _normalize_channel(getattr(channel, 'value', channel))
            rates[key] = count / duration
        rates_by_task[task_id] = rates
    return rates_by_task


# ===========================================================================
# Shared response extraction + baseline profile computation
# ===========================================================================

def add_response_column(df: pd.DataFrame, channel: ChannelSpec) -> pd.DataFrame:
    """Attach a scalar 'Response' column summed over the requested channel(s)."""
    channels = channel if isinstance(channel, list) else [channel]
    norm_channels = [_normalize_channel(c) for c in channels]

    def extract(x):
        if not isinstance(x, dict):
            return 0.0
        norm_x = {_normalize_channel(k): v for k, v in x.items()}
        return float(sum(norm_x.get(c, 0.0) or 0.0 for c in norm_channels))

    out = df.copy()
    out['Response'] = out['Spike Rate by channel'].apply(extract)
    return out


def compute_baseline_profile(df: pd.DataFrame):
    """Compute the per-(ParentId, GenId) baseline responses and the Gen-1 reference.

    Returns (avg_baseline, gen1_avg, avg_catch). `avg_baseline` has columns
    ParentId, GenId, Response, Gen1Response.
    """
    baseline = df[df['StimType'] == 'BASELINE'].copy()
    if baseline.empty:
        raise ValueError("No BASELINE stimuli found in the data.")
    if 'ParentId' not in baseline.columns:
        raise ValueError("ParentId column missing — cannot link baselines to Gen-1 parents.")

    avg_baseline = (baseline
                    .groupby(['ParentId', 'GenId'])['Response']
                    .mean()
                    .reset_index())

    gen1_avg = (df[df['GenId'] == 1]
                .groupby('StimSpecId')['Response']
                .mean()
                .rename('Gen1Response'))
    avg_baseline['Gen1Response'] = avg_baseline['ParentId'].map(gen1_avg)

    catch = df[df['StimType'] == 'CATCH']
    avg_catch = (catch
                 .groupby('GenId')['Response']
                 .mean()
                 .rename('AvgCatch')
                 .reset_index())

    return avg_baseline, gen1_avg, avg_catch


def plot_baseline_profile_onto(ax: plt.Axes,
                               avg_baseline: pd.DataFrame,
                               avg_catch: pd.DataFrame,
                               gen_color: dict,
                               title: str) -> None:
    """Baseline / catch response profiles per generation, on a single Axes.

    x = each baseline parent's Gen-1 response value; y = that baseline's mean
    response in Gen-N. One line per generation. The dashed black line is the
    Gen-1 reference (y = x). Mirrors subplot 1 of
    `BaselineAnalysis._plot_baseline_curves`.
    """
    avg_baseline = avg_baseline.copy()
    parent_gen1 = (avg_baseline[['ParentId', 'Gen1Response']]
                   .drop_duplicates('ParentId')
                   .sort_values('Gen1Response')
                   .reset_index(drop=True))
    x_map = parent_gen1.set_index('ParentId')['Gen1Response']
    avg_baseline['StimX'] = avg_baseline['ParentId'].map(x_map)

    gen1_catch_val = avg_catch.loc[avg_catch['GenId'] == 1, 'AvgCatch']
    if len(gen1_catch_val):
        catch_x = gen1_catch_val.values[0]
    elif len(parent_gen1):
        catch_x = parent_gen1['Gen1Response'].min() - parent_gen1['Gen1Response'].std()
    else:
        catch_x = 0.0

    all_generations = sorted(set(avg_baseline['GenId'].unique()) |
                             set(avg_catch['GenId'].unique()))

    # Gen-1 reference: y = gen-1 response, x = gen-1 response -> diagonal
    gen1_catch_y = gen1_catch_val.values[0] if len(gen1_catch_val) else np.nan
    ax.plot([catch_x] + list(parent_gen1['Gen1Response']),
            [gen1_catch_y] + list(parent_gen1['Gen1Response']),
            marker='o', linewidth=2, markersize=5,
            color='black', linestyle='--', label='Gen 1 (reference)', zorder=3)

    for gen_id in [g for g in all_generations if g > 1]:
        catch_row = avg_catch[avg_catch['GenId'] == gen_id]
        catch_val = catch_row['AvgCatch'].values[0] if len(catch_row) else np.nan
        gen_data = avg_baseline[avg_baseline['GenId'] == gen_id].sort_values('StimX')
        ax.plot([catch_x] + list(gen_data['StimX']),
                [catch_val] + list(gen_data['Response']),
                marker='o', linewidth=1.5, markersize=4,
                color=gen_color.get(gen_id, 'gray'), label=f'Gen {gen_id}')

    if len(parent_gen1):
        tick_xs = [catch_x] + list(parent_gen1['Gen1Response'])
        tick_labels = ([f'{catch_x:.1f}\n(catch)'] +
                       [f'{v:.1f}' for v in parent_gen1['Gen1Response']])
        ax.set_xticks(tick_xs)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
    ax.set_xlabel('Gen-1 response (Hz)')
    ax.set_ylabel('Avg Response (Hz)')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)


# ===========================================================================
# Detection-method definitions + comparison runner
# ===========================================================================

@dataclass
class DetectionMethod:
    """A named spike-detection method that yields a response-bearing DataFrame.

    `build` receives (session_id, base_df, channel) and must return a copy of
    base_df with a scalar 'Response' column populated. `base_df` already carries
    the trial metadata (StimType, GenId, ParentId, StimSpecId, TaskId) and the
    raw-Intan 'Spike Rate by channel' column.
    """
    name: str
    build: Callable[[str, pd.DataFrame, ChannelSpec], pd.DataFrame]


def _method_raw_intan(session_id: str, base_df: pd.DataFrame,
                      channel: ChannelSpec) -> pd.DataFrame:
    """Column A: use the repository's spike.dat-derived per-channel rates."""
    return add_response_column(base_df, channel)


def make_periodic_rms_method(block_size: int = 100,
                             threshold_rms: float = 4.0,
                             highpass_hz: float = 300.0) -> DetectionMethod:
    """Column B: re-detect from wideband with -N x RMS recomputed per trial-block."""

    def build(session_id: str, base_df: pd.DataFrame,
              channel: ChannelSpec) -> pd.DataFrame:
        task_ids = [int(t) for t in base_df['TaskId'].tolist()]
        cache_dir = os.path.join(context.ga_parsed_spikes_path, "periodic_rms_mua")
        parser = PeriodicRmsMUAParser(
            block_size=block_size,
            threshold_rms=threshold_rms,
            highpass_hz=highpass_hz,
            to_cache=True,
            cache_dir=cache_dir,
        )
        spikes_by_task, epochs_by_task, _sr = parser.parse(
            task_ids, context.ga_intan_path)
        rates_by_task = compute_rates_by_task(spikes_by_task, epochs_by_task)

        df = base_df.copy()
        df['Spike Rate by channel'] = df['TaskId'].map(
            lambda tid: rates_by_task.get(int(tid), {}))
        return add_response_column(df, channel)

    return DetectionMethod(
        name=f"-4x RMS (negative)\nrecomputed / {block_size} trials",
        build=build,
    )


def run_comparison(session_id: Optional[str] = None,
                   channel: Optional[ChannelSpec] = None,
                   methods: Optional[list[DetectionMethod]] = None,
                   block_size: int = 100,
                   save_path: Optional[str] = None):
    """Render baseline profiles for each detection method, one column per method.

    Defaults: current session (from context.ga_database), cluster channels
    summed, and the two step-1 methods (raw Intan vs -4x RMS per `block_size`
    trials).
    """
    if session_id is None:
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    if channel is None:
        channel = read_cluster_channels(session_id)
    if methods is None:
        methods = [
            DetectionMethod("Raw Intan spikes\n(spike.dat, -4x RMS seldom updated)",
                            _method_raw_intan),
            make_periodic_rms_method(block_size=block_size),
        ]

    print(f"Loading repository trial data for session {session_id} ...")
    base_df = import_from_repository(session_id, "ga", "GAStimInfo", "RawSpikeResponses")

    channel_label = ', '.join(channel) if isinstance(channel, list) else channel
    channel_str = '_'.join(channel) if isinstance(channel, list) else channel

    # Build each method's response DataFrame + baseline profile
    method_results = []
    all_generations: set = set()
    for method in methods:
        print(f"Building method: {method.name!r}")
        df = method.build(session_id, base_df, channel)
        avg_baseline, _gen1_avg, avg_catch = compute_baseline_profile(df)
        all_generations |= set(avg_baseline['GenId'].unique())
        all_generations |= set(avg_catch['GenId'].unique())
        method_results.append((method.name, avg_baseline, avg_catch))

    # Shared generation color map across all columns for comparability
    gens_sorted = sorted(all_generations)
    colors = cm.viridis(np.linspace(0, 1, max(len(gens_sorted), 1)))
    gen_color = {g: colors[i] for i, g in enumerate(gens_sorted)}

    n = len(method_results)
    fig, axes = plt.subplots(1, n, figsize=(7 * n, 6), squeeze=False, sharey=True)
    fig.suptitle(
        f'Baseline response-per-generation profiles by spike-detection method\n'
        f'Session: {session_id}  |  Channel(s): {channel_label}',
        fontsize=13)

    for i, (name, avg_baseline, avg_catch) in enumerate(method_results):
        plot_baseline_profile_onto(axes[0][i], avg_baseline, avg_catch,
                                   gen_color, title=name)

    # One shared legend (generations) to the right
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=7, loc='center right',
               bbox_to_anchor=(1.0, 0.5))
    fig.tight_layout(rect=(0, 0, 0.92, 1))

    if save_path is None:
        save_dir = f"/home/connorlab/Documents/plots/{session_id}"
        os.makedirs(save_dir, exist_ok=True)
        save_path = f"{save_dir}/{channel_str}_baseline_detection_comparison.png"
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved detection-comparison plot to {save_path}")

    plt.show()
    return fig


def main():
    run_comparison(block_size=100)


if __name__ == "__main__":
    main()

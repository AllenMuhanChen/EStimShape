"""
NAFC parser that detects spikes from raw amplifier data after removing
stimulus artifacts, instead of reading pre-computed spike.dat.

The parser is interchangeable with :class:`NafcNeuralParser`: both
implement :class:`NafcParserBase` and return :class:`NafcTrialEvents`.

The artifact-removal pipeline follows Heffer & Fallon (2008):

    raw signal
       -> SignalPreprocessor       (DC removal + 5 Hz HP)
       -> ArtifactDetector         (threshold-crossing)
       -> ArtifactRemover          (sample-and-interpolate)
       -> SpikeDetector            (-N * RMS / MAD on MUA band)

Each stage is a pluggable strategy so alternative methods can be swapped
in without changing the parser itself.
"""

import os
import pickle
from typing import Dict, List, Optional

import numpy as np

from clat.intan.amplifiers import read_amplifier_data_with_memmap
from clat.intan.marker_channels import read_digitalin_file
from clat.intan.rhs.load_intan_rhs_format import read_data

from src.analysis.nafc.neural.artifact_removal import (
    ArtifactDetector, ArtifactEvent, ArtifactRemover,
    BaselineDriftPreprocessor, RmsThresholdSpikeDetector,
    SampleInterpolateRemover, SignalPreprocessor, SpikeDetector,
    ThresholdArtifactDetector,
)
from src.analysis.nafc.neural.nafc_parser_base import NafcParserBase
from src.analysis.nafc.neural.nafc_trial_events import NafcTrialEvents


def _task_id_from_dir(recording_dir: str) -> int:
    basename = os.path.basename(recording_dir.rstrip('/\\'))
    return int(basename.split('_')[0])


def _rising_edges(channel_data: np.ndarray) -> np.ndarray:
    return np.where(np.diff(channel_data.astype(np.int8)) == 1)[0] + 1


def _falling_edges(channel_data: np.ndarray) -> np.ndarray:
    return np.where(np.diff(channel_data.astype(np.int8)) == -1)[0] + 1


def _first_as_seconds(indices: np.ndarray, sample_rate: float) -> Optional[float]:
    if len(indices) == 0:
        return None
    return float(indices[0]) / sample_rate


class NafcArtifactRemovalParser(NafcParserBase):
    """
    Parse a NAFC Intan recording by detecting spikes from raw amplifier
    data after stimulus-artifact removal.

    The four pipeline stages can be swapped via the constructor:

        preprocessor       : SignalPreprocessor   (default: BaselineDriftPreprocessor)
        artifact_detector  : ArtifactDetector     (default: ThresholdArtifactDetector)
        artifact_remover   : ArtifactRemover      (default: SampleInterpolateRemover)
        spike_detector     : SpikeDetector        (default: RmsThresholdSpikeDetector)

    The directory layout and digital-channel mapping are identical to
    :class:`NafcNeuralParser`. Caching, if enabled, writes a separate
    pickle so the two parsers do not collide.
    """

    CACHE_SUFFIX = "_parsed_nafc_trial_artifact_removed.pkl"

    def __init__(
        self,
        preprocessor: Optional[SignalPreprocessor] = None,
        artifact_detector: Optional[ArtifactDetector] = None,
        artifact_remover: Optional[ArtifactRemover] = None,
        spike_detector: Optional[SpikeDetector] = None,
        post_artifact_blank_s: float = 0.002,
        to_cache: bool = False,
        cache_dir: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        post_artifact_blank_s : float
            Seconds added on each side of every artifact window before and
            after spike detection. Serves two purposes:

            1. **Noise-mask** — these samples are excluded from the RMS/MAD
               noise estimate so zeroed regions don't pull the threshold down.
            2. **Post-filter blank** — after bandpass-filtering the cleaned
               signal the same windows are re-zeroed, preventing filter
               edge-effects (ringing at removal boundaries) from being
               detected as spikes.

            Default 2 ms is conservative; reduce if you are losing genuine
            short-latency responses.
        """
        self.preprocessor = preprocessor or BaselineDriftPreprocessor()
        self.artifact_detector = artifact_detector or ThresholdArtifactDetector()
        self.artifact_remover = artifact_remover or SampleInterpolateRemover()
        self.spike_detector = spike_detector or RmsThresholdSpikeDetector()
        self.post_artifact_blank_s = post_artifact_blank_s
        self.to_cache = to_cache
        self.cache_dir = cache_dir

    # -----------------------------------------------------------------------
    # NafcParserBase
    # -----------------------------------------------------------------------

    def parse(self, recording_dir: str) -> NafcTrialEvents:
        task_id = _task_id_from_dir(recording_dir)

        if self.to_cache and self.cache_dir is not None:
            cached = self._load_cache(task_id)
            if cached is not None:
                return cached

        rhs = self._read_rhs(recording_dir)
        sample_rate = float(rhs['frequency_parameters']['amplifier_sample_rate'])
        amplifier_channels = rhs['amplifier_channels']

        channel_to_raw = self._read_amplifier(recording_dir, amplifier_channels)
        spikes_by_channel = self._detect_spikes_all_channels(channel_to_raw, sample_rate)

        events_dict = self._read_events(recording_dir, sample_rate)
        result = NafcTrialEvents(
            task_id=task_id,
            sample_rate=sample_rate,
            spikes_by_channel=spikes_by_channel,
            **events_dict,
        )

        if self.to_cache and self.cache_dir is not None:
            self._cache(task_id, result)

        return result

    # -----------------------------------------------------------------------
    # Per-channel pipeline (also useful as a public hook for tests/plots)
    # -----------------------------------------------------------------------

    def process_channel(
        self, raw_signal: np.ndarray, sample_rate: float,
    ) -> Dict:
        """
        Run the full artifact-removal + spike-detection pipeline on a
        single channel and return all intermediate products.

        Two correctness guarantees are enforced around artifact windows
        (width = detector event + post_artifact_blank_s on each side):

        * **Noise-mask** — the threshold (RMS/MAD) is computed only from
          samples *outside* those windows, so zeroed regions don't lower
          the noise estimate and make the threshold too permissive.
        * **Post-filter blank** — after bandpass-filtering the cleaned
          signal the same windows are re-zeroed so filter ringing at the
          removal boundaries cannot be detected as spikes.

        Returns
        -------
        dict with keys:
            preprocessed        : np.ndarray
            artifacts           : List[ArtifactEvent]
            cleaned             : np.ndarray
            filtered_for_spikes : np.ndarray  (bandpass-filtered, re-blanked)
            spike_samples       : np.ndarray (int)
            spike_times         : np.ndarray (float, seconds)
            artifact_threshold  : float or None
            spike_threshold     : float
            artifact_blank_mask : np.ndarray (bool) — True where spikes CAN occur
        """
        preprocessed = self.preprocessor.preprocess(raw_signal, sample_rate)
        artifacts: List[ArtifactEvent] = self.artifact_detector.detect(
            preprocessed, sample_rate,
        )
        cleaned = self.artifact_remover.remove(preprocessed, artifacts, sample_rate)

        # Build blank mask: True = sample is in an artifact-exclusion window.
        blank_samples = max(int(round(self.post_artifact_blank_s * sample_rate)), 0)
        n = len(cleaned)
        blank_mask = np.zeros(n, dtype=bool)
        for ev in artifacts:
            lo = max(ev.start_sample - blank_samples, 0)
            hi = min(ev.end_sample + blank_samples, n)
            blank_mask[lo:hi] = True
        noise_mask = ~blank_mask  # samples valid for noise estimation

        # Bandpass-filter the cleaned signal, then re-blank artifact windows
        # to prevent filter ringing at removal boundaries from being detected.
        filtered = self.spike_detector.bandpass(cleaned, sample_rate)
        filtered_for_spikes = filtered.copy()
        filtered_for_spikes[blank_mask] = 0.0

        # Spike detection with noise estimated only from non-artifact samples.
        spike_samples = self.spike_detector.detect_on_filtered(
            filtered_for_spikes, sample_rate, noise_mask=noise_mask,
        )
        spike_threshold = self.spike_detector.compute_threshold(
            filtered_for_spikes, noise_mask=noise_mask,
        )

        spike_times = spike_samples / sample_rate

        artifact_threshold = None
        if isinstance(self.artifact_detector, ThresholdArtifactDetector):
            artifact_threshold = self.artifact_detector.compute_threshold(preprocessed)

        return {
            'preprocessed': preprocessed,
            'artifacts': artifacts,
            'cleaned': cleaned,
            'filtered_for_spikes': filtered_for_spikes,
            'spike_samples': spike_samples,
            'spike_times': spike_times,
            'artifact_threshold': artifact_threshold,
            'spike_threshold': spike_threshold,
            'artifact_blank_mask': blank_mask,
        }

    # -----------------------------------------------------------------------
    # I/O helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _read_rhs(recording_dir: str) -> dict:
        return read_data(os.path.join(recording_dir, "info.rhs"))

    @staticmethod
    def _read_amplifier(recording_dir: str, amplifier_channels: list) -> dict:
        amplifier_path = os.path.join(recording_dir, "amplifier.dat")
        return read_amplifier_data_with_memmap(amplifier_path, amplifier_channels)

    @staticmethod
    def _read_events(recording_dir: str, sample_rate: float) -> dict:
        digital_in_path = os.path.join(recording_dir, "digitalin.dat")
        digital_in = read_digitalin_file(digital_in_path)
        sample_ch = np.array(digital_in[0])
        choices_ch = np.array(digital_in[1])
        return {
            'sample_on':   _first_as_seconds(_rising_edges(sample_ch),  sample_rate),
            'sample_off':  _first_as_seconds(_falling_edges(sample_ch), sample_rate),
            'choices_on':  _first_as_seconds(_rising_edges(choices_ch),  sample_rate),
            'choices_off': _first_as_seconds(_falling_edges(choices_ch), sample_rate),
        }

    def _detect_spikes_all_channels(
        self, channel_to_raw: dict, sample_rate: float,
    ) -> Dict:
        spikes_by_channel: Dict = {}
        for channel, raw in channel_to_raw.items():
            result = self.process_channel(raw, sample_rate)
            spikes_by_channel[channel] = result['spike_times'].tolist()
        return spikes_by_channel

    # -----------------------------------------------------------------------
    # Caching
    # -----------------------------------------------------------------------

    def _cache_path(self, task_id: int) -> str:
        return os.path.join(self.cache_dir, f"{task_id}{self.CACHE_SUFFIX}")

    def _cache(self, task_id: int, events: NafcTrialEvents) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self._cache_path(task_id), 'wb') as f:
            pickle.dump(events, f)

    def _load_cache(self, task_id: int) -> Optional[NafcTrialEvents]:
        path = self._cache_path(task_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception as exc:
            print(
                f"NafcArtifactRemovalParser: failed to load cache "
                f"for task_id={task_id}: {exc}"
            )
            return None

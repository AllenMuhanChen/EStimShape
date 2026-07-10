from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

import numpy as np

from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.pga.stim_types import StimType


@dataclass(kw_only=True)
class GAResponseProcessor:
    db_util: MultiGaDbUtil
    repetition_combination_strategy: Callable[[list[float]], float]
    cluster_combination_strategy: Callable[[list[float]], int]  # TODO: this currently isn't being
    # used, but it should be used to combine the responses from the different channels into a single

    # When set, per-channel response vectors are read from MUAChannelResponses
    # (filtered by this metric) instead of ChannelResponses. Leaves every other
    # step — repetition/cluster combination, baseline normalization — unchanged,
    # so the MUA source composes with the baseline-normalizing subclasses.
    mua_metric: str | None = None

    def process_to_db(self, ga_name: str) -> None:
        # For each stim, combine their cluster responses for each repetition
        responses_for_each_stim_id = self._process_clusters(ga_name)

        # Process repetitions for each stim into driving response
        driving_response_for_each_stim_id = self._process_repetitions(responses_for_each_stim_id)

        # Write processed responses to database
        for stim_id, driving_response in driving_response_for_each_stim_id.items():
            self.db_util.update_driving_response(stim_id, float(driving_response))

    def fetch_response_vector_for_repetitions_of(self, stim_id, *, ga_name: str) -> list[float]:
        """
        response vector is defined as the response for each repetition of stim_id
        one response number is obtaind by combining the responses from all the cluster channels
        according to the cluster_combination_strategy
        """
        cluster_channels = self.db_util.read_current_cluster(ga_name)

        # Get the vector(responses to all the repetitions of stim_id) for each cluster channel
        vector_per_channel = {}
        for channel in cluster_channels:
            if self.mua_metric is not None:
                responses_per_repetition = self.db_util.read_mua_responses_for(
                    stim_id, channel.value, self.mua_metric)
            else:
                responses_per_repetition = self.db_util.read_responses_for(stim_id, channel=channel.value)
            vector_per_channel[channel] = responses_per_repetition

        # Combine the vectors for each channel into a single response vector
        response_vector = []
        number_of_repetitions = len(list(vector_per_channel.values())[0])
        # For each repetition
        for i in range(number_of_repetitions):

            # Save the responses for the current repetition from each channel
            # so we can combine them
            responses_for_current_rep_across_channels = []

            # Do the combining across channels
            for channel, responses_for_repetition in vector_per_channel.items():
                responses_for_current_rep_across_channels.append(responses_for_repetition[i])
            combined_response = self.cluster_combination_strategy(responses_for_current_rep_across_channels)
            response_vector.append(combined_response)

        response_vector = [float(f) for f in response_vector]
        return response_vector

    def _process_clusters(self, ga_name) -> dict[int, list[float]]:
        stims_to_process = self.db_util.read_stims_with_no_driving_response()

        response_vector_for_each_stim: dict[int, list[float]] = {}
        for stim_id in stims_to_process:
            responses_for_stim_id = self.fetch_response_vector_for_repetitions_of(stim_id, ga_name=ga_name)

            response_vector_for_each_stim[stim_id] = responses_for_stim_id

        return response_vector_for_each_stim

    def _process_repetitions(self, responses_to_process: dict[int, list[float]]) -> dict[int, float]:
        driving_responses_for_stim_ids = {}
        for stim_id, responses in responses_to_process.items():
            if not responses:
                continue
            driving_response = self.repetition_combination_strategy(responses)
            driving_responses_for_stim_ids[stim_id] = driving_response
        return driving_responses_for_stim_ids


class BaselineNormalizer:
    """
    In-memory baseline normalization. Pairs Gen-N baseline stims with their
    Gen-1 (regime-zero) parents by identity.

    Operates purely on dicts so callers can use it outside of the GA pipeline
    (e.g. analyses that already loaded stim data into a DataFrame). The
    DB-bound `BaselineNormalizeResponseProcessor` is a thin wrapper around this.
    """

    SKIP_STIM_TYPES = (
        StimType.BASELINE.value,
        "CATCH",
        StimType.REGIME_ZERO.value,
        StimType.REGIME_ZERO_2D.value,
    )

    def normalize(self,
                  driving_responses: dict[int, float],
                  stim_types: dict[int, str],
                  gen_ids: dict[int, int],
                  parent_ids: dict[int, int],
                  *,
                  strict: bool = True) -> dict[int, float]:
        """
        Return a new dict of normalized driving responses.

        Baseline, catch, and regime-zero stims pass through unchanged. If no
        regime-zero parents of baselines are found, raises ValueError when
        `strict=True`; otherwise returns responses unchanged.
        """
        baselines_by_gen: dict[int, dict[int, float]] = defaultdict(dict)
        regime_zero_parent_ids: set[int] = set()

        for stim_id, response in driving_responses.items():
            if stim_types.get(stim_id) == StimType.BASELINE.value:
                pid = parent_ids.get(stim_id)
                gid = gen_ids.get(stim_id)
                if pid is None or gid is None:
                    continue
                baselines_by_gen[gid][pid] = response
                regime_zero_parent_ids.add(pid)

        gen1_dict: dict[int, float] = {
            pid: driving_responses[pid]
            for pid in regime_zero_parent_ids
            if pid in driving_responses
        }

        if not gen1_dict:
            if strict:
                raise ValueError("No regime-zero parents of baseline stims found; cannot normalize.")
            return dict(driving_responses)

        result = dict(driving_responses)
        for stim_id, r in driving_responses.items():
            stype = stim_types.get(stim_id)
            if stype in self.SKIP_STIM_TYPES:
                continue
            gid = gen_ids.get(stim_id)
            if gid is None:
                continue
            bN_dict = baselines_by_gen.get(gid, {})
            factor = self._compute_factor(r, gid, bN_dict, baselines_by_gen, gen1_dict)
            result[stim_id] = r * factor

        return result

    @staticmethod
    def _interpolated_factor(r: float,
                             bN_dict: dict[int, float],
                             gen1_dict: dict[int, float]) -> float:
        """
        Correction factor for a stim with raw response r in the current generation.

        Builds a correction-factor curve from the baseline stim control points
        (bN → gen1/bN), then linearly interpolates at r. np.interp clamps to the
        boundary factor for responses outside [min(bN), max(bN)], so there is no
        extrapolation — the nearest boundary correction is used instead.
        """
        if r == 0:
            return 1.0
        common = sorted(set(bN_dict) & set(gen1_dict))
        if len(common) < 2:
            return 1.0
        bN_arr = np.array([bN_dict[p] for p in common])
        gen1_arr = np.array([gen1_dict[p] for p in common])
        sort_N = np.argsort(bN_arr)
        bN_sorted = bN_arr[sort_N]
        gen1_sorted = gen1_arr[sort_N]
        factors = gen1_sorted / bN_sorted
        return float(np.interp(r, bN_sorted, factors))

    def _compute_factor(self, r: float, gen_id: int, bN_dict: dict[int, float],
                        baselines_by_gen: dict[int, dict[int, float]],
                        gen1_dict: dict[int, float]) -> float:
        return self._interpolated_factor(r, bN_dict, gen1_dict)


class RankBaselineNormalizer(BaselineNormalizer):
    """
    Normalizes responses using baseline stimuli paired by rank rather than identity.

    Baseline responses in Gen N and Gen 1 are each sorted independently by response
    magnitude and paired position-by-position (lowest↔lowest, highest↔highest).
    The correction factor for a stim with response r is interpolated from that ranked
    curve, clamped at the boundaries.

    Example: Gen-1 baselines [5, 15, 20], Gen-7 baselines [1, 2, 3].
      Control points: (1, 5/1=5.0), (2, 15/2=7.5), (3, 20/3=6.67)
      Stim at r=5  → above range, clamp to 20/3 ≈ 6.67
      Stim at r=2.5 → interpolate between 7.5 and 6.67
    """

    def _compute_factor(self, r: float, gen_id: int, bN_dict: dict[int, float],
                        baselines_by_gen: dict[int, dict[int, float]],
                        gen1_dict: dict[int, float]) -> float:
        all_factors = []
        for k in range(1, gen_id):
            bk_dict = gen1_dict if k == 1 else baselines_by_gen.get(k, {})
            if not bk_dict:
                continue
            f = self._interpolated_factor(r, bN_dict, bk_dict)
            all_factors.append(f)
        return float(np.mean(all_factors)) if all_factors else 1.0

    @staticmethod
    def _interpolated_factor(r: float,
                             bN_dict: dict[int, float],
                             gen1_dict: dict[int, float]) -> float:
        if r == 0:
            return 1.0
        bN_sorted = np.sort(list(bN_dict.values()))
        gen1_sorted = np.sort(list(gen1_dict.values()))
        n = min(len(bN_sorted), len(gen1_sorted))
        if n < 2:
            return 1.0
        bN_sorted = bN_sorted[:n]
        gen1_sorted = gen1_sorted[:n]
        factors = gen1_sorted / bN_sorted
        return float(np.interp(r, bN_sorted, factors))


class BaselineNormalizeResponseProcessor(GAResponseProcessor):
    normalizer_cls: type[BaselineNormalizer] = BaselineNormalizer

    def process_to_db(self, ga_name: str) -> None:
        ready_info = self.db_util.read_ready_gas_and_generations_info()
        current_gen_id = ready_info[ga_name]
        if current_gen_id == 1:
            return super().process_to_db(ga_name)  # no normalization for gen 1 since we don't have baselines yet

        # For each stim, combine their cluster responses for each repetition
        responses_for_each_stim_id = self._process_clusters(ga_name)
        # remove empty lists (stims with no responses) to avoid issues in the next steps
        responses_for_each_stim_id = {stim_id: resp for stim_id, resp in responses_for_each_stim_id.items() if resp}

        # Process repetitions for each stim into driving response
        driving_response_for_each_stim_id = self._process_repetitions(responses_for_each_stim_id)

        # Pull per-stim metadata needed by the normalizer
        stim_types: dict[int, str] = {}
        gen_ids: dict[int, int] = {}
        parent_ids: dict[int, int] = {}
        for stim_id in driving_response_for_each_stim_id:
            stim_types[stim_id] = self.db_util.read_stim_type(stim_id)
            gen_ids[stim_id] = self.db_util.read_gen_id(stim_id)
            info = self.db_util.read_stim_ga_info_entry(stim_id)
            if info is not None:
                parent_ids[stim_id] = info.parent_id

        normalizer = self.normalizer_cls()
        normalized = normalizer.normalize(
            driving_response_for_each_stim_id,
            stim_types,
            gen_ids,
            parent_ids,
            strict=True,
        )

        # Write processed responses to database
        stim_ids_to_update = self.db_util.read_stims_with_no_driving_response()
        for stim_id in stim_ids_to_update:
            if stim_id in normalized:
                self.db_util.update_driving_response(stim_id, float(normalized[stim_id]))

    def _process_clusters(self, ga_name) -> dict[int, list[float]]:
        stims_to_process = self.db_util.read_all_stims()

        response_vector_for_each_stim: dict[int, list[float]] = {}
        for stim_id in stims_to_process:
            responses_for_stim_id = self.fetch_response_vector_for_repetitions_of(stim_id, ga_name=ga_name)

            response_vector_for_each_stim[stim_id] = responses_for_stim_id

        return response_vector_for_each_stim


class RankBaselineNormalizeResponseProcessor(BaselineNormalizeResponseProcessor):
    """DB-bound wrapper around `RankBaselineNormalizer`."""
    normalizer_cls = RankBaselineNormalizer

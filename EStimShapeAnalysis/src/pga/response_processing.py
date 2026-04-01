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
            driving_response = self.repetition_combination_strategy(responses)
            driving_responses_for_stim_ids[stim_id] = driving_response
        return driving_responses_for_stim_ids


class BaselineNormalizeResponseProcessor(GAResponseProcessor):
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

        # --- Pass 1: collect per-gen baseline responses keyed by parent_id ---
        # baselines_by_gen: {gen_id: {parent_id: response}}
        baselines_by_gen: dict[int, dict[int, float]] = defaultdict(dict)
        regime_zero_parent_ids = set()

        for stim_id, driving_response in driving_response_for_each_stim_id.items():
            stim_type = self.db_util.read_stim_type(stim_id)
            gen_id = self.db_util.read_gen_id(stim_id)

            if stim_type == StimType.BASELINE.value:
                stim_info = self.db_util.read_stim_ga_info_entry(stim_id)
                if stim_info is not None:
                    baselines_by_gen[gen_id][stim_info.parent_id] = driving_response
                    regime_zero_parent_ids.add(stim_info.parent_id)

        # --- Pass 2: build gen-1 reference dict from regime-zero parents ---
        gen1_dict: dict[int, float] = {
            pid: driving_response_for_each_stim_id[pid]
            for pid in regime_zero_parent_ids
            if pid in driving_response_for_each_stim_id
        }

        if not gen1_dict:
            raise ValueError("No regime-zero parents of baseline stims found; cannot normalize.")

        # --- Pass 3: apply interpolated normalization to experimental stims ---
        for stim_id in list(driving_response_for_each_stim_id.keys()):
            stim_type = self.db_util.read_stim_type(stim_id)
            is_regime_zero = stim_type in (StimType.REGIME_ZERO.value, StimType.REGIME_ZERO_2D.value)

            if stim_type in (StimType.BASELINE.value, "CATCH") or is_regime_zero:
                continue  # leave baseline, catch, and regime-zero stims unnormalized

            gen_id = self.db_util.read_gen_id(stim_id)
            r = driving_response_for_each_stim_id[stim_id]
            bN_dict = baselines_by_gen.get(gen_id, {})
            factor = self._interpolated_factor(r, bN_dict, gen1_dict)
            driving_response_for_each_stim_id[stim_id] *= factor

        # Write processed responses to database
        stim_ids_to_update = self.db_util.read_stims_with_no_driving_response()
        for stim_id in stim_ids_to_update:
            if stim_id in driving_response_for_each_stim_id:
                self.db_util.update_driving_response(stim_id, float(driving_response_for_each_stim_id[stim_id]))

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
        bN_arr   = np.array([bN_dict[p]   for p in common])
        gen1_arr = np.array([gen1_dict[p]  for p in common])
        sort_N       = np.argsort(bN_arr)
        bN_sorted    = bN_arr[sort_N]
        gen1_sorted  = gen1_arr[sort_N]
        factors      = gen1_sorted / bN_sorted
        return float(np.interp(r, bN_sorted, factors))

    def _process_clusters(self, ga_name) -> dict[int, list[float]]:
        stims_to_process = self.db_util.read_all_stims()

        response_vector_for_each_stim: dict[int, list[float]] = {}
        for stim_id in stims_to_process:
            responses_for_stim_id = self.fetch_response_vector_for_repetitions_of(stim_id, ga_name=ga_name)

            response_vector_for_each_stim[stim_id] = responses_for_stim_id

        return response_vector_for_each_stim

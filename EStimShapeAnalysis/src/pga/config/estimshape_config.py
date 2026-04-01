from collections import defaultdict
from statistics import mean

import numpy as np

from src.pga.baseline import BaseLineSideTest
from src.pga.config.simultaneous_2dvs3d_config import Simultaneous3Dvs2DConfig, DnessSideTest
from src.pga.estim_phase import EStimPhaseParentSelector, EStimPhaseMutationAssigner, EStimPhaseMagnitudeAssigner, \
    EStimPhaseTransitioner, EStimVariantDeltaSideTest
from src.pga.ga_classes import Phase, Lineage, RegimeTransitioner
from src.pga.response_processing import GAResponseProcessor
from src.pga.stim_types import StimType


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

class EStimShapeConfig(Simultaneous3Dvs2DConfig):
    """
    Configuration to add a fourth phase to make variants of stimuli to test in EStimShape.
    """
    def __init__(self, *, is_alexnet_mock, database: str, base_intan_path: str, java_output_dir: str,
                 allen_dist_dir: str):
        super().__init__(is_alexnet_mock=is_alexnet_mock, database=database, base_intan_path=base_intan_path, java_output_dir=java_output_dir, allen_dist_dir=allen_dist_dir)

    def make_phases(self):
        return [self.seeding_phase(),
                self.zooming_phase(),
                self.growing_phase(),
                self.estim_variant_phase()
                ]

    def side_tests(self):
        return [DnessSideTest(n_top_3d=4, n_top_2d=4),
                EStimVariantDeltaSideTest(num_deltas_per_variant=self.num_deltas_per_variant(),
                                          delta_resp_ratio_threshold=self.delta_resp_ratio_threshold()),
                BaseLineSideTest()
                ]

    def growing_phase_transitioner(self) -> type[RegimeTransitioner]:
        if self.is_alexnet_mock:
            return MockGrowingPhaseTransitioner()
        else:
            return super().growing_phase_transitioner()

    def estim_variant_phase(self):
        return Phase(
            EStimPhaseParentSelector(
                get_all_stimuli_func=self.get_all_stimuli_func(),
                threshold=self.variant_parent_response_threshold()),
            EStimPhaseMutationAssigner(),
            EStimPhaseMagnitudeAssigner(),
            EStimPhaseTransitioner(),
        )

    def variant_parent_response_threshold(self):
        return self.var_fetcher.get("variant_parent_response_threshold", dtype=float)

    def num_deltas_per_variant(self):
        return self.var_fetcher.get("num_deltas_per_variant", dtype=int)

    def delta_resp_ratio_threshold(self):
        return self.var_fetcher.get("delta_resp_ratio_threshold", dtype=float)

    def make_response_processor(self) -> GAResponseProcessor:
        return BaselineNormalizeResponseProcessor(
            db_util=self.db_util,
            repetition_combination_strategy=mean,
            cluster_combination_strategy=sum
        )
class MockGrowingPhaseTransitioner(RegimeTransitioner):
    num_times = 0
    def should_transition(self, lineage: Lineage) -> bool:
        self.num_times+=1
        if self.num_times > 3:
            return True
        else:
            return False



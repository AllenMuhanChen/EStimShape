from src.pga.baseline import BaseLineSideTest
from src.pga.config.simultaneous_2dvs3d_config import Simultaneous3Dvs2DConfig, DnessSideTest
from src.pga.estim_phase import EStimPhaseParentSelector, EStimPhaseMutationAssigner, EStimPhaseMagnitudeAssigner, \
    EStimPhaseTransitioner, EStimVariantDeltaSideTest
from src.pga.ga_classes import Phase, Lineage, RegimeTransitioner


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
                # BaseLineSideTest()
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


class MockGrowingPhaseTransitioner(RegimeTransitioner):
    num_times = 0
    def should_transition(self, lineage: Lineage) -> bool:
        self.num_times+=1
        if self.num_times > 3:
            return True
        else:
            return False



from statistics import mean

from src.pga.baseline import BaseLineSideTest
from src.pga.config.simultaneous_2dvs3d_config import Simultaneous3Dvs2DConfig, DnessSideTest
from src.pga.estim_phase import EStimPhaseParentSelector, EStimPhaseMutationAssigner, EStimPhaseMagnitudeAssigner, \
    EStimPhaseTransitioner, EStimVariantDeltaSideTest, EStimVariantSideTest
from src.pga.ga_classes import Phase, Lineage, RegimeTransitioner
from src.pga.response_processing import GAResponseProcessor, BaselineNormalizeResponseProcessor, \
    RankBaselineNormalizeResponseProcessor
from src.pga.spike_parsing import MuaIntanResponseParser
from src.pga.shuffle_side_test import ShuffleSideTest
from src.pga.lighting_side_test import LightingSideTest


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
                self.zooming_side_test(),
                self.shuffle_side_test(),
                self.lighting_side_test(),
                EStimVariantDeltaSideTest(num_deltas_per_variant=self.num_deltas_per_variant(),
                                          delta_resp_ratio_threshold=self.delta_resp_ratio_threshold(),
                                          max_attempts_per_variant=self.max_attempts_per_variant(),
                                          max_deltas_per_generation=self.max_deltas_per_generation(),
                                          max_variant_deltas_per_generation=self.max_variant_deltas_per_generation(),
                                          conn=self.connection()
                                          ),
                EStimVariantSideTest(self.get_all_stimuli_func(),
                                     self.connection(),
                                     threshold=self.variant_parent_response_threshold()
                                     ),
                BaseLineSideTest(),
                ]

    def growing_phase_transitioner(self) -> type[RegimeTransitioner]:
        if self.is_alexnet_mock:
            return MockGrowingPhaseTransitioner()
        else:
            return super().growing_phase_transitioner()

    def estim_variant_phase(self):
        return Phase(
            EStimPhaseParentSelector(
                self.get_all_stimuli_func(),
                self.variant_parent_response_threshold(),
                self.connection()),
            EStimPhaseMutationAssigner(),
            EStimPhaseMagnitudeAssigner(),
            EStimPhaseTransitioner(),
        )

    def shuffle_side_test(self):
        return ShuffleSideTest(conn=self.connection(),
                               n_top_responders=self.shuffle_side_test_n_top_responders())

    def shuffle_side_test_n_top_responders(self):
        # Defaults to 1 when the GAVar row is absent.
        n = self.var_fetcher.get("shuffle_side_test_n_top_responders", dtype=int)
        return n if n is not None else 1

    def lighting_side_test(self):
        return LightingSideTest(conn=self.connection(),
                                n_top_responders=self.lighting_side_test_n_top_responders())

    def lighting_side_test_n_top_responders(self):
        # Defaults to 1 when the GAVar row is absent.
        n = self.var_fetcher.get("lighting_side_test_n_top_responders", dtype=int)
        return n if n is not None else 1

    def variant_parent_response_threshold(self):
        return self.var_fetcher.get("variant_parent_response_threshold", dtype=float)

    def num_deltas_per_variant(self):
        return self.var_fetcher.get("num_deltas_per_variant", dtype=int)

    def delta_resp_ratio_threshold(self):
        return self.var_fetcher.get("delta_resp_ratio_threshold", dtype=float)

    def max_attempts_per_variant(self):
        # Absolute ceiling on delta attempts per variant before giving up. Defaults when GAVar absent.
        n = self.var_fetcher.get("delta_max_attempts_per_variant", dtype=int)
        return n if n is not None else 9

    def max_deltas_per_generation(self):
        # Returns None when the GAVar row is absent, leaving deltas uncapped.
        return self.var_fetcher.get("non_variant_deltas_max_per_generation", dtype=int)

    def max_variant_deltas_per_generation(self):
        # Per-generation ceiling on deltas made from true variant parents. Defaults to 25 when the
        # GAVar row is absent.
        n = self.var_fetcher.get("variant_deltas_max_per_generation", dtype=int)
        return n if n is not None else 25

    def make_response_processor(self) -> GAResponseProcessor:
        # When MUA is enabled the response vectors are read from
        # MUAChannelResponses (by metric) instead of ChannelResponses; baseline
        # normalization still composes on top via the same subclass.
        mua_metric = self.mua_metric() if self.is_use_mua_response_processor() else None
        if self.is_use_normalized_ga_response_processor():
            return RankBaselineNormalizeResponseProcessor(
                db_util=self.db_util,
                repetition_combination_strategy=mean,
                cluster_combination_strategy=sum,
                mua_metric=mua_metric,
            )
        elif mua_metric is not None:
            return GAResponseProcessor(
                db_util=self.db_util,
                repetition_combination_strategy=mean,
                cluster_combination_strategy=sum,
                mua_metric=mua_metric,
            )
        else:
            return super().make_response_processor()

    def make_response_parser(self):
        # MUA parser runs the standard spike.dat parse AND the wideband MAD parse
        # (both tables populated); the plain parser only when MUA is disabled.
        if self.is_use_mua_response_processor():
            return MuaIntanResponseParser(
                self.base_intan_path, self.db_util,
                mua_metric=self.mua_metric(),
                threshold_k=self.mua_threshold_k(),
                block_size=self.mua_block_size(),
            )
        return super().make_response_parser()

    def is_use_normalized_ga_response_processor(self):
        return self.var_fetcher.get("use_normalized_ga_response_processor", dtype=bool)

    def is_use_mua_response_processor(self):
        val = self.var_fetcher.get("use_mua_response_processor", dtype=bool)
        return bool(val) if val is not None else False

    def mua_threshold_k(self):
        val = self.var_fetcher.get("mua_threshold_k", dtype=float)
        return val if val is not None else 4.0

    def mua_block_size(self):
        val = self.var_fetcher.get("mua_block_size", dtype=int)
        return val if val is not None else 100

    def mua_metric(self):
        """Detection-method tag written by the parser and read by the processor;
        derived from the params so the two never drift."""
        return f"mad_k{self.mua_threshold_k():g}_block{self.mua_block_size()}"


class MockGrowingPhaseTransitioner(RegimeTransitioner):
    num_times = 0
    def should_transition(self, lineage: Lineage) -> bool:
        self.num_times+=1
        if self.num_times > 3:
            return True
        else:
            return False



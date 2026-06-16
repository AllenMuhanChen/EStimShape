from __future__ import annotations

from src.pga.config.canopy_config import GeneticAlgorithmConfig, singleton
from src.pga.ga_classes import Phase
from src.pga.zooming_phase import ZoomingPhaseParentSelector, ZoomingPhaseMutationMagnitudeAssigner, ZoomSetHandler, \
    ZoomingPhaseMutationAssigner, ZoomingPhaseTransitioner, ZoomingSideTest


class RFGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    zoom_set_handler: ZoomSetHandler

    def make_phases(self):
        return [self.seeding_phase(),
                self.zooming_phase(),
                self.growing_phase(),
                # self.leafing_phase()
                ]

    def zooming_phase(self):
        return Phase(self.zooming_phase_parent_selector(),
                     self.zooming_phase_mutation_assigner(),
                     self.zooming_phase_mutation_magnitude_assigner(),
                     self.zooming_phase_transitioner())

    def zooming_phase_mutation_magnitude_assigner(self):
        return ZoomingPhaseMutationMagnitudeAssigner()

    def zooming_phase_parent_selector(self):
        return ZoomingPhaseParentSelector(
            spontaneous_firing_rate=self.spontaneous_firing_rate(),
            significance_level=self.seeding_phase_significance_threshold(),
            zoom_set_handler=self.get_zoom_set_handler())

    @singleton
    def get_zoom_set_handler(self):
        return ZoomSetHandler(conn=self.connection())

    def zooming_phase_mutation_assigner(self):
        return ZoomingPhaseMutationAssigner(zoom_set_handler=self.get_zoom_set_handler())

    def zooming_phase_transitioner(self):
        return ZoomingPhaseTransitioner(
            zoom_set_handler=self.get_zoom_set_handler(),
            num_full_set=self.zooming_phase_complete_set_number_threshold(),
            parent_selector=self.zooming_phase_parent_selector())

    def zooming_phase_complete_set_number_threshold(self):
        return self.var_fetcher.get("zooming_phase_number_full_set_threshold", dtype=float)

    def zooming_side_test(self):
        # The zooming phase is the second regime (index 1) in make_phases(), so the side test
        # only acts on lineages that have moved past it.
        return ZoomingSideTest(
            zoom_set_handler=self.get_zoom_set_handler(),
            n_top_responders=self.zooming_side_test_n_top_responders(),
            after_regime_index=1)

    def zooming_side_test_n_top_responders(self):
        return self.var_fetcher.get("zoom_side_test_n_top_responders", dtype=int)

from __future__ import annotations

from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase
from src.pga.zooming_phase import ZoomingPhaseParentSelector, ZoomingPhaseMutationMagnitudeAssigner, ZoomSetHandler, \
    ZoomingPhaseMutationAssigner, ZoomingPhaseTransitioner


class RFGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    database = "allen_estimshape_ga_dev_240207"
    zoom_set_handler: ZoomSetHandler
    def make_phases(self):
        return [self.seeding_phase(),
                self.zooming_phase(),
                self.growing_phase(),
                self.leafing_phase()]

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
            zoom_set_handler=self.make_zoom_set_handler())

    def make_zoom_set_handler(self):
        if not hasattr(self, "zoom_set_handler"):
            self.zoom_set_handler = ZoomSetHandler(conn=self.connection)
        return self.zoom_set_handler

    def zooming_phase_mutation_assigner(self):
        return ZoomingPhaseMutationAssigner(zoom_set_handler=self.make_zoom_set_handler())

    def zooming_phase_transitioner(self):
        return ZoomingPhaseTransitioner(
            zoom_set_handler=self.make_zoom_set_handler(),
            percentage_full_set_threshold=self.zooming_phase_complete_set_percent_threshold(),
            parent_selector=self.zooming_phase_parent_selector())

    def zooming_phase_complete_set_percent_threshold(self):
        return self.var_fetcher.get("zooming_phase_percentage_full_set_threshold", dtype=float)


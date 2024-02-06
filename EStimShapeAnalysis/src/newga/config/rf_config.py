from newga.config.canopy_config import GeneticAlgorithmConfig
from newga.ga_classes import Phase
from newga.regime_three import LeafingPhaseParentSelector, LeafingPhaseMutationAssigner, \
    LeafingPhaseMutationMagnitudeAssigner, LeafingPhaseTransitioner


class RFGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    def make_phases(self):
        return [self.seeding_phase(),
                self.growing_phase(),
                self.leafing_phase()]

    def leafing_phase(self):
        return Phase(
            LeafingPhaseParentSelector(
                self.weight_func(),
                self.sampling_smoothing_bandwidth()),
            LeafingPhaseMutationAssigner(),
            LeafingPhaseMutationMagnitudeAssigner(),
            LeafingPhaseTransitioner(self.get_under_sampling_threshold(), bandwidth=self.sampling_smoothing_bandwidth()))

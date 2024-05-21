from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase, MutationMagnitudeAssigner, Lineage, Stimulus
from src.pga.regime_three import LeafingPhaseParentSelector, LeafingPhaseMutationAssigner, \
    LeafingPhaseMutationMagnitudeAssigner, LeafingPhaseTransitioner


class RFGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    database = "allen_estimshape_ga_dev_240207"
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




class ZoomingPhaseMutationMagnitudeAssigner(MutationMagnitudeAssigner):
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus):
        return None

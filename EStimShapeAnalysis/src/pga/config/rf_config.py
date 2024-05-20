from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase
from src.pga.regime_three import LeafingPhaseParentSelector, LeafingPhaseMutationAssigner, \
    LeafingPhaseMutationMagnitudeAssigner, LeafingPhaseTransitioner


class RFGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    database = "allen_estimshape_ga_dev_240207"
    def make_phases(self):
        return [self.seeding_phase(),
                self.growing_phase(),
                self.leafing_phase()]

# 2d vs 3d as a parameter
import random

from pga.config.rf_config import RFGeneticAlgorithmConfig
from pga.ga_classes import MutationAssigner, Stimulus
from pga.stim_types import StimType


class TwoDThreeDGAConfig(RFGeneticAlgorithmConfig):
    database = "allen_estimshape_ga_dev_240207"

    def seeding_phase_mutation_assigner(self):
        return SeedingPhase2D3DMutationAssigner()


class SeedingPhase2D3DMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus):
        # Assign half to RegimeZero and half to RegimeZero2D
        if random.random() < 0.5:
            return StimType.REGIME_ZERO.value
        else:
            return StimType.REGIME_ZERO_2D.value

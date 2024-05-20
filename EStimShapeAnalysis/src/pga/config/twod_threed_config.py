# 2d vs 3d as a parameter
import random

from src.pga.config.rf_config import RFGeneticAlgorithmConfig
from src.pga.ga_classes import MutationAssigner, Stimulus, Lineage
from src.pga.stim_types import StimType


class TwoDThreeDGAConfig(RFGeneticAlgorithmConfig):
    database = "allen_estimshape_ga_dev_240207"

    def seeding_phase_mutation_assigner(self):
        return SeedingPhase2D3DMutationAssigner()

    def growing_phase_mutation_assigner(self):
        return GrowingPhase2D3DMutationAssigner()

    def leafing_phase_mutation_assigner(self):
        return LeafingPhaseMutationAssigner()


class SeedingPhase2D3DMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus):
        # Assign half to RegimeZero and half to RegimeZero2D
        if random.random() < 0.5:
            return StimType.REGIME_ZERO.value
        else:
            return StimType.REGIME_ZERO_2D.value


class GrowingPhase2D3DMutationAssigner(MutationAssigner):
    mutation_chance = 0.2

    def assign_mutation(self, lineage, parent: Stimulus):
        parent_stim_type = parent.mutation_type
        # check if stim_type contains 2D
        if "2D" in parent_stim_type:
            if random.random() < self.mutation_chance:
                return StimType.REGIME_ONE.value
            else:
                return StimType.REGIME_ONE_2D.value
        else:
            if random.random() < self.mutation_chance:
                return StimType.REGIME_ONE_2D.value
            else:
                return StimType.REGIME_ONE.value


class LeafingPhaseMutationAssigner(MutationAssigner):
    mutation_chance = 0.2

    def assign_mutation(self, lineage: Lineage, parent: Stimulus):
        parent_stim_type = parent.mutation_type
        # check if stim_type contains 2D
        if "2D" in parent_stim_type:
            if random.random() < self.mutation_chance:
                return StimType.REGIME_THREE.value
            else:
                return StimType.REGIME_THREE_2D.value
        else:
            if random.random() < self.mutation_chance:
                return StimType.REGIME_THREE_2D.value
            else:
                return StimType.REGIME_THREE.value

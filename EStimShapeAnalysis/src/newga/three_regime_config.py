from newga.four_regime_config import GeneticAlgorithmConfig


class RFGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    def make_phases(self):
        return [self.seeding_phase(),
                self.growing_phase(),
                self.canopy_phase(),
                self.leafing_phase()]

    # def regime_two(self):
    #     return Regime(
    #         RegimeTwoParentSelector(
    #             self.percentage_of_max_threshold(),
    #             self.num_to_select()),
    #         RegimeTwoMutationAssigner(),
    #         RegimeTwoMutationMagnitudeAssigner(),
    #         RegimeTwoTransitioner(self.pair_threshold_high(), self.pair_threshold_low()))

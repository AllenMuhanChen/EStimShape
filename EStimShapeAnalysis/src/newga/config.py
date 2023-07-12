from newga.regime_three import RegimeThreeParentSelector, RegimeThreeMutationAssigner, \
    RegimeThreeMutationMagnitudeAssigner
from newga.regime_two import RegimeTwoParentSelector, RegimeTwoMutationAssigner, RegimeTwoMutationMagnitudeAssigner
from src.newga.ga_classes import Regime, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, RegimeTransitioner
from src.newga.genetic_algorithm import GeneticAlgorithm
from src.newga.regime_one import RegimeOneParentSelector, RegimeOneMutationAssigner, RegimeOneMutationMagnitudeAssigner, \
    RegimeOneTransitioner
from src.newga.regime_zero import RegimeZeroParentSelector, RegimeZeroMutationAssigner, \
    RegimeZeroMutationMagnitudeAssigner, RegimeZeroTransitioner


def genetic_alogrithm():
    ga = GeneticAlgorithm(regimes())


def regimes():
    return [regime_zero(),
            regime_one(),
            regime_two(),
            regime_three()]


def regime_zero():
    return Regime(RegimeZeroParentSelector(),
                  RegimeZeroMutationAssigner(),
                  RegimeZeroMutationMagnitudeAssigner(),
                  RegimeZeroTransitioner(
                      spontaneous_firing_rate(),
                      regime_zero_significance_threshold()))


def regime_zero_significance_threshold():
    return 0.05


def spontaneous_firing_rate():
    return 10


def regime_one():
    return Regime(
        RegimeOneParentSelector(
            get_all_stimuli_func(),
            regime_one_bin_proportions(),
            regime_one_bin_sample_sizes()),
        RegimeOneMutationAssigner(),
        RegimeOneMutationMagnitudeAssigner(),
        RegimeOneTransitioner(
            convergence_threshold()
        ))


def get_all_stimuli_func():
    pass


def regime_one_bin_proportions():
    return regime_one_bin_proportions


def regime_one_bin_sample_sizes():
    return regime_one_bin_sample_sizes


def convergence_threshold():
    pass


def regime_two():
    return Regime(
        RegimeTwoParentSelector(
            percentage_of_max_threshold(),
            x()),
        RegimeTwoMutationAssigner(),
        RegimeTwoMutationMagnitudeAssigner(),
        RegimeTransitioner())


def percentage_of_max_threshold():
    return 0.5


def x():
    return 5


def regime_three():
    return Regime(
        RegimeThreeParentSelector(
            weight_func(),
            bandwidth()),
        RegimeThreeMutationAssigner(),
        RegimeThreeMutationMagnitudeAssigner(),
        RegimeTransitioner())


def weight_func():
    pass


def bandwidth():
    return 0.15

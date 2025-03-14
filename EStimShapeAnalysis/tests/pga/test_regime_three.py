import matplotlib.pyplot as plt
import numpy as np
import unittest

from scipy.stats import gaussian_kde

from src.pga.ga_classes import Stimulus, Lineage, LineageFactory
from src.pga.regime_three import SmoothedSamplingFunction, LeafingPhaseParentSelector, LeafingPhaseTransitioner, \
    HighEndSigmoid


class TestSamplingFunctionCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = SmoothedSamplingFunction(bandwidth=0.15)

    def test_sampling_function_calculator(self):
        responses = np.random.normal(5, 1, 100)
        calculator = self.calculator
        sampling_func = calculator(responses)

        # Plot unsmoothed impulses
        plt.stem(responses, np.ones_like(responses), linefmt='C1-', markerfmt='C1o', basefmt=" ",
                 use_line_collection=True, label='Impulses')

        # Plot smoothed histogram
        x = np.linspace(min(responses), max(responses), 1000)
        y = sampling_func(x)
        plt.plot(x, y, label='Smoothed', color='C0')

        plt.legend()
        plt.show()


def weight_func(response_rate):
    if response_rate > 8:
        return 1
    else:
        return 0


class TestRegimeThreeParentSelector(unittest.TestCase):
    def setUp(self):
        self.selector = LeafingPhaseParentSelector(weight_func)

    def test_select_parents_by_custom_weight(self):
        # Create a lineage with 10 stimuli having response rates from 1 to 10.
        stimuli = [Stimulus(None, "Test", response_rate=i) for i in range(1, 11)]
        lineage = LineageFactory.create_lineage_from_stimuli(stimuli)

        # Select 5 parents.
        parents = self.selector.select_parents(lineage, 5)

        # Check that the correct number of parents were selected.
        self.assertEqual(len(parents), 5)

        # Check that the parents have high response rates (because of our weight function).
        self.assertTrue(all(parent.response_rate > 8 for parent in parents))


class TestRegimeThreeTransitioner(unittest.TestCase):
    def setUp(self):
        # Set the under-sampling threshold to a value that will prevent a transition.
        self.transitioner = LeafingPhaseTransitioner(under_sampling_threshold=0.5)

    def test_should_transition(self):
        # Create a lineage with 10 stimuli having response rates from 1 to 10.

        stimuli = [Stimulus(None, "Test", response_rate=i) for i in range(1, 11)]
        lineage = LineageFactory.create_lineage_from_stimuli(stimuli)
        # Check if we should transition to the next regime.
        # Since the response rates are uniformly distributed, we should transition.
        self.assertTrue(self.transitioner.should_transition(lineage))

        # Now create a lineage with a hole in the response distribution.
        lineage.stimuli = [Stimulus(None, i, response_rate=i) for i in list(range(1, 6)) + list(range(8, 11))]

        # We should not transition because there is under-sampling.
        self.assertFalse(self.transitioner.should_transition(lineage))

class TestHighEndSigmoid(unittest.TestCase):
    def test_sigmoid_plot(self):
        sigmoid = HighEndSigmoid()

        # Generate values to plot
        x_values = np.linspace(0, 1, 100)
        y_values = [sigmoid(x) for x in x_values]

        # Plot the sigmoid
        plt.plot(x_values, y_values)
        plt.title("High-End Sigmoid Function")
        plt.xlabel("Input (0-1)")
        plt.ylabel("Output (0-1)")
        plt.show()

        # Verify some properties, like the value at 0.5 should be greater than 0.5
        self.assertGreater(sigmoid(0.5), 0.5)
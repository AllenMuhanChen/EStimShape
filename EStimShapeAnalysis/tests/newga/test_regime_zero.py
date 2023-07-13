# test_regime_zero.py

import unittest
from src.newga.ga_classes import Stimulus
from src.newga.regime_zero import RegimeZeroTransitioner


class TestRegimeZeroTransitioner(unittest.TestCase):
    def setUp(self):
        self.transitioner = RegimeZeroTransitioner(spontaneous_firing_rate=10, significance_level=0.05)

    def test_should_transition(self):
        # Generate some stimuli with high response rates
        stimuli = [Stimulus(None, "Test") for _ in range(30)]
        for stimulus in stimuli:
            stimulus.set_response_rate(20)

        # The t-test should find that the response rates are significantly higher than the spontaneous firing rate,
        # so should_transition should return True
        self.assertTrue(self.transitioner.should_transition(null))

        # Generate some stimuli with low response rates
        stimuli = [Stimulus(None, "Test") for _ in range(30)]
        for stimulus in stimuli:
            stimulus.set_response_rate(10)

        # The t-test should find that the response rates are not significantly different from the spontaneous firing rate,
        # so should_transition should return False
        self.assertFalse(self.transitioner.should_transition(null))


if __name__ == '__main__':
    unittest.main()

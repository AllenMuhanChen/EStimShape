from unittest import TestCase
from src.data import trialcollector

class TestTrialCollectorMethods(TestCase):
    def test_collect_trials(self):
        trial_whens = trialcollector.collect_trials()
        actualNumCorrect = sum([True for i in trial_whens if (i.start<i.stop)])
        expectedNumCorrect = len(trial_whens)
        self.assertEqual(expectedNumCorrect, actualNumCorrect)

from unittest import TestCase
from clat.compile import TrialCollector
from clat.util.connection import Connection
from clat.util import time_util


class TestTrialCollectorMethods(TestCase):
    conn = Connection("allen_estimshape_train_220725", when=time_util.all())
    trialcollector = TrialCollector(conn)
    def test_collect_trials(self):

        trial_whens = self.trialcollector.collect_trials()
        actualNumCorrect = sum([True for i in trial_whens if (i.start<i.stop)])
        expectedNumCorrect = len(trial_whens)
        self.assertEqual(expectedNumCorrect, actualNumCorrect)

    def test_collect_choices_trials(self):
        trial_whens = self.trialcollector.collect_choice_trials()
        actualNumCorrect = sum([True for i in trial_whens if (i.start<i.stop)])
        expectedNumCorrect = len(trial_whens)
        self.assertEqual(expectedNumCorrect, actualNumCorrect)

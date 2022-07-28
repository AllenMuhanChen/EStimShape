from unittest import TestCase


from src.compile import psychometric_compile as pc
from src.data import trial_field as tf
from src.data import timeutil as time
from src.data import trialcollector
from src.data import reader
class TestTrialTypeField(TestCase):
    def test_get_value(self):
        beh_msg = reader.get_beh_msg()
        trial = pc.IsCorrectField(beh_msg)
        isCorrect = trial.getValue(time.When(1659038500125354,1659038504610070))
        self.assertEqual(True, isCorrect)

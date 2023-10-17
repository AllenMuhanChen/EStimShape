from unittest import TestCase
from util.time_util import When
from util import time_util

from compile.trial import psychometric_compile as pc

PSYCHOMETRIC = When(1659208461019365, 1659208471171128)

RANDOM_CORRECT = When(1659126605490042, 1659126611270426)
from util.connection import Connection

class TestFields(TestCase):
    reader = Connection("allen_estimshape_test_220729", when=time_util.all())
    beh_msg = reader.beh_msg
    stim_spec = reader.stim_spec
    def test_IsCorrect_field_retrieve_value(self):
        trial = pc.IsCorrectField(self.beh_msg)
        trial.get(RANDOM_CORRECT)
        isCorrect = trial.value
        self.assertEqual(True, isCorrect)

    def test_trial_type_field_retrieve_value(self):
        trial = pc.TrialTypeField(self.beh_msg, self.stim_spec)
        trial.get(RANDOM_CORRECT)
        self.assertEqual("Rand", trial.value)

    def test_noise_retrieve_value(self):
        trial = pc.NoiseChanceField(self.beh_msg, self.stim_spec)
        trial.get(RANDOM_CORRECT)
        print(trial.value)

    def test_psychometric_id_retrieve_value(self):
        trial = pc.PsychometricIdField(self.beh_msg, self.stim_spec)
        trial.get(PSYCHOMETRIC)
        print(trial.value)
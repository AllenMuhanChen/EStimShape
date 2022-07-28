from unittest import TestCase

import pandas as pd

import trial
import timeutil

class DuckField:
    def __init__(self, quack):
        self.quack = quack
    def getValue(self, when):
        self.value = self.quack

class SubField(trial.Field):
    pass

class StartField():
    def __init__(self):
        pass
    def getValue(self, when):
        self.value = when.start

class WhenField():
    def getValue(self, when):
        self.value = when.tuple()

class TestField(TestCase):
    def test(self):
        trialList = []
        trialList.append(trial.Trial(timeutil.When(1, 2)))
        trialList.append(trial.Trial(timeutil.When(3, 4)))

        ## Interface for defining fields
        f = trial.Field()
        start1 = StartField()
        when1 = WhenField()
        d1 = DuckField("duck1")
        d2 = DuckField("duck2")
        s1 = SubField()

        ## Interface for adding fields to a trial
        for t in trialList:
            t.add_field(when1)
            t.add_field(start1)
            t.add_field(d1)
            t.add_field(d2)
            t.add_field(s1)

        df = pd.DataFrame()
        for t in trialList:
            df = t.append_to_data_frame(df)

        print(df)
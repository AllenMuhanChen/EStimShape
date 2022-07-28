from unittest import TestCase

import pandas as pd

import trial_field
import timeutil

class DuckField:
    def __init__(self, quack):
        self.quack = quack
        self.name = "Duck"
    def getValue(self, when):
        self.value = self.quack

class SubField(trial.Field):
    pass

class StartField(trial.Field):
    def getValue(self, when):
        self.value = when.start

class WhenField(trial.Field):
    def __init__(self):
        self.name = "tstamps"
    def getValue(self, when):
        self.value = when.tuple()

class TestField(TestCase):
    def test(self):
        trialList = []
        trialList.append(trial_field.Trial(timeutil.When(1, 2)))
        trialList.append(trial_field.Trial(timeutil.When(3, 4)))

        ## Interface for defining fields
        f = trial_field.Field()
        start1 = StartField()
        when1 = WhenField()
        d1 = DuckField("duck1")
        s1 = SubField()

        ## Interface for adding fields to a trial
        fieldList = trial_field.FieldList()
        fieldList.append(when1)
        fieldList.append(start1)
        fieldList.append(d1)
        fieldList.append(s1)

        for t in trialList:
            t.set_fields(fieldList)

        data = []

        for t in trialList:
            data = t.append_to_data(data)
        print(pd.DataFrame(data))

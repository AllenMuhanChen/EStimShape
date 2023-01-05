import math
from typing import Callable

import pandas as pd
import xmltodict

from src.compile.trial_field import Field, DatabaseField
from src.util.time_util import When


class MatchStickField(Field):
    def __init__(self, mstick_spec_data_source, name: str = None):
        super().__init__(name)
        self.mstick_spec_source = mstick_spec_data_source

    def get(self, when: When) -> dict:
        return self.mstick_spec_source.get(when)


class ShaftField(MatchStickField):
    def get(self, when: When) -> list[dict]:
        mstick_data = MatchStickField.get(self, when)
        shaft_data = mstick_data["AllenMStickData"]['shaftData']['ShaftData']
        return shaft_data


class TerminationField(MatchStickField):
    def get(self, when: When) -> list[dict]:
        mstick_data = MatchStickField.get(self, when)
        termination_data = mstick_data["AllenMStickData"]['terminationData']['TerminationData']
        return termination_data


class JunctionField(MatchStickField):
    def get(self, when: When) -> list[dict]:
        mstick_data = MatchStickField.get(self, when)
        termination_data = mstick_data["AllenMStickData"]['junctionData']['JunctionData']
        return termination_data

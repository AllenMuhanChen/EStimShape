import math

import pandas as pd
import xmltodict

from src.compile.database_fields import DatabaseField
from src.compile.trial_field import Field
from src.util.time_util import When


class MatchStickField(Field):
    def __init__(self, mstick_spec_source, name: str = None):
        super().__init__(name)
        self.mstick_spec_source = mstick_spec_source

    def get(self, when: When) -> dict:
        mstick_spec_xml = self.mstick_spec_source.get(when)
        return xmltodict.parse(mstick_spec_xml)


class ShaftField(MatchStickField):
    def get(self, when: When) -> pd.DataFrame:
        mstick_spec = MatchStickField.get(self, when)
        shaft_specs = mstick_spec["AllenMStickSpec"]["mAxis"]["Tube"]["AllenTubeInfo"]

        shaft_data = pd.DataFrame
        for shaft_spec in shaft_specs:
            radial_position, angular_position = cartesian_to_polar(shaft_spec["transRotHis__finalPos"])


def cartesian_to_polar(x, y):
    r = math.sqrt(x ** 2 + y ** 2)
    theta = math.atan2(y, x)
    return r, theta

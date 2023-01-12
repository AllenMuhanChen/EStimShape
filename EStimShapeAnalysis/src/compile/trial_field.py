from __future__ import annotations

from collections import OrderedDict
from typing import Callable

import pandas as pd

from src.util.connection import Connection
from src.util.time_util import When


class Field:
    def __init__(self, name: str = None):
        if name is None:
            self.name = type(self).__name__
        else:
            self.name = name

    def get(self, when: When):
        raise NotImplementedError("Not Implemented")


class FieldList(list[Field]):
    """List of Field types"""

    def get_df(self):
        df = pd.DataFrame(columns=self.get_names())
        return df

    def get_names(self):
        return [field.name for field in self]


class Trial:
    def __init__(self, when: When, fields: FieldList):
        self.when = when
        self.fields = fields

    def append_to_data(self, data):
        field_values = [field.get(self.when) for field in self.fields]
        names = self.fields.get_names()
        new_row = OrderedDict(zip(names, field_values))
        data.append(new_row)




def get_data_from_trials(fields: FieldList, trial_tstamps: list[When]) -> pd.DataFrame:
    trialList = []
    for when in trial_tstamps:
        trialList.append(Trial(when, fields))
    data = []
    for i, t in enumerate(trialList):
        print("working on " + str(i) + " out of " + str(len(trialList)))
        t.append_to_data(data)
    return pd.DataFrame(data)


class DatabaseField(Field):
    def __init__(self, conn: Connection, name: str = None):
        super().__init__(name)
        self.conn = conn

    def get(self, when: When):
        raise NotImplementedError("Not Implemented")

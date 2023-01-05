import ast
import json
import tracemalloc
from math import pi

import pandas as pd
import xmltodict

from src.analysis.rwa import rwa, Binner
from src.compile.classic_database_fields import StimSpecDataField, StimSpecIdField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_field import FieldList, DatabaseField, get_data_from_trials
from src.mock.mock_ga_responses import collect_trials
from src.util import time_util
from src.util.connection import Connection
from src.util.time_util import When


class MockResponseField(StimSpecIdField):
    def __init__(self, conn: Connection, channel: int, name: str = None):
        super().__init__(conn, name=name)
        self.channel = channel

    def get(self, when: When) -> float:
        stim_spec_id = StimSpecIdField.get(self, when)
        self.conn.execute("SELECT memo FROM ExpLog WHERE tstamp = %s", [stim_spec_id])
        responses_for_channels = self.conn.fetch_one()
        responses_for_channels = ast.literal_eval(responses_for_channels)
        response = responses_for_channels.get(self.channel)
        return response


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = FieldList()
    fields.append(StimSpecIdField(conn, "Id"))
    fields.append(MockResponseField(conn, 1, name="Response-1"))
    fields.append(ShaftField(mstick_spec_data_source, name="Shaft"))
    fields.append(TerminationField(mstick_spec_data_source, name="Termination"))
    fields.append(JunctionField(mstick_spec_data_source, name="Junction"))

    data = get_data_from_trials(fields, trial_tstamps)
    return data



def main():
    tracemalloc.start()


    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")
    bin_size = 10
    binner_for_shaft_fields = {
        "theta": Binner(-pi, pi, bin_size),
        "phi": Binner(-pi, pi, bin_size),
        "radialPosition": Binner(0, 20, bin_size),
        "length": Binner(0, 100, bin_size),
        "curvature": Binner(0, 1, bin_size),
        "radius": Binner(0, 20, bin_size),
    }

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    response_weighted_average = rwa(data["Shaft"], data["Response-1"], binner_for_shaft_fields)
    print(response_weighted_average)
    # EXPORT



if __name__ == '__main__':
    main()

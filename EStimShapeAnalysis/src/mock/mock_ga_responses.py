from __future__ import annotations

import pandas as pd

from src.compile.classic_database_fields import StimSpecDataField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_collector import TrialCollector
from src.compile.trial_field import FieldList, get_data_from_trials
from src.util import time_util
from src.util.connection import Connection
from src.util.time_util import When


def collect_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_trials()


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = FieldList()
    fields.append(ShaftField(mstick_spec_data_source))
    fields.append(TerminationField(mstick_spec_data_source))
    fields.append(JunctionField(mstick_spec_data_source))

    return get_data_from_trials(fields, trial_tstamps)


def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)

    print(data)


if __name__ == '__main__':
    main()

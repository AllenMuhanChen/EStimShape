from __future__ import annotations

import pandas as pd

from analysis.nafc.nafc_database_fields import TrialTypeField
from clat.compile.trial.trial_collector import TrialCollector
from clat.compile.trial.trial_field import FieldList, get_data_from_trials
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When


def collect_choice_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_choice_trials()


def compile_psychometric_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    fields = FieldList()
    fields.append(TrialTypeField(conn))

    return get_data_from_trials(fields, trial_tstamps)


def main():
    """example of data analysis pipeline"""

    # PARAMETERS
    conn = Connection("allen_estimshape_test_220729")

    # PIPELINE
    trial_tstamps = collect_choice_trials(conn, time_util.all())
    data = compile_psychometric_data(conn, trial_tstamps)
    print(data)


if __name__ == '__main__':
    main()

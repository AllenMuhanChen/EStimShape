import numpy as np
import pandas as pd
from clat.compile.trial.cached_fields import CachedFieldList
from clat.compile.trial.classic_database_fields import StimSpecDataField, NewGaNameField, NewGaLineageField, \
    RegimeScoreField
from clat.compile.trial.trial_collector import TrialCollector
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When

from src.analysis.ga.fields import ClusterResponseField, TaskIdField, StimIdField, LineageField, RegimeField
from src.analysis.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.startup import context


def main():
    # Setting up connection and time frame to analye in
    conn = Connection(context.ga_database)

    experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    start = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    stop = time_util.now()

    # Collecting trials and compiling data
    trial_tstamps = collect_trials(conn, When(start, stop))
    data = compile_data(conn, trial_tstamps)

    # Removing empty trials (no stim_id)
    # pd.options.display.float_format = '{:20,f}'.format
    print(data.to_string())


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = CachedFieldList()
    fields.append(TaskIdField(conn))
    fields.append(StimIdField(conn))
    fields.append(LineageField(conn))
    fields.append(RegimeField(conn))
    fields.append(ClusterResponseField(conn))
    # fields.append(ShaftField(conn, mstick_spec_data_source))
    # fields.append(TerminationField(conn, mstick_spec_data_source))
    # fields.append(JunctionField(conn, mstick_spec_data_source))

    data = fields.to_data(trial_tstamps)
    return data




def collect_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_trials()



if __name__ == "__main__":
    main()

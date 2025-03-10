import os

import jsonpickle
import numpy as np
import pandas as pd

from src.analysis.ga.rwa import get_next
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When
from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.startup import context
from src.pga.mock.mock_ga_responses import collect_trials
from src.pga.mock.mock_rwa_analysis import remove_empty_response_trials, condition_spherical_angles, \
    hemisphericalize_orientation, compute_shaft_rwa, compute_termination_rwa, compute_junction_rwa, save
from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.compile.tstamp.classic_database_tstamp_fields import StimSpecDataField, StimSpecIdField, NewGaLineageField, \
    NewGaNameField, RegimeScoreField
from src.analysis.matchstick_fields import ShaftField, TerminationField, JunctionField



def main():
    # PARAMETERS
    conn = Connection(context.ga_database)
    n = int(input("Enter the number of lineages to use for RWA: "))

    # PIPELINE
    experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    trial_tstamps = collect_trials(conn, when_for_most_recent_experiment())
    data = compile_data(conn, trial_tstamps)
    data = remove_empty_response_trials(data)
    data = remove_catch_trials(data)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)
    shaft_rwa = compute_shaft_rwa(data, n)
    termination_rwa = compute_termination_rwa(data, n)
    junction_rwa = compute_junction_rwa(data, n)

    # SAVE
    save(get_next(shaft_rwa), f"{experiment_id}_shaft_rwa")
    save(get_next(termination_rwa), f"{experiment_id}_termination_rwa")
    save(get_next(junction_rwa), f"{experiment_id}_junction_rwa")


def remove_catch_trials(data: pd.DataFrame):
    return data[data["Lineage"] != 0]


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = CachedFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(NewGaNameField(conn))
    fields.append(NewGaLineageField(conn))
    fields.append(RegimeScoreField(conn))
    fields.append(ClusterResponseField(conn))
    fields.append(ShaftField(conn, mstick_spec_data_source))
    fields.append(TerminationField(conn, mstick_spec_data_source))
    fields.append(JunctionField(conn, mstick_spec_data_source))

    data = fields.to_data(trial_tstamps)
    return data


class ClusterResponseField(StimSpecIdField):

    def __init__(self, conn: Connection):
        super().__init__(conn)
        self.db_util = MultiGaDbUtil(conn)
        self.cluster_channels = self.db_util.read_current_cluster(context.ga_name)

    def get(self, when: When) -> float:
        stim_spec_id = self.get_cached_super(when, StimSpecIdField)
        all_responses = []
        for cluster_channel in self.cluster_channels:
            self.conn.execute("SELECT spikes_per_second FROM ChannelResponses WHERE stim_id = %s AND channel=%s",
                              [stim_spec_id, cluster_channel.value])
            response = self.conn.fetch_all()
            all_responses.extend(response)

        return np.mean(all_responses)

    def get_name(self):
        return "Response-1"


def when_for_most_recent_experiment():
    """
    Calculate the time range for the most recent experiment.
    """
    start = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    stop = time_util.now()
    return When(start, stop)


def save(response_weighted_average, file_name):
    file_name = f"{file_name}.json"
    filepath = os.path.join(context.rwa_output_dir, file_name)
    with open(filepath, "w") as file:
        file.write(jsonpickle.encode(response_weighted_average))
        file.close()


if __name__ == "__main__":
    main()

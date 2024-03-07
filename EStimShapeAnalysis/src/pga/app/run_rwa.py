import os

import jsonpickle

from analysis.ga.rwa import get_next
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When
from pga.app import config
from pga.mock.mock_ga_responses import collect_trials
from pga.mock.mock_rwa_analysis import compile_data, remove_empty_response_trials, condition_spherical_angles, \
    hemisphericalize_orientation, compute_shaft_rwa, compute_termination_rwa, compute_junction_rwa, save


def main():
    # PARAMETERS
    conn = Connection(config.database)

    # PIPELINE
    experiment_id = config.ga_config.db_util.read_current_experiment_id(config.ga_name)
    trial_tstamps = collect_trials(conn, when_for_most_recent_experiment())
    data = compile_data(conn, trial_tstamps)
    data = remove_empty_response_trials(data)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)

    n = int(input("Enter the number of lineages to use for RWA: "))

    shaft_rwa = compute_shaft_rwa(data, n)
    termination_rwa = compute_termination_rwa(data, n)
    junction_rwa = compute_junction_rwa(data, n)

    # SAVE
    save(get_next(shaft_rwa), f"{experiment_id}_shaft_rwa")
    save(get_next(termination_rwa), f"{experiment_id}_termination_rwa")
    save(get_next(junction_rwa), f"{experiment_id}_junction_rwa")


def when_for_most_recent_experiment():
    """
    Calculate the time range for the most recent experiment.
    """
    start = config.ga_config.db_util.read_current_experiment_id(config.ga_name)
    stop = time_util.now()
    return When(start, stop)


def save(response_weighted_average, file_name):
    file_name = f"{file_name}.json"
    filepath = os.path.join(config.rwa_output_dir, file_name)
    with open(filepath, "w") as file:
        file.write(jsonpickle.encode(response_weighted_average))
        file.close()


if __name__ == "__main__":
    main()

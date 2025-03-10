from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from numpy import double

from src.analysis.matchstick_fields import ShaftField
from clat.compile.task.classic_database_task_fields import TaskIdField, StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.compile.task.task_field import TaskFieldList, get_data_from_tasks
from clat.compile.tstamp.trial_tstamp_collector import TrialCollector
from clat.intan.channels import Channel
from src.analysis.ga.MultiCustomNormalTuningFunction import MultiCustomNormalTuningFunction

from src.pga.mock.mock_rwa_analysis import condition_spherical_angles, hemisphericalize_orientation
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.dictionary_util import flatten_dictionary, \
    extract_values_with_key_into_list
from clat.util.time_util import When


def collect_task_ids(conn):
    task_id_collector = TaskIdCollector(conn)
    task_ids = task_id_collector.collect_task_ids()
    return task_ids


def compile_data_with_task_ids(conn, task_ids):
    # Define the fields
    fields = TaskFieldList()
    fields.append(TaskIdField(name="TaskId"))
    fields.append(StimSpecIdField(conn, name="StimId"))
    fields.append(ShaftField(conn))
    return get_data_from_tasks(fields, task_ids)


def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_ga_dev_240207")

    # conn.execute("TRUNCATE TABLE ExpLog")

    baseline_function = TuningFunction()

    tuning_peak = {
        "angularPosition": {"theta": math.pi, "phi": math.pi / 2},
        "radialPosition": 15,
        "orientation": {"theta": math.pi, "phi": math.pi / 4},
        "length": 35,
        "curvature": 0.02,
        "radius": 8,
    }

    list_of_tuning_ranges = {
        "angularPosition.theta": {"min": -math.pi, "max": math.pi},
        "angularPosition.phi": {"min": 0, "max": math.pi},
        "radialPosition": {"min": 0, "max": 60},
        "orientation.theta": {"min": -math.pi, "max": math.pi},
        "orientation.phi": {"min": 0, "max": math.pi / 2},
        "length": {"min": 0, "max": 50},
        "curvature": {"min": 0, "max": 0.15},
        "radius": {"min": 0, "max": 30},
    }

    shaft_function = ShaftTuningFunction(tuning_peak, list_of_tuning_ranges)

    list_of_tuning_functions = [shaft_function, shaft_function]

    # PIPELINE
    task_ids = collect_task_ids(conn)
    data = compile_data_with_task_ids(conn, task_ids)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)
    response_rates = generate_responses(data, list_of_tuning_functions)

    # PLOTTING
    # plot_responses([response[1] for response in response_rates], data.iterrows())

    # EXPORT]
    insert_to_channel_responses(conn, response_rates, data)


def insert_to_channel_responses(conn, response_rates: list[dict], data: pd.DataFrame):
    for (stim_id, task_id), response_rate in zip(data[["StimId", "TaskId"]].values, response_rates):
        for channel, spikes_per_second in response_rate.items():
            query = ("INSERT IGNORE INTO ChannelResponses "
                     "(stim_id, task_id, channel, spikes_per_second) "
                     "VALUES (%s, %s, %s, %s)")
            params = (int(stim_id), int(task_id), channel.value, float(spikes_per_second))
            conn.execute(query, params)
            conn.mydb.commit()


class TuningFunction:
    response_range = {"min": 0, "max": 100}

    baseline_range = {"min": 0, "max": 30}

    def get_response(self, data: pd.Series) -> float:
        return self.get_baseline_response()

    def get_baseline_response(self):
        return random.uniform(self.baseline_range["min"], self.baseline_range["max"])


class ShaftTuningFunction(TuningFunction):

    def __init__(self, shaft_peaks: dict, field_ranges: dict):
        super().__init__()
        self.tuning_function = None
        self.shaft_peaks = shaft_peaks
        self.field_ranges = field_ranges

    def get_response(self, data: pd.Series):
        peak = []
        flatten_dictionary(self.shaft_peaks, peak, None)

        periodic_indices = [0, 1, 3, 4]
        non_periodic_indices = [2, 5, 6, 7]
        mu = np.array(peak)
        tuning_width = self.assign_tuning_width_from_range(fraction_of_range=1.0 / 2.0)
        self.tuning_function = MultiCustomNormalTuningFunction(mu, tuning_width, periodic_indices, non_periodic_indices,
                                                               100)

        if not isinstance(data['ShaftField'], list):
            data['ShaftField'] = [data['ShaftField']]

        stim = [[
            component['angularPosition']['theta'],
            component['angularPosition']['phi'],
            component["radialPosition"],
            component["orientation"]["theta"],
            component["orientation"]["phi"],
            component["length"],
            component["curvature"],
            component["radius"]
        ] for component in data['ShaftField']]
        stim = [[float(x) for x in component] for component in stim]

        responses_per_component = []
        for component in stim:
            response = self.tuning_function.response(component)
            responses_per_component.append(response)

        response = np.max(responses_per_component)
        return response

    def assign_tuning_width_from_range(self, fraction_of_range: float = 1.0 / 5.0):
        tuning_range_maxes = []
        extract_values_with_key_into_list(self.field_ranges, tuning_range_maxes, "max")
        tuning_range_mins = []
        extract_values_with_key_into_list(self.field_ranges, tuning_range_mins, "min")
        tuning_width = [max - min for max, min in zip(tuning_range_maxes, tuning_range_mins)]
        tuning_width = np.array(tuning_width) * fraction_of_range
        return tuning_width


def collect_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_trials()


def generate_responses(data: pd.DataFrame, list_of_tuning_functions: list[TuningFunction]) -> list[dict[int, double]]:
    # for each row in data, generate a response using tuning functions
    responses = []
    channels = [Channel.A_000, Channel.A_001]
    for index, row in data.iterrows():
        responses.append(
            {channels[unit]: tuning_function.get_response(row) for unit, tuning_function in
             enumerate(list_of_tuning_functions)})

    return responses


def plot_responses(responses, data):
    all_thetas = []
    closest_thetas = []
    all_phis = []
    closest_phis = []
    all_radial_positions = []
    closest_radial_positions = []
    all_lengths = []
    closest_lengths = []
    all_curvatures = []
    closest_curvatures = []
    all_radii = []
    closest_radii = []
    all_responses = []
    closest_responses = []

    for response, row in zip(responses, data):
        row = row[1]
        # DEBUG
        thetas = [float(component["angularPosition"]["theta"]) for component in row["ShaftField"]]
        thetas_differences = [abs(theta - 0) for theta in thetas]
        closest_theta = thetas[np.argmin(thetas_differences)]

        phis = [float(component["angularPosition"]["phi"]) for component in row["ShaftField"]]
        phis_differences = [abs(phi - math.pi / 2) for phi in phis]
        closest_phi = phis[np.argmin(phis_differences)]

        radial_positions = [float(component["radialPosition"]) for component in row["ShaftField"]]
        radial_positions_differences = [abs(radialPosition - 20) for radialPosition in radial_positions]
        closest_radial_position = radial_positions[np.argmin(radial_positions_differences)]

        lengths = [float(component["length"]) for component in row["ShaftField"]]
        lengths_differences = [abs(length - 10) for length in lengths]
        closest_length = lengths[np.argmin(lengths_differences)]

        curvatures = [float(component["curvature"]) for component in row["ShaftField"]]
        curvatures_differences = [abs(curvature - 0) for curvature in curvatures]
        closest_curvature = curvatures[np.argmin(curvatures_differences)]

        radii = [float(component["radius"]) for component in row["ShaftField"]]
        radii_differences = [abs(radius - 10) for radius in radii]
        closest_radius = radii[np.argmin(radii_differences)]

        closest_responses.append(response)
        closest_thetas.append(closest_theta)
        for theta in thetas:
            all_thetas.append(theta)
            all_responses.append(response)
        closest_phis.append(closest_phi)
        for phi in phis:
            all_phis.append(phi)
        closest_radial_positions.append(closest_radial_position)
        for radial_position in radial_positions:
            all_radial_positions.append(radial_position)
        closest_lengths.append(closest_length)
        for length in lengths:
            all_lengths.append(length)
        closest_curvatures.append(closest_curvature)
        for curvature in curvatures:
            all_curvatures.append(curvature)
        closest_radii.append(closest_radius)
        for radius in radii:
            all_radii.append(radius)

    # DEBUG
    fig, axes = plt.subplots(6)
    # print(all_thetas)
    axes[0].scatter(all_thetas, all_phis, c=all_responses)
    axes[1].scatter(closest_thetas, closest_phis, c=closest_responses)
    axes[2].scatter(all_radial_positions, all_responses)
    axes[2].scatter(closest_radial_positions, closest_responses, alpha=0.5)
    axes[3].scatter(all_lengths, all_responses)
    axes[3].scatter(closest_lengths, closest_responses, alpha=0.5)
    axes[4].scatter(all_curvatures, all_responses)
    axes[4].scatter(closest_curvatures, closest_responses, alpha=0.5)
    axes[5].scatter(all_radii, all_responses)
    axes[5].scatter(closest_radii, closest_responses, alpha=0.5)


# write sql query to insert response_rates into ExpLog table
def insert_to_exp_log(conn, response_rates: list[dict[int, double]], ids: pd.Series):
    for stim_id, stim_response_rate in zip(ids, response_rates):
        average_response_rate = sum(stim_response_rate.values()) / len(stim_response_rate)
        conn.execute("UPDATE StimGaInfo SET response = %s WHERE stim_id = %s", (average_response_rate, str(stim_id)))
        # conn.fetch_all()
        conn.mydb.commit()

    for stim_id, stim_response_rate in zip(ids, response_rates):
        conn.execute("INSERT INTO ExpLog (tstamp, memo) VALUES (%s, %s)", (stim_id, str(stim_response_rate)))
        # conn.fetch_all()
        conn.mydb.commit()


if __name__ == '__main__':
    main()

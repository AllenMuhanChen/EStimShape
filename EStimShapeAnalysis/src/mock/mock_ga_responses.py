from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from numpy import double
from scipy.stats import multivariate_normal

from src.compile.classic_database_fields import StimSpecDataField, StimSpecIdField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_collector import TrialCollector
from src.compile.trial_field import FieldList, get_data_from_trials
from src.mock import mock_rwa_plot, mock_rwa_analysis
from src.mock.mock_rwa_analysis import condition_spherical_angles, hemisphericalize_orientation
from src.util import time_util
from src.util.connection import Connection
from src.util.dictionary_util import flatten_dictionary, \
    extract_values_with_key_into_list
from src.util.time_util import When


def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")

    conn.execute("TRUNCATE TABLE ExpLog")

    baseline_function = TuningFunction()

    tuning_peak = {
        "angularPosition": {"theta": 0, "phi": math.pi / 2},
        "radialPosition": 30,
        "orientation": {"theta": 0, "phi": math.pi / 4},
        "length": 25,
        "curvature": 0.06,
        "radius": 6,
    }

    list_of_tuning_ranges = {
        "angularPosition.theta": {"min": -math.pi, "max": math.pi},
        "angularPosition.phi": {"min": 0, "max": math.pi},
        "radialPosition": {"min": 0, "max": 60},
        "orientation.theta": {"min": -math.pi, "max": math.pi},
        "orientation.phi": {"min": 0, "max": math.pi/2},
        "length": {"min": 0, "max": 50},
        "curvature": {"min": 0, "max": 0.15},
        "radius": {"min": 0, "max": 12},
    }

    shaft_function = ShaftTuningFunction(tuning_peak, list_of_tuning_ranges)

    list_of_tuning_functions = [baseline_function, shaft_function]

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)
    response_rates = generate_responses(data, list_of_tuning_functions)

    # PLOTTING
    # plot_responses([response[1] for response in response_rates], data.iterrows())

    # EXPORT]
    insert_to_exp_log(conn, response_rates, data["Id"])

    # DEBUG
    mock_rwa_analysis.main()
    mock_rwa_plot.main()
    # plt.show()


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
        self.shaft_peaks = shaft_peaks
        self.field_ranges = field_ranges

    def get_response(self, data: pd.Series):
        peak = []
        flatten_dictionary(self.shaft_peaks, peak, None)
        print(data)

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
            # distance = np.linalg.norm(np.array(component) - np.array(peak))

            tuning_range_maxes = []
            extract_values_with_key_into_list(self.field_ranges, tuning_range_maxes, "max")
            tuning_range_mins = []
            extract_values_with_key_into_list(self.field_ranges, tuning_range_mins, "min")
            cov = [max - min for max, min in zip(tuning_range_maxes, tuning_range_mins)]
            total_energy = np.prod(cov)
            cov = np.array(cov) / 5
            response = total_energy * multivariate_normal.pdf(np.array(component), mean=np.array(peak), cov=cov,
                                                              allow_singular=True)
            # response = 100 * np.exp((-(distance)**2)/ (2*sigma**2))
            responses_per_component.append(response)

        return np.max(responses_per_component)


def collect_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_trials()


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = FieldList()
    fields.append(StimSpecIdField(conn, "Id"))
    fields.append(ShaftField(mstick_spec_data_source))
    # fields.append(TerminationField(mstick_spec_data_source))
    # fields.append(JunctionField(mstick_spec_data_source))

    return get_data_from_trials(fields, trial_tstamps)


def generate_responses(data: pd.DataFrame, list_of_tuning_functions: list[TuningFunction]) -> list[dict[int, double]]:
    # for each row in data, generate a response using tuning functions
    responses = []

    for index, row in data.iterrows():
        responses.append(
            {unit: tuning_function.get_response(row) for unit, tuning_function in enumerate(list_of_tuning_functions)})

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
    print(all_thetas)
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
        conn.execute("INSERT INTO ExpLog (tstamp, memo) VALUES (%s, %s)", (stim_id, str(stim_response_rate)))


if __name__ == '__main__':
    main()

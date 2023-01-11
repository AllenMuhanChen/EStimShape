from __future__ import annotations


import math
import random

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from numpy import shape, double
from scipy.ndimage import gaussian_filter
from scipy.stats import multivariate_normal

from src.compile.classic_database_fields import StimSpecDataField, StimSpecIdField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_collector import TrialCollector
from src.compile.trial_field import FieldList, get_data_from_trials
from src.util import time_util
from src.util.connection import Connection
from src.util.time_util import When


def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")

    baseline_function = TuningFunction()

    tuning_peak = {"angularPosition": {"theta": 0, "phi": math.pi / 2},
                   "radialPosition": 20,
                   "length": 10,
                   "curvature": 0,
                   "radius": 10}
    list_of_tuning_ranges = {"theta": {"min": -math.pi, "max": math.pi},
                             "phi": {"min": 0, "max": math.pi},
                             "radialPosition": {"min": 0, "max": 100},
                             "length": {"min": 0, "max": 200},
                             "curvature": {"min": 0, "max": 1},
                             "radius": {"min": 0, "max": 20}}
    shaft_function = ShaftTuningFunction(tuning_peak, list_of_tuning_ranges)

    list_of_tuning_functions = [baseline_function, shaft_function]

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    response_rates = generate_responses(data, list_of_tuning_functions)

    # EXPORT]
    insert_to_exp_log(conn, response_rates, data["Id"])

    # DEBUG
    plt.show()


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

    def differences_per_field(self, field: dict, peak_field, peak: dict) -> list[float]:
        # primary_key = field[0].keys()
        # primary_key = next(iter(primary_key))
        primary_key = peak_field
        differences_per_field_per_component = []  # one item in each outer list for each component. one in each inner list for each data field in that component dictionary
        if isinstance(peak, dict):
            for peak_sub_field_key, peak_sub_field_value in peak.items():
                if isinstance(peak_sub_field_value, dict):
                    return self.differences_per_field(field[peak_sub_field_key], peak_sub_field_value, )
                else:
                    differences_per_component = [
                        (float(peak_sub_field_value) - float(component[primary_key][peak_sub_field_key]))
                        for component in field]
                    differences_per_field_per_component.append(differences_per_component)
        else:
            differences_per_component = [(float(peak) - float(component[primary_key])) for component in field]
            differences_per_field_per_component.append(differences_per_component)
        # sum the differences for each component
        return differences_per_field_per_component

    def max_distance(self, peak_field, peak: dict) -> list[float]:
        """ Calculate max possible distance between a shaft field and the peak. """
        max_differences_per_field = []  # one item in each outer list for each component. one in each inner list for each data field in that component dictionary
        if isinstance(peak, dict):
            for peak_sub_field_key, peak_sub_field_value in peak.items():
                if isinstance(peak_sub_field_value, dict):
                    return self.max_distance(peak_sub_field_value)
                else:
                    field_max_difference = max(self.field_ranges[peak_sub_field_key]['max'] - peak_sub_field_value,
                                               abs(self.field_ranges[peak_sub_field_key]['min'] - peak_sub_field_value))
                    max_differences_per_field.append(field_max_difference)
        else:
            field_max_difference = max(self.field_ranges[peak_field]['max'] - peak,
                                       abs(self.field_ranges[peak_field]['min'] - peak))
            max_differences_per_field.append(field_max_difference)
        # sum the differences for each component
        return max_differences_per_field

    def get_response(self, data: pd.Series):
        peak = []
        self.recursively_convert_each_dictionary_value_to_dimension_of_a_point(self.shaft_peaks, peak)

        stim = [[component['angularPosition']['theta'],
                 component['angularPosition']['phi'],
                 component["radialPosition"],
                 component["length"],
                 component["curvature"],
                 component["radius"]] for component in data['ShaftField']]
        stim = [[float(x) for x in component] for component in stim]

        sigma = 1

        responses_per_component = []
        for component in stim:
            # distance = np.linalg.norm(np.array(component) - np.array(peak))

            tuning_range_maxes = []
            self.recursively_put_each_max_value_from_dictionary_into_list(self.field_ranges, tuning_range_maxes)
            tuning_range_mins = []
            self.recursively_put_each_min_value_from_dictionary_into_list(self.field_ranges, tuning_range_mins)
            cov = [max - min for max, min in zip(tuning_range_maxes, tuning_range_mins)]
            total_energy = np.prod(cov)
            cov = np.array(cov) / 2
            response = total_energy * multivariate_normal.pdf(np.array(component), mean=np.array(peak), cov=cov,
                                                              allow_singular=True)
            # response = 100 * np.exp((-(distance)**2)/ (2*sigma**2))
            responses_per_component.append(response)

        return np.max(responses_per_component)

    def recursively_convert_each_dictionary_value_to_dimension_of_a_point(self, dictionary: dict, point: list[float]):
        if isinstance(dictionary, dict):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    self.recursively_convert_each_dictionary_value_to_dimension_of_a_point(value, point)
                else:
                    point.append(value)
        elif isinstance(dictionary, list):
            for value in dictionary:
                if isinstance(value, dict):
                    self.recursively_convert_each_dictionary_value_to_dimension_of_a_point(value, point)
                else:
                    point.append(value)

    def recursively_put_each_max_value_from_dictionary_into_list(self, dictionary: dict, list: list[float]):
        if isinstance(dictionary, dict):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    self.recursively_put_each_max_value_from_dictionary_into_list(value, list)
                else:
                    if key == 'max':
                        list.append(value)

        elif isinstance(dictionary, list):
            for value in dictionary:
                if isinstance(value, dict):
                    self.recursively_put_each_max_value_from_dictionary_into_list(value, list)
                else:
                    list.append(value)

    def recursively_put_each_min_value_from_dictionary_into_list(self, dictionary: dict, list: list[float]):
        if isinstance(dictionary, dict):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    self.recursively_put_each_min_value_from_dictionary_into_list(value, list)
                else:
                    if key == 'min':
                        list.append(value)

        elif isinstance(dictionary, list):
            for value in dictionary:
                if isinstance(value, dict):
                    self.recursively_put_each_min_value_from_dictionary_into_list(value, list)
                else:
                    list.append(value)

    def get_response_classic(self, data: pd.Series) -> float:
        # generate response based on distance between same entry in data and peak
        data = data["ShaftField"]
        raw_distance_per_peak_per_field_per_component = [self.differences_per_field(data, peak_field, peak_value) for
                                                         peak_field, peak_value in
                                                         self.shaft_peaks.items()]
        max_distances_per_peak_per_field_per_component = [self.max_distance(peak_field, peak_value) for
                                                          peak_field, peak_value in
                                                          self.shaft_peaks.items()]

        # PER PEAK
        response_per_peak = []
        for raw_distances_per_field_per_component, max_distance_per_field in zip(
                raw_distance_per_peak_per_field_per_component,
                max_distances_per_peak_per_field_per_component):
            response_per_field = []
            # PER FIELD IN PEAK
            for raw_distances_per_component, max_distance_for_field in zip(raw_distances_per_field_per_component,
                                                                           max_distance_per_field):
                response_per_component = []
                # PER SUBFIELD IN FIELD
                for raw_distance_for_component in raw_distances_per_component:
                    normalized_distance = abs(raw_distance_for_component / max_distance_for_field)
                    normalized_closeness = 1 - normalized_distance
                    response = np.power(normalized_closeness, 3) * self.response_range["max"]
                    response_per_component.append(response)
                response_per_field.append(max(response_per_component))
            response_per_peak.append(np.average(response_per_field))
        response = np.average(response_per_peak)

        return response




def collect_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_trials()


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = FieldList()
    fields.append(StimSpecIdField(conn, "Id"))
    fields.append(ShaftField(mstick_spec_data_source))
    fields.append(TerminationField(mstick_spec_data_source))
    fields.append(JunctionField(mstick_spec_data_source))

    return get_data_from_trials(fields, trial_tstamps)


def generate_responses(data: pd.DataFrame, list_of_tuning_functions: list[TuningFunction]) -> list[dict[int, double]]:
    # for each row in data, generate a response using tuning functions
    responses = []

    # DEBUG
    all_thetas = []
    closest_thetas = []
    all_phis = []
    closest_phis = []
    all_radial_positions = []
    closet_radial_positions = []
    all_responses = []
    closest_responses = []
    #######
    for index, row in data.iterrows():

        responses.append(
            {unit: tuning_function.get_response(row) for unit, tuning_function in enumerate(list_of_tuning_functions)})

        # DEBUG
        response = responses[-1][1]

        thetas = [float(component["angularPosition"]["theta"]) for component in row["ShaftField"]]
        thetas_differences = [abs(theta - 0) for theta in thetas]
        closest_theta = thetas[np.argmin(thetas_differences)]

        phis = [float(component["angularPosition"]["phi"]) for component in row["ShaftField"]]
        phis_differences = [abs(phi - math.pi / 2) for phi in phis]
        closest_phi = phis[np.argmin(phis_differences)]

        radial_positions = [float(component["radialPosition"]) for component in row["ShaftField"]]
        radial_positions_differences = [abs(radialPosition - 20) for radialPosition in radial_positions]
        closest_radial_position = radial_positions[np.argmin(radial_positions_differences)]

        closest_responses.append(response)
        closest_thetas.append(closest_theta)
        for theta in thetas:
            all_thetas.append(theta)
            all_responses.append(response)
        closest_phis.append(closest_phi)
        for phi in phis:
            all_phis.append(phi)
        closet_radial_positions.append(closest_radial_position)
        for radial_position in radial_positions:
            all_radial_positions.append(radial_position)
    # DEBUG
    fig, axes = plt.subplots(3)
    print(all_thetas)
    axes[0].scatter(all_thetas, all_phis, c=all_responses)
    axes[1].scatter(closest_thetas, closest_phis, c=closest_responses)
    axes[2].scatter(all_radial_positions, all_responses)
    axes[2].scatter(closet_radial_positions, closest_responses, alpha=0.5)

    return responses


# write sql query to insert response_rates into ExpLog table
def insert_to_exp_log(conn, response_rates: list[dict[int, double]], ids: pd.Series):
    for stim_id, stim_response_rate in zip(ids, response_rates):
        conn.execute("INSERT INTO ExpLog (tstamp, memo) VALUES (%s, %s)", (stim_id, str(stim_response_rate)))

if __name__ == '__main__':
    main()

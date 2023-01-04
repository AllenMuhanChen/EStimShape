from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd
from numpy import shape, double

from src.compile.classic_database_fields import StimSpecDataField, StimSpecIdField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_collector import TrialCollector
from src.compile.trial_field import FieldList, get_data_from_trials
from src.util import time_util
from src.util.connection import Connection
from src.util.time_util import When


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

    def difference(self, field: dict, peak: dict) -> list[float]:
        primary_key = field[0].keys()
        primary_key = next(iter(primary_key))
        differences = []  # one item in each outer list for each component. one in each inner list for each data field in that component dictionary
        for peak_sub_field_key, peak_sub_field_value in peak.items():
            total_difference = 0
            if isinstance(peak_sub_field_value, dict):
                self.difference(field[peak_sub_field_key], peak_sub_field_value, )
            else:
                component_differences = [
                    (float(peak_sub_field_value) - float(component[primary_key][peak_sub_field_key]))
                    for component in field]
                differences.append(component_differences)

        # sum the differences for each component
        summed_component_differences = [sum(component_differences) for component_differences in differences]
        return summed_component_differences
        # output = {key: value for key, value in zip(peak.keys(), summed_component_differences)}
        # return output

    def get_response(self, data: pd.Series) -> float:
        # generate response based on distance between same entry in data and peak
        field_distances = [self.difference(data["ShaftField"], peak_value) for field, peak_value in
                           self.shaft_peaks.items()]
        normalized_distances = [[distance / self.field_ranges[field]['max'] for distance in distances] for
                                field, distances in
                                zip(self.field_ranges.keys(), field_distances)]
        normalized_distances = [[abs(distance) for distance in distances] for distances in normalized_distances]
        normalized_distances = [[1 - distance for distance in distances] for distances in normalized_distances]

        # component-wise distance. list of lists. inner list is distance between each component's shaft field and peak. outer list is
        # for each shaft field

        component_responses = [
            [normalized_distance * normalized_distance * self.response_range['max'] for normalized_distance in distance]
            for
            distance in normalized_distances]
        response = sum([sum(component_response) for component_response in component_responses])
        # return sum between a random baseline response and the max of responses
        return self.get_baseline_response() + response


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


def normalize_angle(angle):
    return angle % (2 * math.pi)


def generate_responses(data: pd.DataFrame, list_of_tuning_functions: list[TuningFunction]) -> list[dict[int, double]]:
    # for each row in data, generate a response using tuning functions
    responses = []
    for index, row in data.iterrows():
        responses.append(
            {unit: tuning_function.get_response(row) for unit, tuning_function in enumerate(list_of_tuning_functions)})

    return responses


def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")

    baseline_function = TuningFunction()

    tuning_peak = {"angularPosition": {"theta": 0, "phi": 0}}
    list_of_tuning_ranges = {"theta": {"min": -math.pi, "max": math.pi}, "phi": {"min": -math.pi, "max": math.pi}}
    shaft_function = ShaftTuningFunction(tuning_peak, list_of_tuning_ranges)

    list_of_tuning_functions = [baseline_function, shaft_function]

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    response_rates = generate_responses(data, list_of_tuning_functions)

    # EXPORT]
    insert_to_exp_log(conn, response_rates, data["Id"])


# write sql query to insert response_rates into ExpLog table
def insert_to_exp_log(conn, response_rates: list[dict[int, double]], ids: pd.Series):
    for stim_id, stim_response_rate in zip(ids, response_rates):
            conn.execute("INSERT INTO ExpLog (tstamp, memo) VALUES (%s, %s)", (stim_id, str(stim_response_rate)))


if __name__ == '__main__':
    main()

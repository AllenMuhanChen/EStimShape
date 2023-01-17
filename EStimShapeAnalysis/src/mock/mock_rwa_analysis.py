from __future__ import annotations
import ast
from math import pi

import jsonpickle as jsonpickle
import numpy as np
import pandas as pd

from src.analysis.rwa import rwa, Binner, LabelledMatrix
from src.compile.classic_database_fields import StimSpecDataField, StimSpecIdField, GaTypeField, GaLineageField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_field import FieldList, DatabaseField, get_data_from_trials
from src.mock.mock_ga_responses import collect_trials
from src.util import time_util
from src.util.connection import Connection
from src.util.time_util import When


def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")
    num_bins = 10
    binner_for_shaft_fields = {
        "theta": Binner(-pi, pi, num_bins),
        "phi": Binner(0, pi, num_bins),
        "radialPosition": Binner(0, 30, num_bins),
        "length": Binner(0, 50, num_bins),
        "curvature": Binner(0, 0.15, num_bins),
        "radius": Binner(0, 12, num_bins),
    }

    # a percentage of the number of bins
    sigma_for_fields = {
        "theta": 1 / 8,
        "phi": 1 / 8,
        "radialPosition": 1 / 4,
        "length": 1 / 4,
        "curvature": 1 / 2,
        "radius": 1 / 4,
    }

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    data = condition_spherical_angles(data)
    data = condition_for_inside_bins(data, binner_for_shaft_fields)
    response_weighted_average = compute_rwa_from_lineages(data, "3D", binner_for_shaft_fields,
                                                          sigma_for_fields=sigma_for_fields)
    # response_weighted_average = rwa(data["Shaft"], data["Response-1"], binner_for_shaft_fields)

    # SAVE
    filename = "/home/r2_allen/Documents/EStimShape/dev_221110/rwa/test_rwa.json"
    with open(filename, "w") as file:
        file.write(jsonpickle.encode(response_weighted_average))


def compute_rwa_from_lineages(data, ga_type, binner_for_fields, sigma_for_fields=None):
    """sigma_for_fields is expressed as a percentage of the number of bins for that dimension"""
    data = data.loc[data['GaType'] == ga_type]
    rwas = []
    for (lineage, lineage_data) in data.groupby("Lineage"):
        rwas.append(rwa(lineage_data["Shaft"], lineage_data["Response-1"], binner_for_fields, sigma_for_fields))
    print("Multiplying Lineage RWAs")
    rwas_labelled_matrices = [next(r) for r in rwas]
    rwa_prod = np.prod(np.array([rwa_labelled_matrix.matrix for rwa_labelled_matrix in rwas_labelled_matrices]), axis=0)
    return rwas_labelled_matrices[0].copy_labels(rwa_prod)


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = FieldList()
    fields.append(GaTypeField(conn, "GaType"))
    fields.append(GaLineageField(conn, "Lineage"))
    fields.append(StimSpecIdField(conn, "Id"))
    fields.append(MockResponseField(conn, 1, name="Response-1"))
    fields.append(ShaftField(mstick_spec_data_source, name="Shaft"))
    fields.append(TerminationField(mstick_spec_data_source, name="Termination"))
    fields.append(JunctionField(mstick_spec_data_source, name="Junction"))

    data = get_data_from_trials(fields, trial_tstamps)
    return data


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


def condition_spherical_angles(data):
    for column in data:
        column_data = data[column]
        # print(column_data)
        if column_data.dtype == object:
            for stim_data in column_data.array:
                recursively_apply_function_to_subdictionaries_values_with_keys(stim_data, ["theta", "phi"],
                                                                               condition_theta_and_phi)

    return data


def condition_theta_and_phi(dictionary: dict):
    theta = np.float32(dictionary["theta"])
    phi = np.float32(dictionary["phi"])
    pi = np.float32(np.pi)
    # THETA [-pi, pi]
    theta = newMod(theta, (2 * pi))
    if theta > pi:
        theta = -((2 * pi) - theta)
    elif theta < -pi:
        theta = (2 * pi) + theta

    # PHI [0, pi]
    phi = newMod(phi, (2 * pi))
    if phi < 0:
        phi += (2 * pi)
    if phi > pi:
        phi = (2 * pi) - phi
        theta = -theta
    return {"theta": theta, "phi": phi}


def newMod(a, b):
    res = a % b
    return res if not res else res - b if a < 0 else res


def condition_for_inside_bins(data: pd.DataFrame, binner_for_fields: dict[str, Binner]):
    row_indices_to_remove = []
    for column in data:
        column_data = data[column]
        # print(column_data)
        if column_data.dtype == object:
            for stim_index, stim_data in enumerate(column_data.array):
                is_field_outside_range = False
                if recursively_check_condition_for_subdictionaries(stim_data, check_if_outside_binrange,
                                                                   is_field_outside_range, binner_for_fields):
                    row_indices_to_remove.append(stim_index)
    data = data.drop(labels=row_indices_to_remove, axis=0, inplace=False)
    return data


def check_if_outside_binrange(field_name: str, value, binner_for_fields: dict[str, Binner]) -> bool:
    """Outputs true only if the field is outside the bin range specified in its corresponding binner"""
    binner = binner_for_fields.get(field_name)
    if binner is not None:
        return float(value) < binner.start or float(value) > binner.end
    else:
        return False


def recursively_check_condition_for_subdictionaries(dictionary: dict, condition, boolean_to_update, *args):
    """Returns true if any of the subdictionaries of the dictionary satisfy the condition"""
    if isinstance(dictionary, dict):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                if recursively_check_condition_for_subdictionaries(value, condition, boolean_to_update, *args):
                    return True
            else:
                if condition(key, value, *args):
                    return True

    elif isinstance(dictionary, list):
        for item in dictionary:
            if recursively_check_condition_for_subdictionaries(item, condition, boolean_to_update, *args):
                return True


def recursively_apply_function_to_subdictionaries_values_with_keys(dictionary, keys, function):
    if isinstance(dictionary, dict):
        if set(keys).issubset(dictionary.keys()):
            dictionary = function(dictionary)
        else:
            for key, value in dictionary.items():
                dictionary[key] = recursively_apply_function_to_subdictionaries_values_with_keys(value, keys, function)
    elif isinstance(dictionary, list):
        for index, item in enumerate(dictionary):
            dictionary[index] = recursively_apply_function_to_subdictionaries_values_with_keys(item, keys, function)
    return dictionary


if __name__ == '__main__':
    main()

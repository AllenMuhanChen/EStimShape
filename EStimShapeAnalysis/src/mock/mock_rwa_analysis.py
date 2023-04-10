from __future__ import annotations
import ast
from math import pi

import jsonpickle as jsonpickle
import numpy as np
import pandas as pd

from src.analysis.rwa import Binner, AutomaticBinner, rwa, combine_rwas, get_next
from src.compile.classic_database_fields import StimSpecDataField, StimSpecIdField, GaTypeField, GaLineageField, \
    NewGaLineageField, NewGaNameField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_collector import TrialCollector
from src.compile.trial_field import FieldList, get_data_from_trials
from src.util import time_util
from src.util.connection import Connection
from src.util.dictionary_util import apply_function_to_subdictionaries_values_with_keys, \
    check_condition_on_subdictionaries
from src.util.time_util import When


def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")
    num_bins = 10

    # a percentage of the number of bins
    sigma_for_fields = {
        "theta": 1 / 5,
        "angularPosition.phi": 1 / 5,
        "radialPosition": 1 / 5,
        "orientation.phi": 1 / 5,
        "length": 1 / 5,
        "curvature": 1 / 5,
        "radius": 1 / 5,
    }

    padding_for_fields = {
        "theta": "wrap",
        "angularPosition.phi": "wrap",
        "radialPosition": "nearest",
        "orientation.phi": "wrap",
        "length": "nearest",
        "curvature": "nearest",
        "radius": "nearest",
    }

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)
    data_shaft = data['Shaft'].tolist()

    binner_for_shaft_fields = {
        "theta": Binner(-pi, pi, 9),
        "angularPosition.phi": Binner(0, pi, 9),
        "radialPosition": AutomaticBinner("radialPosition", data_shaft, 9),
        "orientation.phi": Binner(0, pi/2, 9),
        "length": AutomaticBinner("length", data_shaft, 9),
        "curvature": AutomaticBinner("curvature", data_shaft, 9),
        "radius": AutomaticBinner("radius", data_shaft, 9),
    }

    response_weighted_average = compute_rwa_from_lineages(data, "New3D", binner_for_shaft_fields,
                                                          sigma_for_fields=sigma_for_fields,
                                                          padding_for_fields=padding_for_fields)

    # response_weighted_average = rwa(data["Shaft"], data["Response-1"], binner_for_shaft_fields,
    #     sigma_for_fields, padding_for_fields)
    # SAVE
    save(response_weighted_average, "test_rwa")


def save(response_weighted_average, file_name):
    filename = "/home/r2_allen/Documents/EStimShape/dev_221110/rwa/%s.json" % file_name
    with open(filename, "w") as file:
        file.write(jsonpickle.encode(response_weighted_average))
        file.close()


def collect_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_trials()


def compute_rwa_from_lineages(data, ga_type, binner_for_fields, sigma_for_fields=None, padding_for_fields=None):
    """sigma_for_fields is expressed as a percentage of the number of bins for that dimension"""
    data = data.loc[data['GaType'] == ga_type]
    rwas = []
    for (lineage, lineage_data) in data.groupby("Lineage"):
        rwas.append(rwa(lineage_data["Shaft"], lineage_data["Response-1"], binner_for_fields,
                        sigma_for_fields, padding_for_fields))
    print("Multiplying Lineage RWAs")

    rwas = [get_next(r) for r in rwas]
    for lineage_index, rwa_lineage in enumerate(rwas):
        save(rwa_lineage, "lineage_rwa_%d" % lineage_index)
    rwa_multiplied = combine_rwas(rwas)

    return rwa_multiplied


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = FieldList()
    fields.append(NewGaNameField(conn, "GaType"))
    fields.append(NewGaLineageField(conn, "Lineage"))
    # fields.append(GaTypeField(conn, "GaType"))
    # fields.append(GaLineageField(conn, "Lineage"))
    fields.append(StimSpecIdField(conn, "Id"))
    fields.append(MockResponseField(conn, 1, name="Response-1"))
    fields.append(ShaftField(mstick_spec_data_source, name="Shaft"))
    # fields.append(TerminationField(mstick_spec_data_source, name="Termination"))
    # fields.append(JunctionField(mstick_spec_data_source, name="Junction"))

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
                apply_function_to_subdictionaries_values_with_keys(stim_data, ["theta", "phi"],
                                                                   condition_theta_and_phi)

    return data


def condition_theta_and_phi(dictionary: dict):
    theta = np.float32(dictionary["theta"])
    phi = np.float32(dictionary["phi"])
    pi = np.float32(np.pi)

    # PHI [0, pi]
    phi = modulus(phi, (2 * pi))
    if phi < 0:
        phi += (2 * pi)
    if phi > pi:
        phi = (2 * pi) - phi
        theta = theta + pi

    # THETA [-pi, pi]
    theta = map_theta(theta)

    return {"theta": theta, "phi": phi}


def map_theta(theta):
    """Maps theta to [-pi, pi]"""
    theta = modulus(theta, (2 * pi))
    if theta > pi:
        theta = -((2 * pi) - theta)
    elif theta < -pi:
        theta = (2 * pi) + theta
    return theta


def modulus(a, b):
    """modulus function that works with negative numbers"""
    res = a % b
    return res if not res else res - b if a < 0 else res


def hemisphericalize_orientation(data):
    for column in data:
        column_data = data[column]
        # print(column_data)
        if column_data.dtype == object:
            for stim_data in column_data.array:
                apply_function_to_subdictionaries_values_with_keys(stim_data, ['orientation'],
                                                                   hemisphericalize)
    return data


def hemisphericalize(dictionary: dict):
    output = dictionary
    orientation = output['orientation']
    theta = np.float32(orientation['theta'])
    phi = np.float32(orientation['phi'])

    while phi > pi / 2:
        phi = pi - phi
        theta = theta + pi
        theta = map_theta(theta)

    output['orientation']['theta'] = theta
    output['orientation']['phi'] = phi
    return output


def condition_for_inside_bins(data: pd.DataFrame, binner_for_fields: dict[str, Binner]):
    row_indices_to_remove = []
    for column in data:
        column_data = data[column]
        # print(column_data)
        if column_data.dtype == object:
            for stim_index, stim_data in enumerate(column_data.array):
                is_field_outside_range = False
                if check_condition_on_subdictionaries(stim_data, check_if_outside_binrange,
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


if __name__ == '__main__':
    main()

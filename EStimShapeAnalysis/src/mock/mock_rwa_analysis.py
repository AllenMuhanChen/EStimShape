from __future__ import annotations
import ast
from math import pi

import jsonpickle as jsonpickle
import numpy as np
import pandas as pd

from src.analysis.rwa import rwa, Binner, AutomaticBinner
from src.compile.classic_database_fields import StimSpecDataField, StimSpecIdField, GaTypeField, GaLineageField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_field import FieldList, get_data_from_trials
from src.mock.mock_ga_responses import collect_trials
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
    data = hemisphericalize_orientation(data)
    data_shaft = data['Shaft'].tolist()
    binner_for_shaft_fields = {
        "theta": AutomaticBinner("theta", data_shaft, num_bins),
        "phi": AutomaticBinner("phi", data_shaft, num_bins),
        "radialPosition": AutomaticBinner("radialPosition", data_shaft, num_bins),
        "length": AutomaticBinner("length", data_shaft, num_bins),
        "curvature": AutomaticBinner("curvature", data_shaft, num_bins),
        "radius": AutomaticBinner("radius", data_shaft, num_bins),
    }
    # data = condition_for_inside_bins(data, binner_for_shaft_fields)
    response_weighted_average = compute_rwa_from_lineages(data, "3D", binner_for_shaft_fields,
                                                          sigma_for_fields=sigma_for_fields)

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
    angularPosition = output['orientation']
    theta = np.float32(angularPosition['theta'])
    phi = np.float32(angularPosition['phi'])

    if phi > pi / 2:
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

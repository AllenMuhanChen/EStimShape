from __future__ import annotations
import ast
from math import pi

import jsonpickle as jsonpickle
import numpy as np
import pandas as pd

from analysis.ga.rwa import Binner, AutomaticBinner, rwa, normalize_and_combine_rwas, get_next
from clat.compile.trial.cached_fields import CachedFieldList
from clat.compile.trial.classic_database_fields import StimSpecDataField, StimSpecIdField, NewGaLineageField, \
    NewGaNameField, RegimeScoreField
from analysis.matchstick_fields import ShaftField, TerminationField, JunctionField
from clat.compile.trial.trial_collector import TrialCollector

from clat.util import time_util
from clat.util.connection import Connection
from clat.util.dictionary_util import apply_function_to_subdictionaries_values_with_keys, \
    check_condition_on_subdictionaries
from clat.util.time_util import When





def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_ga_dev_240207")

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    data = remove_empty_response_trials(data)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)

    n = 3

    shaft_rwa = compute_shaft_rwa(data, n)
    termination_rwa = compute_termination_rwa(data, n)
    junction_rwa = compute_junction_rwa(data, n)
    # SAVE
    save(get_next(shaft_rwa), "shaft_rwa")
    save(get_next(termination_rwa), "termination_rwa")
    save(get_next(junction_rwa), "junction_rwa")





def compute_shaft_rwa(data, n):
    data_shaft = data['Shaft'].tolist()
    # a percentage of the number of bins
    sigma_for_fields = {
        "theta": 1 / 9,
        "angularPosition.phi": 1 / 9,
        "radialPosition": 1 / 9,
        "orientation.phi": 1 / 9,
        "length": 1 / 9,
        "curvature": 1 / 9,
        "radius": 1 / 9,
    }
    padding_for_fields = {
        "theta": "wrap",
        "angularPosition.phi": "nearest",
        "radialPosition": "nearest",
        "orientation.phi": "nearest",
        "length": "nearest",
        "curvature": "nearest",
        "radius": "nearest",
    }
    binner_for_shaft_fields = {
        "theta": Binner(-pi, pi, 9),
        "angularPosition.phi": Binner(0, pi, 9),
        "radialPosition": AutomaticBinner("radialPosition", data_shaft, 9),
        "orientation.phi": Binner(0, pi / 2, 9),
        "length": AutomaticBinner("length", data_shaft, 9),
        "curvature": AutomaticBinner("curvature", data_shaft, 9),
        "radius": AutomaticBinner("radius", data_shaft, 9),
    }
    shaft_rwa = compute_rwa_from_top_n_lineages(data, "Shaft",
                                                "New3D", n, binner_for_shaft_fields,
                                                sigma_for_fields=sigma_for_fields,
                                                padding_for_fields=padding_for_fields)
    return shaft_rwa


def compute_termination_rwa(data, n):
    data_termination = data["Termination"].tolist()
    # a percentage of the number of bins
    sigma_for_fields = {
        "theta": 1 / 9,
        "phi": 1 / 9,
        "radialPosition": 1 / 9,
        "radius": 1 / 9,
    }
    padding_for_fields = {
        "theta": "wrap",
        "phi": "nearest",
        "radialPosition": "nearest",
        "radius": "nearest",
    }
    binner_for_termination_fields = {
        "theta": Binner(-pi, pi, 9),
        "phi": Binner(0, pi, 9),
        "radialPosition": AutomaticBinner("radialPosition", data_termination, 9),
        "radius": AutomaticBinner("radius", data_termination, 9),
    }
    termination_rwa = compute_rwa_from_top_n_lineages(data, "Termination",
                                                      "New3D", n, binner_for_termination_fields,
                                                      sigma_for_fields=sigma_for_fields,
                                                      padding_for_fields=padding_for_fields)
    return termination_rwa


def compute_junction_rwa(data, n):
    data_junction = data["Junction"].tolist()
    # a percentage of the number of bins
    sigma_for_fields = {
        "theta": 1 / 9,
        "phi": 1 / 9,
        "radialPosition": 1 / 9,
        "radius": 1 / 9,
        "angularSubtense": 1 / 9,
        "planarRotation": 1 / 9,
    }
    padding_for_fields = {
        "theta": "wrap",
        "phi": "nearest",
        "radialPosition": "nearest",
        "radius": "nearest",
        "angularSubtense": "nearest",
        "planarRotation": "nearest"
    }
    binner_for_junction_fields = {
        "theta": Binner(-pi, pi, 9),
        "phi": Binner(0, pi, 9),
        "radialPosition": AutomaticBinner("radialPosition", data_junction, 9),
        "radius": AutomaticBinner("radius", data_junction, 9),
        "angularSubtense": Binner(0, pi, 9),
        "planarRotation": AutomaticBinner('planarRotation', data_junction, 9),
    }
    junction_rwa = compute_rwa_from_top_n_lineages(data, "Junction",
                                                   "New3D", n, binner_for_junction_fields,
                                                   sigma_for_fields=sigma_for_fields,
                                                   padding_for_fields=padding_for_fields)
    return junction_rwa


def save(response_weighted_average, file_name):
    filename = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/rwa/%s.json" % file_name
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
    rwa_multiplied = normalize_and_combine_rwas(rwas)

    return rwa_multiplied


def compute_rwa_from_top_n_lineages(data, data_type, ga_type, n, binner_for_fields, sigma_for_fields=None,
                                    padding_for_fields=None,
                                    ):
    """sigma_for_fields is expressed as a percentage of the number of bins for that dimension"""
    data = data.loc[data['GaType'] == ga_type]
    rwas = []
    length_for_lineages = data.groupby("Lineage")["RegimeScore"].size()
    top_n_lineages = length_for_lineages.nlargest(n).index
    filtered_data = data[data["Lineage"].isin(top_n_lineages)]
    lineage_ids = []
    for i, (lineage, lineage_data) in enumerate(filtered_data.groupby("Lineage")):
        if i < n:
            lineage_ids.append(lineage)
            print(lineage)
            response_weighted_average = rwa(lineage_data[("%s" % data_type)], lineage_data["Response-1"].tolist(),
                                            binner_for_fields, sigma_for_fields,
                                            padding_for_fields)
            rwas.append(response_weighted_average)
    print("Multiplying Lineage RWAs")

    rwas = [get_next(r) for r in rwas]
    for lineage_index, rwa_lineage in enumerate(rwas):
        save(rwa_lineage, "%s_lineage_rwa_%d" % (data_type, lineage_ids[lineage_index]))
    rwa_multiplied = normalize_and_combine_rwas(rwas)

    return rwa_multiplied


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = CachedFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(NewGaNameField(conn))
    fields.append(NewGaLineageField(conn))
    fields.append(RegimeScoreField(conn))
    fields.append(MockResponseField(conn, 1))
    fields.append(ShaftField(conn, mstick_spec_data_source))
    fields.append(TerminationField(conn, mstick_spec_data_source))
    fields.append(JunctionField(conn, mstick_spec_data_source))

    data = fields.to_data(trial_tstamps)
    return data


class MockResponseField(StimSpecIdField):

    def __init__(self, conn: Connection, channel: int):
        super().__init__(conn)
        self.channel = channel

    def get(self, when: When) -> float:
        stim_spec_id = self.get_cached_super(when, StimSpecIdField)
        self.conn.execute("SELECT spikes_per_second FROM ChannelResponses WHERE stim_id = %s AND channel=%s", [stim_spec_id, "D-003"])
        response = self.conn.fetch_one()
        return response

    def get_name(self):
        return "Response-1"


def remove_empty_response_trials(data):
    return data[data["Response-1"]!='nan']


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

    phi, theta = map_theta_and_phi(phi, theta)

    return {"theta": theta, "phi": phi}


def map_theta_and_phi(phi, theta):
    # PHI [0, pi]
    phi = modulus(phi, (2 * pi))
    if phi < 0:
        phi += (2 * pi)
    if phi > pi:
        phi = (2 * pi) - phi
        theta = theta + pi
    # THETA [-pi, pi]
    theta = map_theta(theta)
    return phi, theta


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

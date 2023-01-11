from __future__ import annotations
import ast
import json
import tracemalloc
from math import pi

import jsonpickle as jsonpickle
import numpy as np
import pandas as pd
import scipy.io
import xmltodict

from src.analysis.rwa import rwa, Binner
from src.compile.classic_database_fields import StimSpecDataField, StimSpecIdField
from src.compile.matchstick_fields import ShaftField, TerminationField, JunctionField
from src.compile.trial_field import FieldList, DatabaseField, get_data_from_trials
from src.mock.mock_ga_responses import collect_trials
from src.util import time_util
from src.util.connection import Connection
from src.util.time_util import When


def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")
    bin_size = 10
    binner_for_shaft_fields = {
        "theta": Binner(-pi, pi, bin_size),
        "phi": Binner(0, pi, bin_size),
        "radialPosition": Binner(0, 100, bin_size),
        "length": Binner(0, 200, bin_size),
        "curvature": Binner(0, 1, bin_size),
        "radius": Binner(0, 20, bin_size),
    }

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    data = condition_data(data)
    response_weighted_average = rwa(data["Shaft"], data["Response-1"], binner_for_shaft_fields)

    # SAVE
    filename = "/home/r2_allen/Documents/EStimShape/dev_221110/rwa/test_rwa.json"
    with open(filename, "w") as file:
        file.write(jsonpickle.encode(response_weighted_average))


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


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = FieldList()
    fields.append(StimSpecIdField(conn, "Id"))
    fields.append(MockResponseField(conn, 1, name="Response-1"))
    fields.append(ShaftField(mstick_spec_data_source, name="Shaft"))
    fields.append(TerminationField(mstick_spec_data_source, name="Termination"))
    fields.append(JunctionField(mstick_spec_data_source, name="Junction"))

    data = get_data_from_trials(fields, trial_tstamps)
    return data


def condition_spherical_angles(data):
    for row in data["Shaft"]:
        recursively_apply_function_to_subdictionaries_values_with_keys(row, ["theta", "phi"], condition_theta_and_phi)

        print(row)

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


def recursively_apply_function_to_subdictionaries_values_with_keys(dictionary, keys, function):
    if isinstance(dictionary, dict):
        if set(keys).issubset(dictionary.keys()):
            dictionary = function(dictionary)
        for key, value in dictionary.items():
            dictionary[key] = recursively_apply_function_to_subdictionaries_values_with_keys(value, keys, function)
    elif isinstance(dictionary, list):
        for index, item in enumerate(dictionary):
            dictionary[index] = recursively_apply_function_to_subdictionaries_values_with_keys(item, keys, function)
    return dictionary


def condition_data(data):
    data = condition_spherical_angles(data)
    return data


if __name__ == '__main__':
    main()

import numpy as np
import xmltodict
from pandas import DataFrame
from src.util.time_util import When
from dataclasses import dataclass


def beh_msgs_during_trial(beh_msg: DataFrame, when: When):
    later_than_start = beh_msg['tstamp'] >= when.start
    before_stop = beh_msg['tstamp'] <= when.stop
    return np.logical_and(later_than_start, before_stop)


def contains_success(beh_msg: DataFrame, when: When) -> bool:
    # beh_msgs = beh_msg['type'].where(beh_msgs_during_trial(beh_msg, when))
    beh_msgs = beh_msg['type'][beh_msgs_during_trial(beh_msg, when)]
    if beh_msgs.isin(["ChoiceSelectionSuccess"]).any():
        return True
    else:
        return False


def contains_calibration(beh_msg: DataFrame, when: When) -> bool:
    msg_type = beh_msg['type'].where(beh_msgs_during_trial(beh_msg, when))
    if msg_type.isin(["CalibrationPointSetup"]).any():
        return True
    else:
        return False


def get_stim_spec_id(beh_msg: DataFrame, when: When):
    def _get_trial_message(beh_msg, when: When):
        msgs_during_trial = beh_msg["msg"].where(beh_msgs_during_trial(beh_msg, when))
        trial_msg = [msg for msg in msgs_during_trial if "TrialMessage" in str(msg)][0]
        return trial_msg

    def _parse_stim_spec_from_trial_message(trial_msg):
        return int(xmltodict.parse(trial_msg)['TrialMessage']['stimSpecId'])

    trial_msg = _get_trial_message(beh_msg, when)
    stim_spec_id = _parse_stim_spec_from_trial_message(trial_msg)
    return stim_spec_id


def get_stim_spec_data(beh_msg: DataFrame, stim_spec, when: When):
    stim_spec_id = get_stim_spec_id(beh_msg, when)
    stim_spec_data_xml = stim_spec[stim_spec['id'] == stim_spec_id]['util']
    return stim_spec_data_xml.item()


@dataclass
class Coordinates2D:
    x: float
    y: float

    def __init__(self, **entries):
        """Allows initiation of Coordinates2D object with a dict with x and y component"""
        self.__dict__.update(entries)


@dataclass
class EyeLocation:
    left: Coordinates2D
    right: Coordinates2D


def get_eye_location_volts(beh_msg_eye: DataFrame, when: When) -> [EyeLocation]:
    """Returns a list of EyeLocation objects given the beh_msg_eye table and timestamps to search within"""
    eye_msgs_during_trial = beh_msg_eye['msg'].where(beh_msgs_during_trial(beh_msg_eye, when))
    left_volts = [xmltodict.parse(msg)['EyeDeviceMessage']['volt'] for msg in eye_msgs_during_trial if
                  "leftIscan" in str(msg)]
    right_volts = [xmltodict.parse(msg)['EyeDeviceMessage']['volt'] for msg in eye_msgs_during_trial if
                   "rightIscan" in str(msg)]
    locations = _dicts_to_eye_location(left_volts, right_volts)
    return locations


def _dicts_to_eye_location(left_xy_dict, right_xy_dict):
    """Converts two dictionaries composing of x:float and y:float into EyeLocation composed of Coordinates2D"""
    locations = [EyeLocation(Coordinates2D(**left_volt), Coordinates2D(**right_volt)) for left_volt, right_volt in
                 zip(left_xy_dict, right_xy_dict)]
    return locations

import numpy as np
import xmltodict


def get_during_trial(beh_msg, when):
    later_than_start = beh_msg['tstamp'] >= when.start
    before_stop = beh_msg['tstamp'] <= when.stop
    return np.logical_and(later_than_start, before_stop)


def contains_success(beh_msg, when) -> bool:
    msg_type = beh_msg['type'].where(get_during_trial(beh_msg, when))
    if msg_type.isin(["ChoiceSelectionSuccess"]).any():
        return True
    else:
        return False


def get_stim_spec_id(beh_msg, when):
    def _get_trial_message(beh_msg, when):
        msgs_during_trial = beh_msg["msg"].where(get_during_trial(beh_msg, when))
        trial_msg = [msg for msg in msgs_during_trial if "TrialMessage" in str(msg)][0]
        return trial_msg

    def _parse_stim_spec_from_trial_message(trial_msg):
        return int(xmltodict.parse(trial_msg)['TrialMessage']['stimSpecId'])

    trial_msg = _get_trial_message(beh_msg, when)
    stim_spec_id = _parse_stim_spec_from_trial_message(trial_msg)
    return stim_spec_id


def get_stim_spec_data(beh_msg, stim_spec, when):
    stim_spec_id = get_stim_spec_id(beh_msg, when)
    stim_spec_data_xml = stim_spec[stim_spec['id'] == stim_spec_id]['data']
    return stim_spec_data_xml.item()
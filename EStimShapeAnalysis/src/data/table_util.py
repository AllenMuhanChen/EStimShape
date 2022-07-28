import numpy as np

def get_within_tstamps(beh_msg, when):
    later_than_start = beh_msg['tstamp'] >= when.start
    before_stop = beh_msg['tstamp'] <= when.stop
    return np.logical_and(later_than_start, before_stop)

def contains_success(beh_msg, when)->bool:
    msg_type = beh_msg['type'].where(get_within_tstamps(beh_msg, when))
    if msg_type.isin(["ChoiceSelectionSuccess"]).any():
        return True
    else:
        return False

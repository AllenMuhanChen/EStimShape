import numpy as np

def within_tstamps(beh_msg, when):
    later_than_start = beh_msg['tstamp'] >= when.start
    before_stop = beh_msg['tstamp'] <= when.stop
    return np.logical_and(later_than_start, before_stop)

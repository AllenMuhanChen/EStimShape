import numpy as np

from src.compile.trial_collector import TrialCollector
from src.compile.trial_field import Field
from src.util.connection import Connection
from src.util import time_util
from src.util.time_util import When
from src.util import table_util
from pandas import DataFrame
database = "allen_estimshape_train_221020"

class EyeDeviceMessageField(Field):
    def __init__(self, beh_msg_eye: DataFrame):
        self.name = "EyeDeviceMessage"
    def get(self, when: When):
        pass

if __name__ == '__main__':
    conn = Connection(database, when=time_util.all())
    collector = TrialCollector(conn)
    trials = collector.collect_calibration_trials()
    for trial in trials:
        both_eye_volts = table_util.get_eye_location_volts(conn.beh_msg_eye, trial)
        left_eye_volts = [eye.left for eye in both_eye_volts]
        right_eye_volts = [eye.right for eye in both_eye_volts]
        left_mean = np.mean([float(volt.x) for volt in left_eye_volts])
        right_mean = np.mean([float(volt.y) for volt in right_eye_volts])
        print(left_mean)








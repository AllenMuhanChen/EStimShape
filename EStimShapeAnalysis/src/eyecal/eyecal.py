from src.compile.trial_collector import TrialCollector
from src.compile.trial_field import Field
from src.util.connection import Connection
from src.util import time_util
from src.util.time_util import When
from src.util import table_util
from pandas import DataFrame
database = "allen_estimshape_train_220725"

class EyeDeviceMessageField(Field):
    def __init__(self, beh_msg_eye: DataFrame):
        self.name = "EyeDeviceMessage"
    def retrieveValue(self, when: When):
        pass

if __name__ == '__main__':
    conn = Connection(database, when=time_util.all())
    collector = TrialCollector(conn)
    trials = collector.collect_calibration_trials()






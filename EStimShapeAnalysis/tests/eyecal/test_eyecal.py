import unittest
from src.util import time_util, table_util
from src.util.connection import Connection


class MyTestCase(unittest.TestCase):
    conn = Connection("allen_estimshape_train_220725", when=time_util.all())
    beh_msg_eye = conn.beh_msg_eye
    def test_get_eye_location_volts(self):
        test_trial = time_util.When(1658765818046321, 1658765820924871)
        table_util.get_eye_location_volts(self.beh_msg_eye, test_trial)
        print(table_util.get_eye_location_volts(self.beh_msg_eye, test_trial))

if __name__ == '__main__':
    unittest.main()

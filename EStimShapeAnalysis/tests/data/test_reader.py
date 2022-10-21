import unittest
from src.data import connection
from src.data import timeutil


class TestReaderMethods(unittest.TestCase):
    conn = connection.Connection("allen_estimshape_test_220729", when=timeutil.all())

    def test_reads_beh_msg(self):
        behMsg = self.conn.beh_msg
        self.assertTrue(not behMsg.empty)
        print((behMsg))
    def test_reads_stim_spec(self):
        stimSpec = self.conn.beh_msg
        self.assertTrue(not stimSpec.empty)
        print((stimSpec))
    def test_reads_stim_obj_data(self):
        stimObjData = self.conn.stim_obj_data
        self.assertTrue(not stimObjData.empty)
        print(stimObjData)
if __name__ == '__main__':
    unittest.main()
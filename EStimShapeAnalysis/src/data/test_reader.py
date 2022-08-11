import unittest
import connection



class TestReaderMethods(unittest.TestCase):
    def test_connects_to_database(self):
        connection.mydb
    def test_reads_beh_msg(self):
        behMsg = connection._get_beh_msg()
        self.assertTrue(not behMsg.empty)
        print((behMsg))
    def test_reads_stim_spec(self):
        stimSpec = connection._get_stim_sec()
        self.assertTrue(not stimSpec.empty)
        print((stimSpec))
    def test_reads_stim_obj_data(self):
        stimObjData = connection._get_stim_obj_data()
        self.assertTrue(not stimObjData.empty)
        print(stimObjData)
if __name__ == '__main__':
    unittest.main()
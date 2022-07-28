import unittest
import reader



class TestReaderMethods(unittest.TestCase):
    def test_connects_to_database(self):
        reader.mydb
    def test_reads_beh_msg(self):
        behMsg = reader.get_beh_msg()
        self.assertTrue(not behMsg.empty)
        print((behMsg))
    def test_reads_stim_spec(self):
        stimSpec = reader.get_stim_sec()
        self.assertTrue(not stimSpec.empty)
        print((stimSpec))
    def test_reads_stim_obj_data(self):
        stimObjData = reader.get_stim_obj_data()
        self.assertTrue(not stimObjData.empty)
        print(stimObjData)
if __name__ == '__main__':
    unittest.main()
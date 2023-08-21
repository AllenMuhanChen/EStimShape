import unittest

from compile.trial.nafc_database_fields import get_stim_spec_data, get_stim_spec_id
from src.util.connection import Connection
from src.util.time_util import When


class MyTestCase(unittest.TestCase):
    fields = [get_stim_spec_data, get_stim_spec_id]
    # conn = mysql.connector.connect(
    #     host="172.30.6.80",
    #     user="xper_rw",
    #     password="up2nite",
    #     database="allen_estimshape_test_220729"
    # )
    conn = Connection("allen_estimshape_test_220729")
    PSYCHOMETRIC = When(1659208461019365, 1659208471171128)
    RANDOM_CORRECT = When(1659126605490042, 1659126611270426)

    def test(self):
        for field in self.fields:
            print(field(self.conn, self.RANDOM_CORRECT))


if __name__ == '__main__':
    unittest.main()

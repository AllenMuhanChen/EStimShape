from unittest import TestCase

from src.compile.classic_database_fields import get_stim_spec_id, get_stim_spec_data
from src.util.connection import Connection
from src.util.time_util import When


def get_when(conn: Connection):
    conn.execute("SELECT MAX(tstamp) FROM BehMsg WHERE type = 'TrialStart'")
    start = conn.fetch_one()
    conn.execute("SELECT MAX(tstamp) FROM BehMsg WHERE type = 'TrialStop'")
    stop = conn.fetch_one()
    when = When(start, stop)
    return when


class Test(TestCase):
    fields = [get_stim_spec_id, get_stim_spec_data]
    conn = Connection("allen_estimshape_dev_221110")
    test_when = get_when(conn)
    def test_get_stim_spec_id(self):
        for field in self.fields:
            print(field(self.conn, self.test_when))

    def test_task_id(self):
        print(self.test_when)
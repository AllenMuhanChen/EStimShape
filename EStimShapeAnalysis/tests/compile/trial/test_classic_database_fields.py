from unittest import TestCase

from clat.compile import StimSpecDataField
from analysis.matchstick_fields import MatchStickField, ShaftField
from clat.compile import FieldList, get_data_from_trials
from clat.util.connection import Connection
from clat.util.time_util import When


def get_when(conn: Connection):
    conn.execute("SELECT MAX(tstamp) FROM BehMsg WHERE type = 'TrialStart'")
    start = conn.fetch_one()
    conn.execute("SELECT MAX(tstamp) FROM BehMsg WHERE type = 'TrialStop'")
    stop = conn.fetch_one()
    when = When(start, stop)
    return when


class Test(TestCase):
    conn = Connection("allen_estimshape_dev_221110")
    test_when = get_when(conn)
    mstick_spec_data_source = StimSpecDataField(conn)

    def test_get_stim_spec_data_field(self):
        fields = FieldList()
        fields.append(StimSpecDataField(self.conn))
        print(get_data_from_trials(fields, [self.test_when]))

    def test_match_stick_field(self):
        fields = FieldList()
        fields.append(MatchStickField(self.mstick_spec_data_source))
        print(get_data_from_trials(fields, [self.test_when]))

    def test_shaft_field(self):
        fields = FieldList()
        fields.append(ShaftField(self.mstick_spec_data_source))
        print(get_data_from_trials(fields, [self.test_when]))

    def test_task_id(self):
        print(self.test_when)

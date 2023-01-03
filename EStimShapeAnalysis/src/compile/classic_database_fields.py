import xmltodict

from src.compile.nafc_database_fields import DatabaseField
from src.util.connection import Connection
from src.util.time_util import When


class StimSpecDataField(DatabaseField):
    def get(self, when: When):
        return get_stim_spec_data(self.conn, when)


def get_stim_spec_data(conn: Connection, when: When) -> dict:
    """Given a tstamp of trialStart and trialStop, finds the stimSpec Id from Trial Message and then reads data from
    StimSpec """
    stim_spec_id = get_stim_spec_id(conn, when)
    conn.execute("SELECT data from StimSpec WHERE "
                 "id = %s",
                 params=(stim_spec_id,))

    stim_spec_data_xml = conn.fetch_one()
    stim_spec_data_dict = xmltodict.parse(stim_spec_data_xml)
    return stim_spec_data_dict


def get_stim_spec_id(conn: Connection, when: When) -> dict:
    conn.execute(
        "SELECT msg from BehMsg WHERE "
        "type = 'SlideOn' AND "
        "tstamp >= %s AND tstamp <= %s",
        params=(int(when.start), int(when.stop)))
    trial_msg_xml = conn.fetch_one()
    trial_msg_dict = xmltodict.parse(trial_msg_xml)
    return int(trial_msg_dict['SlideEvent']['taskId'])

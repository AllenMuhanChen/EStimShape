import xmltodict

from compile.trial.trial_field import DatabaseField
from src.util.connection import Connection
from src.util.time_util import When


class StimSpecDataField(DatabaseField):
    def get(self, when: When):
        return get_stim_spec_data(self.conn, when)


class TrialTypeField(StimSpecDataField):

    def __init__(self, conn: Connection):
        super().__init__(conn, "TrialType")

    def get(self, when: When):
        stim_spec_data = StimSpecDataField.get(self, when)
        return self._parse_type_from_stim_spec_data(stim_spec_data)

    @staticmethod
    def _parse_type_from_stim_spec_data(stim_spec_data):
        try:
            stim_spec_data_type = list(stim_spec_data.keys())[0]
            if "RandNoisyTrialParameters" in stim_spec_data_type:
                return "Rand"
            elif "Psychometric" in stim_spec_data_type:
                return "Psychometric"
            else:
                return "Unknown"
        except:
            print(stim_spec_data)
            return "Unknown"


def get_stim_spec_id(conn: Connection, when: When) -> dict:
    conn.execute(
        "SELECT msg from BehMsg WHERE "
        "msg LIKE '%TrialMessage%' AND "
        "tstamp >= %s AND tstamp <= %s",
        params=(int(when.start), int(when.stop)))
    trial_msg_xml = conn.fetch_one()
    trial_msg_dict = xmltodict.parse(trial_msg_xml)
    return int(trial_msg_dict['TrialMessage']['stimSpecId'])


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

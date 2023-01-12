import xmltodict

from src.compile.trial_field import DatabaseField
from src.util.connection import Connection
from src.util.time_util import When


class StimSpecIdField(DatabaseField):
    def get(self, when: When) -> int:
        return self.get_stim_spec_id(self.conn, when)

    def get_stim_spec_id(self, conn: Connection, when: When) -> int:
        conn.execute(
            "SELECT msg from BehMsg WHERE "
            "type = 'SlideOn' AND "
            "tstamp >= %s AND tstamp <= %s",
            params=(int(when.start), int(when.stop)))
        trial_msg_xml = conn.fetch_one()
        trial_msg_dict = xmltodict.parse(trial_msg_xml)
        return int(trial_msg_dict['SlideEvent']['taskId'])


class StimSpecDataField(StimSpecIdField):
    def get(self, when: When):
        stim_spec_id = StimSpecIdField(self.conn).get(when)
        return get_stim_spec_data(self.conn, when, stim_spec_id)


def get_stim_spec_data(conn: Connection, when: When, stim_spec_id) -> dict:
    """Given a tstamp of trialStart and trialStop, finds the stimSpec Id from Trial Message and then reads data from
    StimSpec """

    conn.execute("SELECT data from StimSpec WHERE "
                 "id = %s",
                 params=(stim_spec_id,))

    stim_spec_data_xml = conn.fetch_one()
    stim_spec_data_dict = xmltodict.parse(stim_spec_data_xml)
    return stim_spec_data_dict


class GaNameField(StimSpecIdField):
    def get(self, when: When):
        stim_spec_id = StimSpecIdField.get(self, when)
        return get_ga_name_from_stim_spec_id(self.conn, stim_spec_id)


class GaTypeField(GaNameField):
    def get(self, when: When):
        ga_name = GaNameField.get(self, when)
        return get_ga_type_from_ga_name(self.conn, ga_name)


class GaLineageField(GaNameField):
    def get(self, when: When):
        ga_name = GaNameField.get(self, when)
        return get_ga_lineage_from_ga_name(self.conn, ga_name)


def get_ga_name_from_stim_spec_id(conn, stim_spec_id):
    conn.execute("SELECT ga_name FROM TaskToDo t WHERE"
                 " stim_id = %s",
                 params=(stim_spec_id,))

    ga_name = conn.fetch_one()
    return ga_name


def get_ga_type_from_ga_name(conn, ga_name: str):
    ga_type = ga_name.split("-")[0]
    return ga_type


def get_ga_lineage_from_ga_name(conn, ga_name: str):
    ga_lineage = ga_name.split("-")[1]
    return ga_lineage

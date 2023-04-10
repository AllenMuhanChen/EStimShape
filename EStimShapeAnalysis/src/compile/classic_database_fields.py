import xmltodict

from src.compile.trial_field import DatabaseField
from src.util.connection import Connection
from src.util.time_util import When


def get_stim_spec_id(conn: Connection, when: When) -> int:
    conn.execute(
        "SELECT msg from BehMsg WHERE "
        "type = 'SlideOn' AND "
        "tstamp >= %s AND tstamp <= %s",
        params=(int(when.start), int(when.stop)))
    trial_msg_xml = conn.fetch_one()
    trial_msg_dict = xmltodict.parse(trial_msg_xml)
    taskId = int(trial_msg_dict['SlideEvent']['taskId'])

    conn.execute("SELECT stim_id from TaskToDo WHERE "
                 "task_id = %s",
                 params=(taskId,))
    stim_spec_id = conn.fetch_one()
    return stim_spec_id


class StimSpecIdField(DatabaseField):
    def get(self, when: When) -> int:
        return get_stim_spec_id(self.conn, when)


class StimSpecDataField(StimSpecIdField):
    def get(self, when: When) -> dict:
        stim_spec_id = super().get(when)
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


class StimSpecField(StimSpecIdField):
    def get(self, when: When) -> dict:
        stim_spec_id = super().get(when)
        return get_stim_spec(self.conn, when, stim_spec_id)


def get_stim_spec(conn: Connection, when: When, stim_spec_id: int) -> dict:
    conn.execute("SELECT spec from StimSpec WHERE "
                 "id = %s",
                 params=(stim_spec_id,))
    stim_spec_xml = conn.fetch_one()
    stim_spec_dict = xmltodict.parse(stim_spec_xml)
    return stim_spec_dict


def get_ga_name_from_stim_spec_id(conn, stim_spec_id) -> str:
    conn.execute("SELECT ga_name FROM TaskToDo t WHERE"
                 " stim_id = %s",
                 params=(stim_spec_id,))

    ga_name = conn.fetch_one()
    return ga_name


class NewGaNameField(StimSpecIdField):
    def get(self, when: When) -> str:
        stim_spec_id = super().get(when)
        return get_new_ga_name_from_stim_spec_id(self.conn, stim_spec_id)


def get_new_ga_name_from_stim_spec_id(conn, stim_spec_id):
    conn.execute("SELECT ga_name FROM TaskToDo t WHERE"
                 " stim_id = %s",
                 params=(stim_spec_id,))

    ga_name = conn.fetch_one()
    return ga_name


class NewGaLineageField(StimSpecIdField):
    def get(self, when: When) -> str:
        stim_spec_id = super().get(when)
        return get_new_ga_lineage_from_stim_spec_id(self.conn, stim_spec_id)


def get_new_ga_lineage_from_stim_spec_id(conn, stim_spec_id):
    conn.execute("SELECT lineage_id FROM StimGaInfo WHERE"
                 " stim_id = %s",
                 params=(stim_spec_id,))

    lineage = conn.fetch_one()
    return lineage


class GaNameField(StimSpecIdField):
    def get(self, when: When) -> str:
        stim_spec_id = super().get(when)
        return get_ga_name_from_stim_spec_id(self.conn, stim_spec_id)


class GaTypeField(GaNameField):
    def get(self, when: When):
        ga_name = super().get(when)
        return get_ga_type_from_ga_name(self.conn, ga_name)


class GaLineageField(GaNameField):
    def get(self, when: When):
        ga_name = super().get(when)
        return get_ga_lineage_from_ga_name(self.conn, ga_name)


def get_ga_type_from_ga_name(conn, ga_name: str):
    ga_type = ga_name.split("-")[0]
    return ga_type


def get_ga_lineage_from_ga_name(conn, ga_name: str):
    ga_lineage = ga_name.split("-")[1]
    return ga_lineage

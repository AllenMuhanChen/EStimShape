import xmltodict
from mysql.connector import CMySQLConnection

from src.util.time_util import When


def get_stim_spec_id(conn: CMySQLConnection, when: When):
    my_cursor = conn.cursor()
    my_cursor.execute(
        "SELECT msg from BehMsg WHERE "
        "msg LIKE '%TrialMessage%' AND "
        "tstamp >= %s AND tstamp <= %s",
        params=(when.start, when.stop))

    trial_msg_xml = fetch_one(my_cursor)
    dict = xmltodict.parse(trial_msg_xml)
    return int(dict['TrialMessage']['stimSpecId'])


def get_stim_spec_data(conn: CMySQLConnection, when: When):
    stim_spec_id = get_stim_spec_id(conn, when)
    my_cursor = conn.cursor()
    my_cursor.execute("SELECT data from StimSpec WHERE "
                      "id = %s",
                      params=(stim_spec_id,))

    stim_spec_data_xml = fetch_one(my_cursor)
    stim_spec_data_dict = xmltodict.parse(stim_spec_data_xml)
    return stim_spec_data_dict


def fetch_one(my_cursor):
    return "".join(my_cursor.fetchall()[0])

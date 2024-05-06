import xmltodict

from analysis.nafc.nafc_database_fields import get_stim_spec
from analysis.nafc.psychometric_curves import collect_choice_trials
from clat.compile import CachedDatabaseField, CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When


class MStickSpecField(CachedDatabaseField):
    def __init__(self, conn: Connection, when_to_stim_spec_id: callable, stim_spec_id_to_mstick_obj_data: callable):
        super().__init__(conn)
        self.when_to_stim_spec_id = when_to_stim_spec_id
        self.stim_spec_id_to_mstick_obj_data = stim_spec_id_to_mstick_obj_data

    def get_name(self): return "MStickSpecField"

    def get(self, when: When) -> dict:
        stim_spec_id = self.when_to_stim_spec_id(when)
        mstick_obj_data = self.stim_spec_id_to_mstick_obj_data(stim_spec_id)
        return mstick_obj_data


def main():
    conn = Connection("allen_estimshape_train_231211")
    trial_tstamps = collect_choice_trials(conn, time_util.on_date_and_time(2024,
                                                                           1, 11,
                                                                           start_time="18:00:00",  # "16:49:00"
                                                                           end_time=None))

    def get_mstick_obj_from_stim_id(stim_id: int) -> dict:
        conn.execute("SELECT data FROM StimObjData WHERE id = %s", (stim_id,))
        stim_obj_data = conn.fetch_one()
        return xmltodict.parse(stim_obj_data)

    def get_spec_id_from_when(when: When) -> int:
        stim_spec = get_stim_spec(conn, when)
        return int(stim_spec['StimSpec']['sampleObjData'])

    fieldList = CachedFieldList()
    fieldList.append(MStickSpecField(conn, get_spec_id_from_when, get_mstick_obj_from_stim_id))

    data = fieldList.to_data(trial_tstamps)
    print(data.to_string())


if __name__ == '__main__':
    main()

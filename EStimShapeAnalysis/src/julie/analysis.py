import os

from compile.task.compile_task_id import PngSlideIdCollector
from compile.task.julie_database_fields import FileNameField, MonkeyIdField, MonkeyNameField, JpgIdField, \
    MonkeyGroupField
from compile.task.julie_intan_fields import SpikeTimesForChannelsField, EpochStartStopField
from compile.task.task_field import TaskFieldList, get_data_from_tasks, TaskField
from mock.mock_ga_responses import collect_task_ids
from util.connection import Connection


def main():
    # Dependencies Needed for Data Fetching
    conn_xper = Connection("20230908_recording", host="172.30.6.59")
    conn_photo = Connection("photo_metadata", host="172.30.6.59")
    intan_base_path = "/run/user/1003/gvfs/sftp:host=172.30.6.58/home/connorlab/Documents/IntanData"
    date = "2023-09-11"
    intan_data_path = os.path.join(intan_base_path, date)

    # Collect task IDS
    task_id_collector = PngSlideIdCollector(conn_xper)
    task_ids = task_id_collector.collect_task_ids()

    # Task Fields
    fields = TaskFieldList()
    fields.append(TaskField())
    fields.append(FileNameField(conn_xper=conn_xper))
    fields.append(MonkeyIdField(conn_xper=conn_xper, conn_photo=conn_photo))
    fields.append(MonkeyNameField(conn_xper=conn_xper, conn_photo=conn_photo))
    fields.append(JpgIdField(conn_xper=conn_xper, conn_photo=conn_photo))
    fields.append(MonkeyGroupField(conn_xper=conn_xper, conn_photo=conn_photo))
    fields.append(SpikeTimesForChannelsField(intan_data_path=intan_data_path))
    fields.append(EpochStartStopField(intan_data_path=intan_data_path))

    # Get data
    data = get_data_from_tasks(fields, task_ids)
    print(data)

if __name__ == "__main__":
    main()

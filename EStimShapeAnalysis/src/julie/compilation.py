import os
from datetime import datetime, time, date

import jsonpickle
import numpy as np
import pytz

from compile.task.compile_task_id import PngSlideIdCollector
from compile.task.julie_database_fields import FileNameField, MonkeyIdField, MonkeyNameField, JpgIdField, \
    MonkeyGroupField
from compile.task.julie_intan_fields import SpikeTimesForChannelsField, EpochStartStopField
from compile.task.task_field import TaskFieldList, get_data_from_tasks, TaskField
from intan.channels import Channel
from mock.mock_ga_responses import collect_task_ids
from util import time_util
from util.connection import Connection
import matplotlib.pyplot as plt


def main():
    # Main Parameters
    compile_data(day=date(2023, 9, 13),
                 start_time=time(17, 0, 0),
                 end_time=time(17, 59, 0))


def compile_data(day: date = date.today(),
                 start_time: time = time(0, 0, 0),
                 end_time: time = time(23, 59, 59)):
    # Dependencies Needed for Data Fetching
    data = collect_raw_data(day=day, start_time=start_time, end_time=end_time)

    # Clean rows with empty SpikeTimes
    data = data[data['SpikeTimes'].notna()]

    # Save Data
    save_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/compiled/julie"
    filename = f"{day.strftime('%Y-%m-%d')}_{start_time.strftime('%H-%M-%S')}_to_{end_time.strftime('%H-%M-%S')}.pk1"
    save_path = os.path.join(save_dir, filename)
    data.to_pickle(save_path)

    return data


def collect_raw_data(*, day: date, start_time: time, end_time: time):
    # day to string
    day_path = day.strftime("%Y-%m-%d")

    # remove hyphens from date
    date_no_hyphens = day_path.replace('-', '')
    conn_xper = Connection(f"{date_no_hyphens}_recording", host="172.30.6.59")
    conn_photo = Connection("photo_metadata", host="172.30.6.59")
    intan_base_path = "/run/user/1003/gvfs/sftp:host=172.30.6.58/home/connorlab/Documents/IntanData"
    intan_data_path = os.path.join(intan_base_path, day_path)

    # Collect task IDS

    timezone = pytz.timezone('US/Eastern')
    start_datetime = datetime.combine(day, start_time)
    start_datetime = timezone.localize(start_datetime)
    start_unix = time_util.to_unix(start_datetime)

    end_datetime = datetime.combine(day, end_time)
    end_datetime = timezone.localize(end_datetime)
    end_unix = time_util.to_unix(end_datetime)

    task_id_collector = PngSlideIdCollector(conn_xper)
    time_range = (start_unix, end_unix)
    task_ids = task_id_collector.collect_complete_task_ids(time_range)


    # Task Fields
    fields = TaskFieldList()
    fields.append(TaskField())
    fields.append(FileNameField(conn_xper=conn_xper))
    fields.append(MonkeyIdField(conn_xper=conn_xper, conn_photo=conn_photo))
    fields.append(MonkeyNameField(conn_xper=conn_xper, conn_photo=conn_photo))
    fields.append(MonkeyGroupField(conn_xper=conn_xper, conn_photo=conn_photo))
    fields.append(SpikeTimesForChannelsField(intan_data_path=intan_data_path))
    fields.append(EpochStartStopField(intan_data_path=intan_data_path))
    # Get data
    data = get_data_from_tasks(fields, task_ids)
    return data


if __name__ == "__main__":
    main()

import os
import pickle
import re
from datetime import date, time
from typing import Optional

from compile.task.compile_task_id import PngSlideIdCollector
from compile.task.task_field import TaskFieldList, TaskField, get_data_from_tasks
from compile.task.julie_database_fields import FileNameField, MonkeyIdField, MonkeyNameField, MonkeyGroupField
from intan.livenotes import map_task_id_to_epochs_with_livenotes
from intan.marker_channels import epoch_using_marker_channels
from intan.rhd import load_intan_rhd_format
from julie.compile.manual_thresh_compilation import calc_start_and_end_unix_times
from util.connection import Connection


def main():
    compile_data(experiment_name="230928_round_1",
                 day=date(2023, 9, 28))


def compile_data(*, experiment_name: str, day: date):
    # Extract YYYY-MM-DD from filepath
    date_path = day.strftime("%Y-%m-%d")
    date_no_hyphens = date_path.replace('-', '')
    conn_xper = Connection(f"{date_no_hyphens}_recording", host="172.30.6.59")
    conn_photo = Connection("photo_metadata", host="172.30.6.59")
    intan_base_path = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana"
    intan_day_path = os.path.join(intan_base_path, date_path)
    intan_file_path = os.path.join(intan_day_path, experiment_name)
    digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
    notes_path = os.path.join(intan_file_path, "notes.txt")
    rhd_file_path = os.path.join(intan_file_path, "info.rhd")

    # Determine Start and End Unix Times to Collect Data From - DATABASE
    start_unix, end_unix = calc_start_and_end_unix_times(day, time(0, 0, 0), time(23, 59, 59))

    # Collect Epoch Start Stop Times - INTAN
    sample_rate = load_intan_rhd_format.read_data(rhd_file_path)["frequency_parameters"]['amplifier_sample_rate']
    stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path,
                                                           false_negative_correction_duration=10)
    epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(notes_path,
                                                               stim_epochs_from_markers)

    # # Collect Sorted Spikes - SPIKE SORTER
    # sorted_spikes = read_pickle(os.path.join(intan_file_path, "sorted_spikes.pkl"))

    # Collect task Ids
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
    fields.append(EpochStartStopTimesField(epochs_for_task_ids, sample_rate))
    # fields.append(SortedSpikeTStampField(sorted_spikes, sample_rate, epochs_for_task_ids))

    # Get data
    data = fields.to_data(task_ids)

    # Clean rows with empty EpochStartStop
    data = data[data['EpochStartStop'].notna()]
    save_path = os.path.join(intan_file_path, "compiled.pk1")
    data.to_pickle(save_path)

    print(data.to_string())


class EpochStartStopTimesField(TaskField):
    def __init__(self, epoch_indices_for_task_ids: dict, sample_rate, name: str = "EpochStartStop"):
        super().__init__(name=name)
        self.epoch_start_stop_by_task_id = epoch_indices_for_task_ids
        self.sample_rate = sample_rate

    def get(self, task_id: int) -> tuple:
        try:
            epoch_start_index = self.epoch_start_stop_by_task_id[task_id][0]
            epoch_stop_index = self.epoch_start_stop_by_task_id[task_id][1]
            epoch_start_time = epoch_start_index / self.sample_rate
            epoch_stop_time = epoch_stop_index / self.sample_rate
            if epoch_stop_time - epoch_start_time < 1:
                print("Warning, epoch start and stop times are less than 1 second apart.")
            return epoch_start_time, epoch_stop_time
        except KeyError:
            return None


class SortedSpikeTStampField(EpochStartStopTimesField):
    def __init__(self, spike_indices_by_unit_by_channel: dict, sample_rate: int, epoch_times_for_task_ids: dict,
                 name='SpikeTimes'):
        super().__init__(epoch_times_for_task_ids, sample_rate, name=name)
        self.spike_indices_by_unit_by_channel = spike_indices_by_unit_by_channel
        self.sample_rate = sample_rate

    def get(self, task_id: int):
        spikes_tstamps_by_unit = {}
        epoch_start_stop_times = super().get(task_id)
        if epoch_start_stop_times is None:
            return None

        for channel, spike_indices_by_unit in self.spike_indices_by_unit_by_channel.items():
            for unit_name, spike_indices in spike_indices_by_unit.items():
                new_unit_name = f"{channel}_{unit_name}"
                for spike_index in spike_indices:
                    if spike_index >= epoch_start_stop_times[0] or spike_index < epoch_start_stop_times[1]:
                        spike_tstamp = spike_index / self.sample_rate
                        if new_unit_name not in spikes_tstamps_by_unit:
                            spikes_tstamps_by_unit[new_unit_name] = []
                        spikes_tstamps_by_unit[new_unit_name].append(spike_tstamp)
        return spikes_tstamps_by_unit


def read_pickle(path: str):
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
            if isinstance(data, dict):
                return data
            else:
                print(f"Error: The pickle file does not contain a dictionary.")
                return None
    except Exception as e:
        print(f"An error occurred while reading the pickle file: {e}")
        return None


def extract_date_from_path(path: str) -> Optional[str]:
    """
    Extract the date in YYYY-MM-DD format from a given file path.

    Parameters:
    - path (str): The file path from which to extract the date.

    Returns:
    - Optional[str]: The extracted date as a string in YYYY-MM-DD format, or None if not found.
    """
    # Define the regular expression pattern to match YYYY-MM-DD format
    date_pattern = r"(\d{4}-\d{2}-\d{2})"

    # Search for the date pattern in the given path
    match = re.search(date_pattern, path)

    if match:
        return match.group(1)
    else:
        return None


if __name__ == '__main__':
    main()

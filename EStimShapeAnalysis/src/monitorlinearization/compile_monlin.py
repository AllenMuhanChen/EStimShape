from __future__ import annotations

import os
from collections import Counter

import numpy as np
import xmltodict

from clat.compile import StimSpecIdField, StimSpecField
from clat.compile import TaskIdCollector
from clat.compile import TaskFieldList, TaskField
from clat.intan.analogin import read_analogin_file
from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import epoch_using_marker_channels
from clat.util.connection import Connection

def get_most_recent_intan(base_path):
    files = os.listdir(base_path)
    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(base_path, x)))
    intan_filename = os.path.splitext(latest_file)[0]
    return intan_filename

def main():
    conn = Connection("allen_monitorlinearization_240228")
    save_path = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/monitor_linearization"
    date = "2024-03-27"
    base_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/Test/%s" % date

    # Find the most recent file in base_path directory
    intan_filename = get_most_recent_intan(base_path)

    digital_in_path = os.path.join(base_path, intan_filename, "digitalin.dat")
    notes_path = os.path.join(base_path, intan_filename, "notes.txt")
    analog_in_path = os.path.join(base_path, intan_filename, "analogin.dat")

    task_id_collector = TaskIdCollector(conn)
    task_ids = task_id_collector.collect_task_ids()

    stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path, false_negative_correction_duration=0,
                                                           false_positive_correction_duration=0)
    epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(notes_path,
                                                               stim_epochs_from_markers,
                                                               require_trial_complete=False)
    volts = read_analogin_file(analog_in_path, 1)
    volts = volts[0]
    for index, volt in enumerate(volts):
        if volt > 1:
            volts[index] = 0

    fields = TaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(RedField(conn, steps=256))
    fields.append(GreenField(conn, steps=256))
    fields.append(BlueField(conn, steps=256))
    fields.append(EpochField(conn, epochs_for_task_ids, notes_path, analog_in_path))
    fields.append(CandelaField(volts, epochs_for_task_ids))

    data = fields.to_data(task_ids)
    filename = f"monitor_linearization_{intan_filename}.pkl"
    save_filepath = os.path.join(save_path, filename)

    data.to_pickle(save_filepath)


class EpochField(TaskField):
    def __init__(self, conn: Connection, epochs_for_task_ids, notes_path: str, analog_in_path: str,
                 name: str = "Epoch"):
        super().__init__(name)
        self.conn = conn
        self.epochs_for_task_ids = epochs_for_task_ids
        self.notes_path = notes_path
        self.analog_in_path = analog_in_path

    def get(self, task_id: int):
        try:
            return self.epochs_for_task_ids[task_id]
        except KeyError:
            return "None"


class CandelaField(TaskField):
    def __init__(self, volts, epochs_for_task_ids, name: str = "Candela"):
        super().__init__(name)
        self.volts = volts
        self.epochs_for_task_ids = epochs_for_task_ids

    def get(self, task_id: int):
        epoch = self.epochs_for_task_ids[task_id]
        start = epoch[0]
        end = epoch[1]
        if end - start < 10000:
            return 0
        duration = end - start
        volts = self.volts[start:end]
        # volts = self.volts[start:end]
        # volts = volts[int(5*len(volts) / 6):]  # discard the first half of data because of ramping up of sensor
        # discard the first half and last 2000 data points
        # volts = volts[11000:14000]
        # 100mV is 1000D -> 1V is 10000D
        candela = volts * 10000

        # average_candela = sum(candela) / len(candela)
        average_candela = find_asymptote(candela, 50, 1)
        print("average candelas: ", average_candela)
        # n_average = average_n_most_common(candela, 6)
        return average_candela


def find_asymptote(data, window_size=10, min_diff=0.001):
    data = np.array(data)
    window_start = max(0, len(data) - window_size)
    window = data[window_start:]
    asymptote = np.mean(window)

    while window_start > 0:
        window_start = max(0, window_start - window_size)
        window = data[window_start:window_start + window_size]
        window_mean = np.mean(window)

        if abs(window_mean - asymptote) < min_diff:
            break

        asymptote = window_mean

    return asymptote

class CandelaVectorField(TaskField):
    def __init__(self, volts, epochs_for_task_ids, name: str = "CandelaVector"):
        super().__init__(name)
        self.volts = volts
        self.epochs_for_task_ids = epochs_for_task_ids

    def get(self, task_id: int):
        epoch = self.epochs_for_task_ids[task_id]
        start = epoch[0]
        end = epoch[1]
        if end - start < 10000:
            return 0
        # 100mV is 1000D -> 1V is 10000D
        volts = self.volts[start:end]
        candela = volts * 10000
        return candela


class RedField(StimSpecField):
    def __init__(self, conn: Connection, name: str = "Red", steps: int = 256):
        super().__init__(conn, name)
        self.steps = steps - 1

    def get(self, task_id: int) -> float:
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        red = float(stim_spec_dict['StimSpec']['color']['red'])
        return red * self.steps


class GreenField(StimSpecField):
    def __init__(self, conn: Connection, name: str = "Green", steps: int = 256):
        super().__init__(conn, name)
        self.steps = steps - 1

    def get(self, task_id: int) -> float:
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        green = float(stim_spec_dict['StimSpec']['color']['green'])
        return float(green * self.steps)


class BlueField(StimSpecField):
    def __init__(self, conn: Connection, name: str = "Blue", steps: int = 256):
        super().__init__(conn, name)
        self.steps = steps - 1

    def get(self, task_id: int) -> float:
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        blue = float(stim_spec_dict['StimSpec']['color']['blue'])
        return float(blue * self.steps)


if __name__ == "__main__":
    main()




def average_n_most_common(values, n=2):
    value_counts = Counter(values)
    n_most_common = value_counts.most_common(n)
    if len(n_most_common) < n:
        # If there are fewer than n unique values, return the average of all unique values
        total_count = sum(count for value, count in n_most_common)
        average_value = sum(value * count for value, count in n_most_common) / total_count
    else:
        # Average the n most common values
        total_count = sum(count for value, count in n_most_common)
        average_value = sum(value * count for value, count in n_most_common) / total_count
    return average_value

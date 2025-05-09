import os

from clat.compile import StimSpecIdField
from clat.compile import TaskIdCollector
from clat.compile import TaskFieldList
from clat.intan.analogin import read_analogin_file
from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import epoch_using_marker_channels
from clat.util.connection import Connection
from monitorlinearization.compile_monlin import RedField, GreenField, BlueField, EpochField, CandelaField
from monitorlinearization.compile_red_green_sinusoidal import AngleField, GainField


def main():
    conn = Connection("allen_monitorlinearization_240228")
    save_path = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/monitor_linearization"
    date = "2024-03-27"
    base_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/Test/%s" % date

    # Find the most recent file in base_path directory
    files = os.listdir(base_path)
    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(base_path, x)))
    intan_filename = os.path.splitext(latest_file)[0]

    digital_in_path = os.path.join(base_path, intan_filename, "digitalin.dat")
    notes_path = os.path.join(base_path, intan_filename, "notes.txt")
    analog_in_path = os.path.join(base_path, intan_filename, "analogin.dat")

    task_id_collector = TaskIdCollector(conn)
    task_ids = task_id_collector.collect_task_ids()

    stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path)
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
    fields.append(RedField(conn))
    fields.append(GreenField(conn))
    fields.append(BlueField(conn))
    fields.append(EpochField(conn, epochs_for_task_ids, notes_path, analog_in_path))
    fields.append(CandelaField(volts, epochs_for_task_ids))
    fields.append(AngleField(conn))
    fields.append(GainField(conn))
    # fields.append(CandelaVectorField(volts, epochs_for_task_ids))

    data = fields.to_data(task_ids)
    filename = f"cyan_yellow_sinusoidal_{intan_filename}.pkl"
    save_filepath = os.path.join(save_path, filename)

    data.to_pickle(save_filepath)

    print(data.to_string())



if __name__ == "__main__":
    main()
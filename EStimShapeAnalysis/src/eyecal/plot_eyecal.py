from tkinter import filedialog
import tkinter as tk
from clat.compile.trial.cached_fields import CachedFieldList
from clat.compile.trial.trial_collector import TrialCollector
from clat.eyecal.params import EyeCalibrationParameters
from clat.eyecal.plot_eyecal import filter_messages_after_experiment_start, CalibrationPointPositionField, \
    SlideOnOffTimestampField, AverageVoltsField, DegreesField, plot_average_volts
from clat.util import time_util
from src.startup import config
import os


def main():
    current_conn = config.ga_config.connection()
    eyecal_path = config.eyecal_dir

    trial_collector = TrialCollector(conn=current_conn, when=time_util.from_x_days_ago(0))
    calibration_trial_times = trial_collector.collect_calibration_trials()
    calibration_trial_times = filter_messages_after_experiment_start(current_conn, calibration_trial_times)
    print("calibration_trial_times: " + str(calibration_trial_times))

    fields = CachedFieldList()
    fields.append(CalibrationPointPositionField(current_conn))
    fields.append(SlideOnOffTimestampField(current_conn))
    fields.append(AverageVoltsField(current_conn))
    fields.append(DegreesField(current_conn))
    data = fields.to_data(calibration_trial_times)

    plot_average_volts(data)

    user_response = input("Do you want to serialize the current parameters? (yes/no): ").strip().lower()
    if user_response == 'yes':
        # Get the current parameters
        params = EyeCalibrationParameters.read_params(current_conn)
        serialized_params = params.serialize()
        print(serialized_params)

        # Prompt the user for a file name
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        file_name = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")],
                                                 initialdir=eyecal_path)

        # Save the serialized data to the specified file in the eyecal_path directory
        if file_name:
            file_path = os.path.join(eyecal_path, os.path.basename(file_name))
            with open(file_path, 'w') as file:
                file.write(serialized_params)
            print(f"Serialized parameters saved to {file_path}")

        root.destroy()


if __name__ == "__main__":
    main()

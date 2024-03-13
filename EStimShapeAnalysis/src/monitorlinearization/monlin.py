from __future__ import annotations

import os

import numpy as np
import xmltodict
from matplotlib import pyplot as plt
from scipy.interpolate import UnivariateSpline
from scipy.optimize import curve_fit

from clat.compile.task.base_database_fields import StimSpecIdField, StimSpecField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.compile.task.task_field import TaskFieldList, TaskField
from clat.intan.analogin import read_analogin_file
from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import epoch_using_marker_channels
from clat.util.connection import Connection


def main():
    conn = Connection("allen_monitorlinearization_240228")
    save_path =  "/home/r2_allen/Documents/EStimShape/ga_dev_240207/monitor_linearization"
    date = "2024-03-12"
    intan_filepath = "TestRecording_240312_182157"
    digital_in_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/Test/%s/%s/digitalin.dat" % (
    date, intan_filepath)
    notes_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/Test/%s/%s/notes.txt" % (
    date, intan_filepath)
    analog_in_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/Test/%s/%s/analogin.dat" % (
    date, intan_filepath)

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

    data = fields.to_data(task_ids)
    filename = f"{intan_filepath}.pkl"
    save_filepath = os.path.join(save_path, filename)

    data.to_pickle(save_filepath)

    # #filter out the rows where Candela is a numpy.float64
    # # data = data[data['Candela'].apply(lambda x: isinstance(x, np.float64))]
    # print(data.to_string())
    #
    # # plt = plot_candela_values(data)
    # plt = plot_candela_per_all_colors(data)

def plot_candela_values(df):
    """
    Plots Candela values in the order they appear in the DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
    """
    plt.figure(figsize=(10, 6))

    # Plot Candela values in the order they appear in the DataFrame
    x_data = range(len(df))
    y_data = df['Candela']
    plt.plot(x_data, y_data, marker='o', linestyle='-', color='blue', label='Candela Value')

    # Perform spline fitting
    coefficients = np.polyfit(x_data, y_data, 4)
    polynomial = np.poly1d(coefficients)

    # Generate fitted values for plotting
    fitted_x = np.linspace(min(x_data), max(x_data), 100)
    fitted_y = polynomial(fitted_x)

    plt.plot(fitted_x, fitted_y, label='Fitted Spline', color='red')

    plt.title('Candela Values')
    plt.xlabel('Index')
    plt.ylabel('Candela')
    plt.grid(True)
    plt.legend()
    plt.show()
    return plt




    plt.title('Candela Values')
    plt.xlabel('Index')
    plt.ylabel('Candela')
    plt.grid(True)
    plt.legend()
    plt.show()
    return plt


def plot_candela_per_all_colors(df):
    """
    Plots Candela values for non-zero entries of Red, Green, and Blue in a single plot.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
    """
    plt.figure(figsize=(10, 6))

    # Define colors to plot
    colors = ['Red', 'Green', 'Blue']

    for color in colors:
        # Filter rows where the color is not zero
        non_zero_color = df[df[color] > 0.001]

        # Plot each color with its respective line color and label
        x_data = non_zero_color[color]
        y_data = non_zero_color['Candela']
        plt.plot(x_data, y_data, marker='o', linestyle='-', color=color.lower(),
                 label=f'{color} Value')

        # Define the exponential function of form A * B^x
        def exp_func(x, A, gamma):
            return A * x ** gamma

        # Use curve_fit to fit the exponential function to the data
        #fit limits are to handle the case where we had incomplete data
        if color == 'Red':
            fit_limit = int(len(x_data)*0.55)
        elif color == 'Green':
            fit_limit = int(len(x_data)*0.80)
        elif color == 'Blue':
            fit_limit = int(len(x_data)*0.7)
        params, covariance = curve_fit(exp_func, x_data[0:fit_limit], y_data[0:fit_limit])

        # Extract the parameters A and B
        A, gamma = params

        print(f"For Color {color}, Fitted A: {A}, gamma: {gamma}, max value: {max(y_data)}")

        # Generate fitted values for plotting
        fitted_y = exp_func(x_data, A, gamma)

        plt.plot(x_data, fitted_y, label='Fitted Curve', color=color.lower())



    plt.title('Candela per Color Value')
    plt.xlabel('Color Value')
    plt.ylabel('Candela')
    plt.grid(True)
    plt.legend()
    plt.show()
    return plt


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
        volts = self.volts[start+(int(duration/2)):end] #discard the first half of data because of ramping up of sensor
        # 100mV is 1000D -> 1V is 10000D
        candela = volts * 10000
        average_candela = sum(candela) / len(candela)
        return average_candela


class RedField(StimSpecField):
    def __init__(self, conn: Connection, name: str = "Red"):
        super().__init__(conn, name)

    def get(self, task_id: int) -> float:
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        red = float(stim_spec_dict['StimSpec']['color']['red'])
        return red * 255


class GreenField(StimSpecField):
    def __init__(self, conn: Connection, name: str = "Green"):
        super().__init__(conn, name)

    def get(self, task_id: int) -> float:
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        green = float(stim_spec_dict['StimSpec']['color']['green'])
        return float(green * 255)


class BlueField(StimSpecField):
    def __init__(self, conn: Connection, name: str = "Blue"):
        super().__init__(conn, name)

    def get(self, task_id: int) -> float:
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        blue = float(stim_spec_dict['StimSpec']['color']['blue'])
        return float(blue * 255)


if __name__ == "__main__":
    main()

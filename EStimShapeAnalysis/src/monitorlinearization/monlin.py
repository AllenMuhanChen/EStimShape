from __future__ import annotations

import os

import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit

from clat.util.connection import Connection

matplotlib.use("Qt5Agg")

def get_most_recent_pickle_path(type: str):
    monitor_linearization_path = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/monitor_linearization"
    # Find the most recent file containing "red_green_sinusoidal" in the monitor_linearization_path
    files = [f for f in os.listdir(monitor_linearization_path) if type in f]
    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(monitor_linearization_path, x)))
    pickle_path = os.path.join(monitor_linearization_path, latest_file)
    return pickle_path

def main():
    conn = Connection("allen_monitorlinearization_240228")
    # Load data
    pickle_path = get_most_recent_pickle_path("monitor_linearization")
    df = pd.read_pickle(pickle_path)


    # Plot Candela values for non-zero entries of Red, Green, and Blue
    plot_and_fit_monlin(df)
    save_to_db(conn, df)




def plot_and_fit_monlin(df):
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
                 label=f'{color} Value', markersize=3)

        # Define the exponential function of form A * B^x
        def exp_func(x, A, gamma):
            return A * x ** gamma

        # Use curve_fit to fit the exponential function to the data
        # fit limits are to handle the case where we had incomplete data
        if color == 'Red':
            fit_limit = int(len(x_data) * 0.55)
        elif color == 'Green':
            fit_limit = int(len(x_data) * 0.80)
        elif color == 'Blue':
            fit_limit = int(len(x_data) * 0.7)
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


if __name__ == "__main__":
    main()




def save_to_db(conn, data):
    ## Save the data to the database
    # calculate average candela for repeats
    data['color'] = data.apply(lambda row: (row['Red'], row['Green'], row['Blue']), axis=1)
    data['luminance'] = data['Candela']
    avg_candela = data.groupby('color')['Candela'].mean().reset_index()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS MonitorLin (
            red INT,
            green INT,
            blue INT,
            luminance FLOAT,
            PRIMARY KEY (red, green, blue)
        )
    """)
    for _, row in avg_candela.iterrows():
        red, green, blue = row['color']
        luminance = row['Candela']
        conn.execute("""
            INSERT INTO MonitorLin (red, green, blue, luminance)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE luminance = VALUES(luminance)
        """, (red, green, blue, luminance))

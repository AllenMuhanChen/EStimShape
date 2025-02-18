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
    plot_base_colors(df)
    plt.figure(figsize=(10, 6))
    plot_derived_color(df, 'Cyan', ('Green', 'Blue'))
    plot_derived_color(df, 'Yellow', ('Red', 'Green'))
    plt.show()
    save_to_db(conn, df)


def plot_base_colors(df):
    """
    Plots Candela values for entries where only Red or only Green is above a threshold in a single plot.
    Excludes entries that could contribute to derived colors like Cyan or Yellow.
    """
    plt.figure(figsize=(10, 6))

    # Plot Red values where only Red is non-zero
    red_only = df[(df['Red'] > 0.001) & (df['Green'] <= 0.001) & (df['Blue'] <= 0.001)]
    if not red_only.empty:
        plt.plot(red_only['Red'], red_only['Candela'], 'o-', label='Red Candela Value', color='red')

    # Plot Green values where only Green is non-zero
    green_only = df[(df['Green'] > 0.001) & (df['Red'] <= 0.001) & (df['Blue'] <= 0.001)]
    if not green_only.empty:
        plt.plot(green_only['Green'], green_only['Candela'], 'o-', label='Green Candela Value', color='green')

    plt.title('Candela for Pure Base Color Values')
    plt.xlabel('Color Value')
    plt.ylabel('Candela')
    plt.grid(True)
    plt.legend()


def plot_derived_color(df, color_name, color_components):
    """
    Plots a derived color (Cyan or Yellow) with L value on the x-axis.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
        color_name (str): Name of the derived color (Cyan or Yellow).
        color_components (tuple): The two colors that make up the derived color.
    """
    # Filter rows where both colors are non-zero
    non_zero_color = df[(df[color_components[0]] > 0.001) & (df[color_components[1]] > 0.001)]
    if not non_zero_color.empty:


        # Calculate L values
        L_values = np.linspace(0, 100, len(non_zero_color))

        # Plotting Candela as a function of L value for the derived color
        plt.plot(L_values, non_zero_color['Candela'], 'o-', label=f'{color_name} Candela Value', color='black')

        plt.title(f'Candela for {color_name}')
        plt.xlabel('L Value')
        plt.ylabel('Candela')
        plt.grid(True)
        plt.legend()




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
    conn.execute("TRUNCATE TABLE MonitorLin")
    for _, row in avg_candela.iterrows():
        red, green, blue = row['color']
        luminance = row['Candela']
        conn.execute("""
            INSERT INTO MonitorLin (red, green, blue, luminance)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE luminance = VALUES(luminance)
        """, (red, green, blue, luminance))




if __name__ == "__main__":
    main()

import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from clat.util.connection import Connection
from src.monitorlinearization.linear_repeats import plot_candela_vector
from src.monitorlinearization.monlin import get_most_recent_pickle_path

matplotlib.use("Qt5Agg")
def main():



    conn = Connection("allen_monitorlinearization_250128")
    pickle_path = get_most_recent_pickle_path("red_green_sinusoidal")
    # pickle_path = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/monitor_linearization/red_green_sinusoidal_TestRecording_240319_135800.pkl"

    df = pd.read_pickle(pickle_path)
    df = df.sort_values(by=['gain', 'angle'])
    avg_candela = df.groupby(['angle', 'gain'])['Candela'].mean().reset_index()
    avg_candela = avg_candela.sort_values(by=['angle', 'gain'])
    print(df.to_string())
    # plot_candela_vector(df, 1710867286329547)
    plot_candela_values(avg_candela)
    angles, gains = plot_gain_for_luminance(avg_candela, 150)

    # Insert the data into the LuminanceGain table
    luminance_gain_table = LuminanceGainTable(conn)
    for angle, gain in zip(angles, gains):
        luminance_gain_table.insert_data("RedGreen", angle, gain)


def plot_candela_values(df):
    """
    Plots Candela values against the angle, with different gains represented by different colors.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
    """
    plt.figure(figsize=(10, 6))

    # Get unique gain values

    gains = df['gain'].unique()

    # Create a colormap for different gains
    cmap = plt.cm.get_cmap('viridis', len(gains))

    # Plot Candela values against angle for each gain
    for i, gain in enumerate(gains):
        #sort by angle and gain
        gain_data = df[df['gain'] == gain]

        gain_data = gain_data.sort_values(by='angle')
        x_data = gain_data['angle']
        y_data = gain_data['Candela']
        color = cmap(i)
        label = f'Gain: {gain}'
        plt.plot(x_data, y_data, marker='o', linestyle='-', color=color, label=label)

    plt.title('Candela Values vs Angle')
    plt.xlabel('Angle')
    plt.ylabel('Candela')
    plt.grid(True)
    # plt.legend()
    # plt.show()

    return plt


def plot_gain_for_luminance(df, target_luminance):
    """
    Plots the gain for each angle based on a user-specified target luminance.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
        target_luminance (float): The target luminance value.
    """
    plt.figure(figsize=(10, 6))

    # Get unique angle values
    angles = df['angle'].unique()

    # Initialize lists to store the gains for each angle
    plot_angles = []
    plot_gains = []

    # Iterate over each angle
    for angle in angles:
        angle_data = df[df['angle'] == angle]

        # Find the gain closest to the target luminance for the current angle
        luminance_diff = np.abs(angle_data['Candela'] - target_luminance)
        closest_index = luminance_diff.idxmin()
        closest_gain = angle_data.loc[closest_index, 'gain']

        plot_angles.append(angle)
        plot_gains.append(closest_gain)

    # Plot the gain for each angle
    plt.plot(plot_angles, plot_gains, marker='o', linestyle='-', color='blue')

    plt.title(f'Gain vs Angle (Target Luminance: {target_luminance})')
    plt.xlabel('Angle')
    plt.ylabel('Gain')
    plt.grid(True)
    plt.show()
    plt.legend()

    return plot_angles, plot_gains

class LuminanceGainTable:
    def __init__(self, conn):
        self.conn = conn
        self.create_table()

    def create_table(self):
        create_table_query = """
            CREATE TABLE IF NOT EXISTS SinGain (
                colors VARCHAR(255),
                angle FLOAT,
                gain FLOAT
            )
        """
        self.conn.execute(create_table_query)

    def insert_data(self, colors, angle, gain):
        insert_query = """
            INSERT INTO SinGain (colors, angle, gain)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                gain = VALUES(gain)
        """
        self.conn.execute(insert_query, (colors, angle, gain))

if __name__ == "__main__":
    main()
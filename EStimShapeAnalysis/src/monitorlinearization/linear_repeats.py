import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from clat.util.connection import Connection
from src.monitorlinearization.compile_monlin import find_asymptote
from src.monitorlinearization.gray import save_to_db
from src.monitorlinearization.monlin import get_most_recent_pickle_path

matplotlib.use("Qt5Agg")


def main():
    conn = Connection("allen_monitorlinearization_250128")
    pickle_path = get_most_recent_pickle_path("linear_repeats")
    # pickle_path = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/monitor_linearization/linear_repeats_TestRecording_240319_130709.pkl"
    data = pd.read_pickle(
        pickle_path)
    #remove None values (not na)
    data = data[data['Candela']!="None"]
    data.sort_values(by=['Green', 'Red', 'Blue'], inplace=True)
    print(data.to_string())
    # plot_candela_vector(data, 1710948353588074)
    # plot_candela_vector(data, 1710948398565500)
    # plt.show()
    plot_candela_values(data)
    save_to_db(conn, data)


def plot_candela_values(df):
    """
       Plots Candela values for non-zero entries of Red, Green, and Blue in a single plot,

       Args:
           df (pd.DataFrame): DataFrame containing the data with repeats of the same RGB values.
           degree (int): Degree of the polynomial to fit (default: 2).
       """
    plt.figure(figsize=(10, 6))

    # Define colors to plot
    colors = ['Red', 'Green', 'Blue']

    for color in colors:
        # Filter rows where the color is not zero
        non_zero_color = df[df[color] > 0.001]

        # Get unique RGB values for the current color
        unique_rgb_values = non_zero_color[color].unique()

        for rgb_value in unique_rgb_values:
            # Filter rows with the current RGB value
            rgb_data = non_zero_color[non_zero_color[color] == rgb_value]

            # Plot each repeat with its respective line color and label
            x_data = rgb_data[color]
            y_data = rgb_data['Candela']

            plt.plot(x_data, y_data, marker='o', linestyle='-', color=color.lower(),
                     label=f'{color} Value: {rgb_value}', markersize=3)

            # Add order indicator text for each data point
            for i, (x, y) in enumerate(zip(x_data, y_data), start=1):
                plt.text(x, y, str(i), fontsize=8, color=color.lower(),
                         verticalalignment='bottom', horizontalalignment='left')

    plt.title('Candela Values with Repeats')
    plt.xlabel('Color Value (0-255)')
    plt.ylabel('Candela')
    plt.grid(True)

    plt.show()
    return plt


def plot_candela_vector(df, stim_spec_id):
    """
    Plots the CandelaVector for a given StimSpecId.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
        stim_spec_id (int): The StimSpecId to plot the CandelaVector for.
    """
    # Filter the DataFrame based on the StimSpecId
    stim_spec_data = df[df['StimSpecId'] == stim_spec_id]

    if len(stim_spec_data) == 0:
        print(f"No data found for StimSpecId: {stim_spec_id}")
        return

    # Get the CandelaVector for the specified StimSpecId
    candela_vector = stim_spec_data['CandelaVector'].iloc[0]
    # take second half of it
    half_vector = candela_vector[int(len(candela_vector) / 2):]

    # Get the length of the CandelaVector
    vector_length = len(candela_vector)

    # Create a range of indices for the x-axis
    x_range = range(vector_length)

    # Create a new figure
    plt.figure(figsize=(10, 6))

    # Plot the CandelaVector
    plt.plot(x_range, candela_vector, marker='o', linestyle='-', color='blue', label='Candela Value')

    # Calculate the average CandelaVector
    average_candela_vector = np.mean(half_vector, axis=0)
    # median_candela_vector = average_n_most_common(half_vector, n=6)
    asymptote = find_asymptote(candela_vector, 50, 1)

    # repeat the average candela vector to match the length of the original candela vector
    average_candela_vector = np.repeat(average_candela_vector, vector_length)
    median_candela_vector = np.repeat(asymptote, vector_length)

    # Plot the average CandelaVector
    plt.plot(x_range, average_candela_vector, marker='o', linestyle='-', color='red', linewidth=2,
             label='Average Candela Vector')
    plt.plot(x_range, median_candela_vector, marker='o', linestyle='-', color='green', linewidth=2,)
    # Set the title and labels
    plt.title(f'Candela Vector for StimSpecId: {stim_spec_id}')
    plt.xlabel('Index')
    plt.ylabel('Candela')

    # Add a grid and legend
    plt.grid(True)
    plt.legend()




if __name__ == "__main__":
    main()

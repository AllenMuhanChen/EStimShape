import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit

from src.monitorlinearization.monlin import get_most_recent_pickle_path


def main():
    # Load data
    pickle_path = get_most_recent_pickle_path("isoluminance")
    df = pd.read_pickle(
        pickle_path)
    #filter for non NaN
    df = df[df['StimSpecId'].notna()]
    print(df.to_string())
    plot_candela_values(df)


def gaussian(x, a, b, c):
    return a * np.exp(-((x - b) ** 2) / (2 * c ** 2))
def plot_candela_values(df):
    """
    Plots Candela values against the Red/Green ratio,
    along with the linear prediction based on the gamma function.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
    """
    plt.figure(figsize=(10, 6))



    # Average Data by Red/Green Ratio
    # df['Red/Green Ratio'] = df['Red'] / (df['Red'] + df['Green'])
    df = df.sort_values(by=['angle'])
    print(df.to_string())
    # averaged_df = df.groupby('Red/Green Ratio')['Candela'].mean().reset_index()
    averaged_df = df.groupby(['angle','gain'])['Candela'].mean().reset_index()
    averaged_df = averaged_df.sort_values(by=['angle'])
    x_data = averaged_df['angle']
    y_data = averaged_df['Candela']
    plt.plot(x_data, y_data, marker='o', linestyle='-', color='blue', label='Candela Value')


    #Plot Gains
    plt.figure()
    x_data = averaged_df['angle']
    y_data = averaged_df['gain']
    plt.plot(x_data, y_data, marker='o', linestyle='-', color='red', label='Gain')
    plt.show()
    # # Perform Gaussian fitting
    # initial_guess = [max(y_data), np.mean(x_data), np.std(x_data)]
    # popt, _ = curve_fit(gaussian, x_data[1:len(x_data)], y_data[1:len(x_data)], p0=initial_guess)
    # a, b, c = popt

    # # Generate fitted values for plotting
    # fitted_x = np.linspace(min(x_data), max(x_data), 100)
    # fitted_y = gaussian(fitted_x, a, b, c)
    # plt.plot(fitted_x, fitted_y, label='Fitted Gaussian', color='red')

    # # Gamma function parameters
    # red_params = {'A': 0.0012453809963744271, 'gamma': 2.374121012196155, 'max_value': 306.3390568299098}
    # green_params = {'A': 0.0014004255200015716, 'gamma': 2.4477203406649677, 'max_value': 1048.5820044610161}
    #
    # # Calculate linear prediction using gamma function
    # linear_prediction = []
    # for _, row in df.iterrows():
    #     red_value = row['Red']
    #     green_value = row['Green']
    #
    #     red_response = red_params['A'] * red_value ** red_params['gamma']
    #     green_response = green_params['A'] * green_value ** green_params['gamma']
    #
    #     linear_pred = red_response + green_response
    #     linear_prediction.append(linear_pred)

    # plt.plot(x_data, linear_prediction, marker='s', linestyle='-', color='green', label='Linear Prediction')

    plt.title('Candela Values vs Red/Green Ratio')
    plt.xlabel('Red/Green Ratio')
    plt.ylabel('Candela')
    plt.grid(True)
    plt.legend()
    # plt.show()

    #Calculate average distance from desired value
    desired_value = 150
    average_distance = 0
    for index, row in averaged_df.iterrows():
        average_distance += abs(row['Candela']-desired_value)
    average_distance = average_distance/len(averaged_df)
    print("Average distance from desired value: ", average_distance)

    # Calculate average luminance
    average_luminance = 0
    for index, row in averaged_df.iterrows():
        average_luminance += row['Candela']
    average_luminance = average_luminance/len(averaged_df)
    print("Average Luminance: ", average_luminance)

    return plt


if __name__ == "__main__":
    main()


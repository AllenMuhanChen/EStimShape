from __future__ import annotations

import os
import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit
from scipy.stats import linregress
from clat.util.connection import Connection

ORANGE_CUTOFF = 400
CYAN_CUTOFF = 400
GREEN_CUTOFF = 400
RED_CUTOFF = 400

matplotlib.use("Qt5Agg")


def main():
    conn = Connection("allen_monitorlinearization_250128")
    pickle_path = get_most_recent_pickle_path("monitor_linearization")
    df = pd.read_pickle(pickle_path)
    print(df.to_string())
    # Aggregate the measurements
    df_aggregated = aggregate_measurements(df)
    print("Original measurements:", len(df))
    print("Unique RGB combinations:", len(df_aggregated))

    # Store fitted parameters for database use
    fitted_params = {}

    # Plot and fit base colors using aggregated data
    fitted_params.update(plot_base_colors(df_aggregated))

    # Plot and fit derived colors using aggregated data
    plt.figure(figsize=(10, 6))
    fitted_params.update(plot_derived_color(df_aggregated, 'Cyan'))
    fitted_params.update(plot_derived_color(df_aggregated, 'Orange'))
    plt.show()

    # Save aggregated data to db
    save_raw_to_db(conn, df_aggregated)


def aggregate_measurements(df):
    """
    Aggregates measurements by unique RGB combinations while maintaining
    exact same DataFrame format. Only Candela values are averaged.
    """
    # Keep one row for each unique RGB combination (with its StimSpecId and other columns)
    result = df.drop_duplicates(['Red', 'Green', 'Blue']).copy()

    # Calculate means
    means = df.groupby(['Red', 'Green', 'Blue'])['Candela'].mean()

    # Update Candela values directly using the index from the groupby
    for idx in result.index:
        rgb_key = (result.loc[idx, 'Red'],
                   result.loc[idx, 'Green'],
                   result.loc[idx, 'Blue'])
        result.loc[idx, 'Candela'] = means[rgb_key]

    print(f"Original measurements: {len(df)}")
    print(f"Unique RGB combinations: {len(result)}")

    return result
def gamma_function(x, A, gamma, max_value):
    """Gamma function for monitor calibration."""
    return A * (x ** gamma) * (x <= max_value) + A * (max_value ** gamma) * (x > max_value)


def find_cutoff_x(x, y, cutoff_y) -> int:
    """Find the point where the curve passes cutoff_y.
    Returns x value"""
    first_cross_above_cutoff = int(x[np.where(y >= cutoff_y)[0][0]])
    return first_cross_above_cutoff-1


def fit_gamma_curve(x, y, cutoff_y):
    """Fit gamma function to data, handling cutoff."""
    # Find cutoff
    cutoff = find_cutoff_x(x, y, cutoff_y)
    print(f"Cutoff: {cutoff}")
    # Filter data up to cutoff
    mask = x <= cutoff
    x_fit = x[mask]
    y_fit = y[mask]

    # Initial parameter guesses
    p0 = [0.001, 2.2, max(x_fit)]

    try:
        popt, _ = curve_fit(gamma_function, x_fit, y_fit, p0=p0, bounds=([0, 1, 0], [1, 5, np.inf]))
        return popt, cutoff
    except:
        print("Curve fit failed")
        return None, cutoff


def get_most_recent_pickle_path(type: str):
    monitor_linearization_path = "/home/r2_allen/Documents/EStimShape/allen_monlin_250128"
    files = [f for f in os.listdir(monitor_linearization_path) if type in f]
    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(monitor_linearization_path, x)))
    pickle_path = os.path.join(monitor_linearization_path, latest_file)
    return pickle_path


def plot_base_colors(df):
    """Plot and fit base colors (Red and Green)."""
    plt.figure(figsize=(10, 6))
    fitted_params = {}

    # Red
    red_only = df[(df['Red'] > 0.001) & (df['Green'] <= 0.001) & (df['Blue'] <= 0.001)]
    if not red_only.empty:
        x = red_only['Red'].values
        y = red_only['Candela'].values
        popt, cutoff = fit_gamma_curve(x, y, RED_CUTOFF)
        if popt is not None:
            fitted_params['red'] = {'params': popt, 'cutoff': cutoff}
            # Plot original data
            plt.plot(x, y, 'o', label='Red Data', color='red', alpha=0.5)
            # Plot fitted curve
            x_fit = np.linspace(0, max(x), 100)
            y_fit = gamma_function(x_fit, *popt)
            plt.plot(x_fit, y_fit, '-', label='Red Fit', color='darkred')

    # Green
    green_only = df[(df['Green'] > 0.001) & (df['Red'] <= 0.001) & (df['Blue'] <= 0.001)]
    if not green_only.empty:
        x = green_only['Green'].values
        y = green_only['Candela'].values
        popt, cutoff = fit_gamma_curve(x, y, GREEN_CUTOFF)
        if popt is not None:
            fitted_params['green'] = {'params': popt, 'cutoff': cutoff}
            # Plot original data
            plt.plot(x, y, 'o', label='Green Data', color='green', alpha=0.5)
            # Plot fitted curve
            x_fit = np.linspace(0, max(x), 100)
            y_fit = gamma_function(x_fit, *popt)
            plt.plot(x_fit, y_fit, '-', label='Green Fit', color='darkgreen')

    plt.title('Candela for Pure Base Colors with Gamma Fits')
    plt.xlabel('Color Value')
    plt.ylabel('Candela')
    plt.grid(True)
    plt.legend()
    return fitted_params


def plot_derived_color(df, color_name):
    """Plot and fit derived colors (Cyan and Orange)."""
    fitted_params = {}

    if color_name.lower() == 'cyan':
        non_zero_color = df[
            (df['Green'] > 0.001) &
            (df['Blue'] > 0.001) &
            (df['Red'] <= 0.001)
            ]
    elif color_name.lower() == 'orange':
        non_zero_color = df[
            (df['Red'] > 0.001) &
            (df['Green'] > 0.001) &
            (df['Blue'] <= 0.001) &
            (abs(df['Red'] - 2 * df['Green']) < 0.1)
            ]
    else:
        raise ValueError(f"Unsupported color: {color_name}")

    if not non_zero_color.empty:
        # For derived colors, use the maximum of the components as x value
        if color_name.lower() == 'cyan':
            x = non_zero_color[['Green', 'Blue']].max(axis=1).values
        else:  # orange
            x = non_zero_color['Red'].values

        y = non_zero_color['Candela'].values

        # Sort by x for proper plotting
        sort_idx = np.argsort(x)
        x = x[sort_idx]
        y = y[sort_idx]

        if color_name.lower() == 'cyan':
            popt, cutoff = fit_gamma_curve(x, y, CYAN_CUTOFF)
        else:  # orange
            popt, cutoff = fit_gamma_curve(x, y, ORANGE_CUTOFF)
        if popt is not None:
            fitted_params[color_name.lower()] = {'params': popt, 'cutoff': cutoff}

            # Plot original data
            plot_color = 'darkcyan' if color_name.lower() == 'cyan' else 'darkorange'
            plt.plot(x, y, 'o', label=f'{color_name} Data', color=plot_color, alpha=0.5)

            # Plot fitted curve
            x_fit = np.linspace(0, max(x), 100)
            y_fit = gamma_function(x_fit, *popt)
            plt.plot(x_fit, y_fit, '-', label=f'{color_name} Fit',
                     color='cyan' if color_name.lower() == 'cyan' else 'orange')
        else:
            # Plot original data
            plot_color = 'darkcyan' if color_name.lower() == 'cyan' else 'darkorange'
            plt.plot(x, y, 'o', label=f'{color_name} Data', color=plot_color, alpha=0.5)
    plt.title(f'Candela for Derived Colors with Gamma Fits')
    plt.xlabel('Color Value')
    plt.ylabel('Candela')
    plt.grid(True)
    plt.legend()
    return fitted_params

def save_raw_to_db(conn, data):
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

def save_fitted_curves_to_db(conn, fitted_params):
    """Save sampled points from fitted curves to database."""
    # Create table
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

    # Sample points along each curve
    num_samples = 256  # One for each possible color value

    for color, params in fitted_params.items():
        x = np.linspace(0, params['cutoff'], params['cutoff']+1)
        y = gamma_function(x, *params['params'])

        for i, (x_val, y_val) in enumerate(zip(x, y)):
            if x_val == 0:
                continue

            color_val = int(x_val)  # Convert to 0-255 range

            if color == 'red':
                conn.execute("""
                    INSERT INTO MonitorLin (red, green, blue, luminance)
                    VALUES (%s, 0, 0, %s)
                """, (color_val, float(y_val)))
            elif color == 'green':
                conn.execute("""
                    INSERT INTO MonitorLin (red, green, blue, luminance)
                    VALUES (0, %s, 0, %s)
                """, (color_val, float(y_val)))
            elif color == 'cyan':
                conn.execute("""
                    INSERT INTO MonitorLin (red, green, blue, luminance)
                    VALUES (0, %s, %s, %s)
                """, (color_val, color_val, float(y_val)))
            elif color == 'orange':
                green_val = int(color_val / 2)  # Orange has red ≈ 2*green
                conn.execute("""
                    INSERT INTO MonitorLin (red, green, blue, luminance)
                    VALUES (%s, %s, 0, %s)
                """, (color_val, green_val, float(y_val)))


if __name__ == "__main__":
    main()
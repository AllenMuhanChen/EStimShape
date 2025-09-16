import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from clat.util.connection import Connection


def create_frequency_preference_scatter_plots():
    """Create separate scatter plots for each frequency comparing Solid vs Isochromatic Preference Indices for cluster channels only."""

    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # Query solid preference indices but only for cluster channels
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index
                  FROM SolidPreferenceIndices s
                           JOIN Experiments e ON s.session_id = e.session_id
                           JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND s.unit_name = c.channel
                  """

    # Query isochromatic preference indices but only for cluster channels
    isochromatic_query = """
                         SELECT i.session_id, i.unit_name, i.frequency, i.isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices i
                                  JOIN Experiments e ON i.session_id = e.session_id
                                  JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND i.unit_name = c.channel
                         """

    # Execute queries and fetch data
    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()

    # Convert to DataFrames
    solid_df = pd.DataFrame(solid_data, columns=['session_id', 'unit_name', 'solid_preference_index'])
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency', 'isochromatic_preference_index'])

    # Merge the data on session_id and unit_name
    merged_df = pd.merge(solid_df, isochromatic_df, on=['session_id', 'unit_name'], how='inner')

    if merged_df.empty:
        print("No matching data found between the two tables for cluster channels.")
        return

    # Get unique sessions and frequencies
    sessions = sorted(merged_df['session_id'].unique())
    frequencies = sorted(merged_df['frequency'].unique())

    print(f"Found data for {len(sessions)} sessions: {sessions}")
    print(f"Creating plots for {len(frequencies)} frequencies: {frequencies}")
    print(f"Using only cluster channels - {len(merged_df['unit_name'].unique())} total units")

    # Create a plot for each frequency
    frequency_stats = {}
    for frequency in frequencies:
        frequency_stats[frequency] = plot_frequency_data(merged_df, frequency, sessions)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY BY FREQUENCY (CLUSTER CHANNELS ONLY):")
    print("=" * 60)

    for frequency, stats in frequency_stats.items():
        print(f"\nFrequency {frequency} Hz:")
        print(f"  Units: {stats['n']}")
        print(f"  R²: {stats['r_squared']:.3f}")
        print(f"  p-value: {stats['p_value']:.3f}")

    return merged_df


def plot_frequency_data(merged_df, frequency, sessions):
    """Create a plot for a single frequency with all sessions."""

    # Filter data for this frequency
    freq_data = merged_df[merged_df['frequency'] == frequency]

    if freq_data.empty:
        print(f"No data for frequency {frequency} Hz")
        return {'n': 0, 'r_squared': 0, 'r_value': 0, 'p_value': 1, 'slope': 0, 'intercept': 0}

    # Extract values
    x = freq_data['solid_preference_index'].values
    y = freq_data['isochromatic_preference_index'].values

    # Calculate linear regression for combined data
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2

    # Create the scatter plot
    plt.figure(figsize=(12, 8))

    # Create a color map for sessions
    session_colors = plt.cm.Set1(np.linspace(0, 1, len(sessions)))

    # Plot each session with different colors
    for i, session_id in enumerate(sessions):
        session_data = freq_data[freq_data['session_id'] == session_id]
        if not session_data.empty:
            plt.scatter(session_data['solid_preference_index'],
                        session_data['isochromatic_preference_index'],
                        c=[session_colors[i]], alpha=0.7, s=60,
                        label=f'Session {session_id} (n={len(session_data)})')

    # Add trend line for combined data
    if len(x) > 1:
        line_x = np.linspace(x.min(), x.max(), 100)
        line_y = slope * line_x + intercept
        plt.plot(line_x, line_y, 'k-', linewidth=2, label=f'Combined trend (R² = {r_squared:.3f})')

    # Add labels and title
    plt.xlabel('Solid Preference Index')
    plt.ylabel('Isochromatic Preference Index')
    plt.title(
        f'Frequency {frequency} Hz: Solid vs Isochromatic Preference (Cluster Channels)\n(n={len(freq_data)} total units)')

    # Add reference lines at zero
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

    # Add grid
    plt.grid(True, alpha=0.3)

    # Set axis limits
    plt.xlim(-1.1, 1.1)
    plt.ylim(-1.1, 1.1)

    # Add legend
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Add statistics text box
    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {len(freq_data)}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    # Add quadrant labels
    plt.text(0.4, 0.9, 'Prefers 3D &\nIsochromatic', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.5))
    plt.text(-0.6, 0.9, 'Prefers 2D &\nIsochromatic', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.5))
    plt.text(0.4, -0.9, 'Prefers 3D &\nIsoluminant', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral', alpha=0.5))
    plt.text(-0.6, -0.9, 'Prefers 2D &\nIsoluminant', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.5))

    plt.tight_layout()
    plt.show()

    # Print frequency statistics
    print(f"\nFrequency {frequency} Hz Statistics (Cluster Channels Only):")
    print(f"  Total units: {len(freq_data)}")
    print(f"  Solid Preference range: {x.min():.3f} to {x.max():.3f}")
    print(f"  Isochromatic Preference range: {y.min():.3f} to {y.max():.3f}")
    print(f"  Correlation: r = {r_value:.3f}, R² = {r_squared:.3f}, p = {p_value:.3f}")

    # Print breakdown by session
    for session_id in sessions:
        session_data = freq_data[freq_data['session_id'] == session_id]
        if not session_data.empty:
            print(f"    Session {session_id}: {len(session_data)} units")

    return {
        'n': len(freq_data),
        'r_squared': r_squared,
        'r_value': r_value,
        'p_value': p_value,
        'slope': slope,
        'intercept': intercept
    }


if __name__ == "__main__":
    data = create_frequency_preference_scatter_plots()
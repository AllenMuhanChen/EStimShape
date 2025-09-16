import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from clat.util.connection import Connection


def create_simple_preference_scatter_plot():
    """Create a simple scatter plot comparing Solid vs Isochromatic Preference Indices."""

    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # Query both preference tables
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index
                  FROM SolidPreferenceIndices
                  """

    # Since isochromatic now has frequencies, we'll average across frequencies for each unit
    isochromatic_query = """
                         SELECT session_id, \
                                unit_name, \
                                AVG(isochromatic_preference_index) as isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices
                         GROUP BY session_id, unit_name
                         """

    # Execute queries and fetch data
    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()

    # Convert to DataFrames
    solid_df = pd.DataFrame(solid_data, columns=['session_id', 'unit_name', 'solid_preference_index'])
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'isochromatic_preference_index'])

    # Merge the data on session_id and unit_name
    merged_df = pd.merge(solid_df, isochromatic_df, on=['session_id', 'unit_name'], how='inner')

    if merged_df.empty:
        print("No matching data found between the two tables.")
        return

    # Get unique sessions
    sessions = sorted(merged_df['session_id'].unique())
    print(f"Found data for {len(sessions)} sessions: {sessions}")

    # Create combined plot
    combined_stats = plot_combined_data(merged_df, sessions)

    # Print summary
    print(f"\nCombined ({combined_stats['n']} total units):")
    print(f"  R²: {combined_stats['r_squared']:.3f}")
    print(f"  p-value: {combined_stats['p_value']:.3f}")

    return merged_df


def plot_combined_data(merged_df, sessions):
    """Create a combined plot with all sessions, color-coded by session."""

    # Extract values
    x = merged_df['solid_preference_index'].values
    y = merged_df['isochromatic_preference_index'].values

    # Calculate linear regression for combined data
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2

    # Create the scatter plot
    plt.figure(figsize=(12, 8))

    # Create a color map for sessions
    session_colors = plt.cm.Set1(np.linspace(0, 1, len(sessions)))

    # Plot each session with different colors
    for i, session_id in enumerate(sessions):
        session_data = merged_df[merged_df['session_id'] == session_id]
        plt.scatter(session_data['solid_preference_index'],
                    session_data['isochromatic_preference_index'],
                    c=[session_colors[i]], alpha=0.7, s=60,
                    label=f'Session {session_id} (n={len(session_data)})')

    # Add trend line for combined data
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept
    plt.plot(line_x, line_y, 'k-', linewidth=2, label=f'Combined trend (R² = {r_squared:.3f})')

    # Add labels and title
    plt.xlabel('Solid Preference Index')
    plt.ylabel('Isochromatic Preference Index (averaged across frequencies)')
    plt.title(f'Combined: Solid vs Isochromatic Preference Indices\n(n={len(merged_df)} total units)')

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
    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {len(merged_df)}'
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

    # Print combined statistics
    print(f"\nCombined Statistics:")
    print(f"  Total units: {len(merged_df)}")
    print(f"  Solid Preference range: {x.min():.3f} to {x.max():.3f}")
    print(f"  Isochromatic Preference range: {y.min():.3f} to {y.max():.3f}")
    print(f"  Combined correlation: r = {r_value:.3f}, R² = {r_squared:.3f}, p = {p_value:.3f}")

    return {
        'n': len(merged_df),
        'r_squared': r_squared,
        'r_value': r_value,
        'p_value': p_value,
        'slope': slope,
        'intercept': intercept
    }


if __name__ == "__main__":
    data = create_simple_preference_scatter_plot()
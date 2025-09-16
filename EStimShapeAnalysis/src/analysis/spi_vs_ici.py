import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from clat.util.connection import Connection


def create_preference_indices_scatter_plot():
    """Create a scatter plot comparing Solid Preference Index vs Isochromatic Preference Index."""

    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # Query both tables
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index
                  FROM SolidPreferenceIndices \
                  """

    isochromatic_query = """
                         SELECT session_id, unit_name, isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices \
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

    # Extract x and y values for regression
    x = merged_df['solid_preference_index'].values
    y = merged_df['isochromatic_preference_index'].values

    # Calculate linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2

    # Create the scatter plot
    plt.figure(figsize=(10, 8))
    plt.scatter(x, y, alpha=0.7, s=50, color='blue', label='Data points')

    # Add trend line
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept
    plt.plot(line_x, line_y, 'r-', linewidth=2, label=f'Trend line (R² = {r_squared:.3f})')

    # Add labels and title
    plt.xlabel('Solid Preference Index')
    plt.ylabel('Isochromatic Preference Index')
    plt.title('Solid vs Isochromatic Preference Indices')

    # Add reference lines at zero
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

    # Add grid
    plt.grid(True, alpha=0.3)

    # Set axis limits to show the full range (-1 to 1)
    plt.xlim(-1.1, 1.1)
    plt.ylim(-1.1, 1.1)

    # Add legend
    plt.legend()

    # Add statistics text box
    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {len(merged_df)}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    # Add annotations for quadrants
    plt.text(0.5, 0.9, 'Prefers 3D &\nIsochromatic', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.5))
    plt.text(-0.5, 0.9, 'Prefers 2D &\nIsochromatic', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.5))
    plt.text(0.5, -0.9, 'Prefers 3D &\nIsoluminant', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral', alpha=0.5))
    plt.text(-0.5, -0.9, 'Prefers 2D &\nIsoluminant', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.5))

    # Add unit labels if there aren't too many points
    if len(merged_df) <= 20:
        for idx, row in merged_df.iterrows():
            plt.annotate(f"{row['unit_name']}",
                         (row['solid_preference_index'], row['isochromatic_preference_index']),
                         xytext=(5, 5), textcoords='offset points', fontsize=8, alpha=0.7)

    plt.tight_layout()

    # Print summary statistics
    print(f"Number of units with both indices: {len(merged_df)}")
    print(f"Solid Preference Index range: {x.min():.3f} to {x.max():.3f}")
    print(f"Isochromatic Preference Index range: {y.min():.3f} to {y.max():.3f}")
    print(f"Correlation coefficient (r): {r_value:.3f}")
    print(f"R-squared: {r_squared:.3f}")
    print(f"P-value: {p_value:.3f}")
    print(f"Slope: {slope:.3f}")
    print(f"Intercept: {intercept:.3f}")

    plt.show()

    return merged_df


if __name__ == "__main__":
    data = create_preference_indices_scatter_plot()
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from clat.util.connection import Connection


def create_preference_indices_frequency_plots():
    """Create separate plots for each session, with subplots for each frequency, plus combined plots."""

    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # Query preference tables and filter for "Unit" in unit_name
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index
                  FROM SolidPreferenceIndices
                  WHERE unit_name LIKE '%Unit%'
                  """

    # Isochromatic preference with Unit filter
    isochromatic_query = """
                         SELECT session_id, unit_name, frequency, isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices
                         WHERE unit_name LIKE '%Unit%'
                         """

    # Execute queries and fetch data
    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()

    # Convert to DataFrames
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index'])
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency', 'isochromatic_preference_index'])

    # Merge the data on session_id and unit_name
    merged_df = pd.merge(solid_df, isochromatic_df, on=['session_id', 'unit_name'], how='inner')

    if merged_df.empty:
        print("No matching data found between the two tables for units containing 'Unit'.")
        return

    # Get unique sessions and frequencies
    sessions = sorted(merged_df['session_id'].unique())
    frequencies = sorted(merged_df['frequency'].unique())

    print(f"Creating plots for {len(sessions)} sessions: {sessions}")
    print(f"Each session will have {len(frequencies)} frequency subplots: {frequencies}")
    print(f"Using units with 'Unit' in the name")
    print(f"Total units: {len(merged_df['unit_name'].unique())}")

    # Show breakdown by session
    for session in sessions:
        session_units = merged_df[merged_df['session_id'] == session]['unit_name'].nunique()
        print(f"  Session {session}: {session_units} units")

    # Create a separate plot for each session
    for session_id in sessions:
        plot_session_frequencies(merged_df, session_id, frequencies)

    # Add combined plots at the end
    print("\nCreating combined plots...")
    create_combined_frequency_plots(merged_df, sessions, frequencies)

    return merged_df


def plot_session_frequencies(merged_df, session_id, frequencies):
    """Create a plot for one session with subplots for each frequency."""

    # Filter data for this session
    session_data = merged_df[merged_df['session_id'] == session_id]

    if session_data.empty:
        print(f"No data for session {session_id}")
        return

    # Create subplots - arrange frequencies in a 2x2 grid or single row
    n_freq = len(frequencies)
    if n_freq <= 2:
        nrows, ncols = 1, n_freq
    elif n_freq <= 4:
        nrows, ncols = 2, 2
    else:
        nrows, ncols = 2, (n_freq + 1) // 2

    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows))
    fig.suptitle(f'Session {session_id}: Solid vs Isochromatic Preference by Frequency (Units Only)',
                 fontsize=16)

    # Make axes iterable even for single subplot
    if n_freq == 1:
        axes = [axes]
    elif nrows == 1:
        axes = axes
    else:
        axes = axes.flatten()

    # Plot each frequency
    for freq_idx, frequency in enumerate(frequencies):
        # Filter data for this frequency
        freq_data = session_data[session_data['frequency'] == frequency]

        ax = axes[freq_idx]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} Hz')
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-1.1, 1.1)
            continue

        # Extract values
        x = freq_data['solid_preference_index'].values
        y = freq_data['isochromatic_preference_index'].values

        # Calculate linear regression if we have enough points
        if len(x) > 1:
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            r_squared = r_value ** 2
        else:
            slope = intercept = r_value = p_value = r_squared = 0

        # Create scatter plot
        ax.scatter(x, y, alpha=0.7, s=60, color='blue')

        # Add trend line if we have enough points
        if len(x) > 1:
            line_x = np.linspace(x.min(), x.max(), 100)
            line_y = slope * line_x + intercept
            ax.plot(line_x, line_y, 'r-', linewidth=2, alpha=0.8)

        # Set title and labels
        ax.set_title(f'{frequency} Hz (n={len(freq_data)})')
        ax.set_xlabel('Solid Preference Index')
        ax.set_ylabel('Isochromatic Preference Index')

        # Add reference lines at zero
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

        # Add grid
        ax.grid(True, alpha=0.3)

        # Set axis limits
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)

        # Add statistics text
        if len(x) > 1:
            stats_text = f'R²={r_squared:.3f}\nr={r_value:.3f}\np={p_value:.3f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                    verticalalignment='top', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

        # Add unit labels if there are few points
        if len(freq_data) <= 10:
            for idx, row in freq_data.iterrows():
                ax.annotate(f"{row['unit_name']}",
                            (row['solid_preference_index'], row['isochromatic_preference_index']),
                            xytext=(3, 3), textcoords='offset points', fontsize=8, alpha=0.7)

    # Hide any unused subplots
    for idx in range(len(frequencies), len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.show()

    # Print session statistics
    print(f"\nSession {session_id} Statistics (Units Only):")
    for frequency in frequencies:
        freq_data = session_data[session_data['frequency'] == frequency]
        if not freq_data.empty:
            x = freq_data['solid_preference_index'].values
            y = freq_data['isochromatic_preference_index'].values
            if len(x) > 1:
                _, _, r_value, p_value, _ = stats.linregress(x, y)
                print(f"  {frequency} Hz: n={len(freq_data)}, r={r_value:.3f}, p={p_value:.3f}")
            else:
                print(f"  {frequency} Hz: n={len(freq_data)} (insufficient data for correlation)")
        else:
            print(f"  {frequency} Hz: No data")


def create_combined_frequency_plots(merged_df, sessions, frequencies):
    """Create combined plots showing all sessions together for each frequency."""

    # Create a separate combined plot for each frequency
    for frequency in frequencies:
        plot_combined_frequency_data(merged_df, frequency, sessions)


def plot_combined_frequency_data(merged_df, frequency, sessions):
    """Create a combined plot for one frequency with all sessions."""

    # Filter data for this frequency
    freq_data = merged_df[merged_df['frequency'] == frequency]

    if freq_data.empty:
        print(f"No data for frequency {frequency} Hz")
        return

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
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept
    plt.plot(line_x, line_y, 'k-', linewidth=2, label=f'Combined trend (R² = {r_squared:.3f})')

    # Add labels and title
    plt.xlabel('Solid Preference Index')
    plt.ylabel('Isochromatic Preference Index')
    plt.title(
        f'Combined - Frequency {frequency} Hz: Solid vs Isochromatic Preference (Units Only)\n(n={len(freq_data)} total units)')

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
    print(f"\nCombined {frequency} Hz Statistics (Units Only):")
    print(f"  Total units: {len(freq_data)}")
    print(f"  Solid Preference range: {x.min():.3f} to {x.max():.3f}")
    print(f"  Isochromatic Preference range: {y.min():.3f} to {y.max():.3f}")
    print(f"  Correlation: r = {r_value:.3f}, R² = {r_squared:.3f}, p = {p_value:.3f}")


if __name__ == "__main__":
    data = create_preference_indices_frequency_plots()
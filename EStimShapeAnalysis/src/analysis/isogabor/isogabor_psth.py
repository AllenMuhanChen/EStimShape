import pandas as pd

from src.analysis import Analysis
from src.analysis.isogabor import isogabor_raster_pipeline
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


def main():
    channel = None
    session_id, _ = read_session_id_from_db_name(context.isogabor_database)
    if channel is None:
        channel = read_cluster_channels(session_id)[0]

    analysis = IsogaborPSTHAnalysis()
    return analysis.run(session_id, "raw", channel)


class IsogaborPSTHAnalysis(Analysis):

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'isogabor',
                'IsoGaborStimInfo',
                self.response_table,
            )
            print(f"Imported data with columns: {compiled_data.columns}")

        # Define frequencies to include - modify as needed based on your data
        frequencies = None  # Use all frequencies

        # Calculate and plot PSTH

        psth_fig = compute_and_plot_psth(
            compiled_data=compiled_data,
            channel=channel,
            spike_tstamps_col=self.spike_tstamps_col,
            save_path=f"{self.save_path}/{channel}: color_experiment_psth.png",
            bin_size=0.05,
            time_window=(-0.2, 0.5),  # 0 to 500ms
            frequency_to_include=frequencies
        )

        # Show the figure
        plt.show()

        return psth_fig

    def compile_and_export(self):
        isogabor_raster_pipeline.compile_and_export()

    def compile(self):
        isogabor_raster_pipeline.compile()


def compute_and_plot_psth(
        compiled_data: pd.DataFrame,
        channel: str,
        spike_tstamps_col: str,
        save_path: str,
        bin_size: float = 0.01,  # 10ms bins
        time_window: Tuple[float, float] = (0, 0.5),  # 0 to 500ms
        frequency_to_include: Optional[List[float]] = None
):
    """
    Compute and plot PSTH for comparing red/green/red-green and cyan/orange/cyan-orange
    at different spatial frequencies.

    Args:
        compiled_data: DataFrame with trial data
        channel: Channel to analyze
        spike_tstamps_col: Column containing spike timestamps
        save_path: Path to save the resulting figure
        bin_size: Size of time bins in seconds
        time_window: Time range to analyze (start, end) in seconds
        frequency_to_include: List of frequencies to include, if None use all

    Returns:
        Matplotlib figure with the PSTH plots
    """
    # Filter for valid data
    filtered_data = compiled_data[
        (compiled_data[spike_tstamps_col].notnull()) &
        (compiled_data['Type'].isin(['Red', 'Green', 'RedGreen', 'Cyan', 'Orange', 'CyanOrange']))
        ]

    # Limit to specific frequencies if specified
    if frequency_to_include:
        filtered_data = filtered_data[filtered_data['Frequency'].isin(frequency_to_include)]

    # Get unique frequencies for organization
    frequencies = sorted(filtered_data['Frequency'].unique())

    # Create time bins
    start_time, end_time = time_window
    bins = np.arange(start_time, end_time + bin_size, bin_size)
    bin_centers = bins[:-1] + bin_size / 2

    # Define colors for plotting
    colors = {
        'Red': 'red',
        'Green': 'green',
        'RedGreen': 'darkred',
        'Cyan': 'cyan',
        'Orange': 'orange',
        'CyanOrange': 'teal'
    }

    # First pass: calculate max AVERAGE rates to set consistent y-axis limits
    max_avg_rates = []
    min_avg_rates = []
    for freq in frequencies:
        freq_data = filtered_data[filtered_data['Frequency'] == freq]

        # Calculate max average rates for all color groups
        all_colors = ['Red', 'Green', 'RedGreen', 'Cyan', 'Orange', 'CyanOrange']
        for color in all_colors:
            color_data = freq_data[freq_data['Type'] == color]
            if color_data.empty:
                continue

            # Collect all rates for this color
            all_trial_rates = []

            for _, trial in color_data.iterrows():
                if channel not in trial[spike_tstamps_col]:
                    continue

                spike_times = trial[spike_tstamps_col][channel]
                spike_times = [t for t in spike_times if start_time <= t <= end_time]
                counts, _ = np.histogram(spike_times, bins=bins)
                rate = counts / bin_size
                all_trial_rates.append(rate)

            # Calculate average rate if we have trials
            if all_trial_rates:
                avg_rate = np.mean(np.array(all_trial_rates), axis=0)
                max_avg_rates.append(np.max(avg_rate) if len(avg_rate) > 0 else 0)
                min_avg_rates.append(np.min(avg_rate) if len(avg_rate) > 0 else 0)

    # Determine global y-max (with a little padding)
    global_y_max = max(max_avg_rates) * 1.2  # Add 20% padding
    global_y_min = min(min_avg_rates)

    # Create figure with subplots
    n_rows = len(frequencies)
    fig, axes = plt.subplots(n_rows, 2, figsize=(16, 10), sharex=True)

    # If only one frequency, make sure axes is still 2D
    if n_rows == 1:
        axes = np.array([axes]).reshape(1, 2)

    # Process each frequency
    for row_idx, freq in enumerate(frequencies):
        freq_data = filtered_data[filtered_data['Frequency'] == freq]

        # Group by color types
        warm_colors = ['Red', 'Green', 'RedGreen']
        cool_colors = ['Cyan', 'Orange', 'CyanOrange']

        # Plot warm colors (left column)
        ax_warm = axes[row_idx, 0]
        process_and_plot_color_group(
            freq_data, warm_colors, channel, spike_tstamps_col,
            bins, bin_centers, bin_size, ax_warm, colors
        )

        # Plot cool colors (right column)
        ax_cool = axes[row_idx, 1]
        process_and_plot_color_group(
            freq_data, cool_colors, channel, spike_tstamps_col,
            bins, bin_centers, bin_size, ax_cool, colors
        )

        # Set consistent y-axis limits for this row
        ax_warm.set_ylim(global_y_min, global_y_max)
        ax_cool.set_ylim(global_y_min, global_y_max)

        # Add titles and labels for this row
        ax_warm.set_title(f"Red/Green/RedGreen (SF: {freq})")
        ax_cool.set_title(f"Cyan/Orange/CyanOrange (SF: {freq})")

        # Add y-axis label on left plot
        ax_warm.set_ylabel("Firing Rate (spikes/sec)")

        # Grid
        ax_warm.grid(True, linestyle='--', alpha=0.7)
        ax_cool.grid(True, linestyle='--', alpha=0.7)

    # Add common x-axis label
    for ax in axes[-1]:
        ax.set_xlabel("Time (s)")

    # Overall title
    fig.suptitle(f"Peristimulus Time Histogram: Channel {channel}", fontsize=16)

    # Draw a vertical line at time 0 (stimulus onset) if it's in our window
    if start_time <= 0 <= end_time:
        for row in axes:
            for ax in row:
                ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)

    # Adjust layout
    plt.tight_layout()
    fig.subplots_adjust(top=0.92)

    # Save the figure
    plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig


def process_and_plot_color_group(
        freq_data, color_list, channel, spike_tstamps_col,
        bins, bin_centers, bin_size, ax, colors
):
    """
    Process and plot PSTH for a group of colors.

    Args:
        freq_data: DataFrame filtered for specific frequency
        color_list: List of color types to process
        channel: Channel to analyze
        spike_tstamps_col: Column with spike timestamps
        bins: Time bins array
        bin_centers: Centers of time bins
        bin_size: Size of time bins in seconds
        ax: Matplotlib axis to plot on
        colors: Dictionary mapping color names to matplotlib colors
    """
    for color in color_list:
        color_data = freq_data[freq_data['Type'] == color]

        # Skip if no trials for this color
        if color_data.empty:
            continue

        # Collect binned firing rates for all trials
        all_rates = []

        # Process each trial
        for _, trial in color_data.iterrows():
            # Skip if no spikes for this channel
            if channel not in trial[spike_tstamps_col]:
                continue

            spike_times = trial[spike_tstamps_col][channel]

            # Filter spikes within time window
            spike_times = [t for t in spike_times if bins[0] <= t <= bins[-1]]

            # Bin the spike times
            counts, _ = np.histogram(spike_times, bins=bins)

            # Convert to firing rate (spikes/sec)
            firing_rate = counts / bin_size
            all_rates.append(firing_rate)

        # Skip if no valid trials
        if not all_rates:
            continue

        # Calculate statistics
        rates_array = np.array(all_rates)
        mean_rate = np.mean(rates_array, axis=0)
        std_rate = np.std(rates_array, axis=0)

        # Plot mean with std shading
        ax.plot(bin_centers, mean_rate, color=colors[color],
                label=f"{color} (n={len(all_rates)})")
        # ax.fill_between(bin_centers, mean_rate - std_rate, mean_rate + std_rate,
        #                 color=colors[color], alpha=0.2)

    # Add legend
    ax.legend()


if __name__ == "__main__":
    main()

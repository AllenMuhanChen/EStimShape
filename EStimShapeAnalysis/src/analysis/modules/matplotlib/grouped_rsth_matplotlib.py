import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    ComputationModule, AnalysisModule,
    AnalysisModuleFactory
)
from src.analysis.modules.figure_output import FigureSaverOutput
from src.analysis.modules.grouped_rsth import GroupedPSTHInputHandler


# Import the existing SortingUtils


class GroupedPSTHComputation_matplotlib(ComputationModule):
    """
    Computation module that handles PSTH calculation and plotting.

    Responsibility: PSTH calculation and visualization.
    """

    def __init__(self,
                 time_window: Tuple[float, float] = (-0.2, 0.5),
                 bin_size: float = 0.01,
                 figsize: Tuple[float, float] = (16, 10),
                 colors: Optional[Dict[str, str]] = None,
                 y_max: Optional[float] = None,
                 show_std: bool = False,
                 show_stimulus_onset: bool = True,
                 title: Optional[str] = None,
                 col_titles: Optional[List[str]] = None,
                 primary_group_labels: Optional[Dict[str, str]] = None,
                 secondary_group_labels: Optional[Dict[str, str]] = None):
        """
        Initialize the PSTH computation module.

        Args:
            time_window: Time range to analyze (start, end) in seconds
            bin_size: Size of time bins in seconds
            figsize: Figure size (width, height) in inches
            colors: Optional dict mapping group names to colors
            y_max: Optional maximum y-axis value (will be auto-calculated if None)
            show_std: Whether to show standard deviation as shaded area
            show_stimulus_onset: Whether to show a vertical line at stimulus onset (t=0)
            title: Optional overall figure title
            col_titles: Optional custom titles for each column
            primary_group_labels: Optional custom labels for primary groups
            secondary_group_labels: Optional custom labels for secondary groups
        """
        self.time_window = time_window
        self.bin_size = bin_size
        self.figsize = figsize
        self.colors = colors or {}
        self.y_max = y_max
        self.show_std = show_std
        self.show_stimulus_onset = show_stimulus_onset
        self.title = title
        self.col_titles = col_titles
        self.primary_group_labels = primary_group_labels or {}
        self.secondary_group_labels = secondary_group_labels or {}

    def compute(self, prepared_data: Dict[str, Any]) -> plt.Figure:
        """
        Compute PSTHs from prepared data and visualize them.

        Args:
            prepared_data: Output from the input handler

        Returns:
            Matplotlib figure with the PSTH plots
        """
        # Extract data and configuration
        data = prepared_data['data']
        primary_group_col = prepared_data['primary_group_col']
        secondary_group_col = prepared_data['secondary_group_col']
        spike_data_col = prepared_data['spike_data_col']
        spike_data_col_key = prepared_data['spike_data_col_key']
        primary_groups = prepared_data['primary_groups']
        secondary_groups = prepared_data['secondary_groups']
        column_primary_groups = prepared_data['column_primary_groups']
        n_columns = prepared_data['n_columns']

        # Create time bins - this is computation
        start_time, end_time = self.time_window
        bins = np.arange(start_time, end_time + self.bin_size, self.bin_size)
        bin_centers = bins[:-1] + self.bin_size / 2

        # Determine layout
        n_rows = max(1, len(secondary_groups) if secondary_groups else 1)

        # Define colors if not provided
        if not self.colors:
            # Generate colors for each group
            default_colors = plt.cm.tab10(np.linspace(0, 1, len(primary_groups)))
            for i, group in enumerate(primary_groups):
                self.colors[group] = default_colors[i]

        # First pass: calculate max rates for consistent y-axis
        max_rates = []
        min_rates = []

        for secondary_value in secondary_groups or [None]:
            # Get data for this secondary group
            if secondary_group_col and secondary_value is not None:
                secondary_data = data[data[secondary_group_col] == secondary_value]
            else:
                secondary_data = data

            # Calculate max rates for all primary groups
            for group in primary_groups:
                group_data = secondary_data[secondary_data[primary_group_col] == group]
                if group_data.empty:
                    continue

                # Collect all rates for this primary group
                all_trial_rates = []

                for _, trial in group_data.iterrows():
                    # Extract spike times
                    spike_times = self._extract_spike_times(trial, spike_data_col, spike_data_col_key)

                    if not spike_times:
                        continue

                    # Bin spike times
                    counts, _ = np.histogram(spike_times, bins=bins)
                    rates = counts / self.bin_size
                    all_trial_rates.append(rates)

                # Calculate statistics if we have trials
                if all_trial_rates:
                    all_trial_rates = np.array(all_trial_rates)
                    mean_rates = np.mean(all_trial_rates, axis=0)
                    max_rates.append(np.max(mean_rates))
                    min_rates.append(np.min(mean_rates))

        # Determine global y-axis range with padding
        global_y_max = self.y_max if self.y_max is not None else max(max_rates) * 1.1 if max_rates else 1.0
        global_y_min = min(0, min(min_rates)) if min_rates else 0  # Ensure it includes 0

        # Create figure with subplots - dynamic number of columns
        fig, axes = plt.subplots(n_rows, n_columns, figsize=self.figsize, sharex=True, sharey=True)

        # Ensure axes is 2D even with one row or one column
        if n_rows == 1 and n_columns == 1:
            axes = np.array([[axes]])
        elif n_rows == 1:
            axes = np.array([axes]) if isinstance(axes, np.ndarray) else np.array([[axes]])
        elif n_columns == 1:
            axes = np.array([[ax] for ax in axes])

        # Plot PSTHs for each secondary group and column
        for row_idx, secondary_value in enumerate(secondary_groups or [None]):
            # Get data for this secondary group
            if secondary_group_col and secondary_value is not None:
                secondary_data = data[data[secondary_group_col] == secondary_value]
            else:
                secondary_data = data

            # Process each column
            for col_idx in range(n_columns):
                # Get groups for this column
                col_groups = column_primary_groups.get(col_idx, [])

                if not col_groups:
                    # Skip empty columns
                    continue

                # Plot this column's groups
                ax = axes[row_idx, col_idx]
                self._calculate_and_plot_psth(
                    ax,
                    secondary_data,
                    primary_group_col,
                    col_groups,
                    spike_data_col,
                    spike_data_col_key,
                    bins,
                    bin_centers
                )

                # Set y-axis limits
                ax.set_ylim(global_y_min, global_y_max)

                # Add column title
                if self.col_titles and len(self.col_titles) > col_idx:
                    col_title = self.col_titles[col_idx]
                else:
                    col_title = f"Groups: {', '.join(self._get_display_names(col_groups))}"

                # Add secondary group label if applicable
                if secondary_group_col and secondary_value is not None:
                    display_name = self.secondary_group_labels.get(secondary_value, secondary_value)

                    if row_idx == 0:  # Only add to first row
                        # Keep the column title simple
                        ax.set_title(col_title)

                    # Add secondary group label on left side
                    if col_idx == 0:  # Only add to leftmost column
                        ax.set_ylabel(f"{secondary_group_col}: {display_name}")
                else:
                    if row_idx == 0:  # Only add to first row
                        ax.set_title(col_title)

                # Add grid
                ax.grid(True, linestyle='--', alpha=0.7)

                # Add x-axis label on bottom row only
                if row_idx == n_rows - 1:
                    ax.set_xlabel("Time (s)")

                # Draw stimulus onset line if requested
                if self.show_stimulus_onset:
                    if start_time <= 0 <= end_time:
                        ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)

        # Add overall title
        if self.title:
            fig.suptitle(self.title, fontsize=16)

        # Adjust layout
        plt.tight_layout()
        if self.title:
            fig.subplots_adjust(top=0.92)

        return fig

    def _extract_spike_times(self, trial, spike_data_col, spike_data_col_key):
        """
        Extract spike times from a trial, handling different data formats.
        """
        # Get spike times data
        if spike_data_col not in trial:
            return []

        spike_data = trial[spike_data_col]

        # If we have a dictionary and need to extract a specific key
        if isinstance(spike_data, dict) and spike_data_col_key:
            if spike_data_col_key not in spike_data:
                return []
            return spike_data[spike_data_col_key]

        # If we have a direct list of spike times
        elif isinstance(spike_data, list):
            return spike_data

        # Nested dictionary format for multiple channels
        elif isinstance(spike_data, dict) and not spike_data_col_key:
            # Flatten all spike times from all channels
            all_spikes = []
            for channel, spikes in spike_data.items():
                all_spikes.extend(spikes)
            return all_spikes

        return []

    def _calculate_and_plot_psth(self, ax, data, group_col, groups,
                                 spike_data_col, spike_data_col_key,
                                 bins, bin_centers):
        """
        Calculate and plot PSTH for a group of data.
        """
        for group in groups:
            # Filter for this primary group
            group_data = data[data[group_col] == group]

            # Skip if no data for this group
            if group_data.empty:
                continue

            # Collect all trial rates
            all_rates = []

            # Process each trial
            for _, trial in group_data.iterrows():
                # Extract spike times
                spike_times = self._extract_spike_times(trial, spike_data_col, spike_data_col_key)

                if not spike_times:
                    continue

                # Filter spikes within the time window
                spike_times = [t for t in spike_times if bins[0] <= t <= bins[-1]]

                # Bin the spike times
                counts, _ = np.histogram(spike_times, bins=bins)

                # Convert to firing rate (spikes/sec)
                firing_rate = counts / self.bin_size
                all_rates.append(firing_rate)

            # Skip if no valid trials
            if not all_rates:
                continue

            # Calculate statistics
            rates_array = np.array(all_rates)
            mean_rate = np.mean(rates_array, axis=0)
            std_rate = np.std(rates_array, axis=0)

            # Get color for this group
            color = self.colors.get(group, 'gray')

            # Get display name
            display_name = self._get_display_name(group)

            # Plot mean with optional std shading
            ax.plot(bin_centers, mean_rate, color=color,
                    label=f"{display_name} (n={len(all_rates)})")

            if self.show_std:
                ax.fill_between(bin_centers, mean_rate - std_rate, mean_rate + std_rate,
                                color=color, alpha=0.2)

        # Add legend
        if groups:  # Only add legend if we have groups to show
            ax.legend(loc='best', fontsize='small')

    def _get_display_name(self, group):
        """Get the display name for a group, using custom labels if available."""
        return self.primary_group_labels.get(group, group)

    def _get_display_names(self, groups):
        """Get display names for a list of groups, using custom labels if available."""
        return [self._get_display_name(group) for group in groups]


def create_grouped_psth_module_matplotlib(
        primary_group_col: str,
        secondary_group_col: Optional[str] = None,
        filter_values: Optional[Dict[str, List[Any]]] = None,
        spike_data_col: str = 'Spikes by Channel',
        spike_data_col_key: Optional[str] = None,
        time_window: Tuple[float, float] = (-0.2, 0.5),
        bin_size: float = 0.01,
        column_groups: Optional[Dict[int, List[str]]] = None,
        figsize: Tuple[float, float] = (16, 10),
        colors: Optional[Dict[str, str]] = None,
        y_max: Optional[float] = None,
        show_std: bool = False,
        show_stimulus_onset: bool = True,
        title: Optional[str] = None,
        col_titles: Optional[List[str]] = None,
        primary_group_labels: Optional[Dict[str, str]] = None,
        secondary_group_labels: Optional[Dict[str, str]] = None,
        save_path: Optional[str] = None,
        save_svg: bool = False,
        sort_rules: Optional[Dict[str, Any]] = None,
        publish_mode: bool = False,
) -> AnalysisModule:
    """
    Create a pipeline module for grouped PSTH visualization.

    Args:
        primary_group_col: The main column to group data by (determines line colors)
        secondary_group_col: Secondary column for subgrouping (creates rows of plots)
        filter_values: Optional dict mapping column names to lists of values to include
        spike_data_col: Column containing spike timestamps
        spike_data_col_key: Optional key for extracting data if spike_data_col contains dictionaries
        time_window: Time range to analyze (start, end) in seconds
        bin_size: Size of time bins in seconds
        column_groups: Optional dict mapping column indices (0, 1, 2...) to lists of primary group values
                       to explicitly group certain values together in each column.
                       If not provided, all groups will be shown in a single column.
        figsize: Figure size (width, height) in inches
        colors: Optional dict mapping group names to colors
        y_max: Optional maximum y-axis value (will be auto-calculated if None)
        show_std: Whether to show standard deviation as shaded area
        show_stimulus_onset: Whether to show a vertical line at stimulus onset (t=0)
        title: Optional overall figure title
        col_titles: Optional custom titles for each column
        primary_group_labels: Optional custom labels for primary groups
        secondary_group_labels: Optional custom labels for secondary groups
        save_path: Optional path to save the figure
        save_svg: Whether to also save as SVG format
        sort_rules: Optional dict for sorting values with multiple options:
                    - Basic form: {"col": "column_name", "ascending": True/False}
                    - With custom function: {"col": "column_name", "custom_func": callable}

    Returns:
        Configured analysis module
    """
    if publish_mode:
        save_svg = True

    # Create the PSTH module
    psth_module = AnalysisModuleFactory.create(
        input_handler=GroupedPSTHInputHandler(
            primary_group_col=primary_group_col,
            secondary_group_col=secondary_group_col,
            filter_values=filter_values,
            spike_data_col=spike_data_col,
            spike_data_col_key=spike_data_col_key,
            column_groups=column_groups,
            sort_rules=sort_rules
        ),
        computation=GroupedPSTHComputation_matplotlib(
            time_window=time_window,
            bin_size=bin_size,
            figsize=figsize,
            colors=colors,
            y_max=y_max,
            show_std=show_std,
            show_stimulus_onset=show_stimulus_onset,
            title=title,
            col_titles=col_titles,
            primary_group_labels=primary_group_labels,
            secondary_group_labels=secondary_group_labels
        ),
        output_handler=FigureSaverOutput(
            save_path=save_path,
            save_svg=save_svg
        ),
        name="grouped_psth_visualization"
    )

    return psth_module
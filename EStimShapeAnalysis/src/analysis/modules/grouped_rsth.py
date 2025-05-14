from typing import Optional, Dict, List, Any, Tuple

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from clat.pipeline.pipeline_base_classes import ComputationModule, AnalysisModule, AnalysisModuleFactory, InputHandler
from src.analysis.modules.grouped_stims_by_response import PlotlyFigureSaverOutput


def create_psth_module(
        primary_group_col: str,
        secondary_group_col: Optional[str] = None,
        filter_values: Optional[Dict[str, List[Any]]] = None,
        spike_data_col: str = 'Spikes by Channel',
        spike_data_col_key: Optional[str] = None,
        time_window: Tuple[float, float] = (-0.2, 0.5),
        bin_size: float = 0.01,
        column_groups: Optional[Dict[int, List[str]]] = None,
        colors: Optional[Dict[str, str]] = None,
        y_max: Optional[float] = None,
        show_std: bool = False,
        show_stimulus_onset: bool = True,
        title: Optional[str] = None,
        col_titles: Optional[List[str]] = None,
        row_suffix: Optional[str] = None,
        primary_group_labels: Optional[Dict[str, str]] = None,
        secondary_group_labels: Optional[Dict[str, str]] = None,
        save_path: Optional[str] = None,
        save_html: bool = True,
        sort_rules: Optional[Dict[str, Any]] = None,
        height: int = None,
        width: int = None,
        cell_size: Optional[tuple] = None,
        template: str = "plotly_white",
        include_row_labels=None) -> AnalysisModule:
    """
    Create a pipeline module for grouped PSTH visualization using Plotly.

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
        colors: Optional dict mapping group names to colors
        y_max: Optional maximum y-axis value (will be auto-calculated if None)
        show_std: Whether to show standard deviation as shaded area
        show_stimulus_onset: Whether to show a vertical line at stimulus onset (t=0)
        title: Optional overall figure title
        col_titles: Optional custom titles for each column
        row_suffix: Optional suffix to append to row value for row titles
        primary_group_labels: Optional custom labels for primary groups
        secondary_group_labels: Optional custom labels for secondary groups
        save_path: Optional path to save the figure
        save_html: Whether to also save as interactive HTML file
        sort_rules: Optional dict for sorting values
        height: Height of the figure in pixels
        width: Width of the figure in pixels
        template: Plotly template to use (plotly_white, plotly_dark, ggplot2, etc.)

    Returns:
        Configured analysis module
    """
    # Create the Plotly PSTH module
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
        computation=PSTHComputation(
            time_window=time_window,
            bin_size=bin_size,
            colors=colors,
            y_max=y_max,
            show_std=show_std,
            show_stimulus_onset=show_stimulus_onset,
            title=title,
            col_titles=col_titles,
            row_suffix=row_suffix,
            primary_group_labels=primary_group_labels,
            secondary_group_labels=secondary_group_labels,
            cell_size=cell_size,
            height=height,
            width=width,
            template=template,
            include_row_labels=include_row_labels,
        ),
        output_handler=PlotlyFigureSaverOutput(
            save_path=save_path,
            save_html=save_html,
            save_svg=True,
            save_pdf=True,
        ),
        name="plotly_psth_visualization"
    )

    return psth_module


class PSTHComputation(ComputationModule):
    """
    Computation module that handles PSTH calculation and plotting using Plotly.

    Responsibility: PSTH calculation and interactive visualization.
    """

    def __init__(self,
                 time_window: Tuple[float, float] = (-0.2, 0.5),
                 bin_size: float = 0.01,
                 colors: Optional[Dict[str, str]] = None,
                 y_max: Optional[float] = None,
                 show_std: bool = False,
                 show_stimulus_onset: bool = True,
                 title: Optional[str] = None,
                 col_titles: Optional[List[str]] = None,
                 row_suffix: Optional[str] = None,
                 primary_group_labels: Optional[Dict[str, str]] = None,
                 secondary_group_labels: Optional[Dict[str, str]] = None,
                 height: int = None,
                 width: int = None,
                 cell_size: Tuple[int, int] = None,  # (width, height) in pixels for each subplot
                 subplot_spacing: Tuple[float, float] = (30, 30),  # (horizontal, vertical) spacing
                 template: str = "plotly_white",
                 include_row_labels=True):
        """
        Initialize the Plotly PSTH computation module.

        Args:
            time_window: Time range to analyze (start, end) in seconds
            bin_size: Size of time bins in seconds
            colors: Optional dict mapping group names to colors
            y_max: Optional maximum y-axis value (will be auto-calculated if None)
            show_std: Whether to show standard deviation as shaded area
            show_stimulus_onset: Whether to show a vertical line at stimulus onset (t=0)
            title: Optional overall figure title
            col_titles: Optional custom titles for each column
            primary_group_labels: Optional custom labels for primary groups
            secondary_group_labels: Optional custom labels for secondary groups
            height: Height of the figure in pixels
            width: Width of the figure in pixels
            template: Plotly template to use
        """
        self.include_row_labels = include_row_labels
        self.time_window = time_window
        self.bin_size = bin_size
        self.colors = colors or {}
        self.y_max = y_max
        self.show_std = show_std
        self.show_stimulus_onset = show_stimulus_onset
        self.title = title
        self.y_axis_title = "Response Rate (spikes/s)"
        self.col_titles = col_titles
        self.row_suffix = row_suffix
        self.primary_group_labels = primary_group_labels or {}
        self.secondary_group_labels = secondary_group_labels or {}
        self.cell_size = cell_size
        self.subplot_spacing = subplot_spacing
        self.template = template

        # Calculate figure dimensions based on cell size
        self.height = height
        self.width = width


    def compute(self, prepared_data: Dict[str, Any]) -> go.Figure:
        """
        Compute PSTHs from prepared data and visualize them using Plotly.

        Args:
            prepared_data: Output from the input handler

        Returns:
            Plotly figure with the PSTH plots
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

        # Create time bins
        start_time, end_time = self.time_window
        bins = np.arange(start_time, end_time + self.bin_size, self.bin_size)
        bin_centers = bins[:-1] + self.bin_size / 2

        # Determine layout
        n_rows = max(1, len(secondary_groups) if secondary_groups else 1)

        # Define colors if not provided
        if not self.colors:
            # Generate colors using Plotly's colorscales
            from plotly.colors import qualitative
            color_scale = qualitative.Plotly if len(primary_groups) <= 10 else qualitative.Dark24

            # Ensure we have enough colors
            if len(primary_groups) > len(color_scale):
                import plotly.express as px
                # Generate a custom colorscale with enough colors
                color_scale = px.colors.sample_colorscale(
                    "turbo", len(primary_groups)
                )

            for i, group in enumerate(primary_groups):
                self.colors[group] = color_scale[i % len(color_scale)]

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

        # Determine global y-axis range
        global_y_max = self.y_max if self.y_max is not None else max(max_rates) * 1.1 if max_rates else 1.0
        global_y_min = min(0, min(min_rates)) if min_rates else 0

        # Calculate figure dimensions based on cell size
        cell_width, cell_height = self.cell_size

        # Extra space for title, label
        # s, legend, etc.
        title_space = 80 if self.title else 30
        legend_space = 150  # Space for legend on right side
        axis_labels_space = 300  # Space for axis labels
        row_label_space = 500

        # Calculate horizontal and vertical spacing in pixels
        horiz_spacing_px = self.subplot_spacing[0]
        vert_spacing_px = self.subplot_spacing[1]

        # Calculate total figure dimensions
        figure_width = (n_columns * cell_width) + (
                    (n_columns - 1) * horiz_spacing_px) + legend_space + axis_labels_space + row_label_space
        figure_height = (n_rows * cell_height) + ((n_rows - 1) * vert_spacing_px) + title_space + axis_labels_space

        # Use provided dimensions if specified
        if self.width is not None:
            figure_width = self.width
        if self.height is not None:
            figure_height = self.height

        # Create column titles only for the first row
        subplot_titles = []
        for i in range(n_columns):
            title = self.col_titles[i] if self.col_titles and i < len(
                self.col_titles) else f"Groups: {', '.join(self._get_display_names(column_primary_groups.get(i, [])))}"
            subplot_titles.append(title)

        # Add empty strings for the remaining cells
        for i in range(n_columns * (n_rows - 1)):
            subplot_titles.append("")

        # Create figure with subplots
        fig = make_subplots(
            rows=n_rows,
            cols=n_columns,
            shared_xaxes=True,
            shared_yaxes=True,
        )

        # Manually set domain for each subplot to ensure exact sizing
        total_width = figure_width
        total_height = figure_height

        # Calculate actual pixel-to-domain ratio
        width_ratio = cell_width / total_width
        height_ratio = cell_height / total_height

        # Spacing in domain coordinates
        h_space = self.subplot_spacing[0] / total_width
        v_space = self.subplot_spacing[1] / total_height

        # Set exact domain for each subplot
        for row_idx in range(n_rows):
            for col_idx in range(n_columns):
                # Calculate domain coordinates for each cell
                x_start = (col_idx * (width_ratio + h_space)) + (row_label_space / total_width)
                x_end = x_start + width_ratio

                y_end = 1 - (row_idx * (height_ratio + v_space)) - (title_space / total_height)
                y_start = y_end - height_ratio

                # Update the subplot domains
                fig.update_xaxes(domain=[x_start, x_end], row=row_idx + 1, col=col_idx + 1)
                fig.update_yaxes(domain=[y_start, y_end], row=row_idx + 1, col=col_idx + 1)

        fig.update_annotations(font_size=36)

        # Plot PSTHs for each secondary group and column
        for row_idx, secondary_value in enumerate(secondary_groups or [None]):
            if secondary_group_col and secondary_value is not None:
                # Get data for this secondary group
                if secondary_group_col and secondary_value is not None:
                    secondary_data = data[data[secondary_group_col] == secondary_value]
                else:
                    secondary_data = data
                # Add a common y-axis title that appears once
                y_axis_title = "Spike Rate"  # You can make this a parameter in your class
                fig.update_yaxes(
                    title_text=y_axis_title,
                    title_font=dict(size=36),
                    row=row_idx+1,
                    col=1
                )

                # ADD ROW LABELS
                if self.include_row_labels:
                    display_name = self.secondary_group_labels.get(secondary_value, secondary_value)
                    row_label = f"{display_name}{' ' + self.row_suffix if self.row_suffix else ''}"

                    y_domain = fig.get_subplot(row=row_idx + 1, col=1).yaxis.domain

                    # Calculate the center of the domain for this row
                    y_position = (y_domain[0] + y_domain[1]) / 2

                    # Add left-side row label as annotation
                    fig.add_annotation(
                        text=row_label,
                        x=-0.005,  # Position to the left of the plot area
                        y=y_position,  # Middle of the row
                        xref="paper",
                        yref="paper",
                        showarrow=False,
                        font=dict(size=36),
                        textangle=0,  # Horizontal text
                        xanchor="right",
                        yanchor="middle"
                    )

            # Process each column
            for col_idx in range(n_columns):
                # Get groups for this column
                col_groups = column_primary_groups.get(col_idx, [])

                if not col_groups:
                    # Skip empty columns
                    continue

                # Plot this column's groups
                self._calculate_and_plot_psth(
                    fig,
                    secondary_data,
                    primary_group_col,
                    col_groups,
                    spike_data_col,
                    spike_data_col_key,
                    bins,
                    bin_centers,
                    row_idx + 1,
                    col_idx + 1
                )

                # Add x-axis label on bottom row only
                if row_idx == n_rows - 1:
                    fig.update_xaxes(title_text="Time (s)", row=row_idx + 1, col=col_idx + 1, )

                # Draw stimulus onset line if requested
                if self.show_stimulus_onset:
                    if start_time <= 0 <= end_time:
                        fig.add_vline(
                            x=0,
                            line=dict(color="black", width=1, dash="dash"),
                            row=row_idx + 1,
                            col=col_idx + 1
                        )

        # Update layout
        fig.update_layout(
            margin=dict(l=row_label_space),
            title={
                'text': self.title,
                'font': dict(size=36),
                'xanchor': 'center',
                'x': 0.5,
            },
            showlegend=True,
            legend_title_text=primary_group_col,
            legend_title_font=dict(size=36),
            legend_font=dict(size=36),
            height=figure_height,
            width=figure_width,
            yaxis_range=[global_y_min, global_y_max],
        )

        fig.update_traces(line=dict(width=4),)

        # Update all axes for consistent look and feel
        fig.update_xaxes(
            gridcolor='lightgray',
            zerolinecolor='gray',
            zerolinewidth=1,
            title_font=dict(size=36),
            tickfont=dict(size=36),
        )

        fig.update_yaxes(
            gridcolor='lightgray',
            zerolinecolor='gray',
            zerolinewidth=1,
            range=[global_y_min, global_y_max],
            title_font=dict(size=36),
            tickfont= dict(size=36),
        )

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

    def _calculate_and_plot_psth(self, fig, data, group_col, groups,
                                 spike_data_col, spike_data_col_key,
                                 bins, bin_centers, row, col):
        """
        Calculate and plot PSTH for a group of data using Plotly.
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

            # Plot mean
            fig.add_trace(
                go.Scatter(
                    x=bin_centers,
                    y=mean_rate,
                    mode='lines',
                    name=f"{display_name} (n={len(all_rates)})",
                    line=dict(color=color, width=2),
                    legendgroup=display_name,
                    # Show in legend for first appearance in any column
                    showlegend=(row == 1 and not any(data[data[group_col] == group].empty for i in range(col - 1))),
                    hovertemplate="Time: %{x:.3f}s<br>Rate: %{y:.2f} spikes/s<extra></extra>"
                ),
                row=row,
                col=col
            )

            # Add standard deviation if requested
            if self.show_std:
                fig.add_trace(
                    go.Scatter(
                        x=np.concatenate([bin_centers, bin_centers[::-1]]),
                        y=np.concatenate([mean_rate + std_rate, (mean_rate - std_rate)[::-1]]),
                        fill='toself',
                        fillcolor=f'rgba({",".join(str(int(c * 255)) for c in go.colors.hex_to_rgb(color))},0.2)',
                        line=dict(color='rgba(0,0,0,0)'),
                        showlegend=False,
                        hoverinfo='skip',
                        legendgroup=display_name,
                    ),
                    row=row,
                    col=col
                )

    def _get_display_name(self, group):
        """Get the display name for a group, using custom labels if available."""
        return self.primary_group_labels.get(group, group)

    def _get_display_names(self, groups):
        """Get display names for a list of groups, using custom labels if available."""
        return [self._get_display_name(group) for group in groups]


class GroupedPSTHInputHandler(InputHandler):
    """
    Input handler that filters and prepares data for PSTH visualization.

    Responsibility: Data filtering and organization for further computation.
    """

    def __init__(self,
                 primary_group_col: str,
                 secondary_group_col: Optional[str] = None,
                 filter_values: Optional[Dict[str, List[Any]]] = None,
                 spike_data_col: str = None,
                 spike_data_col_key: Optional[str] = None,
                 column_groups: Optional[Dict[int, List[Any]]] = None,
                 sort_rules: Optional[Dict[str, Any]] = None):
        """
        Initialize the PSTH input handler.

        Args:
            primary_group_col: The main column to group data by (creates different lines)
            secondary_group_col: Secondary column for subgrouping (creates rows of plots)
            filter_values: Optional dict mapping column names to values to include
            spike_data_col: Column containing spike timestamps
            spike_data_col_key: Optional key for extracting data if spike_data_col contains dictionaries
            column_groups: Optional dict mapping column indices (0, 1, 2...) to lists of primary_group_col values
                           to explicitly group certain values together in each column.
                           If not provided, all groups will be shown in a single column.
            sort_rules: Optional dict for sorting values with multiple options:
                - Basic form: {"col": "column_name", "ascending": True/False}
                - With custom function: {"col": "column_name", "custom_func": callable}
                  The custom_func will receive: (values_to_sort, dataframe, column_name)
        """
        self.primary_group_col = primary_group_col
        self.secondary_group_col = secondary_group_col
        self.filter_values = filter_values or {}
        self.spike_data_col = spike_data_col
        self.spike_data_col_key = spike_data_col_key
        self.column_groups = column_groups or {}
        self.sort_rules = sort_rules or {}
        self.filtered_data = None  # Will store filtered DataFrame for use in sorting functions

    def prepare(self, compiled_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Filter and organize compiled data for PSTH visualization.
        """
        # Apply any filters
        filtered_data = compiled_data.copy()
        for col, values in self.filter_values.items():
            if col in filtered_data.columns:
                filtered_data = filtered_data[filtered_data[col].isin(values)]

        # Store filtered data for use in sorting functions
        self.filtered_data = filtered_data.copy()

        # Verify required columns exist
        if self.primary_group_col not in filtered_data.columns:
            raise ValueError(f"Primary grouping column '{self.primary_group_col}' not found in data")

        if self.spike_data_col not in filtered_data.columns:
            raise ValueError(f"Spike data column '{self.spike_data_col}' not found in data")

        # Get ordered primary groups
        all_primary_groups = filtered_data[self.primary_group_col].unique()
        if self.primary_group_col in self.filter_values:
            primary_groups = [g for g in self.filter_values[self.primary_group_col]
                              if g in all_primary_groups]
        else:
            primary_groups = sorted(all_primary_groups)

        # Get ordered secondary groups
        secondary_groups = []
        if self.secondary_group_col and self.secondary_group_col in filtered_data.columns:
            all_secondary_groups = filtered_data[self.secondary_group_col].unique()
            if self.secondary_group_col in self.filter_values:
                secondary_groups = [g for g in self.filter_values[self.secondary_group_col]
                                    if g in all_secondary_groups]
            else:
                secondary_groups = sorted(all_secondary_groups)

        # Get unique values for each grouping dimension with optional sorting
        # Using same pattern as GroupedStimuliInputHandler
        if self.sort_rules and "col" in self.sort_rules:
            sort_col = self.sort_rules["col"]
            custom_func = self.sort_rules.get("custom_func")
            ascending = self.sort_rules.get("ascending", True)

            if custom_func and callable(custom_func):
                # Apply custom sorting function
                if sort_col == self.primary_group_col:
                    primary_groups = self._get_sorted_values(filtered_data, self.primary_group_col)
                elif sort_col == self.secondary_group_col:
                    secondary_groups = self._get_sorted_values(filtered_data, self.secondary_group_col)
            else:
                # Standard sorting
                if sort_col == self.primary_group_col:
                    primary_groups = sorted(primary_groups, reverse=not ascending)
                elif sort_col == self.secondary_group_col:
                    secondary_groups = sorted(secondary_groups, reverse=not ascending)

        # Handle column grouping
        column_primary_groups = {}
        if self.column_groups:
            # If column groups are explicitly defined, use them
            for col_idx, group_list in self.column_groups.items():
                # Only include groups that actually exist in the filtered data
                column_primary_groups[col_idx] = [g for g in group_list if g in primary_groups]

            # Check for any groups that weren't assigned to a column
            assigned_groups = set()
            for groups in column_primary_groups.values():
                assigned_groups.update(groups)

            unassigned = [g for g in primary_groups if g not in assigned_groups]
            if unassigned:
                print(
                    f"Warning: The following groups were not assigned to any column and will not be plotted: {unassigned}")
        else:
            # Default behavior: everything in a single column (index 0)
            column_primary_groups[0] = primary_groups

        # Determine number of columns from column_groups
        n_columns = max(column_primary_groups.keys()) + 1 if column_primary_groups else 1

        return {
            'data': filtered_data,
            'primary_group_col': self.primary_group_col,
            'secondary_group_col': self.secondary_group_col,
            'spike_data_col': self.spike_data_col,
            'spike_data_col_key': self.spike_data_col_key,
            'primary_groups': primary_groups,
            'secondary_groups': secondary_groups,
            'column_primary_groups': column_primary_groups,
            'n_columns': n_columns
        }

    def _get_sorted_values(self, data: pd.DataFrame, col_name: Optional[str]) -> List[Any]:
        """
        Get unique values for a column with optional sorting.

        This method follows the same pattern as in the grouped_stims_by_response module
        to maintain consistency across modules.

        Args:
            data: DataFrame containing the data
            col_name: Name of the column to get unique values from

        Returns:
            List of unique values, potentially sorted
        """
        if not col_name or col_name not in data.columns:
            return []

        unique_values = list(data[col_name].unique())

        # Check if we need to sort this column
        if self.sort_rules and self.sort_rules.get("col") == col_name:
            custom_func = self.sort_rules.get("custom_func")
            ascending = self.sort_rules.get("ascending", True)

            if custom_func and callable(custom_func):
                # Before calling the custom function, create a copy of the data for sorting
                filtered_data_for_sorting = self.filtered_data.copy()

                # The custom sorting function might reference a different column for its calculations
                # (e.g., SortingUtils.by_avg_value uses a 'column' parameter)
                # We need to process that column if it contains dictionaries

                # We'll need to check all columns that might contain dictionaries
                for check_col in filtered_data_for_sorting.columns:
                    if len(filtered_data_for_sorting) > 0:
                        first_val = filtered_data_for_sorting[check_col].iloc[0]
                        # If this column contains dictionaries, extract the value using spike_data_col_key
                        if isinstance(first_val, dict) and self.spike_data_col_key:
                            # Create a temporary column with extracted values
                            filtered_data_for_sorting[check_col] = filtered_data_for_sorting[check_col].apply(
                                lambda x: x.get(self.spike_data_col_key, 0)
                                if isinstance(x, dict) and self.spike_data_col_key in x else x
                            )

                return custom_func(unique_values, filtered_data_for_sorting, col_name)
            else:
                # Standard sorting
                return sorted(unique_values, reverse=not ascending)

        # If no sort rules matched or no sort_rules provided
        if col_name in self.filter_values:
            # If we have filter values for this column, use their order
            return [v for v in self.filter_values[col_name] if v in unique_values]
        else:
            # Default to standard sorting
            return sorted(unique_values)

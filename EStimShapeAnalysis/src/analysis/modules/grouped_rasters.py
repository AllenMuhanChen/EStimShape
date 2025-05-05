import itertools

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.gridspec import GridSpec
from typing import Dict, List, Any, Optional, Tuple, Union

# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    InputHandler, ComputationModule, OutputHandler, AnalysisModule,
    AnalysisPipeline, create_pipeline, create_branch,
    AnalysisModuleFactory
)


class GroupedRasterInputHandler(InputHandler):
    """
    Input handler that filters and prepares data for raster plot visualization.

    Responsibility: Data filtering and basic organization only.
    """

    def __init__(self,
                 primary_group_col: str,
                 secondary_group_col: Optional[str] = None,
                 filter_values: Optional[Dict[str, List[Any]]] = None,
                 spike_data_col: str = 'Spikes by Channel',
                 spike_data_col_key: str = None):
        """
        Initialize the raster input handler.

        Args:
            primary_group_col: The main column to group data by
            secondary_group_col: Optional column for subgrouping
            filter_values: Optional dict mapping column names to values to include
            spike_data_col: Column containing spike timestamps
        """
        self.primary_group_col = primary_group_col
        self.secondary_group_col = secondary_group_col
        self.filter_values = filter_values or {}
        self.spike_data_col = spike_data_col
        self.spike_data_col_key = spike_data_col_key

    def prepare(self, compiled_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Filter and organize compiled data for visualization.
        """
        # Apply any filters
        filtered_data = compiled_data.copy()
        for col, values in self.filter_values.items():
            if col in filtered_data.columns:
                filtered_data = filtered_data[filtered_data[col].isin(values)]

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

        # If spike_data_col data is a dict and spike_data_col_key is provided, extract the relevant data
        if isinstance(filtered_data[self.spike_data_col].iloc[0], dict) and self.spike_data_col_key:
            filtered_data[self.spike_data_col] = filtered_data[self.spike_data_col].apply(
                lambda x: x[self.spike_data_col_key] if self.spike_data_col_key in x else None
            )


        # Simple result structure - just the filtered data and configuration
        return {
            'data': filtered_data,
            'primary_group_col': self.primary_group_col,
            'secondary_group_col': self.secondary_group_col,
            'spike_data_col': self.spike_data_col,
            'primary_groups': primary_groups,
            'filter_values': self.filter_values
        }


class GroupedRasterPlotter(ComputationModule):
    """
    Computation module that handles both layout calculation and plotting.

    Responsibility: All visualization logic from layout to actual plotting.
    """

    def __init__(self,
                 equal_group_heights: bool = False,
                 figsize: Tuple[float, float] = (15, 10),
                 time_range: Tuple[float, float] = (-0.2, 0.7),
                 spike_color: str = 'black',
                 title: Optional[str] = None,):
        """
        Initialize the raster visualization module.

        Args:
            equal_group_heights: If True, all groups get equal height
            figsize: Figure size (width, height) in inches
            time_range: Time range to display (min, max) in seconds
            spike_color: Color for spike markers
        """
        self.equal_group_heights = equal_group_heights
        self.figsize = figsize
        self.time_range = time_range
        self.spike_color = spike_color
        self.title = title

    def compute(self, prepared_data: Dict[str, Any]) -> plt.Figure:
        """
        Compute the visualization from prepared data.

        Args:
            prepared_data: Output from the input handler

        Returns:
            Matplotlib figure with the raster plot
        """
        # Extract data and configuration
        data = prepared_data['data']
        primary_group_col = prepared_data['primary_group_col']
        secondary_group_col = prepared_data['secondary_group_col']
        spike_data_col = prepared_data['spike_data_col']
        primary_groups = prepared_data['primary_groups']
        filter_values = prepared_data['filter_values']

        # Calculate layout information for each group
        group_layouts = {}
        for group in primary_groups:
            group_data = data[data[primary_group_col] == group]
            group_layouts[group] = self._calculate_layout(
                group_data,
                secondary_group_col,
                filter_values
            )

        # Calculate height ratios
        if self.equal_group_heights:
            height_ratios = [1] * len(primary_groups)
        else:
            height_ratios = [max(1, layout['total_height'])
                             for group, layout in group_layouts.items()]

        # Create the figure
        fig = plt.figure(figsize=self.figsize)
        gs = GridSpec(len(primary_groups), 1, height_ratios=height_ratios)

        # Create and populate each subplot
        for i, group in enumerate(primary_groups):
            ax = fig.add_subplot(gs[i])
            self._plot_group(
                ax=ax,
                layout=group_layouts[group],
                title=f"{primary_group_col}: {group}",
                spike_data_col=spike_data_col,
                secondary_group_col=secondary_group_col
            )
        if self.title:
            fig.suptitle(self.title, fontsize=16)
        plt.tight_layout()
        return fig

    def _calculate_layout(self,
                          group_data: pd.DataFrame,
                          secondary_group_col: Optional[str],
                          filter_values: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        Calculate layout information for a single group.
        """
        current_y = 0
        secondary_groups = []
        secondary_positions = {}
        trial_positions = {}

        # If we have a secondary grouping column
        if secondary_group_col and secondary_group_col in group_data.columns:
            # Get ordered secondary groups
            all_secondary_values = group_data[secondary_group_col].unique()
            if secondary_group_col in filter_values:
                secondary_groups = [g for g in filter_values[secondary_group_col]
                                    if g in all_secondary_values]
            else:
                secondary_groups = sorted(all_secondary_values)

            # Calculate positions for each secondary group
            for secondary_value in secondary_groups:
                secondary_data = group_data[group_data[secondary_group_col] == secondary_value]
                trial_count = len(secondary_data)

                # Skip empty groups
                if trial_count == 0:
                    continue

                # Store positions for trials in this group
                trial_positions[secondary_value] = []
                for i in range(trial_count):
                    trial_positions[secondary_value].append(current_y)
                    current_y += 1

                # Store center position for this secondary group
                secondary_positions[secondary_value] = current_y - trial_count / 2
                current_y += 1  # Add space between groups
        else:
            # No secondary grouping, just store trial positions
            trial_count = len(group_data)
            trial_positions['all'] = list(range(trial_count))
            current_y = trial_count

        return {
            'data': group_data,
            'secondary_groups': secondary_groups,
            'secondary_positions': secondary_positions,
            'trial_positions': trial_positions,
            'total_height': current_y
        }

    def _plot_group(self,
                    ax: plt.Axes,
                    layout: Dict[str, Any],
                    title: str,
                    spike_data_col: str,
                    secondary_group_col: Optional[str] = None):
        """
        Plot a group's raster plot on the given axes.
        """
        data = layout['data']
        secondary_groups = layout['secondary_groups']
        secondary_positions = layout['secondary_positions']
        trial_positions = layout['trial_positions']

        # Plot with secondary grouping if available
        if secondary_groups and secondary_group_col:
            for secondary_value in secondary_groups:
                # Get data for this secondary group
                secondary_data = data[data[secondary_group_col] == secondary_value]

                # Skip if no trial positions for this group
                if secondary_value not in trial_positions:
                    continue

                # Plot each trial
                for i, (_, trial) in enumerate(secondary_data.iterrows()):
                    if i >= len(trial_positions[secondary_value]):
                        continue  # Skip if index out of range

                    # Plot spike times for this trial
                    y_pos = trial_positions[secondary_value][i]
                    spikes_by_channel = trial[spike_data_col]

                    if isinstance(spikes_by_channel, dict):
                        color_iterator = spike_color_iterator()
                        for channel, spike_times in spikes_by_channel.items():
                            color = next(color_iterator)
                            ax.vlines(spike_times, y_pos, y_pos + 0.9,
                                      color=color, lw=0.5)

                    elif isinstance(spikes_by_channel, list):
                        for spike_time in spikes_by_channel:
                            ax.vlines(spike_time, y_pos, y_pos + 0.9,
                                      color=self.spike_color, lw=0.5)

                # Add label for this secondary group
                if secondary_value in secondary_positions:
                    ax.text(1.02, secondary_positions[secondary_value],
                            f'{secondary_value}', transform=ax.get_yaxis_transform(),
                            verticalalignment='center', fontsize=8)
        else:
            # No secondary grouping, plot all trials
            for i, (_, trial) in enumerate(data.iterrows()):
                y_pos = trial_positions.get('all', [i])[i]

                # Plot spike times
                if spike_data_col in trial and trial[spike_data_col]:
                    spikes_by_channel = trial[spike_data_col]
                    for channel, spike_times in spikes_by_channel.items():
                        ax.vlines(spike_times, y_pos, y_pos + 0.9,
                                  color=self.spike_color, lw=0.5)

        # Configure axes
        ax.set_title(title)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Trials')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Set limits
        ax.set_ylim(-0.5, layout['total_height'] + 0.5)
        ax.set_xlim(*self.time_range)

def spike_color_iterator():
    # Need 32 colors
    # Generate a list of colors
    colors = plt.cm.viridis(np.linspace(0, 1, 32))
    # conver tot list
    colors = [tuple(color) for color in colors]
    return itertools.cycle(colors)

class GroupedRasterOutput(OutputHandler):
    """
    Output handler that handles saving the figure.

    Responsibility: Saving the figure and returning the result.
    """

    def __init__(self, save_path: Optional[str] = None):
        """
        Initialize the output handler.

        Args:
            save_path: Optional path to save the figure
        """
        self.save_path = save_path

    def process(self, figure: plt.Figure) -> plt.Figure:
        """
        Process the figure (save if requested).

        Args:
            figure: The matplotlib figure from the computation module

        Returns:
            The same figure, unchanged
        """
        # Save if requested
        if self.save_path:
            figure.savefig(self.save_path, dpi=300, bbox_inches='tight')

        return figure


def create_grouped_raster_module(
        primary_group_col: str,
        secondary_group_col: Optional[str] = None,
        filter_values: Optional[Dict[str, List[Any]]] = None,
        spike_data_col: str = 'Spikes by Channel',
        spike_data_col_key: str = None,
        equal_group_heights: bool = False,
        figsize: Tuple[float, float] = (15, 10),
        time_range: Tuple[float, float] = (-0.2, 0.7),
        save_path: Optional[str] = None,
        title: Optional[str] = None
) -> AnalysisModule:
    """
    Create a pipeline for grouped raster plots.

    The order of plots will match the order specified in filter_values if provided.

    Args:
        primary_group_col: The main column to group by (creates separate subplots)
        secondary_group_col: Optional column for subgrouping within each primary group
        filter_values: Optional dict mapping column names to lists of values to include
        spike_data_col: Column containing the spike timestamp dictionaries
        equal_group_heights: If True, all groups get equal height
        figsize: Figure size (width, height) in inches
        time_range: Time range to display (min, max) in seconds
        save_path: Optional path to save the figure

    Returns:
        Configured analysis pipeline
    """
    # Create the raster plot module
    raster_plot_module = AnalysisModuleFactory.create(
        input_handler=GroupedRasterInputHandler(
            primary_group_col=primary_group_col,
            secondary_group_col=secondary_group_col,
            filter_values=filter_values,
            spike_data_col=spike_data_col,
            spike_data_col_key=spike_data_col_key
        ),
        computation=GroupedRasterPlotter(
            equal_group_heights=equal_group_heights,
            figsize=figsize,
            time_range=time_range,
            title=title
        ),
        output_handler=GroupedRasterOutput(
            save_path=save_path
        ),
        name="grouped_raster_plot"
    )

    return raster_plot_module

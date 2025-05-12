import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    InputHandler, ComputationModule, OutputHandler, AnalysisModule,
    AnalysisModuleFactory
)


class GroupedStimuliInputHandler(InputHandler):
    """
    Input handler that filters and prepares data for grouped stimuli visualization.

    Will automatically compute aggregated dataframe by averaging all rows' response_col that have the same
    path_col value.

    if filter_values are provided, only the rows that match the filter values will be included in the output.
    if sort_rules are provided, the data will be sorted according to the specified rules.
    """

    def __init__(self,
                 response_col: str,
                 path_col: str,
                 row_col: Optional[str] = None,
                 response_key: Optional[str] = None,
                 col_col: Optional[str] = None,
                 subgroup_col: Optional[str] = None,
                 filter_values: Optional[Dict[str, List[Any]]] = None,
                 sort_rules: Optional[Dict[str, Any]] = None
                 ):
        """
        Initialize the grouped stimuli input handler.

        Args:
            response_col: Column containing response values
            path_col: Column containing paths to stimulus images
            row_col: Optional column for grouping stimuli into rows
            response_key: Optional key to extract from response_col if it contains a dictionary
            col_col: Optional column for grouping stimuli into columns
            subgroup_col: Optional column for subgrouping stimuli
            filter_values: Optional dict mapping column names to lists of values to include
            sort_rules: Optional dict for sorting values with multiple options:
                - Basic form: {"col": "column_name", "ascending": True/False}
                - With custom function: {"col": "column_name", "custom_func": callable}
                  The custom_func will receive: (values_to_sort, dataframe, column_name)
        """
        self.response_col = response_col
        self.response_key = response_key
        self.path_col = path_col
        self.row_col = row_col
        self.col_col = col_col
        self.subgroup_col = subgroup_col
        self.filter_values = filter_values or {}
        self.sort_rules = sort_rules or {}
        self.filtered_data = None  # Will store filtered DataFrame for use in sorting functions

    def prepare(self, compiled_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Filter, sort, and organize compiled data for visualization.
        """
        # Apply any filters
        filtered_data = compiled_data.copy()
        for col, filter_value in self.filter_values.items():
            if col in filtered_data.columns:
                filtered_data = filtered_data[filtered_data[col].isin(filter_value)]

        # Store filtered data for use in sorting functions
        self.filtered_data = filtered_data.copy()

        # Verify required columns exist
        required_cols = [self.response_col, self.path_col]
        for col in [self.row_col, self.col_col, self.subgroup_col]:
            if col is not None:
                required_cols.append(col)

        for col in required_cols:
            if col not in filtered_data.columns:
                raise ValueError(f"Required column '{col}' not found in data")

        # If response_col data is a dict and response_key is provided, extract the data
        if isinstance(filtered_data[self.response_col].iloc[0], dict) and self.response_key:
            filtered_data[self.response_col] = filtered_data[self.response_col].apply(
                lambda x: x[self.response_key] if isinstance(x, dict) and self.response_key in x else 0
            )

        # Get unique values for each grouping dimension with optional sorting
        row_values = self._get_sorted_values(filtered_data, self.row_col)
        col_values = self._get_sorted_values(filtered_data, self.col_col)
        subgroup_values = self._get_sorted_values(filtered_data, self.subgroup_col)

        if self.subgroup_col and subgroup_values:
            print(f"Found {len(subgroup_values)} subgroup values: {subgroup_values}")

        return {
            'data': filtered_data,
            'response_col': self.response_col,
            'path_col': self.path_col,
            'row_col': self.row_col,
            'col_col': self.col_col,
            'subgroup_col': self.subgroup_col,
            'row_values': row_values,
            'col_values': col_values,
            'subgroup_values': subgroup_values,
            'filter_values': self.filter_values
        }

    def _get_sorted_values(self, data: pd.DataFrame, col_name: Optional[str]) -> List[Any]:
        """
        Get unique values for a column with optional sorting.

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
            # Handle custom sort function that can access any column in the dataframe
            custom_func = self.sort_rules.get("custom_func")
            ascending = self.sort_rules.get("ascending", True)

            if custom_func and callable(custom_func):
                # Before calling the custom function, make sure we've extracted response values
                # if needed to prevent dict comparison errors in the sorting functions
                filtered_data_for_sorting = self.filtered_data.copy()

                # Check for dictionary values in the column used for sorting metrics
                # (typically the response column)
                if self.response_col in filtered_data_for_sorting.columns:
                    first_value = filtered_data_for_sorting[self.response_col].iloc[
                        0] if not filtered_data_for_sorting.empty else None
                    if isinstance(first_value, dict) and self.response_key is not None:
                        # Create a copy with extracted values for sorting
                        filtered_data_for_sorting[self.response_col] = filtered_data_for_sorting[
                            self.response_col].apply(
                            lambda x: x.get(self.response_key, 0) if isinstance(x, dict) and self.response_key else 0
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


class GroupedStimuliPlotter(ComputationModule):
    """
    Computation module that handles layout calculation and plotting of grouped stimuli.
    """

    def __init__(self,
                 figsize: Tuple[float, float] = (15, 10),
                 cell_size: Tuple[float, float] = (3, 3),
                 border_width: int = 5,
                 normalize_method: str = 'global',
                 min_response: Optional[float] = None,
                 max_response: Optional[float] = None,
                 color_mode: str = 'intensity',
                 title: Optional[str] = None):
        """
        Initialize the grouped stimuli visualization module.
        """
        self.figsize = figsize
        self.cell_size = cell_size
        self.border_width = border_width
        self.normalize_method = normalize_method
        self.min_response = min_response
        self.max_response = max_response
        self.color_mode = color_mode
        self.title = title

    def compute(self, prepared_data: Dict[str, Any]) -> plt.Figure:
        """
        Compute the visualization from prepared data with separate grids for each subgroup.
        """
        # Extract data and configuration
        data = prepared_data['data']
        response_col = prepared_data['response_col']
        path_col = prepared_data['path_col']
        row_col = prepared_data['row_col']
        col_col = prepared_data['col_col']
        subgroup_col = prepared_data['subgroup_col']
        row_values = prepared_data['row_values']
        col_values = prepared_data['col_values']
        subgroup_values = prepared_data['subgroup_values']

        # Default to single row/column if not specified
        if not row_values:
            row_values = [None]
        if not col_values:
            col_values = [None]
        if not subgroup_values:
            subgroup_values = [None]

        # Normalize responses globally
        min_val, max_val = self._normalize_global(data, response_col)

        # Create a figure with multiple subplots - one grid per subgroup
        nrows = len(subgroup_values)
        ncols = 1  # One column of grids

        # Calculate the size for each grid
        single_grid_height = len(row_values) * self.cell_size[1]
        single_grid_width = len(col_values) * self.cell_size[0]

        # Total figure size
        fig_height = nrows * (single_grid_height) + 1.5  # Extra space for titles
        fig_width = single_grid_width + 2  # Extra space for labels

        # Create figure
        fig = plt.figure(figsize=(fig_width, fig_height))
        if self.title:
            fig.suptitle(self.title, fontsize=16)

        # Create one grid for each subgroup
        for sg_idx, subgroup_value in enumerate(subgroup_values):
            # Calculate safer grid positions
            total_grids = len(subgroup_values)
            grid_height = 0.8 / total_grids  # Allow 20% of figure for margins and titles

            # Position from top to bottom with fixed spacing
            top_pos = 0.95 - (sg_idx * (grid_height + 0.05))
            bottom_pos = top_pos - grid_height

            # Ensure bottom < top with a minimum separation
            if bottom_pos >= top_pos - 0.05:
                bottom_pos = top_pos - 0.05

            # Create a subgrid for this subgroup

            subgrid = fig.add_gridspec(nrows=len(row_values), ncols=len(col_values),
                                       left=0.1, bottom=bottom_pos,
                                       right=0.9, top=top_pos,
                                       wspace=0.05, hspace=-0.30)

            # Add a title for this subgroup's grid
            if subgroup_col and subgroup_value is not None:
                fig.text(0.5, top_pos + 0.02,
                         f"{subgroup_col}: {subgroup_value}",
                         ha='center', fontsize=14)

            # Plot each cell in this grid - order of data in row_values and col_values matters
            bboxs_for_rows = []
            for row_idx, row_value in enumerate(row_values):
                for col_idx, col_value in enumerate(col_values):
                    # Filter data for this specific cell
                    cell_data = data.copy()

                    # Get all data for this row
                    if row_col is not None and row_value is not None:
                        cell_data = cell_data[cell_data[row_col] == row_value]

                    # Filter down to data that matches row AND column
                    if col_col is not None and col_value is not None:
                        cell_data = cell_data[cell_data[col_col] == col_value]

                    # Filter down to data that matches row, column AND subgroup
                    if subgroup_col is not None and subgroup_value is not None:
                        cell_data = cell_data[cell_data[subgroup_col] == subgroup_value]

                    # Create subplot for this cell
                    ax = fig.add_subplot(subgrid[row_idx, col_idx])

                    print(f"Subplot position: {ax.get_position()}")
                    # Plot the image for this cell
                    self._plot_cell(ax, cell_data, response_col, path_col, min_val, max_val)

                    # Set column label
                    if row_idx == 0 and col_col:
                        ax.set_title(f"{col_col}: {col_value}", fontsize=10, pad=0)

                    # Add row label
                    if col_idx == 0 and row_col and row_value is not None:
                        row_center = (ax.get_position().y0 + ax.get_position().y1) / 2
                        fig.text(0.09, row_center, f"{row_value}", ha='right', va='center', fontsize=12)



        return fig

    # Calculate dynamic figure size based on data grid dimensions
    def calculate_dynamic_figsize(self, data, row_col, col_col, cell_size=(2, 2), margin=0.5):
        # Get number of unique row and column values
        n_rows = data[row_col].nunique()
        n_cols = data[col_col].nunique()

        # Calculate minimum viable figure size with margins
        width = (n_cols * cell_size[0]) + margin * 2
        height = (n_rows * cell_size[1]) + margin * 2

        # Ensure figure size is never smaller than 6x4
        width = max(width, 6)
        height = max(height, 4)

        return (width, height)

    def _normalize_global(self, data: pd.DataFrame, response_col: str) -> Tuple[float, float]:
        """Normalize responses globally."""
        min_val = self.min_response if self.min_response is not None else data[response_col].min()
        max_val = self.max_response if self.max_response is not None else data[response_col].max()
        return min_val, max_val

    def _add_colored_border(self, image, response, min_val, max_val):
        """Add a colored border to the image based on response value."""
        normalized_response = 0.0
        response_range = max_val - min_val

        if response_range > 0:
            normalized_response = (response - min_val) / response_range

        if self.color_mode == 'intensity':
            # Red scale intensity
            border_color = (int(255 * normalized_response), 0, 0)
        else:  # 'divergent'
            # Red for positive, blue for negative
            center_point = (min_val + max_val) / 2
            if response >= center_point:
                intensity = (response - center_point) / (max_val - center_point) if max_val > center_point else 0
                border_color = (int(255 * intensity), 0, 0)
            else:
                intensity = (center_point - response) / (center_point - min_val) if center_point > min_val else 0
                border_color = (0, 0, int(255 * intensity))

        return ImageOps.expand(image, border=self.border_width, fill=border_color)

    def _plot_cell(self, ax, cell_data, response_rate_col, path_col, min_val, max_val):
        """Plot images in a single cell with colored borders."""
        if cell_data.empty:
            ax.text(0.5, 0.5, "No data", ha='center', va='center')
            ax.axis('off')
            return

        # For each cell, if there's multiple responses, take the mean.
        img_path = Path(cell_data.iloc[0][path_col])
        responses = cell_data[response_rate_col].values
        response = np.mean(responses) if len(responses) > 0 else 0.0
        std = np.std(responses) if len(responses) > 0 else 0.0
        n = len(responses)
        if img_path.exists():
            try:
                img = Image.open(img_path)
                img_with_border = self._add_colored_border(img, response, min_val, max_val)
                ax.imshow(img_with_border)


                # Add response text
                ax.text(0.5, 0.95, f"Response: {response:.2f} ± {std:.2f} ({n})\n"
                                   f"Id: {cell_data.iloc[0]['StimSpecId']}",
                        transform=ax.transAxes, ha='center', va='top',
                        color='black', fontsize=8, bbox=dict(facecolor='white', alpha=0.7))

            except Exception as e:
                ax.text(0.5, 0.5, f"Error: {str(e)}", ha='center', va='center')
        else:
            ax.text(0.5, 0.5, "Image not found", ha='center', va='center')

        ax.axis('off')


class FigureSaverOutput(OutputHandler):
    """
    Output handler that handles saving the figure.
    """

    def __init__(self, save_path: Optional[str] = None):
        """
        Initialize the output handler.
        """
        self.save_path = save_path

    def process(self, figure: plt.Figure) -> plt.Figure:
        """
        Process the figure (save if requested).
        """
        # Save if requested
        if self.save_path:
            # if parent directory does not exist, create it
            if not os.path.exists(os.path.dirname(self.save_path)):
                print(f"Creating directory for {self.save_path}...")
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            figure.savefig(self.save_path, dpi=300, bbox_inches='tight')

        return figure


def create_grouped_stimuli_module(
        response_rate_col: str,
        path_col: str,
        response_rate_key: str = None,
        row_col: Optional[str] = None,
        col_col: Optional[str] = None,
        subgroup_col: Optional[str] = None,
        filter_values: Optional[Dict[str, List[Any]]] = None,
        sort_rules: Optional[Dict[str, Any]] = None,
        figsize: Tuple[float, float] = (15, 10),
        cell_size: Tuple[float, float] = (3, 3),
        border_width: int = 40,
        normalize_method: str = 'global',
        min_response: Optional[float] = None,
        max_response: Optional[float] = None,
        color_mode: str = 'intensity',
        title: Optional[str] = None,
        save_path: Optional[str] = None
) -> AnalysisModule:
    """
    Create a pipeline module for visualizing grouped stimuli with colored borders.

    Args:
        response_rate_col: Column containing response values
        path_col: Column containing paths to stimulus images
        response_rate_key: Optional key to extract if response_rate_col contains dictionaries
        row_col: Column for grouping stimuli into rows
        col_col: Column for grouping stimuli into columns
        subgroup_col: Column for subgrouping stimuli
        filter_values: Dict mapping column names to lists of values to include
        sort_rules: Optional dict for sorting values (see GroupedStimuliInputHandler docs)
        figsize: Figure size (width, height) in inches
        cell_size: Size of each cell (width, height) in inches
        border_width: Width of colored border in pixels
        normalize_method: Method for normalizing response values ('global')
        min_response: Optional minimum response value for normalization
        max_response: Optional maximum response value for normalization
        color_mode: Color mode for borders ('intensity' or 'divergent')
        title: Optional title for the figure
        save_path: Optional path to save the figure

    Returns:
        Configured analysis module
    """
    # Create the grouped stimuli module
    grouped_stimuli_module = AnalysisModuleFactory.create(
        input_handler=GroupedStimuliInputHandler(
            response_col=response_rate_col,
            response_key=response_rate_key,
            path_col=path_col,
            row_col=row_col,
            col_col=col_col,
            subgroup_col=subgroup_col,
            filter_values=filter_values,
            sort_rules=sort_rules
        ),
        computation=GroupedStimuliPlotter(
            figsize=figsize,
            cell_size=cell_size,
            border_width=border_width,
            normalize_method=normalize_method,
            min_response=min_response,
            max_response=max_response,
            color_mode=color_mode,
            title=title
        ),
        output_handler=FigureSaverOutput(
            save_path=save_path
        ),
        name="grouped_stimuli_visualization"
    )

    return grouped_stimuli_module


class SortingUtils:
    """
    Utility class for creating various types of sorting functions.
    """

    @staticmethod
    def by_avg_value(column, comparison_col=None, ascending=False):
        """
        Create a sorting function that sorts based on the max average value in another column.

        Args:
            column: The column containing the values to average
            comparison_col: Optional column to average within groups in this col. Will sort based on max
             between these groups.
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of the average value for each item
            lookup = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                if filtered.empty or column not in filtered.columns:
                    lookup[value] = 0
                    continue

                if comparison_col:
                    # If we have a grouping column, calculate average within each group first,
                    # then take the maximum average across groups
                    groups = filtered[comparison_col].unique()
                    group_avgs = []

                    for group in groups:
                        group_data = filtered[filtered[comparison_col] == group]
                        if not group_data.empty:
                            group_avg = group_data[column].mean()
                            group_avgs.append(group_avg)

                    # Use the maximum average across groups
                    lookup[value] = max(group_avgs) if group_avgs else 0
                else:
                    # Otherwise, just find the average value
                    lookup[value] = filtered[column].mean()

            # Sort based on the lookup values
            sorted_values = sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)

            # Print debug info
            print(f"\nSorting {sort_col} by average values of {column}:")
            for value in sorted_values:
                print(f"{value}: {lookup.get(value, 0):.4f}")

            return sorted_values

        return sorter

    @staticmethod
    def by_max_avg_difference(column, group_col, ascending=False):
        """
        Create a sorting function that sorts based on the maximum difference
        between group averages.

        Args:
            column: The column containing the values to analyze
            group_col: Column used to group by before finding averages
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of the max difference for each item
            lookup = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                if filtered.empty or column not in filtered.columns:
                    lookup[value] = 0
                    continue

                # If we have a grouping column, calculate averages within each group
                if group_col:
                    groups = filtered[group_col].unique()
                    group_avgs = {}

                    # Calculate average for each group
                    for group in groups:
                        group_data = filtered[filtered[group_col] == group]
                        if not group_data.empty:
                            group_avgs[group] = group_data[column].mean()

                    # Find the maximum difference between any two group averages
                    if len(group_avgs) >= 2:
                        # Get all pairs of groups and find max difference
                        import itertools
                        max_diff = 0
                        for g1, g2 in itertools.combinations(group_avgs.keys(), 2):
                            diff = abs(group_avgs[g1] - group_avgs[g2])
                            max_diff = max(max_diff, diff)
                        lookup[value] = max_diff
                    else:
                        lookup[value] = 0
                else:
                    # If no grouping, just use the std dev as a measure of difference
                    lookup[value] = filtered[column].std() if len(filtered) > 1 else 0

            # Sort based on the lookup values
            sorted_values = sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)

            # Print debug info
            print(f"\nSorting {sort_col} by maximum average differences in {column}:")
            for value in sorted_values:
                print(f"{value}: {lookup.get(value, 0):.4f}")

            return sorted_values

        return sorter

    @staticmethod
    def by_column_value(column, ascending=True):
        """
        Create a sorting function that sorts based on values in another column.

        Args:
            column: The column to use for sorting
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, _):
            # Create a lookup of the first value for each item
            lookup = {}
            for value in values:
                matches = data[data[_] == value]
                if not matches.empty and column in matches.columns:
                    lookup[value] = matches[column].iloc[0]

            # Sort based on the lookup values
            return sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)

        return sorter

    @staticmethod
    def by_max_value(column, group_col=None, ascending=False):
        """
        Create a sorting function that sorts based on the maximum value in another column.

        Args:
            column: The column containing the values to maximize
            group_col: Optional column to group by before finding max
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of the max value for each item
            lookup = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                if group_col:
                    # If we have a grouping column, calculate max within each group
                    groups = filtered[group_col].unique()
                    max_val = 0

                    for group in groups:
                        group_data = filtered[filtered[group_col] == group]
                        if column in group_data.columns:
                            group_max = group_data[column].max()
                            max_val = max(max_val, group_max)

                    lookup[value] = max_val
                else:
                    # Otherwise, just find the max value
                    if column in filtered.columns:
                        lookup[value] = filtered[column].max()
                    else:
                        lookup[value] = 0

            # Sort based on the lookup values
            sorted_values = sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)
            # print values:
            for value in sorted_values:
                print(value, lookup.get(value, 0))
            return sorted_values

        return sorter

    @staticmethod
    def by_aggregation(column, agg_func, group_col=None, ascending=False):
        """
        Create a sorting function based on an aggregation of values.

        Args:
            column: The column containing the values to aggregate
            agg_func: Function to aggregate values (e.g., np.mean, np.max, np.sum)
            group_col: Optional column to group by before aggregating
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of the aggregated value for each item
            lookup = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                if group_col:
                    # If we have a grouping column, calculate aggregates within each group
                    groups = filtered[group_col].unique()
                    agg_values = []

                    for group in groups:
                        group_data = filtered[filtered[group_col] == group]
                        if column in group_data.columns:
                            agg_values.append(agg_func(group_data[column].values))

                    # Aggregate across groups if we have any values
                    if agg_values:
                        lookup[value] = agg_func(agg_values)
                    else:
                        lookup[value] = 0
                else:
                    # Otherwise, just aggregate all values
                    if column in filtered.columns:
                        lookup[value] = agg_func(filtered[column].values)
                    else:
                        lookup[value] = 0

            # Sort based on the lookup values
            return sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)

        return sorter

    @staticmethod
    def by_difference(column, group_col, value1, value2, absolute=True, ascending=False):
        """
        Create a sorting function based on the difference between two grouped values.

        Args:
            column: The column containing the values to compare
            group_col: Column used to differentiate the two values to compare
            value1: First value in the group_col to use
            value2: Second value in the group_col to use
            absolute: Whether to use absolute difference
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of differences
            differences = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                # Get values for the two groups
                group1_data = filtered[filtered[group_col] == value1]
                group2_data = filtered[filtered[group_col] == value2]

                # Calculate difference if we have both groups
                if not group1_data.empty and not group2_data.empty and column in filtered.columns:
                    val1 = group1_data[column].mean()
                    val2 = group2_data[column].mean()
                    diff = val2 - val1

                    if absolute:
                        differences[value] = abs(diff)
                    else:
                        differences[value] = diff
                else:
                    differences[value] = 0

            # Sort based on differences
            return sorted(values, key=lambda x: differences.get(x, 0), reverse=not ascending)

        return sorter

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

    Will automatically compute aggeregated dataframe by averaging all rows' response_col that have the same
    path_col value.

    if filter_values are provided, only the rows that match the filter values will be included in the output.


    """

    def __init__(self,
                 response_col: str,
                 path_col: str,
                 row_col: Optional[str] = None,
                 response_key: Optional[str] = None,
                 col_col: Optional[str] = None,
                 subgroup_col: Optional[str] = None,
                 filter_values: Optional[Dict[str, List[Any]]] = None,
                 ):
        """
        Initialize the grouped stimuli input handler.
        """
        self.response_col = response_col
        self.response_key = response_key
        self.path_col = path_col
        self.row_col = row_col
        self.col_col = col_col
        self.subgroup_col = subgroup_col
        self.filter_values = filter_values or {}

    def prepare(self, compiled_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Filter and organize compiled data for visualization.
        """
        if compiled_data[self.path_col].duplicated().any():
            column_map = {col: "first" for col in compiled_data.columns}
            column_map[self.response_col] = 'mean'

        # Apply any filters
        filtered_data = compiled_data.copy()
        for col, values in self.filter_values.items():
            if col in filtered_data.columns:
                filtered_data = filtered_data[filtered_data[col].isin(values)]

        # Verify required columns exist
        required_cols = [self.response_col, self.path_col]
        for col in [self.row_col, self.col_col, self.subgroup_col]:
            if col is not None:
                required_cols.append(col)

        for col in required_cols:
            if col not in filtered_data.columns:
                raise ValueError(f"Required column '{col}' not found in data")

        # Get unique values for each grouping dimension
        row_values = []
        if self.row_col:
            all_row_values = filtered_data[self.row_col].unique()
            if self.row_col in self.filter_values:
                row_values = [v for v in self.filter_values[self.row_col] if v in all_row_values]
            else:
                row_values = sorted(all_row_values)

        col_values = []
        if self.col_col:
            all_col_values = filtered_data[self.col_col].unique()
            if self.col_col in self.filter_values:
                col_values = [v for v in self.filter_values[self.col_col] if v in all_col_values]
            else:
                col_values = sorted(all_col_values)

        subgroup_values = []
        if self.subgroup_col:
            all_subgroup_values = filtered_data[self.subgroup_col].unique()
            if self.subgroup_col in self.filter_values:
                subgroup_values = [v for v in self.filter_values[self.subgroup_col] if v in all_subgroup_values]
            else:
                subgroup_values = sorted(all_subgroup_values)

            print(f"Found {len(subgroup_values)} subgroup values: {subgroup_values}")

        # if spike_data_col data is a dict and spike_data_key is provided, we need to extract the data
        if isinstance(filtered_data[self.response_col].iloc[0], dict) and self.response_key:
            filtered_data[self.response_col] = filtered_data[self.response_col].apply(
                lambda x: x[self.response_key] if isinstance(x, dict) and self.response_key in x else 0
            )

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
        Compute the visualization from prepared data with separate grids for each StimGaId.
        """
        # Extract data and configuration
        data = prepared_data['data']
        response_col = prepared_data['response_col']
        path_col = prepared_data['path_col']
        row_col = prepared_data['row_col']
        col_col = prepared_data['col_col']
        subgroup_col = prepared_data['subgroup_col']
        row_values = set(data[row_col]) if row_col else None
        col_values = set(data[col_col]) if col_col else None
        subgroup_values = set(data[subgroup_col]) if subgroup_col else None

        # Default to single row/column if not specified
        if not row_values:
            row_values = [None]
        if not col_values:
            col_values = [None]
        if not subgroup_values:
            subgroup_values = [None]

        # Normalize responses globally
        min_val, max_val = self._normalize_global(data, response_col)

        # Create a figure with multiple subplots - one 3×5 grid per StimGaId
        nrows = len(subgroup_values)
        ncols = 1  # One column of grids

        # Calculate the size for each grid
        single_grid_height = len(row_values) * self.cell_size[1]
        single_grid_width = len(col_values) * self.cell_size[0]

        # Total figure size
        fig_height = nrows * (single_grid_height + 1.5)  # Extra space for titles
        fig_width = single_grid_width + 2  # Extra space for labels

        # Create figure
        fig = plt.figure(figsize=(fig_width, fig_height))
        if self.title:
            fig.suptitle(self.title, fontsize=16)

        # Create one grid for each StimGaId
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

            # Create a subgrid for this StimGaId
            subgrid = fig.add_gridspec(nrows=len(row_values), ncols=len(col_values),
                                       left=0.1, bottom=bottom_pos,
                                       right=0.9, top=top_pos)

            # Add a title for this StimGaId's grid
            if subgroup_value is not None:
                fig.text(0.5, top_pos + 0.02,
                         f"{subgroup_col}: {subgroup_value}",
                         ha='center', fontsize=14)

            # Plot each cell in this grid
            for row_idx, row_value in enumerate(row_values):
                for col_idx, col_value in enumerate(col_values):
                    # Filter data for this specific cell
                    cell_data = data.copy()

                    # Apply row filter
                    if row_col is not None and row_value is not None:
                        cell_data = cell_data[cell_data[row_col] == row_value]

                    # Apply column filter
                    if col_col is not None and col_value is not None:
                        cell_data = cell_data[cell_data[col_col] == col_value]

                    # Apply subgroup filter
                    if subgroup_col is not None and subgroup_value is not None:
                        cell_data = cell_data[cell_data[subgroup_col] == subgroup_value]

                    # Create subplot for this cell
                    ax = fig.add_subplot(subgrid[row_idx, col_idx])

                    # Plot the image for this cell
                    self._plot_cell(ax, cell_data, response_col, path_col, min_val, max_val)

                    # Add labels
                    if col_idx == 0:
                        ax.set_ylabel(f"{row_col}: {row_value}", fontsize=10)

                    if row_idx == 0:
                        ax.set_title(f"{col_col}: {col_value}", fontsize=10)

        plt.tight_layout(rect=[0, 0, 1, 0.96])  # Leave room for main title
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
                ax.text(0.5, 0.95, f"Response: {response:.2f} ± {std:.2f} ({n})",
                        transform=ax.transAxes, ha='center', va='top',
                        color='black', fontsize=8, bbox=dict(facecolor='white', alpha=0.7))

            except Exception as e:
                ax.text(0.5, 0.5, f"Error: {str(e)}", ha='center', va='center')
        else:
            ax.text(0.5, 0.5, "Image not found", ha='center', va='center')

        ax.axis('off')


class GroupedStimuliOutput(OutputHandler):
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
            filter_values=filter_values
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
        output_handler=GroupedStimuliOutput(
            save_path=save_path
        ),
        name="grouped_stimuli_visualization"
    )

    return grouped_stimuli_module

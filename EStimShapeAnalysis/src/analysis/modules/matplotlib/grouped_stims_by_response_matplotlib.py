import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import LinearSegmentedColormap, Normalize

# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    ComputationModule, AnalysisModule,
    AnalysisModuleFactory
)
from src.analysis.modules.figure_output import FigureSaverOutput
from src.analysis.modules.grouped_stims_by_response import GroupedStimuliInputHandler


def create_grouped_stimuli_module_matplotlib(
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
        save_path: Optional[str] = None,
        cols_in_info_box=None,
        publish_mode: bool = False,
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
        cols_in_info_box: Columns to include in the info box (if publish_mode is False)
        publish_mode: If True, use publication mode to make certain asthetic changes, remove certain labels and save as
            a svg file. Warning, may overwrite some parameters.

    Returns:
        Configured analysis module
    """
    # Initialize mutable default parameters
    if cols_in_info_box is None:
        cols_in_info_box = ["Response", "StimSpecId"]

    # If publish_mode is True, override certain parameters
    if publish_mode:
        save_svg = True
        cols_in_info_box = []
        border_width = 60
        include_colorbar = True
        include_labels_for = {"row"}
    else:
        save_svg = False
        include_colorbar = False
        include_labels_for = {"row", "col", "subgroup"}

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
        computation=GroupedStimuliPlotter_matplotlib(
            figsize=figsize,
            cell_size=cell_size,
            border_width=border_width,
            normalize_method=normalize_method,
            min_response=min_response,
            max_response=max_response,
            color_mode=color_mode,
            title=title,
            info_box_columns=cols_in_info_box,
            include_colorbar=include_colorbar,
            include_labels_for=include_labels_for,
        ),
        output_handler=FigureSaverOutput(
            save_path=save_path,
            save_svg=save_svg
        ),
        name="grouped_stimuli_visualization"
    )

    return grouped_stimuli_module


class GroupedStimuliPlotter_matplotlib(ComputationModule):
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
                 title: Optional[str] = None,
                 info_box_columns=None,
                 include_colorbar: bool = False,
                 include_labels_for: Optional[set[str]] = None,
                 ):
        """
        Initialize the grouped stimuli visualization module.
        """
        if info_box_columns is None:
            info_box_columns = ['Response', 'StimSpecId']
        self.figsize = figsize
        self.cell_size = cell_size
        self.border_width = border_width
        self.normalize_method = normalize_method
        self.min_response = min_response
        self.max_response = max_response
        self.color_mode = color_mode
        self.title = title
        self.info_box_columns = info_box_columns
        self.include_colorbar = include_colorbar
        self.include_col_labels = "col" in include_labels_for
        self.include_row_labels = "row" in include_labels_for
        self.include_subgroup_labels = "subgroup" in include_labels_for

    def compute(self, prepared_data: Dict[str, Any]) -> plt.Figure:
        """
        Compute the visualization from prepared data with separate grids for each subgroup.
        Ensures all subgroups are properly visible and spaced.
        """
        # Extract data and configuration
        data = prepared_data['data']
        self.response_col = prepared_data['response_col']
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
        min_val, max_val = self._normalize_global(data, self.response_col)

        # Calculate the size for each grid
        single_group_height = len(row_values) * self.cell_size[1]
        single_group_width = len(col_values) * self.cell_size[0]

        # Calculate better vertical spacing for subgroups
        num_subgroups = len(subgroup_values)

        # Size parameters
        subgroup_spacing = 1.0  # Space between subgroups in inches
        title_space = 0.2  # Space for title in inches
        margin_space = 1.0  # Margin space in inches

        # Calculate total figure height more precisely
        total_subgroup_height = num_subgroups * single_group_height
        total_spacing = (num_subgroups - 1) * subgroup_spacing if num_subgroups > 1 else 0
        fig_height = total_subgroup_height + total_spacing + title_space + margin_space

        # Calculate figure width
        fig_width = single_group_width + 5  # Extra space for labels and colorbar

        # Create figure
        fig = plt.figure(figsize=(fig_width, fig_height))
        if self.title:
            fig.suptitle(self.title, fontsize=16, y=0.98)

        # Calculate positions for each subgroup grid
        # We'll work in figure-relative coordinates, evenly distributing the subgroups
        subgroup_positions = []

        # Total height available for subgroups (excluding margins)
        available_height = 0.90  # 90% of figure height

        # Calculate the height for each subgroup as a fraction of figure height
        subgroup_height_fraction = (single_group_height / fig_height) * 0.9
        spacing_fraction = (subgroup_spacing / fig_height) * 0.9 if num_subgroups > 1 else 0

        # Calculate positions from bottom to top
        for i in range(num_subgroups):
            # Calculate the bottom and top positions for this subgroup
            # Start from the bottom (0.05) and work up
            bottom = 0.05 + i * (subgroup_height_fraction + spacing_fraction)
            top = bottom + subgroup_height_fraction
            subgroup_positions.append((bottom, top))

        # Flip the list so we go from top to bottom (makes it easier to match with subgroup_values)
        subgroup_positions.reverse()

        # Create one grid for each subgroup
        for sg_idx, subgroup_value in enumerate(subgroup_values):
            # Get the pre-calculated positions for this subgroup
            bottom_pos, top_pos = subgroup_positions[sg_idx]

            # Ensure positions are valid
            if bottom_pos >= top_pos:
                print(f"Warning: Invalid positions for subgroup {subgroup_value}: bottom={bottom_pos}, top={top_pos}")
                bottom_pos = top_pos - 0.1

            # Adjust grid width to make room for the colorbar if needed
            right_edge = 0.85 if self.include_colorbar else 0.9
            left_edge = 0.2 if hasattr(self, 'include_row_labels') and self.include_row_labels else 0.1

            # Create a subgrid for this subgroup
            subgrid = fig.add_gridspec(
                nrows=len(row_values),
                ncols=len(col_values),
                left=left_edge,
                bottom=bottom_pos,
                right=right_edge,
                top=top_pos,
                wspace=0.05,
                hspace=0.05
            )

            # Add a title for this subgroup's grid
            if subgroup_col and subgroup_value is not None:
                if self.include_subgroup_labels:
                    # Position the title just above the grid
                    fig.text(0.5, top_pos + 0.01,
                             f"{subgroup_col}: {subgroup_value}",
                             ha='center', fontsize=14)

            # Plot each cell in this grid - order of data in row_values and col_values matters
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

                    # Plot the image for this cell
                    self._plot_cell(ax, cell_data, self.response_col, path_col, min_val, max_val)

                    # Set column label
                    if self.include_col_labels:
                        if row_idx == 0 and col_col:
                            ax.set_title(f"{col_value}", fontsize=10, pad=0)

                    # Add row label
                    if self.include_row_labels:
                        if col_idx == 0 and row_col and row_value is not None:
                            row_center = (ax.get_position().y0 + ax.get_position().y1) / 2
                            fig.text(0.19, row_center, f"{row_value}", ha='right', va='center', fontsize=36)

            # Add colorbar for this subgroup if requested
            if self.include_colorbar:
                self._add_colorbar(fig, min_val, max_val, bottom_pos, top_pos)

        # No tight_layout here as it would mess up our carefully positioned elements
        return fig

    def _add_colorbar(self, fig, min_val, max_val, bottom_pos, top_pos):
        """
        Add a colorbar legend to the right side of the figure with intelligent positioning.
        Font sizes scale automatically with the height of the colorbar.

        This method creates a colorbar that adapts to the figure layout and positions itself
        properly regardless of the number of subplots.

        Args:
            fig: The matplotlib figure
            min_val: Minimum response value for the colorbar
            max_val: Maximum response value for the colorbar
            bottom_pos: Bottom position of the current subplot grid
            top_pos: Top position of the current subplot grid
        """
        # Get figure dimensions
        fig_width, fig_height = fig.get_size_inches()

        # Calculate appropriate positioning
        # Width should be proportional to figure width but not too large
        cbar_width = max(0.010, min(0.03, 0.6 / fig_width))

        # Position - leave some space from the right edge of the main grid
        right_margin = 0.025  # Space between main content and colorbar
        cbar_left = 0.85 + right_margin

        # Calculate the height - respect the current grid's vertical span
        cbar_height = top_pos - bottom_pos

        # Scale font sizes based on colorbar height
        # Calculate height in inches for scaling
        cbar_height_inches = cbar_height * fig_height

        # Base font sizes - scale between min and max values based on height
        min_fontsize = 8
        max_fontsize = 14
        optimal_height = 3.0  # Height in inches where we want the max font size

        # Calculate font scaling factor
        # For very small colorbars, use min_fontsize
        # For very large colorbars, cap at max_fontsize
        # Otherwise, scale linearly
        font_scale = min(max_fontsize, max(min_fontsize,
                                           min_fontsize + (
                                                       max_fontsize - min_fontsize) * cbar_height_inches / optimal_height))

        # Calculate font sizes for different elements
        tick_fontsize = font_scale
        label_fontsize = font_scale * 1.2  # Make label slightly larger than ticks

        # Create a new axes for the colorbar
        cbar_ax = fig.add_axes([cbar_left, bottom_pos, cbar_width, cbar_height])

        # Create a colormap based on the color mode
        if self.color_mode == 'intensity':
            # Red scale intensity colormap - start with black for zero/low values
            # to match the border coloring logic
            cmap = LinearSegmentedColormap.from_list('intensity', [(0, 0, 0), (1, 0, 0)])
        else:  # 'divergent'
            # Red for positive, blue for negative colormap
            cmap = LinearSegmentedColormap.from_list('divergent', [(0, 0, 1), (1, 1, 1), (1, 0, 0)])

        # Create the colorbar with normalized values
        norm = Normalize(vmin=min_val, vmax=max_val)
        cbar = ColorbarBase(cbar_ax, cmap=cmap, norm=norm, orientation='vertical')

        # Generate Ticks
        # Adjust number of ticks based on height (more ticks for taller colorbars)
        optimal_tick_spacing = 0.5  # inches between ticks
        n_ticks = max(3, min(7, int(cbar_height_inches / optimal_tick_spacing) + 1))
        tick_values = np.linspace(min_val, max_val, n_ticks)

        # Set the ticks directly using the actual values
        # This uses the normalization built into the colorbar
        cbar.set_ticks(tick_values)

        # Format tick labels with proper precision
        tick_labels = [f'{val:.2f}' for val in tick_values]
        cbar.set_ticklabels(tick_labels)

        # Apply font size to tick labels
        cbar.ax.tick_params(labelsize=tick_fontsize)

        # For divergent colormap, add a line at the center
        if self.color_mode == 'divergent':
            center_point = (min_val + max_val) / 2
            if min_val < center_point < max_val:
                # Add center line - use the actual value, ColorbarBase will normalize it
                cbar.ax.axhline(y=center_point, color='black', linestyle='-', linewidth=0.5)

        # Add label with rotation for better layout (with scaled font size)
        cbar_ax.set_ylabel('Response', rotation=270, labelpad=15, fontsize=label_fontsize)

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
            # ax.text(0.5, 0.5, "No data", ha='center', va='center')
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

                # Text box with various information
                info_text = ""

                for column_name in self.info_box_columns:
                    if column_name in ["Response", self.response_col]:
                        info_text += f"Response: {response:.2f} ± {std:.2f} ({n})"
                    if column_name in cell_data.columns:
                        info_text += f"\n{column_name}: {cell_data.iloc[0][column_name]}"
                ax.text(0.5, 0.95, info_text,
                        transform=ax.transAxes, ha='center', va='top',
                        color='black', fontsize=8, bbox=dict(facecolor='white', alpha=0.7))

            except Exception as e:
                ax.text(0.5, 0.5, f"Error: {str(e)}", ha='center', va='center')
        else:
            ax.text(0.5, 0.5, "Image not found", ha='center', va='center')

        ax.axis('off')



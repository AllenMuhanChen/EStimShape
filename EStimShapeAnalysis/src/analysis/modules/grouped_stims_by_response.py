import base64
import io
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image, ImageOps

# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    InputHandler, ComputationModule, AnalysisModule,
    AnalysisModuleFactory
)

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('grouped_stimuli')


def create_grouped_stimuli_module(
        response_rate_col: str,
        path_col: str,
        response_rate_key: str = None,
        row_col: Optional[str] = None,
        col_col: Optional[str] = None,
        subgroup_col: Optional[str] = None,
        filter_values: Optional[Dict[str, List[Any]]] = None,
        sort_rules: Optional[Dict[str, Any]] = None,
        cell_size: Tuple[int, int] = (300, 300),
        border_width: int = 20,
        normalize_method: str = 'global',
        min_response: Optional[float] = None,
        max_response: Optional[float] = None,
        color_mode: str = 'intensity',
        title: Optional[str] = None,
        save_path: Optional[str] = None,
        cols_in_info_box=None,
        publish_mode: bool = False,
        include_labels_for=None,
        subplot_spacing=None,
        module_name="grouped_stimuli_visualization") -> AnalysisModule:
    """
    Create a pipeline module for visualizing grouped stimuli with colored borders using Plotly.

    Args:
        response_rate_col: Column containing response values
        path_col: Column containing paths to stimulus images
        response_rate_key: Optional key to extract if response_rate_col contains dictionaries
        row_col: Column for grouping stimuli into rows
        col_col: Column for grouping stimuli into columns
        subgroup_col: Column for subgrouping stimuli
        filter_values: Dict mapping column names to lists of values to include
        sort_rules: Optional dict for sorting values
        figsize: Figure size (width, height) in pixels
        cell_size: Size of each cell (width, height) in pixels
        border_width: Width of colored border in pixels
        normalize_method: Method for normalizing response values ('global')
        min_response: Optional minimum response value for normalization
        max_response: Optional maximum response value for normalization
        color_mode: Color mode for borders ('intensity' or 'divergent')
        title: Optional title for the figure
        save_path: Optional path to save the figure
        cols_in_info_box: Columns to include in the info box
        publish_mode: If True, use publication mode with certain aesthetic changes

    Returns:
        An AnalysisModule that can be used in a pipeline.
    """
    # Initialize mutable default parameters
    if cols_in_info_box is None:
        cols_in_info_box = ["Response", "StimSpecId"]

    # If publish_mode is True, override certain parameters
    if publish_mode:
        save_pdf = True
        cols_in_info_box = []
        border_width = 40
        include_colorbar = True
    else:
        save_pdf = False
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
        computation=GroupedStimuliPlotter(
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
            subplot_spacing=subplot_spacing,
        ),
        output_handler=PlotlyFigureSaverOutput(
            save_path=save_path,
            save_pdf=save_pdf,
        ),
        name=module_name
    )

    return grouped_stimuli_module


class GroupedStimuliPlotter(ComputationModule):
    """
    Computation module that handles layout and plotting of grouped stimuli using Plotly.
    """

    def __init__(self,
                 # Size in pixels for Plotly
                 cell_size: Tuple[int, int] = None,
                 border_width: int = 5,
                 normalize_method: str = 'global',
                 min_response: Optional[float] = None,
                 max_response: Optional[float] = None,
                 color_mode: str = 'intensity',
                 title: Optional[str] = None,
                 info_box_columns=None,
                 include_colorbar: bool = True,
                 include_labels_for: Optional[set[str]] = None,
                 subplot_spacing=None,  # (horizontal, vertical) spacing
                 ):
        """Initialize the grouped stimuli visualization module."""
        if info_box_columns is None:
            info_box_columns = ['Response', 'StimSpecId']
        if subplot_spacing is None:
            subplot_spacing = (20, 20)
        self.cell_size = cell_size
        self.border_width = border_width
        self.normalize_method = normalize_method
        self.min_response = min_response
        self.max_response = max_response
        self.color_mode = color_mode
        self.title = title
        self.info_box_columns = info_box_columns
        self.include_colorbar = include_colorbar
        self.subplot_spacing = subplot_spacing
        # Initialize as empty set if None is provided
        include_labels_for = include_labels_for or set()
        self.include_col_labels = "col" in include_labels_for
        self.include_row_labels = "row" in include_labels_for
        self.include_subgroup_labels = "subgroup" in include_labels_for

    def compute(self, prepared_data: Dict[str, Any]) -> go.Figure:
        """
        Compute the visualization from prepared data with exact cell sizing.
        """
        # Extract data and configuration
        data = prepared_data['data']
        self.response_col = prepared_data['response_col']
        self.response_key = prepared_data.get('response_key')
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

        # Calculate grid dimensions
        n_rows = len(row_values)
        n_cols = len(col_values)
        n_subgroups = len(subgroup_values)

        # EXACT PIXEL DIMENSIONS
        cell_width, cell_height = self.cell_size  # Use exactly these pixel dimensions
        horiz_spacing_px = self.subplot_spacing[0]  # Horizontal spacing
        vert_spacing_px = self.subplot_spacing[1]  # Vertical spacing
        # horiz_spacing_px = 20  # Space between cells in pixels
        # vert_spacing_px = 20  # Space between rows in pixels
        subgroup_spacing_px = 100  # Space between subgroups in pixels

        # Extra space for labels and colorbar in pixels
        left_margin_px = 200 if self.include_row_labels else 50
        right_margin_px = 150 if self.include_colorbar else 50  # More space for colorbar
        top_margin_px = 100  # For title and column labels

        # Calculate EXACT figure dimensions in pixels
        content_width_px = (n_cols * cell_width) + ((n_cols - 1) * horiz_spacing_px)
        content_height_px = n_rows * cell_height + ((n_rows - 1) * vert_spacing_px)

        # Total figure dimensions including all subgroups and margins
        fig_width_px = left_margin_px + content_width_px + right_margin_px
        fig_height_px = top_margin_px + (content_height_px * n_subgroups) + \
                        ((n_subgroups - 1) * subgroup_spacing_px)

        # Create a new figure with fixed dimensions
        fig = go.Figure()

        # Add a title if provided
        if self.title:
            fig.update_layout(
                title={
                    'text': self.title,
                    'y': 0.98,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 36}
                }
            )

        # Store cell domains for annotations and content positioning
        cell_domains = {}

        # Calculate scale factors to convert pixels to paper coordinates (0-1 range)
        x_scale = 1.0 / fig_width_px
        y_scale = 1.0 / fig_height_px

        # Process each subgroup with EXACT positioning
        for sg_idx, subgroup_value in enumerate(subgroup_values):
            # Calculate EXACT vertical position for this subgroup in pixels
            # Start from top and work downward
            subgroup_top_px = top_margin_px + (sg_idx * (content_height_px + subgroup_spacing_px))
            subgroup_bottom_px = subgroup_top_px + content_height_px

            # Convert to paper coordinates (0-1 range)
            sg_top = 1.0 - (subgroup_top_px * y_scale)
            sg_bottom = 1.0 - (subgroup_bottom_px * y_scale)
            sg_center = (sg_top + sg_bottom) / 2

            # Add subgroup label if needed
            if self.include_subgroup_labels and subgroup_col and subgroup_value is not None:
                fig.add_annotation(
                    text=f"{subgroup_col}: {subgroup_value}",
                    x=0.5,
                    y=sg_top + 0.02,  # Just above the subgroup
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=16),
                    align="center"
                )

            # Process cells in this subgroup with EXACT sizing
            for row_idx, row_value in enumerate(row_values):
                for col_idx, col_value in enumerate(col_values):
                    # Calculate EXACT pixel positions for this cell
                    cell_left_px = left_margin_px + (col_idx * (cell_width + horiz_spacing_px))
                    cell_right_px = cell_left_px + cell_width

                    # Y position is calculated from the top of the subgroup
                    cell_top_px = subgroup_top_px + (row_idx * (cell_height + vert_spacing_px))
                    cell_bottom_px = cell_top_px + cell_height
                    # Convert to paper coordinates (0-1 range)
                    cell_left = cell_left_px * x_scale
                    cell_right = cell_right_px * x_scale
                    cell_top = 1.0 - (cell_top_px * y_scale)
                    cell_bottom = 1.0 - (cell_bottom_px * y_scale)

                    # Calculate cell center
                    cell_center_x = (cell_left + cell_right) / 2
                    cell_center_y = (cell_top + cell_bottom) / 2

                    # Store the domain for this cell
                    cell_domains[(sg_idx, row_idx, col_idx)] = {
                        'x': [cell_left, cell_right],
                        'y': [cell_bottom, cell_top],
                        'center_x': cell_center_x,
                        'center_y': cell_center_y,
                        'width': cell_right - cell_left,
                        'height': cell_top - cell_bottom
                    }

                    # Add row label if needed
                    if col_idx == 0 and self.include_row_labels and row_col and row_value is not None:
                        fig.add_annotation(
                            text=str(row_value),
                            x=cell_left - (cell_width / 4 * x_scale),
                            y=cell_center_y,
                            xref="paper",
                            yref="paper",
                            showarrow=False,
                            font=dict(size=36),
                            align="right",
                            xanchor="right",
                            yanchor="middle"
                        )

                    # Add column label if needed
                    if row_idx == 0 and self.include_col_labels and col_col and col_value is not None:
                        fig.add_annotation(
                            text=str(col_value),
                            x=cell_center_x,
                            y=cell_top + 0.01,
                            xref="paper",
                            yref="paper",
                            showarrow=False,
                            font=dict(size=36),
                            align="center"
                        )

                    # Filter data for this cell
                    cell_data = data.copy()
                    if row_col is not None and row_value is not None:
                        cell_data = cell_data[cell_data[row_col] == row_value]
                    if col_col is not None and col_value is not None:
                        cell_data = cell_data[cell_data[col_col] == col_value]
                    if subgroup_col is not None and subgroup_value is not None:
                        cell_data = cell_data[cell_data[subgroup_col] == subgroup_value]

                    # Plot this cell
                    if cell_data.empty:
                        # Add "No data" annotation
                        fig.add_annotation(
                            text="No data",
                            x=cell_center_x,
                            y=cell_center_y,
                            xref="paper",
                            yref="paper",
                            showarrow=False,
                            font=dict(size=12)
                        )
                    else:
                        # Process and add the image using the EXACT dimensions
                        image_width = (cell_right - cell_left)
                        image_height = (cell_top - cell_bottom)
                        self._add_cell_to_figure(
                            fig, cell_data, cell_center_x, cell_center_y,
                            image_width, image_height,
                            path_col, min_val, max_val
                        )

            # Add a colorbar for this subgroup if requested
            if self.include_colorbar:
                self._add_subgroup_colorbar(fig, min_val, max_val, sg_center, sg_top, sg_bottom)

        # Set layout properties with EXACT dimensions
        fig.update_layout(
            width=fig_width_px,
            height=fig_height_px,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',  # Transparent background
            paper_bgcolor='rgba(255,255,255,1)',  # White paper
            margin=dict(l=0, r=0, t=0, b=0),  # No auto margins - we control everything
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                showline=False,
                range=[0, 1]
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                showline=False,
                range=[0, 1]
            )
        )

        return fig

    def _add_subgroup_colorbar(self, fig, min_val, max_val, sg_center, sg_top, sg_bottom):
        """Add a colorbar aligned with a specific subgroup."""
        # Create colorscale based on color mode
        if self.color_mode == 'intensity':
            colorscale = [[0, 'rgb(0,0,0)'], [1, 'rgb(255,0,0)']]
        else:  # 'divergent'
            colorscale = [
                [0, 'rgb(0,0,255)'],  # Blue for minimum
                [0.5, 'rgb(255,255,255)'],  # White for center
                [1, 'rgb(255,0,0)']  # Red for maximum
            ]

        # Calculate colorbar height based on subgroup height
        colorbar_height = sg_top - sg_bottom

        # Add a hidden heatmap trace to create the colorbar
        fig.add_trace(
            go.Heatmap(
                z=[[min_val, max_val]],  # Dummy data
                colorscale=colorscale,
                showscale=True,
                zmin=min_val,
                zmax=max_val,
                colorbar=dict(
                    title="Response",
                    titleside="right",
                    thickness=20,
                    len=colorbar_height * 0.8,  # 80% of subgroup height
                    y=sg_center,  # Center aligned with subgroup
                    x=1.05,
                    title_font=dict(size=36),
                    tickfont=dict(size=36),
                ),
                hoverinfo='none',
                opacity=0  # Make the heatmap invisible
            )
        )

    def _normalize_global(self, data: pd.DataFrame, response_col: str) -> Tuple[float, float]:
        """Normalize responses globally."""
        try:
            # Check if we need to handle dictionary values
            if data.shape[0] > 0 and isinstance(data[response_col].iloc[0], dict):
                # Extract values from dictionaries
                response_values = []
                for _, row in data.iterrows():
                    response_dict = row[response_col]
                    if isinstance(response_dict, dict):
                        if self.response_key and self.response_key in response_dict:
                            response_values.append(response_dict[self.response_key])
                        else:
                            # Use first value if no key specified
                            if response_dict:
                                response_values.append(next(iter(response_dict.values())))

                if response_values:
                    min_val = self.min_response if self.min_response is not None else min(response_values)
                    max_val = self.max_response if self.max_response is not None else max(response_values)
                    return min_val, max_val

            # Normal case: numeric column
            min_val = self.min_response if self.min_response is not None else float(data[response_col].min())
            max_val = self.max_response if self.max_response is not None else float(data[response_col].max())
            return min_val, max_val
        except Exception as e:
            logger.error(f"Error normalizing responses: {e}")
            return 0.0, 1.0  # Default fallback values

    def _get_response_value(self, row: pd.Series) -> float:
        """Extract a single response value from a row."""
        try:
            value = row[self.response_col]

            # Handle dictionary responses
            if isinstance(value, dict):
                if self.response_key and self.response_key in value:
                    return value[self.response_key]
                elif value:  # If dict not empty, take first value
                    return next(iter(value.values()))
                return 0.0

            # Handle numeric values
            if isinstance(value, (int, float)):
                return float(value)

            # Handle other types
            return float(value) if value is not None else 0.0
        except Exception as e:
            logger.error(f"Error extracting response value: {e}")
            return 0.0

    def _add_cell_to_figure(self, fig, cell_data, x, y, width, height, path_col, min_val, max_val):
        """Add a cell with image and info to the figure."""
        try:
            # Get the first row and calculate response values
            row = cell_data.iloc[0]
            img_path = Path(row[path_col])

            # Calculate statistics across all matching cells
            responses = [self._get_response_value(row) for _, row in cell_data.iterrows()]
            response_mean = np.mean(responses) if responses else 0.0
            response_std = np.std(responses) if len(responses) > 1 else 0.0
            count = len(responses)

            # Check if image exists
            if not img_path.exists():
                # Image not found, add annotation
                fig.add_annotation(
                    text="Image not found",
                    x=x,
                    y=y,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=12)
                )
                return

            # Process image - add border based on response
            img = self._process_image(img_path, response_mean, min_val, max_val)
            if img is None:
                # Error processing image
                fig.add_annotation(
                    text="Error processing image",
                    x=x,
                    y=y,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=12)
                )
                return

            # Convert to base64 for Plotly
            img_base64 = self._image_to_base64(img)

            # Add image to figure
            fig.add_layout_image(
                dict(
                    source=img_base64,
                    x=x,
                    y=y,
                    xref="paper",
                    yref="paper",
                    sizex=width,
                    sizey=height,
                    xanchor="center",
                    yanchor="middle",
                    sizing="contain"
                )
            )

            # Add info text if requested
            if self.info_box_columns:
                info_text = ""
                for col in self.info_box_columns:
                    if col in ["Response", self.response_col]:
                        info_text += f"Response: {response_mean:.2f}"
                        if count > 1:
                            info_text += f" ± {response_std:.2f}"
                        info_text += f" (n={count})<br>"
                    elif col in cell_data.columns:
                        info_text += f"{col}: {row[col]}<br>"

                if info_text:
                    # Add as annotation below the image
                    fig.add_annotation(
                        text=info_text,
                        x=x,
                        y=y - height / 2 - 0.01,  # Just below the image
                        xref="paper",
                        yref="paper",
                        showarrow=False,
                        font=dict(size=10),
                        align="center",
                        yanchor="top",
                        xanchor="center",
                        bgcolor="rgba(255,255,255,0.7)",
                        bordercolor="rgba(0,0,0,0.3)",
                        borderwidth=1,
                        borderpad=4
                    )

        except Exception as e:
            logger.error(f"Error adding cell to figure: {e}")
            # Add error annotation
            fig.add_annotation(
                text=f"Error: {str(e)[:30]}...",
                x=x,
                y=y,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=10)
            )

    def _process_image(self, img_path, response, min_val, max_val):
        """Process the image, adding a colored border based on response value."""
        try:
            # Open the image
            img = Image.open(img_path)

            # Calculate normalized response (0-1 range)
            if min_val == max_val:
                normalized_response = 0.5  # Default to middle if min=max
            else:
                normalized_response = (response - min_val) / (max_val - min_val)
                normalized_response = max(0.0, min(1.0, normalized_response))  # Clip to 0-1 range

            # Determine border color based on color mode
            if self.color_mode == 'intensity':
                # Red scale intensity (black to red)
                border_color = (int(255 * normalized_response), 0, 0)
            else:  # 'divergent'
                # Center point for divergent color scale
                center_point = 0.5
                if normalized_response >= center_point:
                    # Red for values above center
                    intensity = (normalized_response - center_point) * 2  # Scale to 0-1
                    border_color = (int(255 * intensity), 0, 0)
                else:
                    # Blue for values below center
                    intensity = (center_point - normalized_response) * 2  # Scale to 0-1
                    border_color = (0, 0, int(255 * intensity))

            # Add border to image
            img_with_border = ImageOps.expand(img, border=self.border_width, fill=border_color)

            img_with_border = img_with_border.resize(self.cell_size, Image.LANCZOS)

            return img_with_border

        except Exception as e:
            logger.error(f"Error processing image {img_path}: {e}")
            return None

    def _image_to_base64(self, img):
        """Convert PIL Image to base64 string for use in Plotly."""
        try:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG", optimize=True)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return None

    def _add_colorbar(self, fig, min_val, max_val):
        """Add a colorbar to the figure."""
        # Create colorscale based on color mode
        if self.color_mode == 'intensity':
            colorscale = [[0, 'rgb(0,0,0)'], [1, 'rgb(255,0,0)']]
        else:  # 'divergent'
            colorscale = [
                [0, 'rgb(0,0,255)'],  # Blue for minimum
                [0.5, 'rgb(255,255,255)'],  # White for center
                [1, 'rgb(255,0,0)']  # Red for maximum
            ]

        # Add a hidden heatmap trace to create the colorbar
        fig.add_trace(
            go.Heatmap(
                z=[[min_val, max_val]],
                colorscale=colorscale,
                showscale=True,
                zmin=min_val,
                zmax=max_val,
                colorbar=dict(
                    title="Response",
                    titleside="right",
                    thickness=20,
                    len=0.75,
                    y=0.5,
                    x=1.05,
                    title_font=dict(size=36),
                    tickfont=dict(size=36),
                ),
                hoverinfo='none',
                opacity=0  # Make the heatmap invisible
            )
        )


import os
import plotly.graph_objects as go
from typing import Optional

from clat.pipeline.pipeline_base_classes import OutputHandler


class PlotlyFigureSaverOutput(OutputHandler):
    """
    Output handler that handles saving Plotly figures with vector graphics support.
    """

    def __init__(self,
                 save_path: Optional[str] = None,
                 save_html: bool = False,
                 save_svg: bool = False,
                 save_pdf: bool = False):
        """
        Initialize the output handler.

        Args:
            save_path: Path to save the figure
            save_html: Whether to save as interactive HTML
            save_svg: Whether to save as SVG for vector editing
            save_pdf: Whether to save as PDF for vector editing/printing
        """
        self.save_path = save_path
        self.save_html = save_html
        self.save_svg = save_svg
        self.save_pdf = save_pdf

    def process(self, figure: go.Figure) -> go.Figure:
        """
        Process the figure and save in requested formats.
        """
        # figure.show()

        if not self.save_path:
            return figure

        try:
            # Create directory if needed
            save_dir = os.path.dirname(self.save_path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir)

            # Get base path without extension
            if '.' in os.path.basename(self.save_path):
                base_path = self.save_path.rsplit('.', 1)[0]
                original_ext = self.save_path.rsplit('.', 1)[1]
            else:
                base_path = self.save_path
                original_ext = ''

            # Save as SVG for vector editing
            if self.save_svg:
                svg_path = f"{base_path}.svg"
                figure.write_image(svg_path, format='svg')
                logger.info(f"Saved SVG for vector editing to {svg_path}")

            # Save as PDF if requested
            if self.save_pdf:
                pdf_path = f"{base_path}.pdf"
                figure.write_image(pdf_path, format='pdf')
                logger.info(f"Saved PDF to {pdf_path}")

            # Save as original format (PNG, JPEG, etc.)
            if original_ext and original_ext.lower() not in ['html', 'svg', 'pdf']:
                figure.write_image(self.save_path, scale=2)  # Higher quality rendering
                logger.info(f"Saved figure to {self.save_path}")

            # Save as interactive HTML
            if self.save_html:
                html_path = f"{base_path}.html"
                figure.write_html(html_path)
                logger.info(f"Saved interactive HTML to {html_path}")

        except Exception as e:
            logger.error(f"Error saving figure: {e}")

        return figure


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

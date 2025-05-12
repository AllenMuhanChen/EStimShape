import os
from typing import Optional

from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import OutputHandler


class FigureSaverOutput(OutputHandler):
    """
    Output handler that handles saving the figure in both regular and SVG formats.
    """

    def __init__(self, save_path: Optional[str] = None, save_svg: bool = False):
        """
        Initialize the output handler.

        Args:
            save_path: Optional path to save the figure
            save_svg: If True, also save an SVG version of the figure
        """
        self.save_path = save_path
        self.save_svg = save_svg

    def process(self, figure: plt.Figure) -> plt.Figure:
        """
        Process the figure (save if requested).

        Args:
            figure: The matplotlib figure to save

        Returns:
            The same figure, unchanged
        """
        # Save if requested
        if self.save_path:
            # if parent directory does not exist, create it
            if not os.path.exists(os.path.dirname(self.save_path)):
                print(f"Creating directory for {self.save_path}...")
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

            # Save in the original format (usually PNG)
            figure.savefig(self.save_path, dpi=300, bbox_inches='tight')

            # Optionally save as SVG
            if self.save_svg:
                # Create SVG path by replacing the extension
                svg_path = os.path.splitext(self.save_path)[0] + '.svg'
                figure.savefig(svg_path, format='svg', bbox_inches='tight')
                print(f"Saved SVG version to {svg_path}")

        return figure

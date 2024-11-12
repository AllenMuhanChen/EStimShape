from typing import List, Union, Tuple, Dict

import numpy as np
import onnx
import onnxruntime
from PIL import Image
from PIL.Image import Image
from clat.util.connection import Connection
from torchvision import transforms as transforms

from src.alexnet.frommat.backtrace import calculate_pool_2_contributions, associate_with_conv2_units, backtrace
from src.pga.alexnet import alexnet_context
from src.pga.alexnet.onnx_parser import LayerType, AlexNetONNXResponseParser, UnitIdentifier
from src.pga.alexnet.lighting_posthoc.plot_top_n_lighting import load_all_stim_data


class AlexNetContributionCalculator:
    def __init__(self, conn: Connection, onnx_path: str, unit: UnitIdentifier) -> None:
        self.conn = conn
        self.onnx_path = onnx_path
        self.transform = transforms.Compose([
            transforms.PILToTensor(),
            lambda x: x * 1.0
        ])
        self.unit_id = unit
        self._batch_size=1000

    def process_image(self, image_path: str) -> float:
        unit = self.unit_id.unit - 1  # Zero-based indexing
        x = self.unit_id.x - 1 if self.unit_id.x else None
        y = self.unit_id.y - 1 if self.unit_id.y else None

        # Get stim_id from path
        stim_id = self._get_stim_id_from_path(image_path)
        if not stim_id:
            raise ValueError(f"Could not find stim_id for path: {image_path}")

        def export_to_db(data: Union[Tuple[Tuple[UnitIdentifier, UnitIdentifier], float],
        Dict[Tuple[UnitIdentifier, UnitIdentifier], float]]) -> None:
            """
            Export unit connection contribution(s) to database. Supports both single and batch insertions.

            Args:
                data: Either a tuple of ((from_unit, to_unit), contribution) for single insertion,
                     or a dictionary of {(from_unit, to_unit): contribution} for batch insertion
            """
            if isinstance(data, tuple):
                # Single insertion
                (from_unit, to_unit), contribution = data
                self._insert_contribution(stim_id, from_unit, to_unit, contribution)

            elif isinstance(data, dict):
                # Batch insertion
                self._batch_insert_contributions(stim_id, data)

            else:
                raise ValueError("Data must be either a connection-contribution tuple or a dictionary")

        # Call backtrace with our export function
        backtrace(self.onnx_path, image_path, unit, x, y, export_to_db, 20, 20, 20)

    def _insert_contribution(self, stim_id: int, from_unit: UnitIdentifier,
                             to_unit: UnitIdentifier, contribution: float) -> None:
        """Insert a single contribution record."""
        query = """
          INSERT INTO UnitContributions (stim_id, from_unit_id, to_unit_id, contribution)
          VALUES (%s, %s, %s, %s)
          ON DUPLICATE KEY UPDATE contribution = VALUES(contribution)
          """
        self.conn.execute(query, (
            stim_id,
            from_unit.to_string(),
            to_unit.to_string(),
            float(contribution)
        ))

    def _batch_insert_contributions(self, stim_id: int,
                                    contributions: Dict[Tuple[UnitIdentifier, UnitIdentifier], float]) -> None:
        """Insert multiple contribution records in batches."""
        # Create a multi-row INSERT query
        base_query = """
          INSERT INTO UnitContributions (stim_id, from_unit_id, to_unit_id, contribution)
          VALUES 
          """

        # Convert dictionary items to list for batch processing
        values = [
            (stim_id, from_unit.to_string(), to_unit.to_string(), float(contribution))
            for (from_unit, to_unit), contribution in contributions.items()
        ]

        # Process in batches
        for i in range(0, len(values), self._batch_size):
            batch = values[i:i + self._batch_size]

            # Create the value placeholders for this batch
            placeholders = ",".join([" (%s, %s, %s, %s)"] * len(batch))

            # Flatten the batch values for the query
            flattened_values = [val for tup in batch for val in tup]

            # Construct the complete query with ON DUPLICATE KEY UPDATE
            complete_query = base_query + placeholders + """
              ON DUPLICATE KEY UPDATE 
              contribution = VALUES(contribution)
              """

            # Execute the batch insert
            self.conn.execute(complete_query, flattened_values)
    def _get_stim_id_from_path(self, path: str) -> int:
        """
        Get stim_id from StimPath table using the image path

        Args:
            path: Full path to the image file

        Returns:
            int: The stim_id if found, None otherwise
        """
        query = """
        SELECT stim_id
        FROM StimPath
        WHERE path = %s
        """
        self.conn.execute(query, (path,))
        result = self.conn.fetch_one()
        return result if result else None


def main():
    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )
    contribution_calc = AlexNetContributionCalculator(conn,
                                                      "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3",
                                                      alexnet_context.unit)
    # Load data
    stims: dict[str, list[dict]] = load_all_stim_data(conn)
    print("Total 3D stims:", len(stims['3D']))

    for stim in stims['3D']:
        # if stim['parent_id'] == 1730131310638022:
        print(stim['path'])
        output = contribution_calc.process_image(stim['path'])
        print(output)


if __name__ == '__main__':
    main()

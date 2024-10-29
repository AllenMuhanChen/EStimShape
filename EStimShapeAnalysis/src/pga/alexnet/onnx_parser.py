from dataclasses import dataclass
from enum import Enum
import torch
import torchvision.transforms as transforms
from PIL import Image
import onnxruntime
from typing import List

from src.pga.spike_parsing import IntanResponseParser, ResponseParser


class LayerType(Enum):
    IMAGE = "image"
    CONV1 = "conv1"
    CONV2 = "conv2"
    CONV3 = "conv3"
    CONV4 = "conv4"
    CONV5 = "conv5"
    FC6 = "fc6"
    FC7 = "fc7"
    FC8 = "fc8"


@dataclass
class UnitIdentifier:
    layer: LayerType
    unit: int
    x: int | None = None  # None for FC layers
    y: int | None = None  # None for FC layers

    def to_string(self) -> str:
        """Convert unit identifier to string format."""
        if self.x is None or self.y is None:
            return f"{self.layer.value}_u{self.unit}"
        return f"{self.layer.value}_u{self.unit}_x{self.x}_y{self.y}"

    @staticmethod
    def from_string(identifier: str) -> 'UnitIdentifier':
        """Parse unit identifier from string format."""
        parts = identifier.split('_')
        layer = LayerType(parts[0])
        unit = int(parts[1][1:])  # Remove 'u' prefix

        if len(parts) > 2:  # Has location information
            x = int(parts[2][1:])  # Remove 'x' prefix
            y = int(parts[3][1:])  # Remove 'y' prefix
            return UnitIdentifier(layer, unit, x, y)

        return UnitIdentifier(layer, unit)


class AlexNetONNXResponseParser(ResponseParser):
    def __init__(self, conn, onnx_path: str, unit: UnitIdentifier) -> None:
        self.conn = conn
        self.onnx_path = onnx_path
        self.session = self._load_onnx_model()
        self.transform = transforms.Compose([
            transforms.PILToTensor(),
            lambda x: x * 1.0
        ])

        # Define unit to monitor
        self.unit_id = unit

    def parse_to_db(self, ga_name: str) -> None:
        """Main function to process stimuli and store activations."""
        stim_ids = self._get_stims_without_responses()

        for stim_id in stim_ids:
            image_path = self._get_stim_path(stim_id)
            if not image_path:
                continue

            activation = self.process_image(image_path)
            self._store_activation(stim_id, activation)
            self._update_stim_response(stim_id, activation)

    def process_image(self, image_path: str) -> float:
        """Process an image and return single unit activation."""
        # Load and preprocess image
        image = Image.open(image_path).convert('RGB')
        input_tensor = self.transform(image)
        input_tensor = input_tensor.unsqueeze(0)  # Add batch dimension

        # Get model prediction
        input_name = self.session.get_inputs()[0].name
        conv3_output_name = "conv3"  # This needs to match the ONNX model's layer name
        outputs = self.session.run([conv3_output_name], {input_name: input_tensor.numpy()})

        # outputs is a list with a single element containing the conv3 features
        features = outputs[0]  # Shape should be [1, num_channels, height, width]

        # Get activation for specified unit and location
        activation = float(features[0, self.unit_id.unit-1, self.unit_id.x, self.unit_id.y])
        return activation

    def _load_onnx_model(self) -> onnxruntime.InferenceSession:
        """Load the ONNX model."""
        session = onnxruntime.InferenceSession(self.onnx_path)
        return session

    def _get_stims_without_responses(self) -> List[int]:
        """Get all stim_ids from StimGaInfo that have no response."""
        query = """
            SELECT stim_id 
            FROM StimGaInfo 
            WHERE response IS NULL OR response = ''
        """
        self.conn.execute(query)
        return [row[0] for row in self.conn.fetch_all()]

    def _get_stim_path(self, stim_id: int) -> str:
        """Get the path for a given stim_id from StimPath."""
        query = "SELECT path FROM StimPath WHERE stim_id = %s"
        self.conn.execute(query, (stim_id,))
        result = self.conn.fetch_one()
        return result if result else None

    def _store_activation(self, stim_id: int, activation: float) -> None:
        """Store activation in UnitActivations table."""
        query = """
            INSERT INTO UnitActivations (stim_id, unit, activation) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE activation = %s
        """
        self.conn.execute(query, (stim_id, self.unit_id.to_string(), activation, activation))
        self.conn.mydb.commit()

    def _update_stim_response(self, stim_id: int, activation: float) -> None:
        """Update the response in StimGaInfo."""
        query = "UPDATE StimGaInfo SET response = %s WHERE stim_id = %s"
        self.conn.execute(query, (activation, stim_id))
        self.conn.mydb.commit()

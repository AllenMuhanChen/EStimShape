from dataclasses import dataclass
from typing import List

from PIL.Image import Image

from src.pga.alexnet.onnx_parser import LayerType, AlexNetONNXResponseParser


class AlexNetContributionCalculator(AlexNetONNXResponseParser):
    def process_image(self, image_path: str) -> float:
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

        # Capture contributions from earlier layers and image pixels
        self._capture_contributions(image_path, features)

        return activation

    def _capture_contributions(self, image_path: str, conv3_features: np.ndarray) -> None:
        # Load the image
        image = Image.open(image_path).convert('RGB')
        image_tensor = self.transform(image).unsqueeze(0)

        # Get intermediate layer outputs
        conv1_output_name = "conv1"
        conv2_output_name = "conv2"
        outputs = self.session.run([conv1_output_name, conv2_output_name], {self.session.get_inputs()[0].name: image_tensor.numpy()})
        conv1_features, conv2_features = outputs

        # Calculate contributions from conv2 to conv3
        conv2_contributions = self._calculate_contributions(conv2_features, conv3_features, LayerType.CONV2, LayerType.CONV3)
        self._store_contributions(conv2_contributions)

        # Calculate contributions from conv1 to conv2
        conv1_contributions = self._calculate_contributions(conv1_features, conv2_features, LayerType.CONV1, LayerType.CONV2)
        self._store_contributions(conv1_contributions)

        # Calculate contributions from image pixels to conv1
        image_contributions = self._calculate_image_contributions(image_tensor, conv1_features)
        self._store_contributions(image_contributions)

    def _calculate_contributions(self, input_features: np.ndarray, output_features: np.ndarray, input_layer: LayerType, output_layer: LayerType) -> List[tuple[UnitIdentifier, float]]:
        contributions = []

        # Get the weights connecting the input and output layers
        weights = self._get_layer_weights(input_layer, output_layer)

        # Iterate over output units
        for output_unit in range(output_features.shape[1]):
            for output_x in range(output_features.shape[2]):
                for output_y in range(output_features.shape[3]):
                    output_unit_id = UnitIdentifier(output_layer, output_unit, output_x, output_y)
                    output_activation = output_features[0, output_unit, output_x, output_y]

                    # Calculate contributions from input units
                    for input_unit in range(input_features.shape[1]):
                        for input_x in range(input_features.shape[2]):
                            for input_y in range(input_features.shape[3]):
                                input_unit_id = UnitIdentifier(input_layer, input_unit, input_x, input_y)
                                input_activation = input_features[0, input_unit, input_x, input_y]
                                contribution = weights[output_unit, input_unit] * input_activation

                                contributions.append((output_unit_id, input_unit_id, contribution))

        return contributions

    def _calculate_image_contributions(self, image_tensor: torch.Tensor, conv1_features: np.ndarray) -> List[tuple[UnitIdentifier, float]]:
        contributions = []

        # Get the weights connecting the image to conv1
        weights = self._get_layer_weights(LayerType.IMAGE, LayerType.CONV1)

        # Iterate over conv1 units
        for conv1_unit in range(conv1_features.shape[1]):
            for conv1_x in range(conv1_features.shape[2]):
                for conv1_y in range(conv1_features.shape[3]):
                    conv1_unit_id = UnitIdentifier(LayerType.CONV1, conv1_unit, conv1_x, conv1_y)
                    conv1_activation = conv1_features[0, conv1_unit, conv1_x, conv1_y]

                    # Calculate contributions from image pixels
                    for channel in range(image_tensor.shape[1]):
                        for image_x in range(image_tensor.shape[2]):
                            for image_y in range(image_tensor.shape[3]):
                                image_unit_id = UnitIdentifier(LayerType.IMAGE, 0, image_x, image_y, channel)
                                image_activation = image_tensor[0, channel, image_x, image_y]
                                contribution = weights[conv1_unit, channel] * image_activation

                                contributions.append((conv1_unit_id, image_unit_id, contribution))

        return contributions

    def _get_layer_weights(self, input_layer: LayerType, output_layer: LayerType) -> np.ndarray:
        # Retrieve the weights connecting the input and output layers from the ONNX model
        # You'll need to implement this based on your specific ONNX model structure
        # Return the weights as a numpy array
        pass

    def _store_contributions(self, contributions: List[tuple[UnitIdentifier, UnitIdentifier, float]]) -> None:
        query = """
            INSERT INTO Contributions (stim_id, unit, contribution) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE contribution = %s
        """
        for output_unit_id, input_unit_id, contribution in contributions:
            self.conn.execute(query, (self.stim_id, f"{output_unit_id.to_string()}|{input_unit_id.to_string()}", contribution, contribution))
        self.conn.mydb.commit()
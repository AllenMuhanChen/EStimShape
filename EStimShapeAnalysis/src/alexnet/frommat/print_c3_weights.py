import onnx
import numpy as np


def print_conv3_unit_weights(model_path: str, unit_number: int):
    """Print single weight from conv3 unit."""
    model = onnx.load(model_path)

    for initializer in model.graph.initializer:
        if initializer.name == 'conv3_W':
            weights = onnx.numpy_helper.to_array(initializer)
            print(weights.shape)
            single_weight = weights[0, 0, 0, 0]  # Get weight at position (1,1,1,1)
            print(f"Conv3 weight at [1,1,1,1]: {single_weight}")
            return

    print("Could not find conv3 weights in model")


if __name__ == "__main__":
    model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX'
    unit = 3
    print_conv3_unit_weights(model_path, unit)
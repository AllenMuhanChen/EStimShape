import torch
import onnx
import onnxruntime
import numpy as np
import matplotlib.pyplot as plt

def load_onnx_model(model_path):
    # Load the ONNX model
    onnx_model = onnx.load(model_path)
    return onnx_model

def get_conv_weights(onnx_model, conv_name):
    # Extract weights from the specified convolutional layer
    for init in onnx_model.graph.initializer:
        if init.name == conv_name:
            return np.frombuffer(init.raw_data, dtype=np.float32).reshape(init.dims)
    return None

def visualize_filters(weights, gpu_name):
    # Normalize the weights for better visualization
    weights = (weights - weights.min()) / (weights.max() - weights.min())

    # Create a grid to place the filter visualizations
    num_filters = weights.shape[0]
    num_rows = 6  # You can adjust this for a different layout
    num_cols = num_filters // num_rows + (1 if num_filters % num_rows != 0 else 0)

    fig, axes = plt.subplots(num_rows, num_cols, figsize=(20, 20))
    fig.suptitle(f'{gpu_name} C1 Filters', fontsize=16)

    for i, ax in enumerate(axes.flat):
        if i < num_filters:
            # For grayscale filters
            if weights.shape[1] == 1:
                ax.imshow(weights[i, 0], cmap='gray')
            # For RGB filters
            else:
                ax.imshow(np.transpose(weights[i], (1, 2, 0)))
        ax.axis('off')

    plt.tight_layout()
    return fig

# Load the ONNX model
model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX'  # Update this to your ONNX model's path
onnx_model = load_onnx_model(model_path)

# Get weights for the first convolutional layer of each GPU
weights_gpu1 = get_conv_weights(onnx_model, "conv1_W")
weights_gpu2 = get_conv_weights(onnx_model, "conv1_W")  # Note: This is the same as GPU1 for now

if weights_gpu1 is not None:
    # Visualize filters for GPU1
    fig1 = visualize_filters(weights_gpu1, 'GPU1')

    # Save the figure
    fig1.savefig('onnx_c1_filters.png', dpi=300, bbox_inches='tight')

    plt.show()

    print("Filter visualization saved as 'onnx_c1_filters.png'")
else:
    print("Could not find the specified convolutional layer in the ONNX model.")

# Print model input and output shapes
session = onnxruntime.InferenceSession(model_path)
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

input_shape = session.get_inputs()[0].shape
output_shape = session.get_outputs()[0].shape

print(f"Input shape: {input_shape}")
print(f"Output shape: {output_shape}")
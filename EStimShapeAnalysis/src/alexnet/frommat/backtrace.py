from typing import Tuple, List

import numpy as np
import onnx
import onnxruntime
from PIL import Image
from matplotlib import pyplot as plt
from torchvision import transforms as transforms

from src.pga.alexnet.onnx_parser import UnitIdentifier, LayerType


def backtrace(model_path: str, image_path: str, unit: int, x: int, y: int, exporter_function, top_conv2: int = 10,
              top_conv1: int = 10, top_pixels: int = 10):
    """
    Backtrace contributions through AlexNet layers, focusing on top N positive and negative contributions

    Args:
        model_path: Path to ONNX model
        image_path: Path to input image
        unit: Conv3 unit to analyze
        x: x-coordinate in Conv3 layer
        y: y-coordinate in Conv3 layer
        exporter_function: Function to export contribution data
        top_conv2: Number of top positive/negative Conv2 contributions to track
        top_conv1: Number of top positive/negative Conv1 contributions to track
        top_pixels: Number of top positive/negative pixel contributions to track
    """
    # Get layer weights
    model = onnx.load(model_path)
    conv3_weights = None
    conv2_weights = None
    for initializer in model.graph.initializer:
        if initializer.name == 'conv3_W':
            conv3_weights = onnx.numpy_helper.to_array(initializer)
            unit_weights = conv3_weights[unit]
        elif initializer.name == 'conv2_W':
            conv2_weights = onnx.numpy_helper.to_array(initializer)
        elif initializer.name == 'conv1_W':
            conv1_weights = onnx.numpy_helper.to_array(initializer)

    # Set up runtime session
    session = onnxruntime.InferenceSession(model_path)

    # Preprocess image
    transform = transforms.Compose([
        transforms.PILToTensor(),
        lambda x: x * 1.0
    ])
    image = Image.open(image_path).convert('RGB')
    input_tensor = transform(image)
    input_tensor = input_tensor.unsqueeze(0)

    # Get activations
    input_name = session.get_inputs()[0].name
    outputs = session.run(['conv3', 'pool2', 'norm2', 'relu2', 'conv2', 'pool1',
                           'norm1', 'relu1', 'conv1', 'data_Sub'],
                          {input_name: input_tensor.numpy()})

    conv3_activation = outputs[0][0, unit, x, y]
    pool2_activations = outputs[1][0]  # [256, 13, 13]
    norm2_activations = outputs[2][0]  # [256, 27, 27]
    relu2_activations = outputs[3][0]  # [256, 27, 27]
    conv2_activations = outputs[4][0]  # [256, 27, 27]
    pool1_activations = outputs[5][0]  # [96, 27, 27]
    norm1_activations = outputs[6][0]  # [96, 55, 55]
    relu1_activations = outputs[7][0]  # [96, 55, 55]
    conv1_activations = outputs[8][0]  # [96, 55, 55]
    image_data = outputs[9][0]  # [3, 224, 224]

    # Calculate Conv2 contributions
    pool2_contributions = calculate_pool_2_contributions(pool2_activations, unit_weights, x, y)
    conv2s_for_contributions = associate_with_conv2_units(norm2_activations)

    # Get top N positive and negative Conv2 contributions
    flat_contributions = pool2_contributions.flatten()
    flat_indices = np.arange(len(flat_contributions))

    # Top positive Conv2
    top_pos_conv2_indices = flat_indices[flat_contributions > 0][
        np.argsort(flat_contributions[flat_contributions > 0])[-top_conv2:]]
    # Top negative Conv2
    top_neg_conv2_indices = flat_indices[flat_contributions < 0][
        np.argsort(-flat_contributions[flat_contributions < 0])[-top_conv2:]]

    conv3_unit = UnitIdentifier(LayerType.CONV3, unit + 1, x + 1, y + 1)

    # Process top Conv2 contributions
    for conv2_idx in np.concatenate([top_pos_conv2_indices, top_neg_conv2_indices]):
        conv2_coords = np.unravel_index(conv2_idx, pool2_contributions.shape)
        conv2_channel, conv2_x, conv2_y = conv2s_for_contributions[conv2_coords]
        conv2_unit = UnitIdentifier(LayerType.CONV2, conv2_channel + 1, conv2_x + 1, conv2_y + 1)
        contribution = pool2_contributions[conv2_coords]

        # Export Conv3-Conv2 connection
        connection = (conv3_unit, conv2_unit)
        exporter_function(connection, contribution)

        # Calculate Conv1 contributions for this Conv2 unit
        unit_conv2_weights = conv2_weights[conv2_channel]
        pool1_contributions = calculate_pool_1_contributions(pool1_activations,
                                                             unit_conv2_weights,
                                                             conv2_channel,
                                                             conv2_x,
                                                             conv2_y)
        conv1s_for_contributions = associate_with_conv1_units(norm1_activations)

        # Get top N positive and negative Conv1 contributions
        flat_conv1_contributions = pool1_contributions.flatten()
        flat_conv1_indices = np.arange(len(flat_conv1_contributions))

        # Top positive Conv1
        top_pos_conv1_indices = flat_conv1_indices[flat_conv1_contributions > 0][
            np.argsort(flat_conv1_contributions[flat_conv1_contributions > 0])[-top_conv1:]]
        # Top negative Conv1
        top_neg_conv1_indices = flat_conv1_indices[flat_conv1_contributions < 0][
            np.argsort(-flat_conv1_contributions[flat_conv1_contributions < 0])[-top_conv1:]]

        # Process top Conv1 contributions
        for conv1_idx in np.concatenate([top_pos_conv1_indices, top_neg_conv1_indices]):
            conv1_coords = np.unravel_index(conv1_idx, pool1_contributions.shape)
            conv1_channel, conv1_x, conv1_y = conv1s_for_contributions[conv1_coords]
            conv1_unit = UnitIdentifier(LayerType.CONV1, conv1_channel + 1, conv1_x + 1, conv1_y + 1)
            conv1_contribution = pool1_contributions[conv1_coords]

            # Export Conv2-Conv1 connection
            connection = (conv2_unit, conv1_unit)
            exporter_function(connection, conv1_contribution)

            # Calculate pixel contributions for this Conv1 unit
            unit_conv1_weights = conv1_weights[conv1_channel]  # Shape [3, 11, 11]
            pixel_contributions = calculate_pixel_contributions(
                image_data,
                unit_conv1_weights,
                conv1_activations[conv1_channel],
                conv1_x,
                conv1_y
            )

            # Export pixel contributions
            pixels = get_top_contributing_pixels(pixel_contributions, top_k=top_pixels)
            for px, py, contribution in pixels:
                pixel_id = UnitIdentifier(LayerType.IMAGE, 0, px, py)
                connection = (conv1_unit, pixel_id)
                exporter_function(connection, contribution)


def plot_one_activation(model_path: str, image_path: str, unit: int, x: int, y: int, M: int = 3, N: int = 5):
    """Plot visualization of unit contributions with pixel importance overlays"""
    # Get conv1 weights for visualization
    model = onnx.load(model_path)
    conv1_weights = None
    for initializer in model.graph.initializer:
        if initializer.name == 'conv1_W':
            conv1_weights = onnx.numpy_helper.to_array(initializer)
            break

    # Load original image for overlays
    orig_image = plt.imread(image_path)

    # List to store all contribution data
    contribution_data = []
    current_conv2 = None
    current_conv1s = []
    current_pixels = []

    def collect_for_plot(connection: tuple[UnitIdentifier, UnitIdentifier], contribution: float):
        nonlocal current_conv2, current_conv1s, current_pixels
        from_unit, to_unit = connection

        if from_unit.layer == LayerType.CONV3:
            # Save previous group if exists
            if current_conv2 is not None and current_conv1s:
                contribution_data.append((current_conv2, current_conv1s[:], current_pixels[:]))
            # Start new Conv2 group
            current_conv2 = (to_unit.unit, to_unit.x, to_unit.y, contribution)
            current_conv1s = []
            current_pixels = []
        elif from_unit.layer == LayerType.CONV2:
            current_conv1s.append((to_unit.unit, to_unit.x, to_unit.y, contribution))
        elif isinstance(to_unit, str) and to_unit.startswith('pixel'):
            # Parse pixel coordinates from the ID
            px = int(to_unit.split('_')[1][1:])
            py = int(to_unit.split('_')[2][1:])
            current_pixels.append((px, py, contribution))

    # Collect contributions using backtrace
    backtrace(model_path, image_path, unit, x, y, collect_for_plot,
              top_conv2=M, top_conv1=N)

    # Save final group if exists
    if current_conv2 is not None and current_conv1s:
        contribution_data.append((current_conv2, current_conv1s[:], current_pixels[:]))

    if not contribution_data:
        print("No contributions found!")
        return []

    # Sort by positive Conv2 contribution and take top M
    contribution_data.sort(key=lambda x: x[0][3], reverse=True)
    contribution_data = contribution_data[:M]

    # Create figure with two columns per Conv1 unit: filter and pixel overlay
    fig = plt.figure(figsize=(N * 8, M * 4))

    # For each top Conv2 unit
    for m, (conv2_info, conv1_list, pixel_list) in enumerate(contribution_data):
        conv2_channel, conv2_x, conv2_y, conv2_contribution = conv2_info

        # Sort Conv1s by contribution and take top N
        conv1_list.sort(key=lambda x: x[3], reverse=True)
        top_conv1s = conv1_list[:N]

        # For each Conv1, create filter visualization and pixel overlay
        for n, (conv1_channel, conv1_x, conv1_y, conv1_contribution) in enumerate(top_conv1s):
            # Calculate subplot indices
            subplot_idx = m * (N * 2) + (n * 2) + 1

            # Filter visualization
            ax_filter = plt.subplot(M, N * 2, subplot_idx)

            # Get and normalize filter weights
            filter_weights = conv1_weights[conv1_channel]
            filter_weights = (filter_weights - filter_weights.min()) / (
                    filter_weights.max() - filter_weights.min())

            # Display filter
            ax_filter.imshow(np.transpose(filter_weights, (1, 2, 0)))
            ax_filter.axis('off')

            # Pixel contribution overlay
            ax_pixels = plt.subplot(M, N * 2, subplot_idx + 1)

            # Show original image
            ax_pixels.imshow(orig_image)

            # Create heatmap overlay
            overlay = np.zeros((224, 224))

            # Only use pixels associated with this Conv1 unit
            # Filter pixel_list to only include pixels for current Conv1
            relevant_pixels = [(px, py, val) for px, py, val in pixel_list]

            if relevant_pixels:
                pixel_coords = [(px, py) for px, py, _ in relevant_pixels]
                pixel_values = [val for _, _, val in relevant_pixels]

                # Normalize contribution values
                pixel_values = np.array(pixel_values)
                pixel_values = (pixel_values - pixel_values.min()) / (pixel_values.max() - pixel_values.min())

                # Place values in overlay
                for (px, py), val in zip(pixel_coords, pixel_values):
                    if 0 <= px < 224 and 0 <= py < 224:  # Check bounds
                        overlay[px, py] = val

                # Apply Gaussian blur to make overlay smoother
                from scipy.ndimage import gaussian_filter
                overlay = gaussian_filter(overlay, sigma=3)

                # Show overlay with transparency
                ax_pixels.imshow(overlay, cmap='hot', alpha=0.6)

            ax_pixels.axis('off')

            # Titles and labels
            if m == 0:
                ax_filter.set_title(f'Conv1 {conv1_channel}\nContr: {conv1_contribution:.2f}')
                ax_pixels.set_title('Important Pixels')

            if n == 0:
                ax_filter.set_ylabel(f'Conv2 {conv2_channel}\n'
                                     f'Pos ({conv2_x},{conv2_y})\n'
                                     f'Contr: {conv2_contribution:.2f}')

    plt.tight_layout()
    plt.show()

    return contribution_data

def calculate_pool_2_contributions(pool2_activations, conv3_unit_weights, x, y) -> np.ndarray:
    '''
    # Calculate contributions from pool2
    # For conv3 position (x,y), we need a 3x3 window of pool2 centered at that position

    '''
    contributions = np.zeros(shape=(256, 13, 13))

    kernel_size = 3
    pad = kernel_size // 2
    for i in range(256):  # For each pool2 channel
        for kx in range(kernel_size):
            for ky in range(kernel_size):
                # Get pool2 position
                pool2_x = x - pad + kx
                pool2_y = y - pad + ky

                # Check boundaries
                if 0 <= pool2_x < 13 and 0 <= pool2_y < 13:
                    weight = conv3_unit_weights[i, kx, ky]
                    pool2_activation = pool2_activations[i, pool2_x, pool2_y]
                    contribution = float(weight * pool2_activation)
                    contributions[i, pool2_x, pool2_y] = contribution
    print(np.max(contributions))
    return contributions


def associate_with_conv2_units(norm2_activations):
    '''

    Args:
        norm2_activations:

    Returns:

    '''
    # Map each pool2 to its source conv2
    associated_conv2s = np.zeros((256, 13, 13),
                                 dtype=tuple)  # Last dim stores (x,y) coordinates of the winner of relu, norm and pooling
    # For each pool2 activation
    for channel in range(256):
        for pool2_x in range(13):
            for pool2_y in range(13):
                # Get corresponding conv2 window
                pool_start_x = pool2_x * 2
                pool_start_y = pool2_y * 2

                # Find which conv2 unit in the 3x3 window had max activation
                max_val = float('-inf')
                max_pos = (0, 0)

                # Check 3x3 window in norm2 (pre-pooling)
                for px in range(3):
                    for py in range(3):
                        conv2_x = pool_start_x + px
                        conv2_y = pool_start_y + py

                        if conv2_x < 27 and conv2_y < 27:
                            curr_val = norm2_activations[channel, conv2_x, conv2_y]
                            if curr_val > max_val:
                                max_val = curr_val
                                max_pos = (conv2_x, conv2_y)
                        else:
                            print("Problem, conv2_x, conv2_y too high:", conv2_x, conv2_y)

                # Store the winning conv2 coordinates for this pool2 location
                associated_conv2s[channel, pool2_x, pool2_y] = (channel, max_pos[0], max_pos[1])
    return associated_conv2s


def calculate_pool_1_contributions(pool1_activations, conv2_weights, channel, x, y):
    '''
    Calculate contributions from pool1 to a specific conv2 unit, respecting AlexNet's split architecture
    Args:
        pool1_activations: shape [96, 27, 27]
        conv2_weights: weights for the specific conv2 unit we're analyzing, shape [48, 5, 5]
                      (only 48 inputs due to split architecture)
        channel: which conv2 channel we're analyzing
        x, y: position in conv2 space we're analyzing
    Returns:
        contributions: array of shape [96, 27, 27] showing each pool1 unit's contribution
    '''
    contributions = np.zeros(shape=(96, 27, 27))

    kernel_size = 5  # conv2 has 5x5 receptive field
    pad = kernel_size // 2

    # Determine which half of pool1 this conv2 unit connects to
    # First 128 conv2 units connect to first 48 pool1 channels
    # Last 128 conv2 units connect to last 48 pool1 channels
    pool1_start_idx = 48 if channel >= 128 else 0

    # For each connected pool1 channel (only 48 of them)
    for i in range(48):
        pool1_channel = pool1_start_idx + i
        for kx in range(kernel_size):
            for ky in range(kernel_size):
                # Get pool1 position
                pool1_x = x - pad + kx
                pool1_y = y - pad + ky

                # Check boundaries
                if 0 <= pool1_x < 27 and 0 <= pool1_y < 27:
                    weight = conv2_weights[i, kx, ky]  # weight from this pool1 to our conv2
                    pool1_activation = pool1_activations[pool1_channel, pool1_x, pool1_y]
                    contribution = float(weight * pool1_activation)
                    contributions[pool1_channel, pool1_x, pool1_y] = contribution

    return contributions


def associate_with_conv1_units(norm1_activations):
    '''
    Map each pool1 to its source conv1, considering split architecture
    Args:
        norm1_activations: shape [96, 55, 55]

    Returns:
        np.ndarray of size (96, 27, 27) containing tuples (channel, x, y)
        96: number of neurons in conv1
        27: kernel size of pool1 (is half of size of conv1 because pooling reduces by half)
        tuple: (channel in range 0-96, x coordinate in conv1 space, y coordinate in conv1 space)
    '''
    # Map each pool1 to its source conv1
    associated_conv1s = np.zeros((96, 27, 27), dtype=tuple)

    # For each pool1 activation (respecting split architecture)
    for channel in range(96):  # 96 total channels, split into two groups of 48
        for pool1_x in range(27):
            for pool1_y in range(27):
                # Get corresponding conv1 window
                pool_start_x = pool1_x * 2
                pool_start_y = pool1_y * 2

                # Find which conv1 unit in the 3x3 window had max activation
                max_val = float('-inf')
                max_pos = (0, 0)

                # Check 3x3 window in norm1 (pre-pooling)
                for px in range(3):
                    for py in range(3):
                        conv1_x = pool_start_x + px
                        conv1_y = pool_start_y + py

                        if conv1_x < 55 and conv1_y < 55:
                            curr_val = norm1_activations[channel, conv1_x, conv1_y]
                            if curr_val > max_val:
                                max_val = curr_val
                                max_pos = (conv1_x, conv1_y)

                # Store the winning conv1 coordinates for this pool1 location
                # Note: channel stays the same since split architecture is handled at conv2 level
                associated_conv1s[channel, pool1_x, pool1_y] = (channel, max_pos[0], max_pos[1])

    return associated_conv1s


def calculate_pixel_contributions(image_data: np.ndarray, conv1_weights: np.ndarray,
                                  conv1_activation: float, x: int, y: int) -> np.ndarray:
    """
    Calculate contribution of each input pixel to a Conv1 unit's activation using model's preprocessed input

    Args:
        image_data: Preprocessed image data from model [3, 224, 224]
        conv1_weights: Weights for this Conv1 unit [3, 11, 11]
        conv1_activation: Activation value for this Conv1 unit
        x, y: Position of Conv1 unit
    Returns:
        contributions: Array of shape [224, 224] with contribution values
    """
    kernel_size = 11  # Conv1 uses 11x11 kernels
    stride = 4  # Conv1 uses stride 4

    # Calculate input field bounds
    start_x = x * stride - kernel_size // 2
    start_y = y * stride - kernel_size // 2

    # Initialize contributions array to match image dimensions
    contributions = np.zeros((224, 224), dtype=float)

    # For each pixel in receptive field
    for kx in range(kernel_size):
        for ky in range(kernel_size):
            img_x = start_x + kx
            img_y = start_y + ky

            # Check image boundaries
            if 0 <= img_x < 227 and 0 <= img_y < 227:
                # Calculate contribution across channels
                for c in range(3):  # RGB channels
                    weight = conv1_weights[c, kx, ky]
                    pixel_value = image_data[c, img_x, img_y]
                    contributions[img_x, img_y] += (weight * pixel_value)

    return contributions

def get_top_contributing_pixels(contributions: np.ndarray, top_k: int = 25) -> List[Tuple[int, int, float]]:
    """Get coordinates and values of top contributing pixels"""
    flat_idx = np.argsort(contributions.ravel())[-top_k:]
    coords = np.unravel_index(flat_idx, contributions.shape)

    return [(coords[0][i], coords[1][i], contributions[coords[0][i], coords[1][i]])
            for i in range(len(flat_idx))]

if __name__ == "__main__":
    model_path = '/home/r2_allen/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3'
    image_path = '/home/r2_allen/Documents/EStimShape/allen_alexnet_lighting_exp_241028_0/stimuli/ga/pngs/1730133711234972_1730132722800937.png'

    # Get activation for unit 3 at position (6,6)
    # backtrace(model_path, image_path, unit=373, x=6, y=6, exporter_function=lambda x, y: None)
    plot_one_activation(model_path, image_path, unit=373, x=6, y=6, M=10, N=10)

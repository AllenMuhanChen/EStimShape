import numpy as np
import onnx
import onnxruntime
from PIL import Image
from matplotlib import pyplot as plt
from torchvision import transforms as transforms


def trace_one_activation(model_path: str, image_path: str, unit: int, x: int, y: int, M: int = 3, N: int = 5):
    # Get conv3 weights
    model = onnx.load(model_path)
    conv3_weights = None
    conv2_weights = None
    for initializer in model.graph.initializer:
        if initializer.name == 'conv3_W':
            conv3_weights = onnx.numpy_helper.to_array(initializer)
            unit_weights = conv3_weights[unit]  # Shape should be [256, 3, 3]
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
    outputs = session.run(['conv3', 'pool2', 'norm2', 'relu2', 'conv2', 'pool1', 'norm1'],
                          {input_name: input_tensor.numpy()})

    conv3_activation = outputs[0][0, unit, x, y]
    pool2_activations = outputs[1][0]  # [256, 13, 13]
    norm2_activations = outputs[2][0]  # [256, 27, 27]
    relu2_activations = outputs[3][0]  # [256, 27, 27]
    conv2_activations = outputs[4][0]  # [256, 27, 27]
    pool1_activations = outputs[5][0]  # [96, 27, 27]
    norm1_activations = outputs[6][0]  # [96, 55, 55]

    ### PURE MATH BELOW
    pool2_contributions = calculate_pool_2_contributions(pool2_activations, unit_weights, x, y)
    print(np.max(pool2_contributions))
    conv2s_for_contributions = associate_with_conv2_units(norm2_activations)

    # Get top M contributing conv2 units
    top_m_indices = np.argsort(pool2_contributions.flatten())[-M:][::-1]

    # Create figure for all visualizations
    fig = plt.figure(figsize=(N * 4, M * 4))

    # For each top conv2 unit
    for m, conv2_idx in enumerate(top_m_indices):
        # Get conv2 unit info
        channel, conv2_x, conv2_y = conv2s_for_contributions[np.unravel_index(conv2_idx, conv2s_for_contributions.shape)]
        contribution = pool2_contributions[np.unravel_index(conv2_idx, pool2_contributions.shape)]
        print(f"\nConv2 #{m + 1}: channel {channel} at ({conv2_x}, {conv2_y}), contribution: {contribution:.4f}")

        # Get weights for this conv2 unit
        unit_conv2_weights = conv2_weights[channel]

        # Calculate pool1 contributions for this conv2 unit
        pool1_contributions = calculate_pool_1_contributions(pool1_activations,
                                                             unit_conv2_weights,
                                                             channel,
                                                             conv2_x,
                                                             conv2_y)
        conv1s_for_contributions = associate_with_conv1_units(norm1_activations)

        # Get top N contributing conv1 units for this conv2 unit
        top_n_indices = np.argsort(pool1_contributions.flatten())[-N:][::-1]
        top_contributing_conv1s = [conv1s_for_contributions[np.unravel_index(idx, pool1_contributions.shape)]
                                   for idx in top_n_indices]

        # Create subplot row for this conv2 unit
        for n, (conv1_channel, conv1_x, conv1_y) in enumerate(top_contributing_conv1s):
            ax = plt.subplot(M, N, m * N + n + 1)

            # Get and normalize filter weights
            filter_weights = conv1_weights[conv1_channel]
            filter_weights = (filter_weights - filter_weights.min()) / (filter_weights.max() - filter_weights.min())

            # Display filter
            ax.imshow(np.transpose(filter_weights, (1, 2, 0)))
            ax.axis('off')

            # Title only for first row
            if m == 0:
                ax.set_title(f'Conv1 {conv1_channel}')

            # Conv2 info on left side
            if n == 0:
                ax.set_ylabel(f'Conv2 {channel}\nPos ({conv2_x},{conv2_y})\nContr: {contribution:.2f}')

    plt.tight_layout()
    plt.show()


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
        np.ndarray of size 256,13,13,2
        256: number of neurons in conv2
        13: kernel size of pool2 (is half of size of conv2 because pooling reduces by half)
        2: x,y coordinates of winner of relu, norm and mapping in conv2 space.
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


if __name__ == "__main__":
    model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX_with_conv3'
    image_path = '/run/user/1000/gvfs/sftp:host=172.30.6.80/home/r2_allen/Documents/EStimShape/allen_alexnet_lighting_exp_241028_0/stimuli/ga/pngs/1730133711318240_1730132722800937.png'

    # Get activation for unit 3 at position (6,6)
    trace_one_activation(model_path, image_path, unit=374, x=6, y=6, M=10, N=10)

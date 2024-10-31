import numpy as np
from PIL import Image
from scipy import ndimage
import matplotlib.pyplot as plt
from skimage.feature import peak_local_max
from scipy.spatial import Delaunay
from collections import defaultdict


def load_and_prepare_image(image_path):
    """Load image and convert to grayscale height field, creating mask for gray background."""
    # Load image without converting to grayscale first
    img = Image.open(image_path)
    img_array = np.array(img)

    # Create mask for non-gray pixels
    # If image is RGB, check for gray pixels (R=G=B)
    if len(img_array.shape) == 3:
        mask = ~((img_array[..., 0] == img_array[..., 1]) &
                 (img_array[..., 1] == img_array[..., 2]))
    else:
        # If image is already grayscale, assume all non-zero pixels are valid
        mask = img_array != 127  # Assuming 8-bit grayscale where gray is 127

    # Convert to grayscale and normalize
    img_gray = img.convert('L')
    height_field = np.array(img_gray, dtype=float) / 255.0

    # Apply mask to height field
    height_field[~mask] = np.nan

    return height_field, mask


def compute_gradient(height_field, mask):
    """Compute gradient field using Sobel operators, respecting masked regions."""
    # Fill NaN values temporarily for gradient computation
    height_field_filled = height_field.copy()
    height_field_filled[~mask] = 0

    gradient_y = ndimage.sobel(height_field_filled, axis=0)
    gradient_x = ndimage.sobel(height_field_filled, axis=1)

    # Zero out gradients in masked regions
    gradient_y[~mask] = 0
    gradient_x[~mask] = 0

    return np.stack([gradient_x, gradient_y], axis=-1)


def find_critical_points(height_field, gradient_field, mask, threshold=0.01):
    """Find maxima, minima, and saddle points, excluding masked regions."""
    gradient_magnitude = np.sqrt(np.sum(gradient_field ** 2, axis=-1))

    # Create masked versions for peak detection
    height_field_masked = height_field.copy()
    height_field_masked[~mask] = -np.inf  # For maxima detection

    max_min_distance = 10
    min_min_distance = 10
    max_rel_threshold = 0.2
    min_rel_threshold = 0.2

    # Find maxima in unmasked regions
    maxima = peak_local_max(height_field_masked,
                            min_distance=max_min_distance,
                            threshold_rel=max_rel_threshold,
                            num_peaks=20,
                            exclude_border=False)

    # Create inverse height field for minima detection
    valid_max = np.nanmax(height_field)
    height_field_inv = height_field.copy()
    height_field_inv[np.isnan(height_field_inv)] = valid_max

    minima = peak_local_max(valid_max - height_field_inv,
                            min_distance=min_min_distance,
                            threshold_rel=min_rel_threshold,
                            num_peaks=20,
                            exclude_border=False)

    # Saddle point detection
    potential_saddles = np.where((gradient_magnitude < threshold) & mask)
    saddles = []
    max_saddles = 30

    maxima_lookup = np.zeros_like(height_field, dtype=bool)
    minima_lookup = np.zeros_like(height_field, dtype=bool)
    maxima_lookup[maxima[:, 0], maxima[:, 1]] = True
    minima_lookup[minima[:, 0], minima[:, 1]] = True

    step = 2
    for i in range(0, len(potential_saddles[0]), step):
        if len(saddles) >= max_saddles:
            break

        y, x = potential_saddles[0][i], potential_saddles[1][i]

        if mask[y, x] and not (maxima_lookup[y, x] or minima_lookup[y, x]):
            hxx = ndimage.sobel(gradient_field[..., 0], axis=1)[y, x]
            hyy = ndimage.sobel(gradient_field[..., 1], axis=0)[y, x]
            hxy = ndimage.sobel(gradient_field[..., 0], axis=0)[y, x]

            if (hxx * hyy - hxy * hxy) < 0:
                saddles.append([y, x])

    # Ensure saddles is a 2D array even if empty
    saddles = np.array(saddles)
    if len(saddles) == 0:
        saddles = np.zeros((0, 2))  # Create empty 2D array with correct shape

    return maxima, saddles, minima

def trace_gradient_flow(point, gradient_field, mask, step_size=0.1, max_steps=1000):
    """Trace gradient flow from a point until reaching a critical point or masked region."""
    path = [point]
    current = np.array(point, dtype=float)

    for _ in range(max_steps):
        y, x = int(current[0]), int(current[1])
        if not (0 <= y < gradient_field.shape[0] - 1 and 0 <= x < gradient_field.shape[1] - 1):
            break

        # Stop if we hit a masked region
        if not mask[y, x]:
            break

        gradient = gradient_field[y, x]
        magnitude = np.sqrt(np.sum(gradient ** 2))

        if magnitude < 0.01:  # Near critical point
            break

        current = current + step_size * gradient / magnitude
        path.append(current.copy())

    return np.array(path)


def compute_morse_smale_complex(image_path):
    """Compute the Morse-Smale complex from an image, ignoring gray background."""
    # Load and prepare image
    height_field, mask = load_and_prepare_image(image_path)

    # Compute gradient field
    gradient_field = compute_gradient(height_field, mask)

    # Find critical points
    maxima, saddles, minima = find_critical_points(height_field, gradient_field, mask)

    # Initialize structures for edges
    ascending_manifolds = []
    descending_manifolds = []
    separatrices = {
        'ascending': [],  # Saddle to maximum connections
        'descending': [],  # Saddle to minimum connections
        'direct': []  # Direct maximum to minimum connections (for when no saddles exist)
    }

    if len(saddles) > 0:
        # Normal case with saddle points - compute manifolds from saddles
        for saddle_idx, saddle in enumerate(saddles):
            # Trace ascending manifold (towards maxima)
            ascending = trace_gradient_flow(saddle, gradient_field, mask)
            if len(ascending) > 0:
                ascending_manifolds.append(ascending)

                # Find connected maximum
                end_point = ascending[-1]
                end_y, end_x = int(end_point[0]), int(end_point[1])

                if len(maxima) > 0:
                    dists = np.sqrt(np.sum((maxima - [end_y, end_x]) ** 2, axis=1))
                    closest_max_idx = np.argmin(dists)
                    if dists[closest_max_idx] < 10:
                        separatrices['ascending'].append((saddle_idx, closest_max_idx))

            # Trace descending manifold (towards minima)
            descending = trace_gradient_flow(saddle, -gradient_field, mask)
            if len(descending) > 0:
                descending_manifolds.append(descending)

                end_point = descending[-1]
                end_y, end_x = int(end_point[0]), int(end_point[1])

                if len(minima) > 0:
                    dists = np.sqrt(np.sum((minima - [end_y, end_x]) ** 2, axis=1))
                    closest_min_idx = np.argmin(dists)
                    if dists[closest_min_idx] < 10:
                        separatrices['descending'].append((saddle_idx, closest_min_idx))

    else:
        # No saddle points - connect maxima and minima directly based on proximity
        if len(maxima) > 0 and len(minima) > 0:
            # For each maximum, find the closest minimum
            for max_idx, maximum in enumerate(maxima):
                dists = np.sqrt(np.sum((minima - maximum) ** 2, axis=1))
                closest_indices = np.argsort(dists)

                # Connect to the two closest minima
                for min_idx in closest_indices[:2]:
                    if dists[min_idx] < 100:  # Adjust threshold as needed
                        separatrices['direct'].append((max_idx, min_idx))

                        # Create a direct path between maximum and minimum
                        path = np.array([maximum, minima[min_idx]])
                        ascending_manifolds.append(path)

    return {
        'height_field': height_field,
        'gradient_field': gradient_field,
        'maxima': maxima,
        'minima': minima,
        'saddles': saddles,
        'ascending_manifolds': ascending_manifolds,
        'descending_manifolds': descending_manifolds,
        'separatrices': separatrices,
        'mask': mask
    }


def visualize_morse_smale(ms_complex):
    """Visualize the Morse-Smale complex with masked regions and edges."""
    plt.figure(figsize=(12, 12))

    # Create a masked array for visualization
    masked_height_field = np.ma.array(ms_complex['height_field'],
                                      mask=np.isnan(ms_complex['height_field']))

    # Plot height field
    plt.imshow(masked_height_field, cmap='gray')

    # Plot critical points with checks for empty arrays
    if len(ms_complex['maxima']) > 0:
        plt.plot(ms_complex['maxima'][:, 1], ms_complex['maxima'][:, 0], 'r.',
                 label='Maxima', markersize=10)

    if len(ms_complex['minima']) > 0:
        plt.plot(ms_complex['minima'][:, 1], ms_complex['minima'][:, 0], 'b.',
                 label='Minima', markersize=10)

    if len(ms_complex['saddles']) > 0:
        # Case with saddle points
        plt.plot(ms_complex['saddles'][:, 1], ms_complex['saddles'][:, 0], 'g.',
                 label='Saddles', markersize=10)

        # Plot manifolds with checks for empty arrays
        if ms_complex['ascending_manifolds']:
            for manifold in ms_complex['ascending_manifolds']:
                if len(manifold) > 0:
                    plt.plot(manifold[:, 1], manifold[:, 0], 'r-', alpha=0.3)

        if ms_complex['descending_manifolds']:
            for manifold in ms_complex['descending_manifolds']:
                if len(manifold) > 0:
                    plt.plot(manifold[:, 1], manifold[:, 0], 'b-', alpha=0.3)

        # Plot separatrices
        saddles = ms_complex['saddles']
        maxima = ms_complex['maxima']
        minima = ms_complex['minima']

        for saddle_idx, max_idx in ms_complex['separatrices']['ascending']:
            if saddle_idx < len(saddles) and max_idx < len(maxima):
                saddle = saddles[saddle_idx]
                maximum = maxima[max_idx]
                plt.plot([saddle[1], maximum[1]], [saddle[0], maximum[0]],
                         'r-', linewidth=2, alpha=0.7)

        for saddle_idx, min_idx in ms_complex['separatrices']['descending']:
            if saddle_idx < len(saddles) and min_idx < len(minima):
                saddle = saddles[saddle_idx]
                minimum = minima[min_idx]
                plt.plot([saddle[1], minimum[1]], [saddle[0], minimum[0]],
                         'b-', linewidth=2, alpha=0.7)

    else:
        # Case with no saddle points - draw direct connections between maxima and minima
        maxima = ms_complex['maxima']
        minima = ms_complex['minima']

        for max_idx, min_idx in ms_complex['separatrices']['direct']:
            if max_idx < len(maxima) and min_idx < len(minima):
                maximum = maxima[max_idx]
                minimum = minima[min_idx]
                plt.plot([maximum[1], minimum[1]], [maximum[0], minimum[0]],
                         'purple', linewidth=2, alpha=0.7)

    plt.legend()
    plt.title('Morse-Smale Complex')
    plt.show()
if __name__ == "__main__":
    # Replace with your image path
    image_path = "/home/r2_allen/Documents/EStimShape/allen_alexnet_lighting_exp_241028_0/stimuli/ga/pngs/1730133711234972_1730132722800937.png"
    ms_complex = compute_morse_smale_complex(image_path)
    visualize_morse_smale(ms_complex)
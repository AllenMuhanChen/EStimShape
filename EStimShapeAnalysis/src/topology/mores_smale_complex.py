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
    min_min_distance = 15
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

    # Improved saddle point detection
    saddles = []
    max_saddles = 10

    # Create a padded version of the height field for neighborhood analysis
    height_padded = np.pad(height_field, ((1, 1), (1, 1)), mode='edge')
    mask_padded = np.pad(mask, ((1, 1), (1, 1)), mode='constant', constant_values=False)

    # Adjust threshold for saddle detection
    saddle_threshold = 0.1  # Less restrictive threshold

    # Find potential saddle points
    potential_saddles = np.where((gradient_magnitude < saddle_threshold) & mask)

    for i in range(len(potential_saddles[0])):
        if len(saddles) >= max_saddles:
            break

        y, x = potential_saddles[0][i], potential_saddles[1][i]

        # Skip if too close to the boundary
        if y == 0 or y == height_field.shape[0] - 1 or x == 0 or x == height_field.shape[1] - 1:
            continue

        # Get 3x3 neighborhood
        neighborhood = height_field[y - 1:y + 2, x - 1:x + 2]
        mask_neighborhood = mask[y - 1:y + 2, x - 1:x + 2]

        if not np.all(mask_neighborhood):  # Skip if any neighbor is masked
            continue

        # Check if point is a saddle by looking at neighborhood structure
        neighbors = neighborhood.flatten()
        center_val = neighbors[4]  # Center point

        # Get the values higher and lower than the center
        higher = neighbors > center_val
        lower = neighbors < center_val

        # Count transitions between higher and lower values
        transitions = 0
        for j in range(8):
            if (higher[j] and lower[(j + 1) % 8]) or (lower[j] and higher[(j + 1) % 8]):
                transitions += 1

        # A saddle point should have at least 4 transitions
        if transitions >= 4:
            # Additional check: must have both higher and lower neighbors
            if np.any(higher) and np.any(lower):
                saddles.append([y, x])

    saddles = np.array(saddles)
    if len(saddles) == 0:
        saddles = np.zeros((0, 2))

    # Debug print
    print(f"Found {len(maxima)} maxima, {len(minima)} minima, and {len(saddles)} saddles")

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
        'descending': []  # Saddle to minimum connections
    }

    # For each saddle point, find its associated maximum and minimum
    for saddle_idx, saddle in enumerate(saddles):
        # Trace ascending manifold (towards maxima)
        ascending = trace_gradient_flow(saddle, gradient_field, mask)
        if len(ascending) > 0:
            ascending_manifolds.append(ascending)

            # Find connected maximum
            end_point = ascending[-1]
            end_y, end_x = int(end_point[0]), int(end_point[1])

            # Find the closest maximum
            if len(maxima) > 0:
                dists = np.sqrt(np.sum((maxima - [end_y, end_x]) ** 2, axis=1))
                closest_max_idx = np.argmin(dists)
                if dists[closest_max_idx] < 10:  # Distance threshold
                    separatrices['ascending'].append((saddle_idx, closest_max_idx))

        # Trace descending manifold (towards minima)
        descending = trace_gradient_flow(saddle, -gradient_field, mask)
        if len(descending) > 0:
            descending_manifolds.append(descending)

            # Find connected minimum
            end_point = descending[-1]
            end_y, end_x = int(end_point[0]), int(end_point[1])

            # Find the closest minimum
            if len(minima) > 0:
                dists = np.sqrt(np.sum((minima - [end_y, end_x]) ** 2, axis=1))
                closest_min_idx = np.argmin(dists)
                if dists[closest_min_idx] < 10:  # Distance threshold
                    separatrices['descending'].append((saddle_idx, closest_min_idx))

    # Count connections for each critical point
    max_connections = defaultdict(int)
    min_connections = defaultdict(int)
    saddle_ascending = defaultdict(int)
    saddle_descending = defaultdict(int)

    for saddle_idx, max_idx in separatrices['ascending']:
        max_connections[max_idx] += 1
        saddle_ascending[saddle_idx] += 1

    for saddle_idx, min_idx in separatrices['descending']:
        min_connections[min_idx] += 1
        saddle_descending[saddle_idx] += 1

    print(f"\nConnection statistics:")
    print(f"Number of maxima: {len(maxima)}, minima: {len(minima)}, saddles: {len(saddles)}")
    print(f"Maximum connections per maximum: {max(max_connections.values()) if max_connections else 0}")
    print(f"Maximum connections per minimum: {max(min_connections.values()) if min_connections else 0}")

    return {
        'height_field': height_field,
        'gradient_field': gradient_field,
        'maxima': maxima,
        'minima': minima,
        'saddles': saddles,
        'ascending_manifolds': ascending_manifolds,
        'descending_manifolds': descending_manifolds,
        'separatrices': separatrices,
        'mask': mask,
        'max_connections': dict(max_connections),
        'min_connections': dict(min_connections),
        'saddle_ascending': dict(saddle_ascending),
        'saddle_descending': dict(saddle_descending)
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
        plt.plot(ms_complex['saddles'][:, 1], ms_complex['saddles'][:, 0], 'g.',
                 label='Saddles', markersize=10)

    # Plot the flow lines with lower alpha for better visibility
    if ms_complex['ascending_manifolds']:
        for manifold in ms_complex['ascending_manifolds']:
            if len(manifold) > 0:
                plt.plot(manifold[:, 1], manifold[:, 0], 'r-', alpha=0.2)

    if ms_complex['descending_manifolds']:
        for manifold in ms_complex['descending_manifolds']:
            if len(manifold) > 0:
                plt.plot(manifold[:, 1], manifold[:, 0], 'b-', alpha=0.2)

    # Plot separatrices with varying transparency based on connection count
    saddles = ms_complex['saddles']
    maxima = ms_complex['maxima']
    minima = ms_complex['minima']

    max_conn = ms_complex['max_connections']
    min_conn = ms_complex['min_connections']
    #
    # # Plot ascending separatrices (saddle to maximum)
    # for saddle_idx, max_idx in ms_complex['separatrices']['ascending']:
    #     if saddle_idx < len(saddles) and max_idx < len(maxima):
    #         saddle = saddles[saddle_idx]
    #         maximum = maxima[max_idx]
    #         # Adjust alpha based on number of connections
    #         alpha = 1.0 / max(1, max_conn.get(max_idx, 1))
    #         plt.plot([saddle[1], maximum[1]], [saddle[0], maximum[0]],
    #                  'r-', linewidth=2, alpha=min(0.8, max(0.2, alpha)))
    #
    # # Plot descending separatrices (saddle to minimum)
    # for saddle_idx, min_idx in ms_complex['separatrices']['descending']:
    #     if saddle_idx < len(saddles) and min_idx < len(minima):
    #         saddle = saddles[saddle_idx]
    #         minimum = minima[min_idx]
    #         # Adjust alpha based on number of connections
    #         alpha = 1.0 / max(1, min_conn.get(min_idx, 1))
    #         plt.plot([saddle[1], minimum[1]], [saddle[0], minimum[0]],
    #                  'b-', linewidth=2, alpha=min(0.8, max(0.2, alpha)))

    plt.legend()
    plt.title(f'Morse-Smale Complex\n'
              f'Maxima: {len(maxima)}, Minima: {len(minima)}, Saddles: {len(saddles)}')
    plt.show()

if __name__ == "__main__":
    # Replace with your image path
    image_path = "/home/r2_allen/Documents/EStimShape/allen_alexnet_lighting_exp_241028_0/stimuli/ga/pngs/1730133711234972_1730132722800937.png"
    ms_complex = compute_morse_smale_complex(image_path)
    visualize_morse_smale(ms_complex)
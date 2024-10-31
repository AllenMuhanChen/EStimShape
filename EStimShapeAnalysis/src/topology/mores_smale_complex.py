import numpy as np
from PIL import Image
from scipy import ndimage
import matplotlib.pyplot as plt
from skimage.feature import peak_local_max
from scipy.spatial import Delaunay
from collections import defaultdict

def load_and_prepare_image(image_path):
    """Load image and convert to grayscale height field."""
    img = Image.open(image_path).convert('L')
    return np.array(img, dtype=float) / 255.0

def compute_gradient(height_field):
    """Compute gradient field using Sobel operators."""
    gradient_y = ndimage.sobel(height_field, axis=0)
    gradient_x = ndimage.sobel(height_field, axis=1)
    return np.stack([gradient_x, gradient_y], axis=-1)


def find_critical_points(height_field, gradient_field, threshold=0.01):
    """Find maxima, minima, and saddle points."""
    gradient_magnitude = np.sqrt(np.sum(gradient_field ** 2, axis=-1))

    # Separate parameters for maxima and minima
    max_min_distance = 15
    min_min_distance = 15

    # Different thresholds for maxima and minima
    max_rel_threshold = 0.2
    min_rel_threshold = 0.2

    maxima = peak_local_max(height_field,
                            min_distance=max_min_distance,
                            threshold_rel=max_rel_threshold,  # Changed to relative
                            num_peaks=20,
                            exclude_border=False)

    # Find minima with relative threshold
    # Apply Gaussian smoothing to help detect minima

    minima = peak_local_max(height_field.max() - height_field,
                            min_distance=min_min_distance,
                            threshold_rel=min_rel_threshold,  # Changed to relative
                            num_peaks=20,
                            exclude_border=False)


    # Saddle point detection
    potential_saddles = np.where(gradient_magnitude < threshold)
    saddles = []
    max_saddles = 30

    # Create lookup arrays
    maxima_lookup = np.zeros_like(height_field, dtype=bool)
    minima_lookup = np.zeros_like(height_field, dtype=bool)
    maxima_lookup[maxima[:, 0], maxima[:, 1]] = True
    minima_lookup[minima[:, 0], minima[:, 1]] = True

    step = 2
    for i in range(0, len(potential_saddles[0]), step):
        if len(saddles) >= max_saddles:
            break

        y, x = potential_saddles[0][i], potential_saddles[1][i]

        if not (maxima_lookup[y, x] or minima_lookup[y, x]):
            hxx = ndimage.sobel(gradient_field[..., 0], axis=1)[y, x]
            hyy = ndimage.sobel(gradient_field[..., 1], axis=0)[y, x]
            hxy = ndimage.sobel(gradient_field[..., 0], axis=0)[y, x]

            if (hxx * hyy - hxy * hxy) < 0:
                saddles.append([y, x])

    return maxima, np.array(saddles), minima

def trace_gradient_flow(point, gradient_field, step_size=0.1, max_steps=1000):
    """Trace gradient flow from a point until reaching a critical point."""
    path = [point]
    current = np.array(point, dtype=float)

    for _ in range(max_steps):
        # Interpolate gradient at current position
        y, x = int(current[0]), int(current[1])
        if not (0 <= y < gradient_field.shape[0]-1 and 0 <= x < gradient_field.shape[1]-1):
            break

        gradient = gradient_field[y, x]
        magnitude = np.sqrt(np.sum(gradient**2))

        if magnitude < 0.01:  # Near critical point
            break

        # Update position
        current = current + step_size * gradient / magnitude
        path.append(current.copy())

    return np.array(path)

def compute_morse_smale_complex(image_path):
    """Compute the Morse-Smale complex from an image."""
    # Load and prepare image
    height_field = load_and_prepare_image(image_path)

    # Compute gradient field
    gradient_field = compute_gradient(height_field)

    # Find critical points
    maxima, saddles, minima = find_critical_points(height_field, gradient_field)

    # Compute ascending and descending manifolds
    ascending_manifolds = []
    descending_manifolds = []

    # Trace from saddle points
    for saddle in saddles:
        # Trace ascending manifold
        ascending = trace_gradient_flow(saddle, gradient_field)
        ascending_manifolds.append(ascending)

        # Trace descending manifold
        descending = trace_gradient_flow(saddle, -gradient_field)
        descending_manifolds.append(descending)

    return {
        'height_field': height_field,
        'gradient_field': gradient_field,
        'maxima': maxima,
        'minima': minima,
        'saddles': saddles,
        'ascending_manifolds': ascending_manifolds,
        'descending_manifolds': descending_manifolds
    }

def visualize_morse_smale(ms_complex):
    """Visualize the Morse-Smale complex."""
    plt.figure(figsize=(12, 12))

    # Plot height field
    plt.imshow(ms_complex['height_field'], cmap='gray')

    # Plot critical points
    plt.plot(ms_complex['maxima'][:, 1], ms_complex['maxima'][:, 0], 'r.', label='Maxima')
    plt.plot(ms_complex['minima'][:, 1], ms_complex['minima'][:, 0], 'b.', label='Minima')
    plt.plot(ms_complex['saddles'][:, 1], ms_complex['saddles'][:, 0], 'g.', label='Saddles')

    # Plot manifolds
    for manifold in ms_complex['ascending_manifolds']:
        plt.plot(manifold[:, 1], manifold[:, 0], 'r-', alpha=0.5)
    for manifold in ms_complex['descending_manifolds']:
        plt.plot(manifold[:, 1], manifold[:, 0], 'b-', alpha=0.5)

    plt.legend()
    plt.title('Morse-Smale Complex')
    plt.show()

# Example usage
if __name__ == "__main__":
    # Replace with your image path
    image_path = "/home/r2_allen/Documents/EStimShape/allen_alexnet_lighting_exp_241028_0/stimuli/ga/pngs/1730133711234972_1730132722800937.png"
    ms_complex = compute_morse_smale_complex(image_path)
    visualize_morse_smale(ms_complex)
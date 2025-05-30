import numpy as np
import matplotlib.pyplot as plt
from scipy import fftpack, stats
from skimage import io, color as skcolor, exposure


def pixel_randomize_preserve_contrast(image, mask=None):
    """
    Shuffles pixels randomly within the foreground region while preserving the background.

    Args:
        image: Input image (can be color with alpha channel)
        mask: Binary mask (1 inside region to randomize, 0 outside)

    Returns:
        Pixel-shuffled image with background preserved
    """
    # Create a copy of the original image
    result = image.copy().astype(np.float32)

    # Extract alpha channel if exists
    if image.shape[2] == 4:
        rgb = result[:, :, :3]
        alpha = result[:, :, 3:4]
    else:
        rgb = result
        alpha = None

    # Handle mask creation if not provided
    if mask is None:
        # Create a mask where pixels are NOT equal to [38, 38, 38, 255]
        if image.shape[2] == 4:  # Image has alpha channel
            mask = np.logical_not(np.all(image[:, :, :3] == [38, 38, 38], axis=-1))
        else:  # RGB image
            mask = np.logical_not(np.all(image == [38, 38, 38], axis=-1))

    # Get the coordinates of all foreground pixels
    foreground_coords = np.where(mask)
    num_foreground_pixels = len(foreground_coords[0])

    if num_foreground_pixels == 0:
        # No foreground pixels to shuffle
        return result.astype(image.dtype)

    # Extract all foreground pixel values (RGB)
    foreground_pixels = rgb[foreground_coords]  # Shape: (num_pixels, 3)

    # Shuffle the pixel values
    shuffled_indices = np.random.permutation(num_foreground_pixels)
    shuffled_pixels = foreground_pixels[shuffled_indices]

    # Create the result image by copying the original
    rgb_shuffled = rgb.copy()

    # Replace the foreground pixels with shuffled values
    rgb_shuffled[foreground_coords] = shuffled_pixels

    # Reattach alpha channel if needed
    if alpha is not None:
        result = np.concatenate([rgb_shuffled, alpha], axis=2)
    else:
        result = rgb_shuffled

    # Convert back to original data type
    if image.dtype == np.uint8:
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result


def main():
    # Load the image
    image = io.imread(
        '/home/r2_allen/Documents/EStimShape/allen_ga_test_250417_0/stimuli/ga/pngs/1744994720353694.png')

    # Create the randomized image
    randomized_image = pixel_randomize_preserve_contrast(image)

    # Test if statistical properties are preserved
    def analyze_image_stats(img, name="Image"):
        if img.shape[2] == 4:  # Handle alpha channel
            rgb = img[:, :, :3]
        else:
            rgb = img

        # Normalize if needed
        if rgb.max() > 1.0:
            rgb_norm = rgb / 255.0
        else:
            rgb_norm = rgb

        # Convert to LAB
        lab = skcolor.rgb2lab(rgb_norm)
        L = lab[:, :, 0]  # Luminance

        # Create mask for non-background pixels
        if img.shape[2] == 4:  # Image has alpha channel
            mask = np.logical_not(np.all(img[:, :, :3] == [38, 38, 38], axis=-1))
        else:  # RGB image
            mask = np.logical_not(np.all(img == [38, 38, 38], axis=-1))

        # Get masked luminance values
        L_masked = L[mask]

        # Calculate statistics
        mean = np.mean(L_masked)
        std = np.std(L_masked)
        min_val = np.min(L_masked)
        max_val = np.max(L_masked)

        print(f"{name} Statistics:")
        print(f"  Mean Luminance: {mean:.2f}")
        print(f"  Std Dev: {std:.2f}")
        print(f"  Min: {min_val:.2f}")
        print(f"  Max: {max_val:.2f}")
        print(f"  Dynamic Range: {max_val - min_val:.2f}")

        return mean, std, min_val, max_val, L_masked

    # Analyze both images
    orig_mean, orig_std, orig_min, orig_max, orig_values = analyze_image_stats(image, "Original")
    rand_mean, rand_std, rand_min, rand_max, rand_values = analyze_image_stats(randomized_image, "Randomized")

    # Print differences
    print("\nDifferences:")
    print(f"  Mean: {abs(orig_mean - rand_mean):.2f}")
    print(f"  Std Dev: {abs(orig_std - rand_std):.2f}")
    print(f"  Min: {abs(orig_min - rand_min):.2f}")
    print(f"  Max: {abs(orig_max - rand_max):.2f}")

    # Display the original and randomized images along with histograms
    fig = plt.figure(figsize=(15, 10))

    # Image comparison
    plt.subplot(2, 2, 1)
    plt.title(f'Original Image\nMean: {orig_mean:.2f}, StdDev: {orig_std:.2f}')
    plt.imshow(image)
    plt.axis('off')

    plt.subplot(2, 2, 2)
    plt.title(f'Pixel Shuffled\nMean: {rand_mean:.2f}, StdDev: {rand_std:.2f}')
    plt.imshow(randomized_image)
    plt.axis('off')

    # Histogram comparison
    plt.subplot(2, 2, 3)
    plt.title('Luminance Histograms')
    plt.hist(orig_values, bins=50, alpha=0.5, label='Original', color='blue')
    plt.hist(rand_values, bins=50, alpha=0.5, label='Randomized', color='red')
    plt.legend()
    plt.grid(alpha=0.3)

    # Add power spectrum comparison
    plt.subplot(2, 2, 4)
    plt.title('Power Spectrum Comparison')

    # Function to calculate and plot power spectrum
    def plot_power_spectrum(img, plot_color, label, alpha=0.7):
        if img.shape[2] >= 3:
            # Convert to grayscale for spectrum analysis
            gray = skcolor.rgb2gray(img[:, :, :3])
        else:
            gray = img[:, :, 0]

        # Calculate 2D FFT
        f_transform = fftpack.fft2(gray)
        f_transform_shifted = np.fft.fftshift(f_transform)

        # Calculate power spectrum
        power_spectrum = np.abs(f_transform_shifted) ** 2

        # Calculate radial average (1D power spectrum)
        h, w = gray.shape
        center_y, center_x = h // 2, w // 2
        y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]
        r = np.sqrt(x * x + y * y)
        r = r.astype(np.int32)

        # Bin the radial values
        radial_bins = np.bincount(r.ravel(), weights=power_spectrum.ravel())
        radial_bins_count = np.bincount(r.ravel())
        radial_bins = radial_bins / radial_bins_count

        # Plot log-log scale
        plt.loglog(radial_bins[1:], color=plot_color, alpha=alpha, label=label)

    # Plot power spectra
    plot_power_spectrum(image, 'blue', 'Original')
    plot_power_spectrum(randomized_image, 'red', 'Randomized')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.xlabel('Spatial Frequency')
    plt.ylabel('Power')

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
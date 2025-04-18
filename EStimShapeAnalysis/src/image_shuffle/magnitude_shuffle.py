import numpy as np
import matplotlib.pyplot as plt
from scipy import fftpack, stats
from skimage import io, color as skcolor, exposure


def magnitude_randomize_preserve_contrast(image, mask=None):
    """
    Shuffles the magnitude while preserving phase information, color distribution,
    and average luminance through histogram matching.

    Args:
        image: Input image (can be color with alpha channel)
        mask: Binary mask (1 inside region to randomize, 0 outside)

    Returns:
        Magnitude-randomized image with preserved statistical properties
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

    # Normalize RGB to 0-1 range if needed
    if rgb.max() > 1.0:
        rgb_norm = rgb / 255.0
    else:
        rgb_norm = rgb

    # Convert to LAB color space
    lab = skcolor.rgb2lab(rgb_norm)

    # Extract luminance channel
    L = lab[:, :, 0]  # Luminance channel

    # Save the original luminance values in the masked region for histogram matching later
    L_masked_orig = L[mask]

    # Apply mask to luminance channel
    L_roi = L * mask

    # Apply Fourier transform to the ROI
    fft_L_roi = fftpack.fft2(L_roi)

    # Extract phase (which we'll keep)
    phase = np.angle(fft_L_roi)

    # Extract original magnitude (which we'll randomize)
    original_magnitude = np.abs(fft_L_roi)

    # Create a randomized version of the magnitude spectrum
    # We'll randomize by shuffling the magnitude values while preserving their distribution
    magnitude_values = original_magnitude.flatten()
    np.random.shuffle(magnitude_values)
    shuffled_magnitude = magnitude_values.reshape(original_magnitude.shape)

    # Preserve DC component (0,0) magnitude to maintain average intensity
    shuffled_magnitude[0, 0] = original_magnitude[0, 0]

    # Combine shuffled magnitude with original phase
    real_part = shuffled_magnitude * np.cos(phase)
    imag_part = shuffled_magnitude * np.sin(phase)
    randomized_fft = real_part + 1j * imag_part

    # Apply inverse Fourier transform
    randomized_L_roi = np.real(fftpack.ifft2(randomized_fft))

    # Create a new luminance channel that replaces the masked region
    randomized_L = L.copy()
    randomized_L[mask] = randomized_L_roi[mask]

    # Now perform histogram matching to ensure the luminance distribution is preserved
    # Extract the randomized values in the masked region
    randomized_values = randomized_L[mask]

    # Match the histogram of the randomized values to the original values
    matched_values = exposure.match_histograms(
        randomized_values.reshape(-1, 1),
        L_masked_orig.reshape(-1, 1)
    ).flatten()

    # Replace the values in the randomized luminance channel
    L_matched = L.copy()
    L_matched[mask] = matched_values

    # Recombine LAB channels
    lab_new = lab.copy()
    lab_new[:, :, 0] = L_matched

    # Convert back to RGB
    rgb_new = skcolor.lab2rgb(lab_new)

    # Scale back to original range if needed
    if image.max() > 1.0:
        rgb_new = rgb_new * 255.0

    # Reattach alpha channel if needed
    if alpha is not None:
        result = np.concatenate([rgb_new, alpha], axis=2)
    else:
        result = rgb_new

    # Convert back to original data type
    if image.dtype == np.uint8:
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result


def main():
    # Load the image
    image = io.imread(
        '/home/r2_allen/Documents/EStimShape/allen_ga_test_250417_0/stimuli/ga/pngs/1744994720396364.png')

    # Create the randomized image
    randomized_image = magnitude_randomize_preserve_contrast(image)

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
    plt.title(f'Magnitude Randomized (Phase Preserved)\nMean: {rand_mean:.2f}, StdDev: {rand_std:.2f}')
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
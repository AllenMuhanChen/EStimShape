import numpy as np
from matplotlib import pyplot as plt
from scipy import fftpack, ndimage
from skimage import color as skcolor


def create_boundary_subtraction_image(image, mask, erosion_iterations=2):
    """
    Create an image for boundary subtraction that isolates interior content.

    This creates an image with:
    - Original boundary pixels (from erosion-removed region)
    - Interior filled with interior average value
    - Same sharp edges as original for perfect cancellation

    Args:
        image: Input image (luminance channel)
        mask: Binary mask of region to process
        erosion_iterations: Number of erosion iterations to define interior

    Returns:
        subtraction_image: Image to subtract from original in frequency domain
    """
    # Create interior mask (well away from boundaries)
    interior_mask = ndimage.binary_erosion(mask, iterations=erosion_iterations)

    # Create boundary mask (what erosion removed)
    boundary_mask = mask & ~interior_mask

    # Create subtraction image
    subtraction_image = np.zeros_like(image)

    # Keep boundary pixels from original
    subtraction_image[boundary_mask] = image[boundary_mask]

    # Fill interior with interior average
    if np.any(interior_mask):
        interior_average = np.mean(image[interior_mask])
        subtraction_image[interior_mask] = interior_average

    return subtraction_image


def get_clean_interior_fft(image, mask, erosion_iterations=2):
    """
    Get FFT of interior content with boundary artifacts removed.

    Args:
        image: Input image (luminance channel)
        mask: Binary mask of region to process
        erosion_iterations: Number of erosion iterations

    Returns:
        fft_clean: FFT with boundary artifacts cancelled out
    """
    # Create boundary subtraction image
    boundary_image = create_boundary_subtraction_image(image, mask, erosion_iterations)

    # Original masked image
    original_masked = image * mask

    # Subtract in frequency domain to cancel boundary artifacts
    fft_original = fftpack.fft2(original_masked)
    fft_boundary = fftpack.fft2(boundary_image)
    fft_clean = fft_original - fft_boundary

    return fft_clean


def apply_clean_interior_processing(image, mask, processing_func, erosion_iterations=2):
    """
    Apply frequency domain processing with clean boundary handling.

    Uses the approach: original - boundary_with_average = interior_variations
    Then: processed_interior_variations + boundary_with_average = final_result

    Args:
        image: Input image (luminance channel)
        mask: Binary mask of region to process
        processing_func: Function that takes FFT and returns modified FFT
        erosion_iterations: Number of erosion iterations

    Returns:
        processed_image: Processed image with clean boundaries
    """
    # Step 1: Get clean interior FFT (original - boundary_with_average)
    fft_clean_interior = get_clean_interior_fft(image, mask, erosion_iterations)

    # Step 2: Apply processing function to clean interior content
    fft_processed_interior = processing_func(fft_clean_interior)

    # Step 3: Convert processed interior back to spatial domain
    processed_interior_variations = np.real(fftpack.ifft2(fft_processed_interior))

    # Step 4: Reconstruct full image by adding back boundary image
    boundary_image = create_boundary_subtraction_image(image, mask, erosion_iterations)
    result = processed_interior_variations + boundary_image

    return result


def plot_orientation_spectrum(img, plot_color, label, alpha=0.7):
    """Plot orientation-specific power spectrum using clean interior method"""
    if img.shape[2] >= 3:
        # Convert to grayscale for spectrum analysis
        gray = skcolor.rgb2gray(img[:, :, :3])
    else:
        gray = img[:, :, 0]

    # Apply the same masking as used in processing for fair comparison
    if img.shape[2] == 4:  # Image has alpha channel
        rgb_for_background = img[:, :, :3]
    else:  # RGB image
        rgb_for_background = img

    # Find background pixel
    pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])
    unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)
    background_pixel = unique_pixels[np.argmax(counts)]

    # Create mask
    if img.shape[2] == 4:  # Image has alpha channel
        mask = np.logical_not(np.all(img[:, :, :3] == background_pixel, axis=-1))
    else:  # RGB image
        mask = np.logical_not(np.all(img == background_pixel, axis=-1))

    # Use same clean interior approach as processing
    fft_clean_interior = get_clean_interior_fft(gray, mask, erosion_iterations=2)
    f_transform_shifted = np.fft.fftshift(fft_clean_interior)

    # Calculate power spectrum
    power_spectrum = np.abs(f_transform_shifted) ** 2

    # Get image dimensions and center
    h, w = gray.shape
    center_y, center_x = h // 2, w // 2

    # Simply exclude ONLY the DC component (cleanest approach)
    power_spectrum_no_dc = power_spectrum.copy()
    power_spectrum_no_dc[center_y, center_x] = 0

    # Create coordinate arrays
    y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]

    # Calculate angles (orientation) for each point
    angles = np.arctan2(y, x)

    # Convert to degrees and normalize to 0-180 range (since power spectrum is symmetric)
    angles_deg = np.degrees(angles) % 180

    # Create orientation bins
    orientation_bins = np.arange(0, 181, 5)  # 5-degree bins from 0 to 180
    orientation_power = np.zeros(len(orientation_bins) - 1)

    # Calculate power for each orientation bin
    for i in range(len(orientation_bins) - 1):
        angle_min = orientation_bins[i]
        angle_max = orientation_bins[i + 1]

        # Create mask for this orientation range
        angle_mask = (angles_deg >= angle_min) & (angles_deg < angle_max)

        # Sum power in this orientation
        if np.any(angle_mask):
            orientation_power[i] = np.mean(power_spectrum_no_dc[angle_mask])

    # NORMALIZE BY TOTAL POWER (this was missing!)
    total_power = np.sum(orientation_power)
    if total_power > 0:
        orientation_power_normalized = orientation_power / total_power
    else:
        orientation_power_normalized = orientation_power

    # Plot orientation spectrum
    bin_centers = (orientation_bins[:-1] + orientation_bins[1:]) / 2
    plt.plot(bin_centers, orientation_power_normalized, color=plot_color, alpha=alpha, label=label, linewidth=2)


def plot_2d_power_spectrum_diff(original_img, randomized_img):
    """Plot 2D power spectrum difference visualization"""

    def get_2d_power_spectrum(img):
        if img.shape[2] >= 3:
            gray = skcolor.rgb2gray(img[:, :, :3])
        else:
            gray = img[:, :, 0]

        # Apply the same masking as used in processing for fair comparison
        if img.shape[2] == 4:  # Image has alpha channel
            rgb_for_background = img[:, :, :3]
        else:  # RGB image
            rgb_for_background = img

        # Find background pixel
        pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])
        unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)
        background_pixel = unique_pixels[np.argmax(counts)]

        # Create mask
        if img.shape[2] == 4:  # Image has alpha channel
            mask = np.logical_not(np.all(img[:, :, :3] == background_pixel, axis=-1))
        else:  # RGB image
            mask = np.logical_not(np.all(img == background_pixel, axis=-1))

        # Use same clean interior approach as processing
        fft_clean_interior = get_clean_interior_fft(gray, mask, erosion_iterations=2)
        f_transform_shifted = np.fft.fftshift(fft_clean_interior)
        power_spectrum = np.abs(f_transform_shifted) ** 2

        # Exclude DC component for consistency with orientation analysis
        h, w = gray.shape
        center_y, center_x = h // 2, w // 2
        power_spectrum_no_dc = power_spectrum.copy()
        power_spectrum_no_dc[center_y, center_x] = 0

        return power_spectrum_no_dc

    orig_power = get_2d_power_spectrum(original_img)
    rand_power = get_2d_power_spectrum(randomized_img)

    # Normalize by total power for fair comparison
    orig_total = np.sum(orig_power)
    rand_total = np.sum(rand_power)

    if orig_total > 0 and rand_total > 0:
        orig_power_norm = orig_power / orig_total
        rand_power_norm = rand_power / rand_total
        power_diff = rand_power_norm - orig_power_norm
    else:
        power_diff = rand_power - orig_power

    # Display the difference
    im = plt.imshow(power_diff, cmap='RdBu_r', origin='lower')
    plt.colorbar(im, label='Normalized Power Difference')
    plt.xlabel('Frequency X')
    plt.ylabel('Frequency Y')


def create_analysis_plot(original_image, randomized_image, output_path, title):
    """
    Create analysis plot showing histograms and power spectrum comparison.

    Args:
        original_image: Original image array
        randomized_image: Phase-randomized image array
        output_path: Path to save the analysis plot
    """

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

        # Create mask for non-background pixels (find most common pixel as background)
        if img.shape[2] == 4:  # Image has alpha channel
            rgb_for_background = img[:, :, :3]
        else:  # RGB image
            rgb_for_background = img

        # Reshape to (num_pixels, num_channels) for easier processing
        pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])

        # Find unique pixels and their counts
        unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)

        # Get the most common pixel value (background)
        background_pixel = unique_pixels[np.argmax(counts)]

        # Create mask for non-background pixels
        if img.shape[2] == 4:  # Image has alpha channel
            mask = np.logical_not(np.all(img[:, :, :3] == background_pixel, axis=-1))
        else:  # RGB image
            mask = np.logical_not(np.all(img == background_pixel, axis=-1))

        # Get masked luminance values
        L_masked = L[mask]

        # Calculate statistics
        mean = np.mean(L_masked)
        std = np.std(L_masked)
        min_val = np.min(L_masked)
        max_val = np.max(L_masked)

        return mean, std, min_val, max_val, L_masked

    def plot_power_spectrum(img, plot_color, label, alpha=0.7):
        if img.shape[2] >= 3:
            # Convert to grayscale for spectrum analysis
            gray = skcolor.rgb2gray(img[:, :, :3])
        else:
            gray = img[:, :, 0]

        # Find background pixel and create mask (same as other functions)
        if img.shape[2] == 4:  # Image has alpha channel
            rgb_for_background = img[:, :, :3]
        else:  # RGB image
            rgb_for_background = img

        pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])
        unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)
        background_pixel = unique_pixels[np.argmax(counts)]

        if img.shape[2] == 4:  # Image has alpha channel
            mask = np.logical_not(np.all(img[:, :, :3] == background_pixel, axis=-1))
        else:  # RGB image
            mask = np.logical_not(np.all(img == background_pixel, axis=-1))

        # Use clean interior approach for consistency
        fft_clean_interior = get_clean_interior_fft(gray, mask, erosion_iterations=2)
        f_transform_shifted = np.fft.fftshift(fft_clean_interior)

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

    # Analyze both images
    orig_mean, orig_std, orig_min, orig_max, orig_values = analyze_image_stats(original_image, "Original")
    rand_mean, rand_std, rand_min, rand_max, rand_values = analyze_image_stats(randomized_image, "Randomized")

    # Create the analysis plot
    fig = plt.figure(figsize=(20, 12))

    # Image comparison
    plt.subplot(2, 3, 1)
    plt.title(f'Original Image\nMean: {orig_mean:.2f}, StdDev: {orig_std:.2f}')
    plt.imshow(original_image)
    plt.axis('off')

    plt.subplot(2, 3, 2)
    plt.title(f'{title}\nMean: {rand_mean:.2f}, StdDev: {rand_std:.2f}')
    plt.imshow(randomized_image)
    plt.axis('off')

    # Histogram comparison
    plt.subplot(2, 3, 3)
    plt.title('Luminance Histograms')
    plt.hist(orig_values, bins=50, alpha=0.5, label='Original', color='blue')
    plt.hist(rand_values, bins=50, alpha=0.5, label='Randomized', color='red')
    plt.legend()
    plt.grid(alpha=0.3)

    # Radial power spectrum comparison
    plt.subplot(2, 3, 4)
    plt.title('Radial Power Spectrum')
    plot_power_spectrum(original_image, 'blue', 'Original')
    plot_power_spectrum(randomized_image, 'red', 'Randomized')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.xlabel('Spatial Frequency')
    plt.ylabel('Power')

    # Orientation power spectrum comparison
    plt.subplot(2, 3, 5)
    plt.title('Orientation Power Spectrum')
    plot_orientation_spectrum(original_image, 'blue', 'Original')
    plot_orientation_spectrum(randomized_image, 'red', 'Randomized')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.xlabel('Orientation (degrees)')
    plt.ylabel('Power')

    # 2D Power spectrum visualization
    plt.subplot(2, 3, 6)
    plt.title('2D Power Spectrum Difference')
    plot_2d_power_spectrum_diff(original_image, randomized_image)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()  # Close to free memory
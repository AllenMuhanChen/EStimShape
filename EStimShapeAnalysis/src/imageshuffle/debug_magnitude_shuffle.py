import numpy as np
from matplotlib import pyplot as plt
from scipy import fftpack, ndimage
from skimage import color as skcolor


def create_boundary_subtraction_image(image, mask, erosion_iterations=5):
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


def get_clean_interior_fft(image, mask, erosion_iterations=5):
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


def apply_clean_interior_processing(image, mask, processing_func, erosion_iterations=5):
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


def plot_phase_changes_by_frequency_orientation(original_img, randomized_img, original_fft=None, processed_fft=None):
    """
    Plot how phase changes vary by frequency and orientation.

    CORRECTED VERSION: Uses actual interior FFTs when available, instead of trying to
    reverse-engineer them from reconstructed images.

    Args:
        original_img: Original image (for fallback analysis)
        randomized_img: Processed image (for fallback analysis)
        original_fft: Original clean interior FFT (preferred)
        processed_fft: Processed clean interior FFT (preferred)
    """

    # Use direct FFT comparison if available (most accurate)
    if original_fft is not None and processed_fft is not None:
        # Direct analysis of actual FFTs that were processed
        orig_fft_shifted = np.fft.fftshift(original_fft)
        proc_fft_shifted = np.fft.fftshift(processed_fft)

        # Calculate phase differences
        orig_phase = np.angle(orig_fft_shifted)
        proc_phase = np.angle(proc_fft_shifted)

        print(f"Using direct FFT analysis (accurate)")
        print(f"  Original FFT shape: {original_fft.shape}")
        print(f"  Processed FFT shape: {processed_fft.shape}")

    else:
        # Fallback: Try to extract interior FFT from reconstructed images (less accurate)
        print(f"Warning: Using fallback analysis (may include reconstruction artifacts)")

        def get_fft_data_fallback(img):
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

            return f_transform_shifted

        # Get FFT data for both images using fallback method
        orig_fft_shifted = get_fft_data_fallback(original_img)
        proc_fft_shifted = get_fft_data_fallback(randomized_img)

        # Calculate phase differences
        orig_phase = np.angle(orig_fft_shifted)
        proc_phase = np.angle(proc_fft_shifted)

    # Phase difference with proper circular wrapping
    # This gives the shortest angular distance between phases
    phase_diff = proc_phase - orig_phase

    # Wrap to [-π, π] range (shortest path on circle)
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))

    # Calculate absolute phase change (magnitude of change regardless of direction)
    abs_phase_change = np.abs(phase_diff)

    # Get image dimensions and center
    h, w = orig_fft_shifted.shape
    center_y, center_x = h // 2, w // 2

    # Create coordinate arrays
    y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]

    # Calculate frequency (distance from center)
    frequency = np.sqrt(x * x + y * y)

    # Calculate orientation angles
    angles = np.arctan2(y, x)
    angles_deg = np.degrees(angles) % 180  # 0-180 range

    # Exclude DC component
    mask_no_dc = frequency > 0

    # Print verification statistics
    max_phase_change = np.max(abs_phase_change[mask_no_dc])
    mean_phase_change = np.mean(abs_phase_change[mask_no_dc])

    print(f"Phase change statistics:")
    print(f"  Max phase change: {max_phase_change:.8f} radians")
    print(f"  Mean phase change: {mean_phase_change:.8f} radians")

    if original_fft is not None and processed_fft is not None:
        print(f"  Expected for magnitude shuffle: ~0 (phase should be preserved)")
        if max_phase_change < 1e-6:
            print(f"  ✓ Phase preservation confirmed")
        else:
            print(f"  ✗ Unexpected phase changes detected")
    else:
        print(f"  Note: Using fallback analysis (may include artifacts)")

    # Create frequency bins (log scale for better distribution)
    freq_values = frequency[mask_no_dc]
    min_freq = np.log10(np.maximum(freq_values.min(), 1))
    max_freq = np.log10(freq_values.max())
    freq_bins_log = np.linspace(min_freq, max_freq, 10)
    freq_bins = 10 ** freq_bins_log

    # Create orientation bins
    orientation_bins = np.arange(0, 181, 18)  # 18-degree bins

    # Create 2D histogram of phase changes
    phase_change_matrix = np.zeros((len(freq_bins) - 1, len(orientation_bins) - 1))

    for i in range(len(freq_bins) - 1):
        freq_mask = (frequency >= freq_bins[i]) & (frequency < freq_bins[i + 1]) & mask_no_dc

        for j in range(len(orientation_bins) - 1):
            angle_mask = (angles_deg >= orientation_bins[j]) & (angles_deg < orientation_bins[j + 1])

            combined_mask = freq_mask & angle_mask

            if np.any(combined_mask):
                phase_change_matrix[i, j] = np.mean(abs_phase_change[combined_mask])

    # Create the plot
    freq_centers = (freq_bins[:-1] + freq_bins[1:]) / 2
    orientation_centers = (orientation_bins[:-1] + orientation_bins[1:]) / 2

    # Create meshgrid for plotting
    X, Y = np.meshgrid(orientation_centers, freq_centers)

    # Plot as heatmap
    im = plt.pcolormesh(X, Y, phase_change_matrix, cmap='viridis', shading='auto')
    plt.colorbar(im, label='Mean |Phase Change| (radians)')
    plt.xlabel('Orientation (degrees)')
    plt.ylabel('Spatial Frequency')
    plt.yscale('log')

    # Add contour lines for better readability
    plt.contour(X, Y, phase_change_matrix, levels=5, colors='white', alpha=0.3, linewidths=0.5)


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
        fft_clean_interior = get_clean_interior_fft(gray, mask, erosion_iterations=5)
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


def create_analysis_plot(original_image, randomized_image, output_path, title,
                         original_fft=None, processed_fft=None, algorithm_type="spatial"):
    """
    Create analysis plot showing histograms and power spectrum comparison.

    CORRECTED VERSION: Uses actual interior FFTs for phase analysis when available.

    Args:
        original_image: Original image array
        randomized_image: Phase-randomized image array
        output_path: Path to save the analysis plot
        title: Title for the plot
        original_fft: Original clean interior FFT (for accurate phase analysis)
        processed_fft: Processed clean interior FFT (for accurate phase analysis)
        algorithm_type: "spatial" for pixel shuffle, "fft" for magnitude/phase shuffle
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

    # Phase change analysis by frequency and orientation - CORRECTED VERSION
    plt.subplot(2, 3, 6)
    plt.title('Phase Changes by Frequency & Orientation')
    plot_phase_changes_by_frequency_orientation(
        original_image, randomized_image,
        original_fft=original_fft, processed_fft=processed_fft
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()  # Close to free memory
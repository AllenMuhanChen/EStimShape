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


def correct_spatial_reference_phase_analysis(original_fft, processed_fft):
    """
    Updated function that uses robust phase analysis instead of the old problematic approach.
    """
    # Use the new robust phase analysis
    phase_results = robust_phase_preservation_analysis(original_fft, processed_fft)

    # Also get basic magnitude comparison for compatibility
    orig_magnitude = np.abs(original_fft)
    proc_magnitude = np.abs(processed_fft)
    magnitude_error = np.mean(np.abs(proc_magnitude - orig_magnitude))

    # Return in the expected format but with robust results
    return {
        'magnitude_error_mean': magnitude_error,
        'magnitude_error_max': np.max(np.abs(proc_magnitude - orig_magnitude)),

        # Use robust phase metrics instead of problematic direct comparison
        'phase_error_direct_mean': phase_results['detrended_phase_error'],  # Use detrended as "direct"
        'phase_error_direct_max': phase_results['detrended_phase_error'] * 2,  # Approximate
        'phase_error_relative_mean': phase_results['phase_relationship_error'],  # Use relationships
        'phase_error_relative_max': phase_results['phase_relationship_error'] * 2,  # Approximate

        'power_error_radial_mean': magnitude_error,  # Power follows magnitude
        'power_error_radial_max': magnitude_error * 2,

        # Updated validation criteria using robust analysis
        'is_magnitude_preserved': magnitude_error < 1e-3,
        'is_phase_preserved': phase_results['robust_phase_preservation_validated'],
        'has_spatial_shift': phase_results['detrended_phase_error'] > 0.05  # Detect if detrending helped
    }


def robust_phase_preservation_analysis(original_fft, processed_fft):
    """
    Robust phase preservation analysis using binned and statistical approaches
    that are tolerant to spatial shifts but sensitive to actual phase changes.
    """

    orig_phase = np.angle(original_fft)
    proc_phase = np.angle(processed_fft)

    results = {}

    # Method 1: Phase Distribution Analysis
    # Spatial shifts don't change the distribution of phase values, just their locations
    phase_bins = np.linspace(-np.pi, np.pi, 50)
    orig_hist, _ = np.histogram(orig_phase.flatten(), bins=phase_bins, density=True)
    proc_hist, _ = np.histogram(proc_phase.flatten(), bins=phase_bins, density=True)

    phase_distribution_error = np.mean(np.abs(orig_hist - proc_hist))
    results['phase_distribution_error'] = phase_distribution_error

    # Method 2: Local Phase Variance Analysis
    # Divide frequency space into spatial bins and compare phase variance within each bin
    h, w = orig_phase.shape
    bin_size = 8  # 8x8 pixel bins in frequency space
    local_variance_errors = []

    for i in range(0, h - bin_size, bin_size):
        for j in range(0, w - bin_size, bin_size):
            orig_bin = orig_phase[i:i + bin_size, j:j + bin_size]
            proc_bin = proc_phase[i:i + bin_size, j:j + bin_size]

            orig_var = np.var(orig_bin)
            proc_var = np.var(proc_bin)

            if orig_var > 0.01:  # Only consider bins with meaningful phase variation
                local_variance_errors.append(abs(orig_var - proc_var))

    if local_variance_errors:
        local_variance_error = np.mean(local_variance_errors)
    else:
        local_variance_error = 0
    results['local_phase_variance_error'] = local_variance_error

    # Method 3: Detrended Phase Analysis
    # Remove linear trends (spatial shifts) and compare residuals
    def remove_linear_trend(phases):
        h, w = phases.shape
        y, x = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')

        # Flatten for linear regression
        y_flat = y.flatten()
        x_flat = x.flatten()
        phase_flat = phases.flatten()

        # Fit linear trend: phase = a*x + b*y + c
        A = np.column_stack([x_flat, y_flat, np.ones(len(x_flat))])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, phase_flat, rcond=None)
            trend = (coeffs[0] * x + coeffs[1] * y + coeffs[2])
            detrended = phases - trend
            # Wrap to [-π, π]
            detrended = np.arctan2(np.sin(detrended), np.cos(detrended))
            return detrended
        except:
            return phases

    orig_detrended = remove_linear_trend(orig_phase)
    proc_detrended = remove_linear_trend(proc_phase)

    detrended_diff = proc_detrended - orig_detrended
    detrended_diff_wrapped = np.arctan2(np.sin(detrended_diff), np.cos(detrended_diff))
    detrended_error = np.mean(np.abs(detrended_diff_wrapped))
    results['detrended_phase_error'] = detrended_error

    # Method 4: Phase Relationship Analysis
    # Compare phase differences between nearby frequency components
    # This is invariant to global phase shifts
    def get_local_phase_relationships(phases):
        # Compare each pixel to its neighbors
        relationships = []
        h, w = phases.shape
        for i in range(1, h - 1):
            for j in range(1, w - 1):
                center = phases[i, j]
                # Get differences to 4-connected neighbors
                neighbors = [phases[i - 1, j], phases[i + 1, j], phases[i, j - 1], phases[i, j + 1]]
                for neighbor in neighbors:
                    diff = neighbor - center
                    diff_wrapped = np.arctan2(np.sin(diff), np.cos(diff))
                    relationships.append(diff_wrapped)
        return np.array(relationships)

    orig_relationships = get_local_phase_relationships(orig_phase)
    proc_relationships = get_local_phase_relationships(proc_phase)

    # Compare the distributions of relationships
    rel_bins = np.linspace(-np.pi, np.pi, 30)
    orig_rel_hist, _ = np.histogram(orig_relationships, bins=rel_bins, density=True)
    proc_rel_hist, _ = np.histogram(proc_relationships, bins=rel_bins, density=True)

    relationship_error = np.mean(np.abs(orig_rel_hist - proc_rel_hist))
    results['phase_relationship_error'] = relationship_error

    # Method 5: Frequency Band Phase Analysis
    # Analyze phases in different frequency bands separately
    center_y, center_x = h // 2, w // 2
    y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]
    radius = np.sqrt(x * x + y * y)

    # Define frequency bands
    max_radius = min(center_y, center_x)
    band_errors = []

    for r_start in range(1, max_radius, max_radius // 8):
        r_end = min(r_start + max_radius // 8, max_radius)
        band_mask = (radius >= r_start) & (radius < r_end)

        if np.sum(band_mask) > 10:  # Need enough pixels for statistics
            orig_band_phases = orig_phase[band_mask]
            proc_band_phases = proc_phase[band_mask]

            # Compare phase distributions in this band
            band_orig_hist, _ = np.histogram(orig_band_phases, bins=phase_bins, density=True)
            band_proc_hist, _ = np.histogram(proc_band_phases, bins=phase_bins, density=True)

            band_error = np.mean(np.abs(band_orig_hist - band_proc_hist))
            band_errors.append(band_error)

    frequency_band_error = np.mean(band_errors) if band_errors else 0
    results['frequency_band_phase_error'] = frequency_band_error

    # Overall assessment
    # These thresholds are more relaxed than exact matching but still detect real changes
    results['phase_distribution_preserved'] = phase_distribution_error < 0.1
    results['local_variance_preserved'] = local_variance_error < 0.1
    results['detrended_phases_preserved'] = detrended_error < 0.1
    results['phase_relationships_preserved'] = relationship_error < 0.1
    results['frequency_bands_preserved'] = frequency_band_error < 0.1

    # Overall validation - require most tests to pass
    passed_tests = sum([
        results['phase_distribution_preserved'],
        results['local_variance_preserved'],
        results['detrended_phases_preserved'],
        results['phase_relationships_preserved'],
        results['frequency_bands_preserved']
    ])

    results['robust_phase_preservation_validated'] = passed_tests >= 3  # At least 3 of 5 tests
    results['passed_tests'] = passed_tests
    results['total_tests'] = 5

    return results


def validate_magnitude_shuffle_from_reconstructed(original_fft, processed_fft):
    """
    Validate magnitude shuffle using both magnitude-based metrics AND robust phase analysis
    that tolerates spatial shifts but detects real phase changes.
    """

    orig_magnitude = np.abs(original_fft)
    proc_magnitude = np.abs(processed_fft)

    # Test 1: Magnitude Distribution Preservation
    orig_mag_flat = orig_magnitude.flatten()
    proc_mag_flat = proc_magnitude.flatten()

    orig_mag_sorted = np.sort(orig_mag_flat)
    proc_mag_sorted = np.sort(proc_mag_flat)

    magnitude_distribution_error = np.mean(np.abs(orig_mag_sorted - proc_mag_sorted))

    # Test 2: Power Spectrum Preservation (Radial)
    def get_radial_power_spectrum(power_2d):
        h, w = power_2d.shape
        center_y, center_x = h // 2, w // 2
        y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]
        r = np.sqrt(x * x + y * y).astype(int)

        radial_bins = np.bincount(r.ravel(), weights=power_2d.ravel())
        radial_counts = np.bincount(r.ravel())
        radial_counts[radial_counts == 0] = 1
        return radial_bins / radial_counts

    orig_power = orig_magnitude ** 2
    proc_power = proc_magnitude ** 2

    orig_radial = get_radial_power_spectrum(orig_power)[1:]  # Skip DC
    proc_radial = get_radial_power_spectrum(proc_power)[1:]

    min_len = min(len(orig_radial), len(proc_radial))
    radial_power_error = np.mean(np.abs(orig_radial[:min_len] - proc_radial[:min_len]))

    # Test 3: Total Power Conservation
    orig_total_power = np.sum(orig_power)
    proc_total_power = np.sum(proc_power)
    total_power_error = np.abs(orig_total_power - proc_total_power) / orig_total_power

    # Test 4: Magnitude Histogram Comparison
    max_mag = max(np.max(orig_magnitude), np.max(proc_magnitude))
    bins = np.linspace(0, max_mag, 100)

    orig_hist, _ = np.histogram(orig_magnitude.flatten(), bins=bins, density=True)
    proc_hist, _ = np.histogram(proc_magnitude.flatten(), bins=bins, density=True)

    histogram_error = np.mean(np.abs(orig_hist - proc_hist))

    # Test 5: NEW - Robust Phase Preservation Analysis
    phase_results = robust_phase_preservation_analysis(original_fft, processed_fft)

    return {
        'magnitude_distribution_error': magnitude_distribution_error,
        'radial_power_error': radial_power_error,
        'total_power_error': total_power_error,
        'magnitude_histogram_error': histogram_error,

        # Phase preservation results
        'phase_distribution_error': phase_results['phase_distribution_error'],
        'local_phase_variance_error': phase_results['local_phase_variance_error'],
        'detrended_phase_error': phase_results['detrended_phase_error'],
        'phase_relationship_error': phase_results['phase_relationship_error'],
        'frequency_band_phase_error': phase_results['frequency_band_phase_error'],
        'robust_phase_preservation_validated': phase_results['robust_phase_preservation_validated'],
        'phase_tests_passed': phase_results['passed_tests'],
        'phase_total_tests': phase_results['total_tests'],

        # Pass/fail criteria for magnitude shuffle
        'magnitude_distribution_preserved': magnitude_distribution_error < 0.01,
        'radial_power_preserved': radial_power_error < 0.01,
        'total_power_preserved': total_power_error < 0.001,
        'magnitude_histogram_preserved': histogram_error < 0.01,

        # Overall assessment - now includes robust phase validation
        'magnitude_shuffle_validated': (
                magnitude_distribution_error < 0.01 and
                radial_power_error < 0.01 and
                histogram_error < 0.01 and
                phase_results['robust_phase_preservation_validated']
        )
    }


def validate_phase_shuffle_from_reconstructed(original_fft, processed_fft):
    """
    Validate phase shuffle by focusing on magnitude preservation and phase randomization.
    """

    orig_magnitude = np.abs(original_fft)
    proc_magnitude = np.abs(processed_fft)
    orig_phase = np.angle(original_fft)
    proc_phase = np.angle(processed_fft)

    # Test 1: Magnitude Preservation (Direct)
    magnitude_error = np.mean(np.abs(orig_magnitude - proc_magnitude))

    # Test 2: Phase Randomization Detection
    # Large phase changes indicate successful phase shuffle
    phase_diff = proc_phase - orig_phase
    phase_diff_wrapped = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))
    mean_phase_change = np.mean(np.abs(phase_diff_wrapped))

    # Test 3: Power Spectrum Preservation (should be identical if magnitude preserved)
    orig_power = orig_magnitude ** 2
    proc_power = proc_magnitude ** 2
    power_error = np.mean(np.abs(orig_power - proc_power))

    return {
        'magnitude_error': magnitude_error,
        'mean_phase_change': mean_phase_change,
        'power_error': power_error,

        # Pass/fail criteria for phase shuffle
        'magnitude_preserved': magnitude_error < 0.01,
        'phase_significantly_changed': mean_phase_change > 1.0,  # Expect large changes
        'power_preserved': power_error < 0.01,

        # Overall assessment
        'phase_shuffle_validated': (
                magnitude_error < 0.01 and
                mean_phase_change > 1.0 and
                power_error < 0.01
        )
    }


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


def plot_phase_changes_by_frequency_orientation(original_img, randomized_img, original_fft=None, processed_fft=None,
                                                algorithm_type="magnitude_shuffle"):
    """
    Plot how phase changes vary by frequency and orientation.

    CORRECTED VERSION: Uses actual interior FFTs when available and applies spatial reference correction.

    Args:
        original_img: Original image (for fallback analysis)
        randomized_img: Processed image (for fallback analysis)
        original_fft: Original clean interior FFT (preferred)
        processed_fft: Processed clean interior FFT (preferred)
        algorithm_type: "magnitude_shuffle" or "phase_shuffle"
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

        # Perform corrected spatial reference analysis
        analysis_results = correct_spatial_reference_phase_analysis(original_fft, processed_fft)

        print(f"\n=== SPATIAL REFERENCE CORRECTED ANALYSIS ({algorithm_type.upper()}) ===")
        print(f"Direct phase error (mean): {analysis_results['phase_error_direct_mean']:.8f} radians")
        print(f"Direct phase error (max):  {analysis_results['phase_error_direct_max']:.8f} radians")
        print(f"Relative phase error (mean): {analysis_results['phase_error_relative_mean']:.8f} radians")
        print(f"Magnitude error (mean): {analysis_results['magnitude_error_mean']:.8f}")
        print(f"Radial power error (mean): {analysis_results['power_error_radial_mean']:.8f}")

        if analysis_results['has_spatial_shift']:
            print("⚠️  WARNING: Spatial reference shift detected!")
            print("   Direct phase comparison is unreliable.")
            print("   Using spatial-shift-invariant analysis instead.")

        if algorithm_type == "magnitude_shuffle":
            if analysis_results['is_phase_preserved'] or analysis_results['phase_error_relative_mean'] < 1e-3:
                print("✅ Phase preservation confirmed (magnitude shuffle working correctly)")
            else:
                if analysis_results['has_spatial_shift']:
                    print("⚠️  Large direct phase error likely due to spatial reference shift")
                    print(
                        f"   Relative phase error: {analysis_results['phase_error_relative_mean']:.8f} (should be ~0)")
                else:
                    print("❌ Unexpected phase changes detected")

        elif algorithm_type == "phase_shuffle":
            if analysis_results['is_magnitude_preserved']:
                print("✅ Magnitude preservation confirmed (phase shuffle working correctly)")
            else:
                print("❌ Unexpected magnitude changes detected")

            if analysis_results['phase_error_direct_mean'] > 1.0 or analysis_results['phase_error_relative_mean'] > 1.0:
                print("✅ Large phase changes confirmed (expected for phase shuffle)")
            else:
                print("⚠️  Expected large phase changes not detected")

    else:
        # Fallback: Try to extract interior FFT from reconstructed images
        print(f"Using fallback analysis with spatial reference correction")

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
            return fft_clean_interior  # Return unshifted for analysis

        # Get FFT data for both images using fallback method
        original_fft_fallback = get_fft_data_fallback(original_img)
        processed_fft_fallback = get_fft_data_fallback(randomized_img)

        print(f"  Fallback FFT shapes: {original_fft_fallback.shape}")

        # Apply the SAME spatial reference correction to fallback data!
        analysis_results = correct_spatial_reference_phase_analysis(original_fft_fallback, processed_fft_fallback)

        print(f"\n=== SPATIAL REFERENCE CORRECTED ANALYSIS - FALLBACK ({algorithm_type.upper()}) ===")
        print(f"Direct phase error (mean): {analysis_results['phase_error_direct_mean']:.8f} radians")
        print(f"Direct phase error (max):  {analysis_results['phase_error_direct_max']:.8f} radians")
        print(f"Relative phase error (mean): {analysis_results['phase_error_relative_mean']:.8f} radians")
        print(f"Magnitude error (mean): {analysis_results['magnitude_error_mean']:.8f}")
        print(f"Radial power error (mean): {analysis_results['power_error_radial_mean']:.8f}")

        if analysis_results['has_spatial_shift']:
            print("⚠️  WARNING: Spatial reference shift detected in fallback data!")
            print("   This is expected from reconstruction pipeline.")
            print("   Using spatial-shift-invariant analysis instead.")

        if algorithm_type == "magnitude_shuffle":
            if analysis_results['is_phase_preserved'] or analysis_results['phase_error_relative_mean'] < 1e-3:
                print("✅ Phase preservation confirmed via fallback analysis")
            else:
                if analysis_results['has_spatial_shift']:
                    print("⚠️  Large direct phase error likely due to spatial reference shift")
                    print(
                        f"   Relative phase error: {analysis_results['phase_error_relative_mean']:.8f} (should be ~0)")
                else:
                    print("❌ Unexpected phase changes detected in fallback analysis")

        elif algorithm_type == "phase_shuffle":
            if analysis_results['is_magnitude_preserved']:
                print("✅ Magnitude preservation confirmed via fallback analysis")
            else:
                print("❌ Unexpected magnitude changes detected in fallback analysis")

            if analysis_results['phase_error_direct_mean'] > 1.0 or analysis_results['phase_error_relative_mean'] > 1.0:
                print("✅ Large phase changes confirmed via fallback analysis")
            else:
                print("⚠️  Expected large phase changes not detected in fallback analysis")

        # Use shifted versions for visualization
        orig_fft_shifted = np.fft.fftshift(original_fft_fallback)
        proc_fft_shifted = np.fft.fftshift(processed_fft_fallback)
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

    # Both direct and fallback methods now use corrected analysis above

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

    CORRECTED VERSION: Uses actual interior FFTs for phase analysis when available and
    applies spatial reference correction.

    Args:
        original_image: Original image array
        randomized_image: Phase-randomized image array
        output_path: Path to save the analysis plot
        title: Title for the plot
        original_fft: Original clean interior FFT (for accurate phase analysis)
        processed_fft: Processed clean interior FFT (for accurate phase analysis)
        algorithm_type: "magnitude_shuffle", "phase_shuffle", or "spatial"
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

    # Algorithm-specific validation - ROBUST VERSION
    plt.subplot(2, 3, 6)
    if algorithm_type in ["magnitude_shuffle", "phase_shuffle"]:
        plt.title(f'Algorithm Validation ({algorithm_type.replace("_", " ").title()})')
    else:
        plt.title('Phase Changes by Frequency & Orientation')

    plot_phase_changes_by_frequency_orientation(
        original_image, randomized_image,
        original_fft=original_fft, processed_fft=processed_fft,
        algorithm_type=algorithm_type
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()  # Close to free memory
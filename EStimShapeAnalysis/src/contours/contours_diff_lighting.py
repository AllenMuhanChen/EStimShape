import numpy as np
from PIL import Image
from skimage import color
import matplotlib.pyplot as plt

def normalize_lightness(lightness):
    lightness_zeros_removed = lightness[lightness > 0]
    if lightness_zeros_removed.size > 0:
        l_min, l_max = np.percentile(lightness_zeros_removed, [1, 99])
        lightness_normalized = np.clip((lightness - l_min) / (l_max - l_min), 0, 1)
    else:
        lightness_normalized = np.zeros_like(lightness)
    return lightness_normalized

def create_lab_colormap(hue_values):
    L = np.full_like(hue_values, 75)  # Constant lightness
    a = np.cos(2 * np.pi * hue_values) * 100
    b = np.sin(2 * np.pi * hue_values) * 100
    lab = np.dstack((L, a, b))
    return color.lab2rgb(lab)

def adjust_brightness_range(grayscale, min_val=0.5, max_val=1.0):
    non_zero_mask = grayscale > 0
    adjusted = grayscale.copy()
    adjusted[non_zero_mask] = (max_val - min_val) * grayscale[non_zero_mask] + min_val
    return adjusted

def create_random_background(shape):
    hue = np.random.random(shape[:2])
    saturation = np.full_like(hue, 0.7)  # Fixed saturation
    value = np.full_like(hue, 0.5)  # Fixed brightness as requested
    hsv = np.dstack((hue, saturation, value))
    return color.hsv2rgb(hsv)


def adjust_brightness_range(grayscale, min_val=0.5, max_val=1.0):
    non_zero_mask = grayscale > 0
    adjusted = grayscale.copy()
    adjusted[non_zero_mask] = (max_val - min_val) * grayscale[non_zero_mask] + min_val
    return adjusted


def create_background_from_colored_image(colored_image, grayscale, dark_threshold=0.1):
    # Find pixels just above the dark threshold
    near_dark_mask = (grayscale > dark_threshold) & (grayscale < dark_threshold + 0.1)

    if np.any(near_dark_mask):
        # Get the colors of pixels just above the dark threshold
        near_dark_colors = colored_image[near_dark_mask]

        # Calculate the average color of these pixels
        background_color = np.mean(near_dark_colors, axis=0)

        # Darken the background color
        background_color = np.clip(background_color * 0.7, 0, 1)
    else:
        # Fallback to a dark gray if no suitable pixels are found
        background_color = np.array([0.1, 0.1, 0.1])

    print(f"Background color: {background_color}")
    return np.full_like(colored_image, background_color)


def process_image(original_image_path, lighting_image_path, output_dir):
    # Open and process images
    original_img = Image.open(original_image_path).convert('RGB')
    original_img_array = np.array(original_img)
    lighting_img = Image.open(lighting_image_path).convert('RGB')
    lighting_img_array = np.array(lighting_img)

    original_rgb = original_img_array.astype(float) / 255.0
    lighting_rgb = lighting_img_array.astype(float) / 255.0

    # Convert to grayscale
    original_grayscale = np.mean(original_rgb, axis=2)
    lighting_grayscale = np.mean(lighting_rgb, axis=2)

    # Create mask for dark areas (adjust threshold as needed)
    dark_threshold = 0.000001
    dark_mask = original_grayscale < dark_threshold
    print(f"Percentage of dark pixels: {np.mean(dark_mask) * 100:.2f}%")

    adjusted_original_grayscale = adjust_brightness_range(original_grayscale)
    adjusted_lighting_grayscale = adjust_brightness_range(lighting_grayscale)

    # Save adjusted grayscale image
    plt.imsave(f"{output_dir}/grayscale_image.png", adjusted_original_grayscale, cmap='gray')

    # Process original image
    original_hue_map = normalize_lightness(adjusted_original_grayscale)
    original_colormap = create_lab_colormap(original_hue_map)
    plt.imsave(f"{output_dir}/original_colormap.png", original_colormap)

    # Create initial colored image
    original_colored_image = adjusted_original_grayscale[:, :, np.newaxis] * original_colormap

    # Create background from colored image
    background = create_background_from_colored_image(original_colored_image, original_grayscale, dark_threshold)
    plt.imsave(f"{output_dir}/debug_background.png", background)

    # Combine original colored image with background
    original_final_image = np.where(np.expand_dims(dark_mask, axis=2),
                                    background,
                                    original_colored_image)
    plt.imsave(f"{output_dir}/original_final_image.png", np.clip(original_final_image, 0, 1))

    # Process lighting image
    lighting_hue_map = normalize_lightness(adjusted_lighting_grayscale)
    lighting_colormap = create_lab_colormap(lighting_hue_map)
    plt.imsave(f"{output_dir}/lighting_colormap.png", lighting_colormap)

    # Create initial lighting colored image
    lighting_colored_image = adjusted_original_grayscale[:, :, np.newaxis] * lighting_colormap

    # Combine lighting colored image with background
    lighting_final_image = np.where(np.expand_dims(dark_mask, axis=2),
                                    background,
                                    lighting_colored_image)
    plt.imsave(f"{output_dir}/lighting_final_image.png", np.clip(lighting_final_image, 0, 1))

    print(f"Shape of final image: {original_final_image.shape}")
    print(f"Range of values in final image: {original_final_image.min()} to {original_final_image.max()}")


# Paths
original_image_path = "/home/r2_allen/git/EStimShape/plots/poster_sfn2024/lighting_variations/original_angle_with_lighting_0.png"
lighting_image_path = "/home/r2_allen/git/EStimShape/plots/poster_sfn2024/lighting_variations/original_angle_with_lighting_1.png"
output_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/contours/data"

# Process images
process_image(original_image_path, lighting_image_path, output_dir)
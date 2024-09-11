import numpy as np
from PIL import Image
import colorsys
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color

def normalize_lightness(lightness):
    lightness_zeros_removed = lightness[lightness > 0]
    l_min, l_max = np.percentile(lightness_zeros_removed, [1, 99])
    lightness_normalized = np.clip((lightness - l_min) / (l_max - l_min), 0, 1)
    return lightness_normalized

def lab_to_rgb(lab):
    rgb = convert_color(LabColor(lab[0], lab[1], lab[2]), sRGBColor)
    return np.clip([rgb.rgb_r, rgb.rgb_g, rgb.rgb_b], 0, 1)

def create_isoluminant_colormap(hue_values):
    L = 70  # Constant lightness value (0-100)
    colormap = np.zeros((hue_values.shape[0], hue_values.shape[1], 3))
    for i in range(hue_values.shape[0]):
        for j in range(hue_values.shape[1]):
            hue = hue_values[i, j] * 360  # Scale hue to 0-360
            a = np.cos(np.radians(hue)) * 50
            b = np.sin(np.radians(hue)) * 50
            colormap[i, j] = lab_to_rgb([L, a, b])
            print(i, j)
    return colormap

def process_image(input_path, colormap_output_path, final_output_path):
    img = Image.open(input_path).convert('RGBA')
    img_array = np.array(img)
    img_normalized = img_array.astype(float) / 255.0

    lightness = np.zeros((img_array.shape[0], img_array.shape[1]))
    for i in range(img_array.shape[0]):
        for j in range(img_array.shape[1]):
            _, l, _ = colorsys.rgb_to_hls(img_normalized[i, j, 0],
                                          img_normalized[i, j, 1],
                                          img_normalized[i, j, 2])
            lightness[i, j] = l

    lightness_normalized = normalize_lightness(lightness)
    hue_map = lightness_normalized

    # Create and save perceptually isoluminant colormap
    colormap = create_isoluminant_colormap(hue_map)
    colormap_with_alpha = np.dstack((colormap, np.ones(hue_map.shape)))
    Image.fromarray((colormap_with_alpha * 255).astype(np.uint8)).save(colormap_output_path)

    # Apply hue modulation while preserving original brightness
    final_image = np.zeros_like(img_array, dtype=float)
    for i in range(img_array.shape[0]):
        for j in range(img_array.shape[1]):
            h, l, s = colorsys.rgb_to_hls(img_normalized[i, j, 0],
                                          img_normalized[i, j, 1],
                                          img_normalized[i, j, 2])
            new_h = hue_map[i, j]
            r, g, b = colorsys.hls_to_rgb(new_h, l, 0.5)
            final_image[i, j] = [r * 255, g * 255, b * 255, img_array[i, j, 3]]

    final_image = np.clip(final_image, 0, 255).astype(np.uint8)
    Image.fromarray(final_image).save(final_output_path)

# Example usage
input_image_path = "/home/r2_allen/Documents/EStimShape/allen_estimshape_ga_train_240604/stimuli/ga/pngs/1717521925194310_0.png"
colormap_output_path = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/contours/perceptual_isoluminant_colormap.png"
final_output_path = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/contours/final_hue_modulated_image.png"
process_image(input_image_path, colormap_output_path, final_output_path)
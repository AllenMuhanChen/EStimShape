import numpy as np
from PIL import Image
from skimage import color


def normalize_lightness(lightness):
    lightness_zeros_removed = lightness[lightness > 0]
    l_min, l_max = np.percentile(lightness_zeros_removed, [1, 99])
    lightness_normalized = np.clip((lightness - l_min) / (l_max - l_min), 0, 1)
    return lightness_normalized


def create_lab_colormap(hue_values):
    L = np.full_like(hue_values, 75)  # Constant lightness
    a = np.cos(2 * np.pi * hue_values) * 100
    b = np.sin(2 * np.pi * hue_values) * 100
    lab = np.dstack((L, a, b))
    return color.lab2rgb(lab)


def process_image(input_path, grayscale_output_path, colormap_output_path, final_output_path):
    # Open the image
    img = Image.open(input_path).convert('RGBA')
    img_array = np.array(img)

    # Separate RGB and alpha
    rgb = img_array[:, :, :3].astype(float) / 255.0
    alpha = img_array[:, :, 3]

    # Convert RGB to grayscale using CIELAB luminance
    lab = color.rgb2lab(rgb)
    grayscale = lab[:, :, 0] / 100.0  # L channel normalized to 0-1

    # Save grayscale image
    grayscale_image = Image.fromarray((grayscale * 255).astype(np.uint8))
    grayscale_image.save(grayscale_output_path)

    # Normalize grayscale to create hue map
    hue_map = normalize_lightness(grayscale)

    # Create and save CIELAB-based colormap
    colormap = create_lab_colormap(hue_map)
    colormap_with_alpha = np.dstack((colormap, np.ones_like(grayscale)))
    Image.fromarray((colormap_with_alpha * 255).astype(np.uint8)).save(colormap_output_path)

    # Multiply grayscale image with CIELAB-based colormap
    colored_image = np.expand_dims(grayscale, axis=2) * colormap

    # Combine with original alpha channel
    final_image = np.dstack((colored_image, alpha / 255.0))

    # Save final image
    Image.fromarray((final_image * 255).astype(np.uint8)).save(final_output_path)


# Example usage
input_image_path = "/home/r2_allen/Documents/EStimShape/allen_estimshape_train_240604/stimuli/240723/procedural/pngs/1721836111082299_procedural_I.png"
grayscale_output_path = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/contours/grayscale_image.png"
colormap_output_path = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/contours/lab_colormap.png"
final_output_path = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/contours/final_multiplied_image.png"
process_image(input_image_path, grayscale_output_path, colormap_output_path, final_output_path)
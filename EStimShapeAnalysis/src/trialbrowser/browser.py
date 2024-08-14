import os
import matplotlib.pyplot as plt
import xmltodict
from PIL import Image
import numpy as np
from clat.util.connection import Connection
from src.startup import config
from src.startup.setup_xper_properties_and_dirs import XperPropertiesModifier
import math


def get_stim_spec(conn: Connection, stim_spec_id: int) -> str:
    query = "SELECT spec FROM StimSpec WHERE id = %s"
    conn.execute(query, params=(stim_spec_id,))
    result = conn.fetch_one()
    if result:
        return result
    else:
        print(f"No StimSpec found for id {stim_spec_id}")
        return None


def parse_stim_spec(xml_string: str) -> tuple:
    xml_dict = xmltodict.parse(xml_string)
    sample_obj_data = xml_dict["StimSpec"]["sampleObjData"]
    choice_obj_data = xml_dict["StimSpec"]["choiceObjData"]["long"]
    return sample_obj_data, choice_obj_data


def find_image(image_path: str, obj_id: str, suffix: str = "") -> str:
    for filename in os.listdir(image_path):
        if filename.startswith(obj_id) and filename.endswith(suffix):
            return os.path.join(image_path, filename)
    return None


def get_nafc_generator_png_path():
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.procedural'
    modifier = XperPropertiesModifier(xper_properties_file_path)

    for line in modifier.properties_content:
        if line.startswith("generator.png_path="):
            return line.split("=", 1)[1].strip()

    raise ValueError("generator.png_path not found in xper.properties.procedural")


def overlay_images(base_img, noisemap_img):
    base = np.array(base_img).astype(float)
    noisemap = np.array(noisemap_img).astype(float)

    # Ensure base image is RGB
    if base.ndim == 2:
        base = np.stack((base,) * 3, axis=-1)
    elif base.shape[2] == 4:
        base = base[:, :, :3]

    # Extract red channel from noisemap
    if noisemap.ndim == 3:
        red_channel = noisemap[:, :, 0]
    else:
        red_channel = noisemap

    # Normalize red channel to [0, 1]
    red_channel = red_channel / 255.0

    # Create red overlay
    red_overlay = np.zeros_like(base)
    red_overlay[:, :, 0] = 255  # Red channel

    # Blend images
    blended = base * (1 - red_channel[:, :, np.newaxis]) + red_overlay * red_channel[:, :, np.newaxis]

    return Image.fromarray(blended.astype('uint8'))


def plot_trial_images(stim_spec_id: int, conn: Connection):
    stim_spec = get_stim_spec(conn, stim_spec_id)
    if not stim_spec:
        return

    sample_obj_data, choice_obj_data = parse_stim_spec(stim_spec)

    image_path = get_nafc_generator_png_path()

    sample_image_path = find_image(image_path, sample_obj_data, "_sample_notDeltaNoise.png")
    sample_noisemap_path = find_image(image_path, sample_obj_data, "_sample_notDeltaNoise_noisemap.png")
    choice_image_paths = [find_image(image_path, choice_id) for choice_id in choice_obj_data]

    if not sample_image_path or not sample_noisemap_path or not all(choice_image_paths):
        print("Some images not found")
        return

    n_choices = len(choice_image_paths)
    n_cols = math.ceil(math.sqrt(n_choices))
    n_rows = math.ceil(n_choices / n_cols)

    fig = plt.figure(figsize=(5 * (n_cols + 1), 5 * n_rows))

    # Plot sample image with noisemap overlay
    ax1 = fig.add_subplot(1, 2, 1)
    sample_img = Image.open(sample_image_path)
    noisemap_img = Image.open(sample_noisemap_path)
    overlaid_sample = overlay_images(sample_img, noisemap_img)
    ax1.imshow(overlaid_sample)
    ax1.axis('off')
    ax1.set_title("Sample with Noisemap")

    # Create a subplot for choices
    choices_subplot = fig.add_subplot(1, 2, 2)
    choices_subplot.axis('off')
    choices_subplot.set_title("Choices")

    # Plot choice images
    for i, choice_path in enumerate(choice_image_paths):
        ax = choices_subplot.inset_axes([
            (i % n_cols) / n_cols,
            1 - (i // n_cols + 1) / n_rows,
            1 / n_cols,
            1 / n_rows
        ])
        choice_img = Image.open(choice_path)
        ax.imshow(choice_img)
        ax.axis('off')
        ax.set_title(f"Choice {i + 1}")

    plt.tight_layout()
    plt.show()


# Example usage
if __name__ == "__main__":
    conn = Connection(config.nafc_database)
    stim_spec_id = 1722374738207048  # Replace with the desired stimSpecId

    plot_trial_images(stim_spec_id, conn)
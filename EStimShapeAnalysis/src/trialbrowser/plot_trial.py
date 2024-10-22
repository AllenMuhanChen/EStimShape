import os
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
import math
import re
import xmltodict
from src.startup.setup_xper_properties_and_dirs import XperPropertiesModifier
from clat.util.connection import Connection


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


def get_nafc_generator_png_path():
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.procedural'
    modifier = XperPropertiesModifier(xper_properties_file_path)

    for line in modifier.properties_content:
        if line.startswith("generator.png_path="):
            return line.split("=", 1)[1].strip()

    raise ValueError("generator.png_path not found in xper.properties.procedural")


def find_image(image_path: str, obj_id: str, image_type: str) -> str:
    for filename in os.listdir(image_path):
        if filename.startswith(obj_id):
            if image_type == "sample" and "sample" in filename and "noisemap" not in filename and "compmap" not in filename:
                return os.path.join(image_path, filename)
            elif image_type == "sample_noisemap" and "sample" in filename and "noisemap" in filename:
                return os.path.join(image_path, filename)
            elif image_type == "sample_compmap" and "sample" in filename and "compmap" in filename:
                return os.path.join(image_path, filename)
            elif image_type == "choice":
                return os.path.join(image_path, filename)
    return None


def get_roman_numeral(filename):
    match = re.search(r'_(I+V*|V|IV|IX|X)\.png$', filename)
    return match.group(1) if match else None


def overlay_images(base_img, noisemap_img, alpha=0.5):
    base = np.array(base_img).astype(float)
    noisemap = np.array(noisemap_img).astype(float)

    # Ensure base image is RGB
    if base.ndim == 2:
        base = np.stack((base,) * 3, axis=-1)
    elif base.shape[2] == 4:
        base = base[:, :, :3]

    # Ensure noisemap is RGB
    if noisemap.ndim == 2:
        noisemap = np.stack((noisemap,) * 3, axis=-1)
    elif noisemap.shape[2] == 4:
        noisemap = noisemap[:, :, :3]

    # Create an alpha channel for the noisemap
    noisemap_alpha = np.any(noisemap != 0, axis=2).astype(float)

    # Apply constant alpha to non-black pixels
    noisemap_alpha *= alpha

    # Blend images
    blended = base * (1 - noisemap_alpha[:, :, np.newaxis]) + noisemap * noisemap_alpha[:, :, np.newaxis]

    # Ensure the result is in the valid range [0, 255]
    blended = np.clip(blended, 0, 255)

    return Image.fromarray(blended.astype('uint8'))


def plot_trial_images(stim_spec_id: int, conn: Connection, fig):
    stim_spec = get_stim_spec(conn, stim_spec_id)
    if not stim_spec:
        return

    sample_obj_data, choice_obj_data = parse_stim_spec(stim_spec)

    image_path = get_nafc_generator_png_path()

    sample_image_path = find_image(image_path, sample_obj_data, "sample")
    sample_noisemap_path = find_image(image_path, sample_obj_data, "sample_noisemap")
    sample_compmap_path = find_image(image_path, sample_obj_data, "sample_compmap")
    choice_image_paths = [find_image(image_path, choice_id, "choice") for choice_id in choice_obj_data]

    if not sample_image_path or not sample_noisemap_path or not sample_compmap_path or not all(choice_image_paths):
        print("Some images not found")
        return

    # Sort choice images by Roman numeral
    choice_images_with_numerals = [(path, get_roman_numeral(os.path.basename(path))) for path in choice_image_paths]
    choice_images_with_numerals.sort(key=lambda x: ['I', 'II', 'III', 'IV'].index(x[1]))

    # Create a 2x2 grid
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1], height_ratios=[1, 1])

    # Plot regular sample image with noisemap overlay
    ax1 = fig.add_subplot(gs[0, 0])
    sample_img = Image.open(sample_image_path)
    noisemap_img = Image.open(sample_noisemap_path)
    overlaid_sample = overlay_images(sample_img, noisemap_img)
    ax1.imshow(overlaid_sample)
    ax1.axis('off')
    ax1.set_title("Sample with Noisemap")

    # Plot compmap sample image
    ax2 = fig.add_subplot(gs[1, 0])
    compmap_img = Image.open(sample_compmap_path)
    ax2.imshow(compmap_img)
    ax2.axis('off')
    ax2.set_title("Sample Compmap")

    # Create a subplot for choices
    choices_subplot = fig.add_subplot(gs[:, 1])
    choices_subplot.axis('off')
    choices_subplot.set_title("Choices")

    # Plot choice images
    for i, (choice_path, numeral) in enumerate(choice_images_with_numerals):
        ax = choices_subplot.inset_axes([
            (i % 2) / 2,
            1 - (i // 2 + 1) / 2,
            1 / 2,
            1 / 2
        ])
        choice_img = Image.open(choice_path)
        ax.imshow(choice_img)
        ax.axis('off')
        ax.set_title(f"Choice {numeral}")

    plt.tight_layout()


if __name__ == "__main__":
    # This block is for testing purposes
    from src.startup import context

    conn = Connection(context.nafc_database)
    fig, ax = plt.subplots(figsize=(12, 6))
    plot_trial_images(1722374738207048, conn, fig)  # Replace with a valid stim_spec_id
    plt.show()
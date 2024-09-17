import os
import matplotlib.pyplot as plt
from PIL import Image
from src.startup.setup_xper_properties_and_dirs import XperPropertiesModifier

def get_set_path():
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.procedural'
    modifier = XperPropertiesModifier(xper_properties_file_path)

    for line in modifier.properties_content:
        if line.startswith("generator.set_path="):
            return line.split("=", 1)[1].strip()

    raise ValueError("generator.set_path not found in xper.properties.procedural")

def find_set_images(set_path: str):
    set_images = {'I': None, 'II': None, 'III': None, 'IV': None}
    for filename in os.listdir(set_path):
        for numeral in set_images.keys():
            if filename.endswith(f"_{numeral}.png"):
                set_images[numeral] = os.path.join(set_path, filename)
                break
    return set_images

def plot_set(fig):
    set_path = get_set_path()
    set_images = find_set_images(set_path)

    if not all(set_images.values()):
        print("Not all set images found")
        return

    for i, (numeral, image_path) in enumerate(set_images.items()):
        ax = fig.add_subplot(2, 2, i+1)
        img = Image.open(image_path)
        ax.imshow(img)
        ax.axis('off')
        ax.set_title(f"Set {numeral}")

    plt.tight_layout()
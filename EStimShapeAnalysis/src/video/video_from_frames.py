import imageio
import os
import re
from pathlib import Path

def create_gif_from_frames(frames_dir):
    # Get all image files
    files = [os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if re.match(r'frame_\d+\.jpg', f)]
    # Sort the files by the frame number
    files.sort(key=lambda f: int(re.sub('\D', '', f)))

    # Get the path for the output GIF
    parent_dir = Path(frames_dir).parent
    output_gif_path = os.path.join(parent_dir, 'output.gif')

    # Create a list to hold the images
    images = []

    for file in files:
        images.append(imageio.imread(file))

    # Save the frames as a GIF
    imageio.mimsave(output_gif_path, images, duration=1/30)  # Duration is the time spent on each frame in seconds

    print(f"The GIF was successfully saved to {output_gif_path}")

def main():
    frames_directory = "/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/test_mjpeg"
    create_gif_from_frames(frames_directory)

if __name__ == '__main__':
    main()

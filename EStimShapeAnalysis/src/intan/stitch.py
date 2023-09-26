import os
import shutil
import tkinter as tk
from tkinter import filedialog, simpledialog

import tkfilebrowser


class IntanFileStitcher:
    def __init__(self, folder_paths):
        self.folder_paths = sorted(folder_paths)

    def read_append_write(self, filename, output_folder):
        with open(os.path.join(output_folder, filename), 'wb') as output_file:
            for folder in self.folder_paths:
                input_file_path = os.path.join(folder, filename)
                with open(input_file_path, 'rb') as input_file:
                    shutil.copyfileobj(input_file, output_file)

    def append_notes(self, filename, output_folder):
        cumulative_last_index = 0
        with open(os.path.join(output_folder, filename), 'w') as output_file:
            for folder in self.folder_paths:
                input_file_path = os.path.join(folder, filename)
                local_last_index = 0  # Last index within the current file
                with open(input_file_path, 'r') as input_file:
                    lines = input_file.readlines()
                    for line in lines:
                        line = line.strip()
                        if not line:  # Skip empty lines
                            continue
                        index, timestamp, info = line.split(", ")
                        new_index = int(index) + cumulative_last_index
                        output_file.write(f"{new_index}, {timestamp}, {info}\n\n")  # Added two extra newlines
                        local_last_index = new_index  # Update the last index for the current file
                cumulative_last_index = local_last_index  # Update the cumulative last index for the next file

    def copy_auxiliary_files(self, filename, output_folder):
        source_path = os.path.join(self.folder_paths[0], filename)
        destination_path = os.path.join(output_folder, filename)
        shutil.copyfile(source_path, destination_path)

    def stitch_files(self, output_folder):
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        files_to_stitch = ['amplifier.dat', 'digitalin.dat']
        for filename in files_to_stitch:
            self.read_append_write(filename, output_folder)

        self.append_notes('notes.txt', output_folder)

        auxiliary_files = ['info.rhd', 'settings.xml']
        for filename in auxiliary_files:
            self.copy_auxiliary_files(filename, output_folder)

        self.create_merge_info(output_folder)

    def create_merge_info(self, output_folder):
        with open(os.path.join(output_folder, "mergeinfo.txt"), 'w') as f:
            for folder in self.folder_paths:
                folder_name = os.path.basename(folder)
                f.write(f"{folder_name}\n")

def open_gui():
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    default_folder = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana"
    # default_folder = "/run/user/1003/gvfs/sftp:host=172.30.6.58/home/connorlab/Documents/IntanData"

    folder_paths = tkfilebrowser.askopendirnames(initialdir=default_folder, title="Select Folders to Stitch")
    folder_paths = list(folder_paths)  # Convert tuple to list

    if folder_paths:  # If folders were selected
        output_folder_name = simpledialog.askstring("Output Folder", "Enter the name for the output folder:")

        if output_folder_name:  # If an output folder name was provided
            # Get the parent directory of each selected folder
            parent_directories = [os.path.dirname(folder) for folder in folder_paths]

            # Get the common parent directory of all selected folders
            common_parent_directory = os.path.commonprefix(parent_directories)

            # Append the output folder name to the common parent directory
            final_output_folder_path = os.path.join(common_parent_directory, output_folder_name)

            # Run the stitcher
            stitcher = IntanFileStitcher(folder_paths)
            stitcher.stitch_files(final_output_folder_path)
def main():
    open_gui()

if __name__ == '__main__':
    main()
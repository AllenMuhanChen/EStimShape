import os
import tkinter as tk
from tkinter import simpledialog
import datetime
import sys

from clat.intan.stitch import IntanFileStitcher


def find_amplifier_dat_in_directory(directory):
    """Find all subdirectories containing amplifier.dat files"""
    amplifier_dirs = []

    print(f"Searching for amplifier.dat files in {directory} and subdirectories...")

    # Walk through all directories
    for dirpath, dirnames, filenames in os.walk(directory):
        if 'amplifier.dat' in filenames:
            amplifier_dirs.append(dirpath)

    return amplifier_dirs


def sort_by_modification_time(directory_list):
    """
    Sort directories by the modification time of their amplifier.dat file
    from oldest to newest
    """

    def get_mod_time(directory):
        amplifier_path = os.path.join(directory, 'amplifier.dat')
        return os.path.getmtime(amplifier_path)

    # Sort directories by amplifier.dat modification time
    return sorted(directory_list, key=get_mod_time)


def main():
    # ============================================================
    # CONFIGURATION - MODIFY THESE VARIABLES
    # ============================================================

    # Specify a list of parent directories to search
    # Specify a list of parent directories to search
    parent_directories = [
        # Example paths - replace with your actual paths
        "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_ga_exp_250911_0",
        "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_isogabor_exp_250911_0",
        "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_lightness_exp_250911_0",
        # Add more parent directories as needed
    ]

    # Generate output folder name based on input directories
    exp_types = []
    date_value = ""
    location_id = ""

    for path in parent_directories:
        # Get the last component of the path which contains the experiment info
        exp_folder = path.split('/')[-1]

        # Find all parts that start with "allen_"
        if exp_folder.startswith('allen_'):
            # Split by underscore
            parts = exp_folder.split('_')

            # Extract experiment type (second element after splitting "allen_")
            if len(parts) > 1:
                exp_type = parts[1]
                if exp_type not in exp_types:
                    exp_types.append(exp_type)

            # Extract date (assuming it's the second-to-last element)
            if len(parts) > 2:
                date_value = parts[-2]

            # Extract location ID (assuming it's the last element)
            if len(parts) >= 1:
                location_id = parts[-1]

    # Create output folder name
    output_folder_name = f"allen_sort_{date_value}_{location_id}"
    # ============================================================

    # Initialize tkinter (needed for dialog boxes)
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Find directories containing amplifier.dat in the parent directories
    amplifier_dirs = []
    for parent_dir in parent_directories:
        if os.path.exists(parent_dir):
            found_dirs = find_amplifier_dat_in_directory(parent_dir)
            amplifier_dirs.extend(found_dirs)
            print(f"Found {len(found_dirs)} directories with amplifier.dat in {parent_dir}")
        else:
            print(f"Warning: Parent directory {parent_dir} does not exist, skipping.")

    if not amplifier_dirs:
        print("Error: No directories containing amplifier.dat found.")
        input("Press Enter to exit...")
        return

    # Sort directories by modification time
    sorted_dirs = sort_by_modification_time(amplifier_dirs)

    # Display the directories found (with modification times for verification)
    for i, directory in enumerate(sorted_dirs):
        amplifier_path = os.path.join(directory, 'amplifier.dat')
        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(amplifier_path))
        print(f"{i + 1}. {directory}")
        print(f"   Modified: {mod_time}")

    # Ask user to confirm stitching with these directories
    proceed = simpledialog.askstring("Confirm Stitching",
                                     f"Found {len(sorted_dirs)} directories to stitch in chronological order.\n\n"
                                     f"First: {os.path.basename(sorted_dirs[0])}\n"
                                     f"Last: {os.path.basename(sorted_dirs[-1])}\n\n"
                                     f"Type 'yes' to proceed:")

    if proceed and proceed.lower() == 'yes':
        # Determine output folder location
        common_parent = os.path.commonpath(sorted_dirs)
        output_folder_path = os.path.join(common_parent, output_folder_name)

        print(f"Output folder path: {output_folder_path}")
        print(f"Directories to stitch (in order):")
        for dir in sorted_dirs:
            print(f" - {dir}")


        stitcher = IntanFileStitcher(sorted_dirs)
        stitcher.stitch_files(output_folder_path)
    else:
        print("Operation cancelled.")
        input("Press Enter to exit...")


if __name__ == '__main__':
    main()
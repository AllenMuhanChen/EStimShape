"""
Entry point for the MRI viewer package.
Usage: python -m mri_viewer [path_to_par_file]
"""

import os, sys
import tkinter as tk

from src.mri.viewer import TriplanarMRIViewer


def main():
    default_path = sys.argv[1] if len(sys.argv) > 1 else None

    root = tk.Tk()
    app = TriplanarMRIViewer(root, default_path)

    # Load app config — look in current working directory.
    cfg_file = os.path.join(os.getcwd(), "mri_viewer_config.json")
    app._load_config(cfg_file, override_default_path=default_path)

    root.mainloop()


if __name__ == "__main__":
    main()
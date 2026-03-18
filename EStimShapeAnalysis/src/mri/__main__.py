"""
Entry point for the MRI viewer package.
Usage: python -m mri_viewer [path_to_par_file]
"""

import os, sys, json
import tkinter as tk

from src.mri.viewer import TriplanarMRIViewer


def main():
    default_path = sys.argv[1] if len(sys.argv) > 1 else None

    root = tk.Tk()
    app = TriplanarMRIViewer(root, default_path)

    # Load app config — look in current working directory
    cfg_file = os.path.join(os.getcwd(), "mri_viewer_config.json")
    cfg = {}
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file) as f:
                cfg = json.load(f)
            saved = cfg.get("default_path")
            if default_path is None and saved:
                app.default_path = saved
                app.file_path_var.set(saved)
                default_path = saved
            if "ebz_world" in cfg:
                ew = cfg["ebz_world"]
                app.ebz_ml_var.set(ew[0])
                app.ebz_ap_var.set(ew[1])
                app.ebz_dv_var.set(ew[2])
        except Exception as e:
            print(f"Config error: {e}")

    if default_path and os.path.exists(default_path):
        app.load_and_visualize()
        if "ebz_world" in cfg:
            app._set_ebz_manual()
        monkey_path = cfg.get("monkey_specific_path")
        if monkey_path and os.path.exists(monkey_path):
            app._load_chamber_from_path(monkey_path)

        # Auto-load atlas if saved in config
        atlas_nifti = cfg.get("atlas_nifti_path")
        if atlas_nifti and os.path.exists(atlas_nifti):
            app._load_atlas_from_path(atlas_nifti)
            atlas_labels = cfg.get("atlas_label_path")
            if atlas_labels and os.path.exists(atlas_labels):
                app._load_atlas_labels_from_path(atlas_labels)

    root.mainloop()


if __name__ == "__main__":
    main()
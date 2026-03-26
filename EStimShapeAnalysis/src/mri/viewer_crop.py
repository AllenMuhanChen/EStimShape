import numpy as np
import tkinter as tk
from tkinter import ttk
from src.mri.volume import compute_world_bbox, reslice_view
from src.mri.correction import save_crop_bounds, save_corrections

class CropMixin:
    def _toggle_crop_mode(self):
        if self.crop_mode:
            self._exit_crop_mode(); return
        if self.ebz_pick_armed:
            self._disarm_ebz_pick()
        self.crop_mode = True
        self.btn_crop.config(text="Cancel Crop")
        self.crop_status_var.set("CROP MODE: drag a rectangle on any view")
        self._saved_crop_for_cancel = self.crop_bounds.copy()
        self.crop_bounds = {}
        self._recompute(); self._setup_sliders(); self.display_all()

    def _exit_crop_mode(self):
        self.crop_mode = False
        self._crop_start = None; self._crop_rect = None; self._crop_view = None
        self.btn_crop.config(text="Crop Views (drag rectangle)")
        if hasattr(self, '_saved_crop_for_cancel'):
            if not self.crop_bounds and self._saved_crop_for_cancel:
                self.crop_bounds = self._saved_crop_for_cancel
                self._recompute(); self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
                self._setup_sliders(); self.display_all()
            delattr(self, '_saved_crop_for_cancel')
        self.crop_status_var.set("")

    # ================================================================ Zoom
    def _on_scroll(self, event):
        """Scroll-wheel zooms the view under the cursor, centered on the mouse.
        zoom_bounds are stored in EBZ-relative display coords."""
        if self.data is None or event.inaxes is None:
            return
        ax = event.inaxes
        if not hasattr(ax, '_vi'):
            return
        vi = ax._vi
        _, h_wax, v_wax = self.SLICE_CFG[vi]

        # Current visible window in display coords
        if vi in self.zoom_bounds:
            h_lo, h_hi, v_lo, v_hi = self.zoom_bounds[vi]
        else:
            # Default: full resliced extent in display (EBZ-relative) coords
            disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
            db = self.view_display_bounds[vi]
            h_lo = db[0] - disp_off[h_wax]
            h_hi = db[1] - disp_off[h_wax]
            v_lo = db[3] - disp_off[v_wax]   # v_hi becomes v_lo in display (inverted)
            v_hi = db[2] - disp_off[v_wax]

        mx, my = event.xdata, event.ydata  # already in EBZ-relative display coords
        if mx is None or my is None:
            return

        factor = 0.75 if event.button == 'up' else (1.0 / 0.75)

        new_h_lo = mx + (h_lo - mx) * factor
        new_h_hi = mx + (h_hi - mx) * factor
        new_v_lo = my + (v_lo - my) * factor
        new_v_hi = my + (v_hi - my) * factor

        # Full extent in display coords (used as zoom-out limit)
        disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
        db = self.view_display_bounds[vi]
        full_h_span = db[1] - db[0]
        full_v_span = db[3] - db[2]

        if (new_h_hi - new_h_lo) >= full_h_span * 1.01 and \
           abs(new_v_hi - new_v_lo) >= full_v_span * 1.01:
            self.zoom_bounds.pop(vi, None)
        else:
            self.zoom_bounds[vi] = (new_h_lo, new_h_hi, new_v_lo, new_v_hi)

        self.display_all()

    def _reset_zoom(self, vi=None):
        """Reset zoom for one view index, or all if vi is None."""
        if vi is None:
            self.zoom_bounds.clear()
        else:
            self.zoom_bounds.pop(vi, None)
        if self.data is not None:
            self.display_all()

    # ================================================================ Interpolation / resolution
    def _on_interp_change(self, event=None):
        order_map = {"Nearest (order 0)": 0, "Linear (order 1)": 1, "Cubic (order 3)": 3}
        self.interp_order = order_map.get(self.interp_var.get(), 3)
        if self.data is not None:
            self.display_all()

    def _on_voxel_size_change(self, event=None):
        try:
            vs = float(self.voxel_size_var.get())
            if vs <= 0:
                raise ValueError
        except (ValueError, tk.TclError):
            self.voxel_size_var.set(self.output_voxel_size)
            return
        self.output_voxel_size = vs
        if self.data is not None:
            self._recompute()
            self.display_all()

    def _reset_crop(self):
        self.crop_bounds = {}
        if self.crop_mode:
            self._exit_crop_mode()
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
        self._setup_sliders()
        save_crop_bounds(self.corr_config, self.crop_bounds)
        save_corrections(self.corr_json_path, self.corr_config)
        self.display_all()
        self.crop_status_var.set("Crop reset.")

    # ================================================================ Chamber

"""
Tri-planar PAR/REC MRI Viewer with reslicing correction pipeline.

Transform chain:
    voxel  --[native_affine]--> raw_world  --[correction]--> corrected_world

Each displayed slice is resliced from the raw volume by sampling along a plane
in corrected world space, then mapping back to voxel space via:
    vox = inv(correction @ native_affine) @ world_point

This means rotations in the correction matrix *visually rotate the image*,
not just relabel coordinates.

The correction matrix is persisted in <basename>_corrections.json with full
version history (timestamped, with notes), undo/redo, and jump-to-version.

Coordinate convention (RAS+):
    +X = Right,  +Y = Anterior,  +Z = Superior
Lab labels:
    ML = world X,  AP = world Y,  DV = world Z
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import FuncFormatter
from nibabel.parrec import load as load_parrec
import nibabel as nib
from scipy.ndimage import map_coordinates
import os, sys, json, pprint, datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ====================================================================
# Correction-matrix persistence
# ====================================================================

def _default_entry(matrix=None, note="identity"):
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "note": note,
        "matrix": (matrix if matrix is not None else np.eye(4)).tolist(),
    }

def load_corrections(path):
    if not os.path.exists(path):
        e = _default_entry()
        cfg = {"correction_history": [e], "current_index": 0}
        return np.eye(4), cfg
    with open(path) as f:
        cfg = json.load(f)
    hist = cfg.get("correction_history", [])
    if not hist:
        e = _default_entry()
        cfg["correction_history"] = [e]
        cfg["current_index"] = 0
        return np.eye(4), cfg
    idx = cfg.get("current_index", len(hist) - 1)
    return np.array(hist[idx]["matrix"]), cfg

def save_corrections(path, cfg):
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)

def push_correction(cfg, mat, note=""):
    cfg["correction_history"].append(_default_entry(mat, note))
    cfg["current_index"] = len(cfg["correction_history"]) - 1


# ====================================================================
# Rotation / translation builders
# ====================================================================

def rot_x(deg):
    r = np.radians(deg); c, s = np.cos(r), np.sin(r)
    M = np.eye(4); M[1,1]=c; M[1,2]=-s; M[2,1]=s; M[2,2]=c; return M

def rot_y(deg):
    r = np.radians(deg); c, s = np.cos(r), np.sin(r)
    M = np.eye(4); M[0,0]=c; M[0,2]=s; M[2,0]=-s; M[2,2]=c; return M

def rot_z(deg):
    r = np.radians(deg); c, s = np.cos(r), np.sin(r)
    M = np.eye(4); M[0,0]=c; M[0,1]=-s; M[1,0]=s; M[1,1]=c; return M

def xlate(dx, dy, dz):
    M = np.eye(4); M[:3, 3] = [dx, dy, dz]; return M


# ====================================================================
# Viewer
# ====================================================================

class TriplanarMRIViewer:
    """
    Display conventions:
        Sagittal : horiz = A/P,  vert = S/I  (S at top)
        Coronal  : horiz = R/L,  vert = S/I  (S at top)
        Axial    : horiz = R/L,  vert = A/P  (A at top)
    """

    VIEW_NAMES = ["Sagittal", "Coronal", "Axial"]
    # (fixed_world_axis, horiz_world_axis, vert_world_axis)
    SLICE_CFG = [(0, 1, 2), (1, 0, 2), (2, 0, 1)]
    WORLD_LABELS = ["ML (R/L)", "AP (A/P)", "DV (S/I)"]

    def __init__(self, root, default_path=None):
        self.root = root
        self.root.title("PAR/REC Tri-Planar MRI Viewer")
        self.root.geometry("1450x960")
        self.root.resizable(True, True)

        # Data
        self.img = None
        self.data = None          # raw 3D (or 4D) volume
        self.native_affine = None
        self.correction = np.eye(4)
        self.corrected_affine = None
        self.inv_corrected = None
        self.voxel_sizes = None
        self.default_path = default_path
        self.output_voxel_size = 0.75  # mm, for resliced output grid

        # Correction persistence
        self.corr_config = None
        self.corr_json_path = None

        # Volume dims
        self.dim_sizes = [0, 0, 0]
        self.has_dynamics = False
        self.dynamics = 1
        self.current_dynamic = 0

        # World-space bounding box (recomputed when correction changes)
        self.world_min = np.zeros(3)
        self.world_max = np.zeros(3)
        self.world_center = np.zeros(3)
        # Output grid sizes per view (pixels)
        self.grid_sizes = [(0, 0)] * 3  # (n_h, n_v) for each view

        # Crosshair position in corrected world space (mm)
        self.cursor_world = np.zeros(3)

        # EBZ in corrected world space
        self.ebz_set = False
        self.ebz_world = np.zeros(3)

        # EBZ pick mode: right-click only sets EBZ when armed
        self.ebz_pick_armed = False

        # Crop bounds per view: {view_idx: (h_lo, h_hi, v_lo, v_hi)} in world mm
        # None means full (uncropped)
        self.crop_bounds = {}  # persisted in corrections JSON
        self.crop_mode = False  # True when user is drawing a crop rectangle
        self._crop_rect = None  # matplotlib Rectangle patch during drag
        self._crop_start = None  # (x, y) in world mm at mouse-down
        self._crop_view = None   # which view the crop drag is happening in

        self._setup_ui()

    # ---------------------------------------------------------------- UI
    def _setup_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # File row
        row = ttk.Frame(main); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="PAR File:").pack(side=tk.LEFT, padx=3)
        self.file_path_var = tk.StringVar(value=self.default_path or "")
        ttk.Entry(row, textvariable=self.file_path_var, width=55).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        ttk.Button(row, text="Browse...", command=self._browse).pack(side=tk.LEFT, padx=2)
        ttk.Button(row, text="Load", command=self.load_and_visualize).pack(side=tk.LEFT, padx=2)
        ttk.Button(row, text="Save Defaults", command=self._save_defaults).pack(side=tk.LEFT, padx=2)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main, textvariable=self.status_var).pack(fill=tk.X, padx=5)

        # ---- Collapsible panels container ----
        self._panels_frame = ttk.Frame(main)
        self._panels_frame.pack(fill=tk.X, padx=0, pady=0)
        self._panels_visible = True

        # Toggle button for collapsing/expanding panels
        self._toggle_panels_btn = ttk.Button(
            main, text="▲ Hide Controls", command=self._toggle_panels)
        self._toggle_panels_btn.pack(fill=tk.X, padx=5, pady=1)

        # --- EBZ panel (inside collapsible) ---
        ebz = ttk.LabelFrame(self._panels_frame, text="EBZ (External Brain Zero) - corrected world coords")
        ebz.pack(fill=tk.X, padx=5, pady=2)
        for i, (lbl, vn) in enumerate([("AP mm:", "ebz_ap"), ("DV mm:", "ebz_dv"), ("ML mm:", "ebz_ml")]):
            ttk.Label(ebz, text=lbl).grid(row=0, column=2*i, padx=3, pady=2)
            v = tk.DoubleVar(value=0.0); setattr(self, vn + "_var", v)
            ttk.Entry(ebz, textvariable=v, width=10).grid(row=0, column=2*i+1, padx=3)
        self.btn_set_ebz = ttk.Button(ebz, text="Set EBZ (manual)",
                                       command=self._set_ebz_manual, state="disabled")
        self.btn_set_ebz.grid(row=0, column=6, padx=3)
        self.btn_ebz_xhair = ttk.Button(ebz, text="Set EBZ to crosshair",
                                          command=self._set_ebz_to_crosshair, state="disabled")
        self.btn_ebz_xhair.grid(row=0, column=7, padx=3)
        self.btn_reset_ebz = ttk.Button(ebz, text="Reset EBZ",
                                         command=self._reset_ebz, state="disabled")
        self.btn_reset_ebz.grid(row=0, column=8, padx=3)
        self.btn_ebz_pick = ttk.Button(ebz, text="Pick EBZ (right-click)",
                                        command=self._toggle_ebz_pick, state="disabled")
        self.btn_ebz_pick.grid(row=0, column=9, padx=3)

        self.cursor_info_var = tk.StringVar(value="Crosshair: ---")
        ttk.Label(ebz, textvariable=self.cursor_info_var).grid(
            row=1, column=0, columnspan=10, sticky="w", padx=5)
        self.ebz_pick_label_var = tk.StringVar(value="")
        ttk.Label(ebz, textvariable=self.ebz_pick_label_var, foreground="red").grid(
            row=2, column=0, columnspan=10, sticky="w", padx=5)

        # --- Correction panel (inside collapsible) ---
        corr = ttk.LabelFrame(self._panels_frame, text="Correction Matrix  (rotations applied in corrected world space)")
        corr.pack(fill=tk.X, padx=5, pady=2)

        r_row = ttk.Frame(corr); r_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r_row, text="Rotate (deg):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X (ML/roll)", "x"), ("Y (AP/pitch)", "y"), ("Z (DV/yaw)", "z")]:
            ttk.Label(r_row, text=f"{al}:").pack(side=tk.LEFT, padx=(8, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"rot_{an}_var", v)
            ttk.Entry(r_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)

        t_row = ttk.Frame(corr); t_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(t_row, text="Translate (mm):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X (ML)", "tx"), ("Y (AP)", "ty"), ("Z (DV)", "tz")]:
            ttk.Label(t_row, text=f"{al}:").pack(side=tk.LEFT, padx=(8, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"trans_{an}_var", v)
            ttk.Entry(t_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)

        b_row = ttk.Frame(corr); b_row.pack(fill=tk.X, padx=3, pady=2)
        self.btn_apply = ttk.Button(b_row, text="Apply", command=self._apply_correction, state="disabled")
        self.btn_apply.pack(side=tk.LEFT, padx=3)
        self.btn_reset_corr = ttk.Button(b_row, text="Reset to Identity",
                                          command=self._reset_correction, state="disabled")
        self.btn_reset_corr.pack(side=tk.LEFT, padx=3)
        self.btn_undo = ttk.Button(b_row, text="Undo", command=self._undo, state="disabled")
        self.btn_undo.pack(side=tk.LEFT, padx=3)
        self.btn_redo = ttk.Button(b_row, text="Redo", command=self._redo, state="disabled")
        self.btn_redo.pack(side=tk.LEFT, padx=3)
        ttk.Button(b_row, text="History", command=self._show_history).pack(side=tk.LEFT, padx=3)
        ttk.Button(b_row, text="Header", command=self._show_header).pack(side=tk.LEFT, padx=3)

        self.corr_info_var = tk.StringVar(value="Correction: identity")
        ttk.Label(corr, textvariable=self.corr_info_var).pack(anchor="w", padx=5, pady=1)
        self.corr_ver_var = tk.StringVar(value="")
        ttk.Label(corr, textvariable=self.corr_ver_var).pack(anchor="w", padx=5, pady=1)

        note_row = ttk.Frame(corr); note_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(note_row, text="Note:").pack(side=tk.LEFT, padx=3)
        self.corr_note_var = tk.StringVar(value="")
        ttk.Entry(note_row, textvariable=self.corr_note_var, width=50).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        # --- Crop panel (inside collapsible) ---
        crop_frame = ttk.LabelFrame(self._panels_frame, text="View Cropping")
        crop_frame.pack(fill=tk.X, padx=5, pady=2)
        self.btn_crop = ttk.Button(crop_frame, text="Crop Views (drag rectangle)",
                                    command=self._toggle_crop_mode, state="disabled")
        self.btn_crop.pack(side=tk.LEFT, padx=3, pady=2)
        self.btn_reset_crop = ttk.Button(crop_frame, text="Reset All Crops",
                                          command=self._reset_crop, state="disabled")
        self.btn_reset_crop.pack(side=tk.LEFT, padx=3, pady=2)
        self.crop_status_var = tk.StringVar(value="")
        ttk.Label(crop_frame, textvariable=self.crop_status_var, foreground="blue").pack(
            side=tk.LEFT, padx=10, pady=2)

        # Figure
        fig_frame = ttk.Frame(main)
        fig_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        self.fig = Figure(figsize=(14, 5), dpi=100)
        self.fig.subplots_adjust(left=0.04, right=0.98, top=0.93, bottom=0.07, wspace=0.25)
        self.axes = [self.fig.add_subplot(1, 3, i + 1) for i in range(3)]
        self.canvas = FigureCanvasTkAgg(self.fig, master=fig_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, fig_frame)
        self.toolbar.update()
        self.canvas.mpl_connect("button_press_event", self._on_click)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)

        # Slice sliders with "→ EBZ" buttons
        sf = ttk.Frame(main); sf.pack(fill=tk.X, padx=5, pady=2)
        self.slice_vars, self.slice_scales, self.slice_lbls = [], [], []
        self.ebz_goto_btns = []
        for i, name in enumerate(self.VIEW_NAMES):
            ttk.Label(sf, text=f"{name}:").grid(row=i, column=0, sticky="w", padx=3, pady=1)
            v = tk.DoubleVar(value=0.0)
            sc = ttk.Scale(sf, from_=0, to=1, orient=tk.HORIZONTAL, variable=v,
                           command=lambda val, idx=i: self._on_slider(idx))
            sc.grid(row=i, column=1, sticky="we", padx=3)
            lb = ttk.Label(sf, text="0.00 mm", width=20)
            lb.grid(row=i, column=2, padx=3)
            btn = ttk.Button(sf, text="→0", width=3,
                             command=lambda idx=i: self._goto_ebz_zero(idx), state="disabled")
            btn.grid(row=i, column=3, padx=2)
            self.slice_vars.append(v)
            self.slice_scales.append(sc)
            self.slice_lbls.append(lb)
            self.ebz_goto_btns.append(btn)
        sf.columnconfigure(1, weight=1)

        # Dynamic slider
        self.dyn_frame = ttk.Frame(sf)
        self.dyn_frame.grid(row=3, column=0, columnspan=4, sticky="we")
        ttk.Label(self.dyn_frame, text="Dynamic:").grid(row=0, column=0, sticky="w", padx=3)
        self.dyn_var = tk.IntVar(value=0)
        self.dyn_scale = ttk.Scale(self.dyn_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                   variable=self.dyn_var,
                                   command=lambda *a: self._on_dyn_slider())
        self.dyn_scale.grid(row=0, column=1, sticky="we", padx=3)
        self.dyn_lbl = ttk.Label(self.dyn_frame, text="0/0", width=14)
        self.dyn_lbl.grid(row=0, column=2, padx=3)
        self.dyn_frame.columnconfigure(1, weight=1)
        self.dyn_frame.grid_remove()

    def _toggle_panels(self):
        """Show/hide the control panels to maximize figure space."""
        if self._panels_visible:
            self._panels_frame.pack_forget()
            self._toggle_panels_btn.config(text="▼ Show Controls")
            self._panels_visible = False
        else:
            # Re-insert panels before the toggle button
            self._panels_frame.pack(fill=tk.X, padx=0, pady=0,
                                     before=self._toggle_panels_btn)
            self._toggle_panels_btn.config(text="▲ Hide Controls")
            self._panels_visible = True

    # ---------------------------------------------------------------- File helpers
    def _browse(self):
        d = None
        if self.default_path:
            d = os.path.dirname(self.default_path) if not os.path.isdir(
                self.default_path) else self.default_path
        fn = filedialog.askopenfilename(
            title="Select PAR File",
            filetypes=[("PAR", "*.PAR *.par"), ("All", "*.*")], initialdir=d)
        if fn:
            self.file_path_var.set(fn)

    def _check_rec(self, par):
        b = os.path.splitext(par)[0]
        return os.path.exists(b + ".REC") or os.path.exists(b + ".rec")

    def _save_defaults(self):
        p = self.file_path_var.get().strip()
        if not p: messagebox.showerror("Error", "No path"); return
        cp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "mri_viewer_config.json")
        try:
            c = {"default_path": p}
            if self.ebz_set:
                c["ebz_world"] = self.ebz_world.tolist()
            with open(cp, "w") as f: json.dump(c, f, indent=2)
            self.default_path = p
            messagebox.showinfo("Saved", f"Defaults saved to {cp}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _corr_json_for(self, par):
        return os.path.splitext(par)[0] + "_corrections.json"

    # ---------------------------------------------------------------- Loading
    def load_and_visualize(self):
        par = self.file_path_var.get().strip()
        if not par: messagebox.showerror("Error", "Select a PAR file."); return
        if not os.path.exists(par): messagebox.showerror("Error", f"{par} not found."); return
        if not par.upper().endswith(".PAR"):
            if not messagebox.askyesno("Warning", "Not a .PAR extension. Continue?"): return
        if not self._check_rec(par):
            messagebox.showerror("Error", ".REC not found."); return

        try:
            self.status_var.set(f"Loading {par}..."); self.root.update()
            self.img = load_parrec(par, strict_sort=True)
            raw = self.img.get_fdata()
            self.native_affine = self.img.affine.copy()
            self.voxel_sizes = nib.affines.voxel_sizes(self.native_affine)

            if raw.ndim == 4:
                self.data = raw; self.has_dynamics = True; self.dynamics = raw.shape[3]
            elif raw.ndim == 3:
                self.data = raw; self.has_dynamics = False; self.dynamics = 1
            else:
                raise ValueError(f"Unexpected ndim={raw.ndim}")
            self.dim_sizes = list(self.data.shape[:3])

            # Load correction
            self.corr_json_path = self._corr_json_for(par)
            self.correction, self.corr_config = load_corrections(self.corr_json_path)
            self._load_crop_from_config()
            self._recompute()

            # Centre crosshair
            self.cursor_world = self.world_center.copy()

            # Configure sliders
            self._setup_sliders()

            if self.has_dynamics:
                self.dyn_scale.configure(from_=0, to=self.dynamics - 1)
                self.dyn_var.set(0); self.dyn_frame.grid()
            else:
                self.dyn_frame.grid_remove()

            for b in (self.btn_set_ebz, self.btn_ebz_xhair, self.btn_apply,
                      self.btn_reset_corr, self.btn_undo, self.btn_redo,
                      self.btn_ebz_pick, self.btn_crop, self.btn_reset_crop):
                b.config(state="normal")
            for b in self.ebz_goto_btns:
                b.config(state="normal")

            self._update_corr_info()
            self.display_all()
            self.status_var.set(
                f"Loaded {os.path.basename(par)}  shape={self.dim_sizes}  "
                f"voxel={self.voxel_sizes[0]:.3f}x{self.voxel_sizes[1]:.3f}x"
                f"{self.voxel_sizes[2]:.3f} mm")
        except Exception as e:
            self.status_var.set("Error"); messagebox.showerror("Error", str(e))
            import traceback; traceback.print_exc()

    def _recompute(self):
        """Recompute corrected affine and world bounding box."""
        self.corrected_affine = self.correction @ self.native_affine
        self.inv_corrected = np.linalg.inv(self.corrected_affine)

        # World bounding box from voxel corners (full, uncropped)
        ds = self.dim_sizes
        corners = np.array([
            [0, 0, 0, 1], [ds[0]-1, 0, 0, 1], [0, ds[1]-1, 0, 1],
            [0, 0, ds[2]-1, 1], [ds[0]-1, ds[1]-1, 0, 1],
            [ds[0]-1, 0, ds[2]-1, 1], [0, ds[1]-1, ds[2]-1, 1],
            [ds[0]-1, ds[1]-1, ds[2]-1, 1],
        ], dtype=float)
        cw = (self.corrected_affine @ corners.T).T[:, :3]
        self.full_world_min = cw.min(axis=0)
        self.full_world_max = cw.max(axis=0)
        self.world_center = (self.full_world_min + self.full_world_max) / 2.0

        # Keep shared world_min/max as the full uncropped bbox
        # (used for slider ranges on the fixed axis, and for clamping crosshair)
        self.world_min = self.full_world_min.copy()
        self.world_max = self.full_world_max.copy()

        # Per-view display bounds: each view can have independent h/v crop
        # view_display_bounds[vi] = (h_lo, h_hi, v_lo, v_hi)
        vs = self.output_voxel_size
        self.view_display_bounds = []
        self.grid_sizes = []
        for vi in range(3):
            _, h_wax, v_wax = self.SLICE_CFG[vi]
            h_lo = self.full_world_min[h_wax]
            h_hi = self.full_world_max[h_wax]
            v_lo = self.full_world_min[v_wax]
            v_hi = self.full_world_max[v_wax]
            if vi in self.crop_bounds:
                ch_lo, ch_hi, cv_lo, cv_hi = self.crop_bounds[vi]
                h_lo = max(h_lo, ch_lo)
                h_hi = min(h_hi, ch_hi)
                v_lo = max(v_lo, cv_lo)
                v_hi = min(v_hi, cv_hi)
            self.view_display_bounds.append((h_lo, h_hi, v_lo, v_hi))
            n_h = max(2, int(np.ceil((h_hi - h_lo) / vs)))
            n_v = max(2, int(np.ceil((v_hi - v_lo) / vs)))
            self.grid_sizes.append((n_h, n_v))

    def _setup_sliders(self):
        for i in range(3):
            fix_wax = self.SLICE_CFG[i][0]
            lo, hi = self.world_min[fix_wax], self.world_max[fix_wax]
            self.slice_scales[i].configure(from_=lo, to=hi)
            self.slice_vars[i].set(self.world_center[fix_wax])

    # ---------------------------------------------------------------- Coordinate transforms
    def vox_to_world(self, vox):
        return (self.corrected_affine @ np.array([*vox[:3], 1.0]))[:3]

    def world_to_vox(self, w):
        return (self.inv_corrected @ np.array([*w[:3], 1.0]))[:3]

    # ---------------------------------------------------------------- Resliced slice extraction
    def _reslice_view(self, view_idx):
        """
        Sample a 2D slice from the volume at the current crosshair position
        for the given view. Returns (img2d, h_coords_mm, v_coords_mm).

        The slice is sampled in corrected world space, then mapped back to
        voxel space and interpolated with scipy map_coordinates.
        """
        fix_wax, h_wax, v_wax = self.SLICE_CFG[view_idx]
        n_h, n_v = self.grid_sizes[view_idx]
        vs = self.output_voxel_size

        fix_val = self.cursor_world[fix_wax]

        # Use per-view display bounds
        h_lo, h_hi, v_lo, v_hi = self.view_display_bounds[view_idx]

        # Build sampling grid in corrected world space
        h_coords = np.linspace(h_lo, h_hi, n_h)
        # Vert: top = max (S for sag/cor, A for axial)
        v_coords = np.linspace(v_hi, v_lo, n_v)

        hh, vv = np.meshgrid(h_coords, v_coords)

        # Build world coordinate array (n_v x n_h x 4)
        world_pts = np.ones((n_v, n_h, 4))
        world_pts[:, :, fix_wax] = fix_val
        world_pts[:, :, h_wax] = hh
        world_pts[:, :, v_wax] = vv

        # Map to voxel space
        flat = world_pts.reshape(-1, 4)
        vox_flat = (self.inv_corrected @ flat.T).T[:, :3]

        # Get volume data (handle 4D)
        vol = self.data
        if self.has_dynamics:
            vol = self.data[:, :, :, self.current_dynamic]

        # Sample with trilinear interpolation
        coords = [vox_flat[:, ax] for ax in range(3)]
        sampled = map_coordinates(vol, coords, order=1, mode='constant', cval=0)
        img2d = sampled.reshape(n_v, n_h)

        return img2d, h_coords, v_coords

    # ---------------------------------------------------------------- Display
    def display_all(self):
        if self.data is None:
            return

        for vi in range(3):
            ax = self.axes[vi]
            ax.clear()

            fix_wax, h_wax, v_wax = self.SLICE_CFG[vi]
            img2d, h_coords, v_coords = self._reslice_view(vi)
            n_h, n_v = len(h_coords), len(v_coords)

            # Extent for imshow: [left, right, bottom, top] in mm
            h_lo, h_hi = h_coords[0], h_coords[-1]
            v_lo, v_hi = v_coords[-1], v_coords[0]  # v_coords goes high->low
            extent = [h_lo, h_hi, v_lo, v_hi]

            im = ax.imshow(img2d, cmap='gray', aspect='equal', origin='upper',
                           interpolation='nearest', extent=extent)
            try:
                nz = img2d[img2d > 0]
                if len(nz) > 100:
                    vmin, vmax = np.percentile(nz, [1, 99])
                    im.set_clim(vmin, vmax)
            except:
                pass

            # Crosshair
            ch = self.cursor_world[h_wax]
            cv = self.cursor_world[v_wax]
            ax.axvline(ch, color='lime', lw=0.7, alpha=0.6)
            ax.axhline(cv, color='lime', lw=0.7, alpha=0.6)

            # EBZ marker
            if self.ebz_set:
                ax.axvline(self.ebz_world[h_wax], color='red', lw=0.5, alpha=0.4, ls='--')
                ax.axhline(self.ebz_world[v_wax], color='red', lw=0.5, alpha=0.4, ls='--')
                ax.plot(self.ebz_world[h_wax], self.ebz_world[v_wax], 'r*', markersize=8)

            # Title
            wval = self.cursor_world[fix_wax]
            if self.ebz_set:
                rel = wval - self.ebz_world[fix_wax]
                title = (f"{self.VIEW_NAMES[vi]}  "
                         f"{self.WORLD_LABELS[fix_wax]}={wval:.2f} mm  "
                         f"({rel:+.2f} from EBZ)")
            else:
                title = f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[fix_wax]}={wval:.2f} mm"
            ax.set_title(title, fontsize=10)
            ax.set_xlabel(self.WORLD_LABELS[h_wax], fontsize=9)
            ax.set_ylabel(self.WORLD_LABELS[v_wax], fontsize=9)
            ax.tick_params(labelsize=7)

            # Store view info for click mapping
            ax._vi = vi

        self.fig.canvas.draw_idle()
        self._update_info()
        self._sync_sliders()

    def _update_info(self):
        if self.data is None: return
        w = self.cursor_world
        vox = self.world_to_vox(w)
        txt = (f"Crosshair: ML={w[0]:.2f}, AP={w[1]:.2f}, DV={w[2]:.2f} mm"
               f"   voxel=[{vox[0]:.1f}, {vox[1]:.1f}, {vox[2]:.1f}]")
        if self.ebz_set:
            rel = w - self.ebz_world
            txt += f"   rel EBZ: ML={rel[0]:.2f}, AP={rel[1]:.2f}, DV={rel[2]:.2f}"
        self.cursor_info_var.set(txt)

    def _sync_sliders(self):
        for i in range(3):
            fix_wax = self.SLICE_CFG[i][0]
            val = self.cursor_world[fix_wax]
            self.slice_vars[i].set(val)
            if self.ebz_set:
                rel = val - self.ebz_world[fix_wax]
                self.slice_lbls[i].config(
                    text=f"{val:.2f} mm ({rel:+.2f} EBZ)")
            else:
                self.slice_lbls[i].config(text=f"{val:.2f} mm")

    # ---------------------------------------------------------------- Events
    def _on_slider(self, view_idx):
        if self.data is None: return
        fix_wax = self.SLICE_CFG[view_idx][0]
        new_val = self.slice_vars[view_idx].get()
        if abs(new_val - self.cursor_world[fix_wax]) > 0.01:
            self.cursor_world[fix_wax] = new_val
            self.display_all()

    def _goto_ebz_zero(self, view_idx):
        """Jump the slider for this view to 0 relative to EBZ."""
        if self.data is None:
            return
        if not self.ebz_set:
            self.status_var.set("Set EBZ first to use Go-to-zero.")
            return
        fix_wax = self.SLICE_CFG[view_idx][0]
        self.cursor_world[fix_wax] = self.ebz_world[fix_wax]
        self.display_all()

    def _on_dyn_slider(self):
        self.current_dynamic = self.dyn_var.get()
        self.dyn_lbl.config(text=f"{self.current_dynamic}/{self.dynamics-1}")
        self.display_all()

    def _on_click(self, event):
        if self.data is None or event.inaxes is None: return
        ax = event.inaxes
        if not hasattr(ax, '_vi'): return
        vi = ax._vi
        _, h_wax, v_wax = self.SLICE_CFG[vi]
        x, y = event.xdata, event.ydata
        if x is None or y is None: return

        # --- Crop mode: start rectangle drag ---
        if self.crop_mode and event.button == 1:
            self._crop_start = (x, y)
            self._crop_view = vi
            # Add a rectangle patch
            from matplotlib.patches import Rectangle
            self._crop_rect = Rectangle((x, y), 0, 0,
                                         linewidth=2, edgecolor='cyan',
                                         facecolor='cyan', alpha=0.15)
            ax.add_patch(self._crop_rect)
            self.fig.canvas.draw_idle()
            return

        # --- EBZ pick mode: right-click sets EBZ ---
        if self.ebz_pick_armed and event.button == 3:
            self.cursor_world[h_wax] = np.clip(x, self.world_min[h_wax], self.world_max[h_wax])
            self.cursor_world[v_wax] = np.clip(y, self.world_min[v_wax], self.world_max[v_wax])
            self._set_ebz_to_crosshair()
            self._disarm_ebz_pick()
            return

        # --- Normal left-click: move crosshair ---
        if event.button == 1:
            self.cursor_world[h_wax] = np.clip(x, self.world_min[h_wax], self.world_max[h_wax])
            self.cursor_world[v_wax] = np.clip(y, self.world_min[v_wax], self.world_max[v_wax])
            self.display_all()

    def _on_release(self, event):
        """Handle mouse button release — finalize crop rectangle."""
        if not self.crop_mode or self._crop_start is None: return
        if event.inaxes is None: return
        ax = event.inaxes
        if not hasattr(ax, '_vi') or ax._vi != self._crop_view: return

        x, y = event.xdata, event.ydata
        if x is None or y is None: return

        x0, y0 = self._crop_start
        # Ensure min < max
        h_lo, h_hi = min(x0, x), max(x0, x)
        v_lo, v_hi = min(y0, y), max(y0, y)

        # Minimum size check (at least 5mm in each direction)
        if (h_hi - h_lo) < 5 or (v_hi - v_lo) < 5:
            self.crop_status_var.set("Crop rectangle too small, ignored.")
            self._crop_start = None
            self._crop_rect = None
            self._crop_view = None
            self.display_all()
            return

        vi = self._crop_view
        _, h_wax, v_wax = self.SLICE_CFG[vi]

        # Merge: keep old crops from other views, add/replace this view's crop
        old_crops = getattr(self, '_saved_crop_for_cancel', {})
        self.crop_bounds = {k: v for k, v in old_crops.items() if k != vi}
        self.crop_bounds[vi] = (h_lo, h_hi, v_lo, v_hi)

        # Exit crop mode
        # Clear the saved-for-cancel since we're applying a real crop
        if hasattr(self, '_saved_crop_for_cancel'):
            delattr(self, '_saved_crop_for_cancel')
        self.crop_mode = False
        self._crop_start = None
        self._crop_rect = None
        self._crop_view = None
        self.btn_crop.config(text="Crop Views (drag rectangle)")

        # Recompute with new crop, reclamp crosshair
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.world_min, self.world_max)
        self._setup_sliders()
        self._save_crop_to_config()
        self.display_all()
        self.crop_status_var.set(
            f"Cropped {self.VIEW_NAMES[vi]}: "
            f"{self.WORLD_LABELS[h_wax]}=[{h_lo:.1f},{h_hi:.1f}], "
            f"{self.WORLD_LABELS[v_wax]}=[{v_lo:.1f},{v_hi:.1f}] mm")

    def _on_motion(self, event):
        if self.data is None or event.inaxes is None: return
        ax = event.inaxes

        # Update crop rectangle if dragging
        if self.crop_mode and self._crop_start is not None and self._crop_rect is not None:
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                x0, y0 = self._crop_start
                self._crop_rect.set_xy((min(x0, x), min(y0, y)))
                self._crop_rect.set_width(abs(x - x0))
                self._crop_rect.set_height(abs(y - y0))
                self.fig.canvas.draw_idle()
            return

        if hasattr(ax, '_vi'):
            vi = ax._vi
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                _, h_wax, v_wax = self.SLICE_CFG[vi]
                self.status_var.set(
                    f"{self.VIEW_NAMES[vi]}  "
                    f"{self.WORLD_LABELS[h_wax]}={x:.2f}  "
                    f"{self.WORLD_LABELS[v_wax]}={y:.2f} mm")

    # ---------------------------------------------------------------- EBZ
    def _set_ebz_to_crosshair(self):
        if self.data is None: return
        self.ebz_world = self.cursor_world.copy()
        self.ebz_ap_var.set(round(self.ebz_world[1], 3))
        self.ebz_dv_var.set(round(self.ebz_world[2], 3))
        self.ebz_ml_var.set(round(self.ebz_world[0], 3))
        self.ebz_set = True
        self.btn_reset_ebz.config(state="normal")
        self.display_all()

    def _set_ebz_manual(self):
        if self.data is None: return
        try:
            self.ebz_world = np.array([
                self.ebz_ml_var.get(), self.ebz_ap_var.get(), self.ebz_dv_var.get()])
            self.ebz_set = True
            self.btn_reset_ebz.config(state="normal")
            self.display_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _reset_ebz(self):
        self.ebz_set = False; self.ebz_world = np.zeros(3)
        self.ebz_ap_var.set(0); self.ebz_dv_var.set(0); self.ebz_ml_var.set(0)
        self.btn_reset_ebz.config(state="disabled")
        self.display_all()

    def _toggle_ebz_pick(self):
        """Toggle EBZ pick mode — when armed, next right-click sets EBZ."""
        if self.ebz_pick_armed:
            self._disarm_ebz_pick()
        else:
            self.ebz_pick_armed = True
            self.ebz_pick_label_var.set("EBZ PICK ACTIVE — right-click on any view to set EBZ, or click button again to cancel")
            self.btn_ebz_pick.config(text="Cancel EBZ Pick")
            # Exit crop mode if active
            if self.crop_mode:
                self._exit_crop_mode()

    def _disarm_ebz_pick(self):
        self.ebz_pick_armed = False
        self.ebz_pick_label_var.set("")
        self.btn_ebz_pick.config(text="Pick EBZ (right-click)")

    # ---------------------------------------------------------------- Cropping
    def _toggle_crop_mode(self):
        """Enter crop mode: temporarily show full extent so user can draw a new rectangle."""
        if self.crop_mode:
            self._exit_crop_mode()
            return

        # Disarm EBZ pick if active
        if self.ebz_pick_armed:
            self._disarm_ebz_pick()

        self.crop_mode = True
        self.btn_crop.config(text="Cancel Crop")
        self.crop_status_var.set("CROP MODE: drag a rectangle on any view to crop it (other crops preserved)")

        # Temporarily remove all crops so user can see full extent to draw
        self._saved_crop_for_cancel = self.crop_bounds.copy()
        self.crop_bounds = {}
        self._recompute()
        self._setup_sliders()
        self.display_all()

    def _exit_crop_mode(self):
        self.crop_mode = False
        self._crop_start = None
        self._crop_rect = None
        self._crop_view = None
        self.btn_crop.config(text="Crop Views (drag rectangle)")
        if not hasattr(self, '_saved_crop_for_cancel'):
            return
        # If no new crop was applied, restore the old crops
        if not self.crop_bounds and self._saved_crop_for_cancel:
            self.crop_bounds = self._saved_crop_for_cancel
            self._recompute()
            self.cursor_world = np.clip(self.cursor_world, self.world_min, self.world_max)
            self._setup_sliders()
            self.display_all()
        if hasattr(self, '_saved_crop_for_cancel'):
            delattr(self, '_saved_crop_for_cancel')
        self.crop_status_var.set("")

    def _reset_crop(self):
        """Reset all crop bounds to full view."""
        self.crop_bounds = {}
        if self.crop_mode:
            self._exit_crop_mode()
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.world_min, self.world_max)
        self._setup_sliders()
        self._save_crop_to_config()
        self.display_all()
        self.crop_status_var.set("Crop reset to full view.")

    def _save_crop_to_config(self):
        """Persist crop bounds in the corrections JSON."""
        if self.corr_config is None or self.corr_json_path is None:
            return
        if self.crop_bounds:
            self.corr_config["crop_bounds"] = {
                str(k): list(v) for k, v in self.crop_bounds.items()
            }
        else:
            self.corr_config.pop("crop_bounds", None)
        save_corrections(self.corr_json_path, self.corr_config)

    def _load_crop_from_config(self):
        """Load crop bounds from corrections JSON."""
        if self.corr_config is None:
            return
        cb = self.corr_config.get("crop_bounds", {})
        self.crop_bounds = {int(k): tuple(v) for k, v in cb.items()}

    # ---------------------------------------------------------------- Correction matrix
    def _apply_correction(self):
        if self.data is None: return
        rx = self.rot_x_var.get(); ry = self.rot_y_var.get(); rz = self.rot_z_var.get()
        tx = self.trans_tx_var.get(); ty = self.trans_ty_var.get(); tz = self.trans_tz_var.get()

        delta = xlate(tx, ty, tz) @ rot_z(rz) @ rot_y(ry) @ rot_x(rx)
        new_corr = delta @ self.correction

        note = self.corr_note_var.get().strip()
        if not note:
            parts = []
            if rx: parts.append(f"Rx={rx}")
            if ry: parts.append(f"Ry={ry}")
            if rz: parts.append(f"Rz={rz}")
            if tx: parts.append(f"Tx={tx}")
            if ty: parts.append(f"Ty={ty}")
            if tz: parts.append(f"Tz={tz}")
            note = ", ".join(parts) if parts else "no-op"

        self.correction = new_corr
        push_correction(self.corr_config, new_corr, note)
        save_corrections(self.corr_json_path, self.corr_config)

        self._recompute()
        # Reclamp crosshair into new bbox
        self.cursor_world = np.clip(self.cursor_world, self.world_min, self.world_max)
        self._setup_sliders()
        self._update_corr_info()

        for v in (self.rot_x_var, self.rot_y_var, self.rot_z_var,
                  self.trans_tx_var, self.trans_ty_var, self.trans_tz_var):
            v.set(0)
        self.corr_note_var.set("")
        self.display_all()

    def _reset_correction(self):
        if self.data is None: return
        self.correction = np.eye(4)
        push_correction(self.corr_config, self.correction, "reset to identity")
        save_corrections(self.corr_json_path, self.corr_config)
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.world_min, self.world_max)
        self._setup_sliders()
        self._update_corr_info()
        self.display_all()

    def _load_version(self, idx):
        hist = self.corr_config["correction_history"]
        if 0 <= idx < len(hist):
            self.corr_config["current_index"] = idx
            self.correction = np.array(hist[idx]["matrix"])
            save_corrections(self.corr_json_path, self.corr_config)
            self._recompute()
            self.cursor_world = np.clip(self.cursor_world, self.world_min, self.world_max)
            self._setup_sliders()
            self._update_corr_info()
            self.display_all()

    def _undo(self):
        if self.data is None: return
        idx = self.corr_config.get("current_index", 0)
        if idx > 0: self._load_version(idx - 1)
        else: self.status_var.set("Already at oldest version.")

    def _redo(self):
        if self.data is None: return
        idx = self.corr_config.get("current_index", 0)
        n = len(self.corr_config.get("correction_history", []))
        if idx < n - 1: self._load_version(idx + 1)
        else: self.status_var.set("Already at newest version.")

    def _update_corr_info(self):
        if self.corr_config is None: return
        idx = self.corr_config.get("current_index", 0)
        n = len(self.corr_config["correction_history"])
        entry = self.corr_config["correction_history"][idx]
        is_id = np.allclose(self.correction, np.eye(4))
        if is_id:
            self.corr_info_var.set("Correction: identity")
        else:
            det = np.linalg.det(self.correction[:3, :3])
            t = self.correction[:3, 3]
            self.corr_info_var.set(
                f"Correction: det={det:.6f}  T=[{t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}] mm")
        self.corr_ver_var.set(
            f"Version {idx+1}/{n}  |  {entry.get('timestamp','')}  |  {entry.get('note','')}")

    def _show_history(self):
        if not self.corr_config: messagebox.showinfo("Info", "No history."); return
        win = tk.Toplevel(self.root)
        win.title("Correction History"); win.geometry("850x550")
        frame = ttk.Frame(win); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set, font=("Courier", 10))
        txt.pack(fill=tk.BOTH, expand=True); sb.config(command=txt.yview)

        cur = self.corr_config.get("current_index", 0)
        for i, e in enumerate(self.corr_config["correction_history"]):
            mark = "  << CURRENT" if i == cur else ""
            txt.insert(tk.END, f"--- Version {i+1}{mark} ---\n")
            txt.insert(tk.END, f"  Time: {e.get('timestamp','')}\n")
            txt.insert(tk.END, f"  Note: {e.get('note','')}\n")
            for row in np.array(e["matrix"]):
                txt.insert(tk.END,
                    f"    [{row[0]:10.6f} {row[1]:10.6f} {row[2]:10.6f} {row[3]:10.6f}]\n")
            txt.insert(tk.END, "\n")

        jf = ttk.Frame(win); jf.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(jf, text="Jump to version:").pack(side=tk.LEFT, padx=3)
        jv = tk.IntVar(value=cur + 1)
        ttk.Entry(jf, textvariable=jv, width=5).pack(side=tk.LEFT, padx=3)
        def jump():
            t = jv.get() - 1
            nh = len(self.corr_config["correction_history"])
            if 0 <= t < nh:
                self._load_version(t); win.destroy()
            else: messagebox.showerror("Error", f"1-{nh}")
        ttk.Button(jf, text="Jump", command=jump).pack(side=tk.LEFT, padx=3)
        txt.config(state=tk.DISABLED)

    # ---------------------------------------------------------------- Header
    def _show_header(self):
        if self.img is None: return
        win = tk.Toplevel(self.root); win.title("Header"); win.geometry("900x700")
        frame = ttk.Frame(win); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set)
        txt.pack(fill=tk.BOTH, expand=True); sb.config(command=txt.yview)
        txt.insert(tk.END, "=== NATIVE AFFINE ===\n")
        txt.insert(tk.END, f"{self.native_affine}\n\n")
        txt.insert(tk.END, "=== CORRECTION ===\n")
        txt.insert(tk.END, f"{self.correction}\n\n")
        txt.insert(tk.END, "=== CORRECTED AFFINE ===\n")
        txt.insert(tk.END, f"{self.corrected_affine}\n\n")
        txt.insert(tk.END, f"Voxel sizes: {self.voxel_sizes}\n")
        txt.insert(tk.END, f"Dims: {self.dim_sizes}\n")
        txt.insert(tk.END, f"Full world bbox: {self.full_world_min} to {self.full_world_max}\n")
        txt.insert(tk.END, f"Display bbox: {self.world_min} to {self.world_max}\n")
        if self.crop_bounds:
            txt.insert(tk.END, f"Crop bounds: {self.crop_bounds}\n")
        txt.insert(tk.END, "\n")
        h = self.img.header
        if hasattr(h, "general_info"):
            txt.insert(tk.END, "=== GENERAL INFO ===\n")
            for k, v in sorted(h.general_info.items()):
                txt.insert(tk.END, f"  {k}: {v}\n")
        txt.insert(tk.END, "\n=== FULL HEADER ===\n")
        txt.insert(tk.END, pprint.pformat(h.__dict__))
        txt.config(state=tk.DISABLED)


# ====================================================================
# Main
# ====================================================================
if __name__ == "__main__":
    dp = sys.argv[1] if len(sys.argv) > 1 else None
    root = tk.Tk()
    app = TriplanarMRIViewer(root, dp)

    cf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "mri_viewer_config.json")
    cfg = {}
    if os.path.exists(cf):
        try:
            with open(cf) as f: cfg = json.load(f)
            s = cfg.get("default_path")
            if dp is None and s:
                app.default_path = s; app.file_path_var.set(s); dp = s
            if "ebz_world" in cfg:
                ew = cfg["ebz_world"]
                app.ebz_ml_var.set(ew[0])
                app.ebz_ap_var.set(ew[1])
                app.ebz_dv_var.set(ew[2])
        except Exception as e: print(f"Config error: {e}")

    if dp and os.path.exists(dp):
        app.load_and_visualize()
        if "ebz_world" in cfg:
            app._set_ebz_manual()

    root.mainloop()
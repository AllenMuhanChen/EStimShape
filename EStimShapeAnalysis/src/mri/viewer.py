"""
Tri-planar PAR/REC MRI Viewer — main UI class.

Delegates to:
    volume.py      — PAR/REC loading, reslicing
    correction.py  — correction matrix persistence, transforms
    chamber.py     — chamber geometry, overlay drawing
    penetrations.py — DB-backed penetration management
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import os, json, pprint
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.mri.volume import load_volume, compute_world_bbox, reslice_view
from src.mri.correction import (
    rot_x, rot_y, rot_z, xlate,
    load_corrections, save_corrections, push_correction,
    load_crop_bounds, save_crop_bounds,
)
from src.mri.chamber import fit_chamber, draw_chamber_overlay
from src.mri.penetrations import PenetrationStore, PenetrationListWindow, COLORS


class TriplanarMRIViewer:
    """
    Coordinate convention (RAS+):  +X = Right, +Y = Anterior, +Z = Superior
    Lab labels:  ML = world X,  AP = world Y,  DV = world Z

    Display:
        Sagittal : fix X, show Y(horiz) x Z(vert), S at top
        Coronal  : fix Y, show X(horiz) x Z(vert), S at top
        Axial    : fix Z, show X(horiz) x Y(vert), A at top
    """

    VIEW_NAMES = ["Sagittal", "Coronal", "Axial"]
    SLICE_CFG = [(0, 1, 2), (1, 0, 2), (2, 0, 1)]
    WORLD_LABELS = ["ML (R/L)", "AP (A/P)", "DV (S/I)"]

    def __init__(self, root, default_path=None):
        self.root = root
        self.root.title("PAR/REC Tri-Planar MRI Viewer")
        self.root.geometry("1450x960")
        self.root.resizable(True, True)

        # Volume state
        self.img = None
        self.data = None
        self.native_affine = None
        self.correction = np.eye(4)
        self.corrected_affine = None
        self.inv_corrected = None
        self.voxel_sizes = None
        self.default_path = default_path
        self.output_voxel_size = 0.75

        # Correction persistence
        self.corr_config = None
        self.corr_json_path = None

        # Volume dims
        self.dim_sizes = [0, 0, 0]
        self.has_dynamics = False
        self.dynamics = 1
        self.current_dynamic = 0

        # Bounding boxes
        self.full_world_min = np.zeros(3)
        self.full_world_max = np.zeros(3)
        self.world_min = np.zeros(3)
        self.world_max = np.zeros(3)
        self.world_center = np.zeros(3)
        self.view_display_bounds = [(0, 1, 0, 1)] * 3
        self.grid_sizes = [(2, 2)] * 3

        # Crosshair (corrected world mm)
        self.cursor_world = np.zeros(3)

        # EBZ
        self.ebz_set = False
        self.ebz_world = np.zeros(3)
        self.ebz_pick_armed = False

        # Crop
        self.crop_bounds = {}
        self.crop_mode = False
        self._crop_rect = None
        self._crop_start = None
        self._crop_view = None

        # Zoom: per-view viewport in display (EBZ-relative) coords {vi: (h_lo,h_hi,v_lo,v_hi)}
        # Reslicing always uses full crop extent; zoom only restricts the visible window via ax limits.
        self.zoom_bounds = {}

        # Interpolation order for reslicing (0=nearest, 1=linear, 3=cubic)
        self.interp_order = 3

        # Chamber state (dict passed to chamber.draw_chamber_overlay)
        self.chamber_state = {
            'loaded': False, 'screws_ebz': None,
            'center': None, 'origin': None, 'x': None, 'y': None, 'normal': None,
            'radius': 7.0, 'cor_offset': 2.54,
        }
        self.chamber_show = True
        self._chamber_params = {
            'ref_screw_idx': 4, 'is_fit_circle': True,
            'center_of_rotation_offset': 2.54, 'chamber_depth': 12.0,
        }

        # Penetrations (DB-backed)
        self.pen_store = PenetrationStore()
        self.pen_show = True

        self._chamber_path = None  # set by _load_chamber_from_path; persisted in config

        self._setup_ui()

    # ================================================================ UI
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

        # Collapsible panels
        self._panels_frame = ttk.Frame(main)
        self._panels_frame.pack(fill=tk.X)
        self._panels_visible = True
        self._toggle_panels_btn = ttk.Button(main, text="▲ Hide Controls",
                                              command=self._toggle_panels)
        self._toggle_panels_btn.pack(fill=tk.X, padx=5, pady=1)

        self._build_ebz_panel(self._panels_frame)
        self._build_correction_panel(self._panels_frame)
        self._build_crop_panel(self._panels_frame)
        self._build_chamber_panel(self._panels_frame)

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
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

        # Sliders
        self._build_sliders(main)

    # ---- Panel builders ----
    def _build_ebz_panel(self, parent):
        ebz = ttk.LabelFrame(parent, text="EBZ (External Brain Zero)")
        ebz.pack(fill=tk.X, padx=5, pady=2)
        for i, (lbl, vn) in enumerate([("AP mm:", "ebz_ap"), ("DV mm:", "ebz_dv"), ("ML mm:", "ebz_ml")]):
            ttk.Label(ebz, text=lbl).grid(row=0, column=2*i, padx=3, pady=2)
            v = tk.DoubleVar(value=0.0); setattr(self, vn + "_var", v)
            ttk.Entry(ebz, textvariable=v, width=10).grid(row=0, column=2*i+1, padx=3)
        self.btn_set_ebz = ttk.Button(ebz, text="Set EBZ (manual)", command=self._set_ebz_manual, state="disabled")
        self.btn_set_ebz.grid(row=0, column=6, padx=3)
        self.btn_ebz_xhair = ttk.Button(ebz, text="Set EBZ to crosshair", command=self._set_ebz_to_crosshair, state="disabled")
        self.btn_ebz_xhair.grid(row=0, column=7, padx=3)
        self.btn_reset_ebz = ttk.Button(ebz, text="Reset EBZ", command=self._reset_ebz, state="disabled")
        self.btn_reset_ebz.grid(row=0, column=8, padx=3)
        self.btn_ebz_pick = ttk.Button(ebz, text="Pick EBZ (right-click)", command=self._toggle_ebz_pick, state="disabled")
        self.btn_ebz_pick.grid(row=0, column=9, padx=3)
        self.cursor_info_var = tk.StringVar(value="Crosshair: ---")
        ttk.Label(ebz, textvariable=self.cursor_info_var).grid(row=1, column=0, columnspan=10, sticky="w", padx=5)
        self.ebz_pick_label_var = tk.StringVar(value="")
        ttk.Label(ebz, textvariable=self.ebz_pick_label_var, foreground="red").grid(row=2, column=0, columnspan=10, sticky="w", padx=5)

    def _build_correction_panel(self, parent):
        corr = ttk.LabelFrame(parent, text="Correction Matrix")
        corr.pack(fill=tk.X, padx=5, pady=2)
        r_row = ttk.Frame(corr); r_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r_row, text="Rotate (deg):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML/roll)", "x"), ("Y(AP/pitch)", "y"), ("Z(DV/yaw)", "z")]:
            ttk.Label(r_row, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"rot_{an}_var", v)
            ttk.Entry(r_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)
        t_row = ttk.Frame(corr); t_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(t_row, text="Translate (mm):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML)", "tx"), ("Y(AP)", "ty"), ("Z(DV)", "tz")]:
            ttk.Label(t_row, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"trans_{an}_var", v)
            ttk.Entry(t_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)
        b_row = ttk.Frame(corr); b_row.pack(fill=tk.X, padx=3, pady=2)
        self.btn_apply = ttk.Button(b_row, text="Apply", command=self._apply_correction, state="disabled")
        self.btn_apply.pack(side=tk.LEFT, padx=3)
        self.btn_reset_corr = ttk.Button(b_row, text="Reset to Identity", command=self._reset_correction, state="disabled")
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
        ttk.Entry(note_row, textvariable=self.corr_note_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

    def _build_crop_panel(self, parent):
        crop = ttk.LabelFrame(parent, text="View Cropping & Display")
        crop.pack(fill=tk.X, padx=5, pady=2)

        row1 = ttk.Frame(crop); row1.pack(fill=tk.X, padx=3, pady=2)
        self.btn_crop = ttk.Button(row1, text="Crop (drag rect)", command=self._toggle_crop_mode, state="disabled")
        self.btn_crop.pack(side=tk.LEFT, padx=3)
        self.btn_reset_crop = ttk.Button(row1, text="Reset Crops", command=self._reset_crop, state="disabled")
        self.btn_reset_crop.pack(side=tk.LEFT, padx=3)
        self.btn_reset_zoom = ttk.Button(row1, text="Reset Zoom", command=self._reset_zoom, state="disabled")
        self.btn_reset_zoom.pack(side=tk.LEFT, padx=3)
        ttk.Label(row1, text="  Scroll to zoom, double-click to reset view", foreground="#555555").pack(side=tk.LEFT, padx=6)
        self.crop_status_var = tk.StringVar(value="")
        ttk.Label(row1, textvariable=self.crop_status_var, foreground="blue").pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(crop); row2.pack(fill=tk.X, padx=3, pady=(0, 4))
        ttk.Label(row2, text="Interpolation:").pack(side=tk.LEFT, padx=3)
        self.interp_var = tk.StringVar(value="Cubic (order 3)")
        interp_cb = ttk.Combobox(row2, textvariable=self.interp_var, state="readonly", width=18,
                                  values=["Nearest (order 0)", "Linear (order 1)", "Cubic (order 3)"])
        interp_cb.pack(side=tk.LEFT, padx=3)
        interp_cb.bind("<<ComboboxSelected>>", self._on_interp_change)

    def _build_chamber_panel(self, parent):
        ch = ttk.LabelFrame(parent, text="Chamber & Penetrations")
        ch.pack(fill=tk.X, padx=5, pady=2)
        r1 = ttk.Frame(ch); r1.pack(fill=tk.X, padx=3, pady=2)
        self.btn_load_chamber = ttk.Button(r1, text="Load monkey_specific.py...", command=self._load_chamber_file)
        self.btn_load_chamber.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_chamber = ttk.Button(r1, text="Hide Chamber", command=self._toggle_chamber, state="disabled")
        self.btn_toggle_chamber.pack(side=tk.LEFT, padx=3)
        self.btn_connect_db = ttk.Button(r1, text="Connect DB", command=self._connect_db)
        self.btn_connect_db.pack(side=tk.LEFT, padx=3)
        self.btn_pen_list = ttk.Button(r1, text="Penetration List", command=self._show_pen_list, state="disabled")
        self.btn_pen_list.pack(side=tk.LEFT, padx=3)
        self.chamber_info_var = tk.StringVar(value="No chamber loaded")
        ttk.Label(ch, textvariable=self.chamber_info_var).pack(anchor="w", padx=5, pady=1)

        pen_row = ttk.Frame(ch); pen_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(pen_row, text="Az(°):").pack(side=tk.LEFT, padx=2)
        self.pen_az_var = tk.DoubleVar(value=0.0)
        ttk.Entry(pen_row, textvariable=self.pen_az_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="El(°):").pack(side=tk.LEFT, padx=2)
        self.pen_el_var = tk.DoubleVar(value=0.0)
        ttk.Entry(pen_row, textvariable=self.pen_el_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Dist(mm):").pack(side=tk.LEFT, padx=2)
        self.pen_dist_var = tk.DoubleVar(value=35.0)
        ttk.Entry(pen_row, textvariable=self.pen_dist_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Label:").pack(side=tk.LEFT, padx=2)
        self.pen_label_var = tk.StringVar(value="")
        ttk.Entry(pen_row, textvariable=self.pen_label_var, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Notes:").pack(side=tk.LEFT, padx=2)
        self.pen_notes_var = tk.StringVar(value="")
        ttk.Entry(pen_row, textvariable=self.pen_notes_var, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        br = ttk.Frame(ch); br.pack(fill=tk.X, padx=3, pady=2)
        self.btn_add_pen = ttk.Button(br, text="Add Penetration", command=self._add_penetration, state="disabled")
        self.btn_add_pen.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_pens = ttk.Button(br, text="Hide Penetrations", command=self._toggle_pens, state="disabled")
        self.btn_toggle_pens.pack(side=tk.LEFT, padx=3)

    def _build_sliders(self, parent):
        sf = ttk.Frame(parent); sf.pack(fill=tk.X, padx=5, pady=2)
        self.slice_vars, self.slice_scales, self.slice_lbls, self.ebz_goto_btns = [], [], [], []
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
            self.slice_vars.append(v); self.slice_scales.append(sc)
            self.slice_lbls.append(lb); self.ebz_goto_btns.append(btn)
        sf.columnconfigure(1, weight=1)

        self.dyn_frame = ttk.Frame(sf)
        self.dyn_frame.grid(row=3, column=0, columnspan=4, sticky="we")
        ttk.Label(self.dyn_frame, text="Dynamic:").grid(row=0, column=0, sticky="w", padx=3)
        self.dyn_var = tk.IntVar(value=0)
        self.dyn_scale = ttk.Scale(self.dyn_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                   variable=self.dyn_var, command=lambda *a: self._on_dyn_slider())
        self.dyn_scale.grid(row=0, column=1, sticky="we", padx=3)
        self.dyn_lbl = ttk.Label(self.dyn_frame, text="0/0", width=14)
        self.dyn_lbl.grid(row=0, column=2, padx=3)
        self.dyn_frame.columnconfigure(1, weight=1)
        self.dyn_frame.grid_remove()

    def _toggle_panels(self):
        if self._panels_visible:
            self._panels_frame.pack_forget()
            self._toggle_panels_btn.config(text="▼ Show Controls")
            self._panels_visible = False
        else:
            self._panels_frame.pack(fill=tk.X, before=self._toggle_panels_btn)
            self._toggle_panels_btn.config(text="▲ Hide Controls")
            self._panels_visible = True

    # ================================================================ File I/O
    def _browse(self):
        d = os.path.dirname(self.default_path) if self.default_path and not os.path.isdir(self.default_path) else self.default_path
        fn = filedialog.askopenfilename(title="Select PAR File",
                                        filetypes=[("PAR", "*.PAR *.par"), ("All", "*.*")],
                                        initialdir=d)
        if fn:
            self.file_path_var.set(fn)

    def _check_rec(self, par):
        b = os.path.splitext(par)[0]
        return os.path.exists(b + ".REC") or os.path.exists(b + ".rec")

    def _save_defaults(self):
        p = self.file_path_var.get().strip()
        if not p:
            messagebox.showerror("Error", "No path"); return
        cp = os.path.join(os.getcwd(), "mri_viewer_config.json")
        try:
            c = {"default_path": p}
            if self.ebz_set:
                c["ebz_world"] = self.ebz_world.tolist()
            if self._chamber_path and os.path.exists(self._chamber_path):
                c["monkey_specific_path"] = self._chamber_path
            with open(cp, "w") as f:
                json.dump(c, f, indent=2)
            self.default_path = p
            # Show exactly what got saved so it's easy to verify
            saved_keys = [k for k in c if k != "default_path"]
            extra = f"  +  {', '.join(saved_keys)}" if saved_keys else ""
            messagebox.showinfo("Saved", f"Defaults saved{extra}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _corr_json_for(self, par):
        return os.path.splitext(par)[0] + "_corrections.json"

    # ================================================================ Loading
    def load_and_visualize(self):
        par = self.file_path_var.get().strip()
        if not par:
            messagebox.showerror("Error", "Select a PAR file."); return
        if not os.path.exists(par):
            messagebox.showerror("Error", f"{par} not found."); return
        if not par.upper().endswith(".PAR"):
            if not messagebox.askyesno("Warning", "Not a .PAR extension. Continue?"):
                return
        if not self._check_rec(par):
            messagebox.showerror("Error", ".REC not found."); return

        try:
            self.status_var.set(f"Loading {par}..."); self.root.update()
            self.data, self.native_affine, self.voxel_sizes, self.img = load_volume(par)

            if self.data.ndim == 4:
                self.has_dynamics = True; self.dynamics = self.data.shape[3]
            else:
                self.has_dynamics = False; self.dynamics = 1
            self.dim_sizes = list(self.data.shape[:3])

            self.corr_json_path = self._corr_json_for(par)
            self.correction, self.corr_config = load_corrections(self.corr_json_path)
            self.crop_bounds = load_crop_bounds(self.corr_config)
            self._recompute()
            self.cursor_world = self.world_center.copy()
            self._setup_sliders()

            if self.has_dynamics:
                self.dyn_scale.configure(from_=0, to=self.dynamics - 1)
                self.dyn_var.set(0); self.dyn_frame.grid()
            else:
                self.dyn_frame.grid_remove()

            for b in (self.btn_set_ebz, self.btn_ebz_xhair, self.btn_apply,
                      self.btn_reset_corr, self.btn_undo, self.btn_redo,
                      self.btn_ebz_pick, self.btn_crop, self.btn_reset_crop,
                      self.btn_reset_zoom):
                b.config(state="normal")
            for b in self.ebz_goto_btns:
                b.config(state="normal")

            self._update_corr_info()
            self.display_all()
            self.status_var.set(
                f"Loaded {os.path.basename(par)}  shape={self.dim_sizes}  "
                f"voxel={self.voxel_sizes[0]:.3f}×{self.voxel_sizes[1]:.3f}×{self.voxel_sizes[2]:.3f} mm")
        except Exception as e:
            self.status_var.set("Error"); messagebox.showerror("Error", str(e))
            import traceback; traceback.print_exc()

    # ================================================================ Recompute
    def _recompute(self):
        self.corrected_affine = self.correction @ self.native_affine
        self.inv_corrected = np.linalg.inv(self.corrected_affine)

        self.full_world_min, self.full_world_max = compute_world_bbox(self.corrected_affine, self.dim_sizes)
        self.world_center = (self.full_world_min + self.full_world_max) / 2.0
        self.world_min = self.full_world_min.copy()
        self.world_max = self.full_world_max.copy()

        vs = self.output_voxel_size
        self.view_display_bounds = []
        self.grid_sizes = []
        for vi in range(3):
            _, h_wax, v_wax = self.SLICE_CFG[vi]
            h_lo, h_hi = self.full_world_min[h_wax], self.full_world_max[h_wax]
            v_lo, v_hi = self.full_world_min[v_wax], self.full_world_max[v_wax]
            if vi in self.crop_bounds:
                ch_lo, ch_hi, cv_lo, cv_hi = self.crop_bounds[vi]
                h_lo = max(h_lo, ch_lo); h_hi = min(h_hi, ch_hi)
                v_lo = max(v_lo, cv_lo); v_hi = min(v_hi, cv_hi)
            self.view_display_bounds.append((h_lo, h_hi, v_lo, v_hi))
            n_h = max(2, int(np.ceil((h_hi - h_lo) / vs)))
            n_v = max(2, int(np.ceil((v_hi - v_lo) / vs)))
            self.grid_sizes.append((n_h, n_v))

    def _setup_sliders(self):
        for i in range(3):
            fix_wax = self.SLICE_CFG[i][0]
            lo, hi = self.full_world_min[fix_wax], self.full_world_max[fix_wax]
            self.slice_scales[i].configure(from_=lo, to=hi)
            self.slice_vars[i].set(self.world_center[fix_wax])

    # ================================================================ Coordinate transforms
    def vox_to_world(self, vox):
        return (self.corrected_affine @ np.array([*vox[:3], 1.0]))[:3]

    def world_to_vox(self, w):
        return (self.inv_corrected @ np.array([*w[:3], 1.0]))[:3]

    # ================================================================ Display
    def display_all(self):
        if self.data is None:
            return
        for vi in range(3):
            ax = self.axes[vi]
            ax.clear()

            fix_wax, h_wax, v_wax = self.SLICE_CFG[vi]
            img2d, h_coords, v_coords = reslice_view(
                self.data, self.inv_corrected, self.view_display_bounds[vi],
                self.grid_sizes[vi], self.SLICE_CFG[vi], self.cursor_world,
                self.current_dynamic, self.has_dynamics,
                interp_order=self.interp_order)

            # When EBZ is set, show coords relative to EBZ so the star is at (0,0)
            disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
            h_off = disp_off[h_wax]
            v_off = disp_off[v_wax]

            extent = [h_coords[0] - h_off, h_coords[-1] - h_off,
                      v_coords[-1] - v_off, v_coords[0] - v_off]
            im = ax.imshow(img2d, cmap='gray', aspect='equal', origin='upper',
                           interpolation='nearest', extent=extent)
            try:
                nz = img2d[img2d > 0]
                if len(nz) > 100:
                    im.set_clim(*np.percentile(nz, [1, 99]))
            except:
                pass

            # Crosshair
            ax.axvline(self.cursor_world[h_wax] - h_off, color='lime', lw=0.7, alpha=0.6)
            ax.axhline(self.cursor_world[v_wax] - v_off, color='lime', lw=0.7, alpha=0.6)

            # EBZ — always at (0,0) in EBZ-relative display space
            if self.ebz_set:
                ax.axvline(0, color='red', lw=0.5, alpha=0.4, ls='--')
                ax.axhline(0, color='red', lw=0.5, alpha=0.4, ls='--')
                ax.plot(0, 0, 'r*', markersize=8)

            # Chamber + penetrations
            draw_chamber_overlay(
                ax, vi, self.SLICE_CFG[vi], self.chamber_state,
                self.ebz_world if self.ebz_set else np.zeros(3),
                self.pen_store.penetrations if self.pen_store.connected else [],
                show_chamber=self.chamber_show,
                show_penetrations=self.pen_show,
                display_offset=disp_off)

            # Title
            wval = self.cursor_world[fix_wax]
            if self.ebz_set:
                rel = wval - self.ebz_world[fix_wax]
                title = f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[fix_wax]}={wval:.2f} mm  ({rel:+.2f} from EBZ)"
            else:
                title = f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[fix_wax]}={wval:.2f} mm"
            ax.set_title(title, fontsize=10)
            ax.set_xlabel(self.WORLD_LABELS[h_wax], fontsize=9)
            ax.set_ylabel(self.WORLD_LABELS[v_wax], fontsize=9)
            ax.tick_params(labelsize=7)
            ax._vi = vi

            # Apply zoom — restricts the visible window WITHOUT changing what was resliced
            if vi in self.zoom_bounds:
                zh_lo, zh_hi, zv_lo, zv_hi = self.zoom_bounds[vi]
                ax.set_xlim(zh_lo, zh_hi)
                # origin='upper' means y-axis is inverted; pass (hi, lo) to keep that orientation
                ax.set_ylim(zv_hi, zv_lo)

        self.fig.canvas.draw_idle()
        self._update_info()
        self._sync_sliders()

    def _update_info(self):
        if self.data is None:
            return
        w = self.cursor_world
        vox = self.world_to_vox(w)
        txt = f"Crosshair: ML={w[0]:.2f}, AP={w[1]:.2f}, DV={w[2]:.2f} mm   voxel=[{vox[0]:.1f}, {vox[1]:.1f}, {vox[2]:.1f}]"
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
                self.slice_lbls[i].config(text=f"{val:.2f} mm ({rel:+.2f} EBZ)")
            else:
                self.slice_lbls[i].config(text=f"{val:.2f} mm")

    # ================================================================ Mouse events
    def _on_slider(self, view_idx):
        if self.data is None:
            return
        fix_wax = self.SLICE_CFG[view_idx][0]
        new_val = self.slice_vars[view_idx].get()
        if abs(new_val - self.cursor_world[fix_wax]) > 0.01:
            self.cursor_world[fix_wax] = new_val
            self.display_all()

    def _goto_ebz_zero(self, view_idx):
        if self.data is None or not self.ebz_set:
            self.status_var.set("Set EBZ first."); return
        self.cursor_world[self.SLICE_CFG[view_idx][0]] = self.ebz_world[self.SLICE_CFG[view_idx][0]]
        self.display_all()

    def _on_dyn_slider(self):
        self.current_dynamic = self.dyn_var.get()
        self.dyn_lbl.config(text=f"{self.current_dynamic}/{self.dynamics-1}")
        self.display_all()

    def _on_click(self, event):
        if self.data is None or event.inaxes is None:
            return
        ax = event.inaxes
        if not hasattr(ax, '_vi'):
            return
        vi = ax._vi
        _, h_wax, v_wax = self.SLICE_CFG[vi]
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        # Double-click resets zoom on this view
        if event.dblclick and event.button == 1 and not self.crop_mode:
            self._reset_zoom(vi)
            return

        # Display coords are EBZ-relative; convert back to absolute world coords
        disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
        x_world = x + disp_off[h_wax]
        y_world = y + disp_off[v_wax]

        if self.crop_mode and event.button == 1:
            from matplotlib.patches import Rectangle
            self._crop_start = (x, y)
            self._crop_view = vi
            self._crop_rect = Rectangle((x, y), 0, 0, linewidth=2,
                                         edgecolor='cyan', facecolor='cyan', alpha=0.15)
            ax.add_patch(self._crop_rect)
            self.fig.canvas.draw_idle()
            return

        if self.ebz_pick_armed and event.button == 3:
            self.cursor_world[h_wax] = np.clip(x_world, self.world_min[h_wax], self.world_max[h_wax])
            self.cursor_world[v_wax] = np.clip(y_world, self.world_min[v_wax], self.world_max[v_wax])
            self._set_ebz_to_crosshair()
            self._disarm_ebz_pick()
            return

        if event.button == 1:
            self.cursor_world[h_wax] = np.clip(x_world, self.world_min[h_wax], self.world_max[h_wax])
            self.cursor_world[v_wax] = np.clip(y_world, self.world_min[v_wax], self.world_max[v_wax])
            self.display_all()

    def _on_release(self, event):
        if not self.crop_mode or self._crop_start is None:
            return
        if event.inaxes is None:
            return
        ax = event.inaxes
        if not hasattr(ax, '_vi') or ax._vi != self._crop_view:
            return
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        x0, y0 = self._crop_start
        h_lo, h_hi = min(x0, x), max(x0, x)
        v_lo, v_hi = min(y0, y), max(y0, y)
        if (h_hi - h_lo) < 5 or (v_hi - v_lo) < 5:
            self.crop_status_var.set("Too small, ignored.")
            self._crop_start = None; self._crop_rect = None; self._crop_view = None
            self.display_all()
            return

        vi = self._crop_view
        # Convert display (EBZ-relative) coords back to absolute world for storage
        _, h_wax_c, v_wax_c = self.SLICE_CFG[vi]
        disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
        h_lo += disp_off[h_wax_c]; h_hi += disp_off[h_wax_c]
        v_lo += disp_off[v_wax_c]; v_hi += disp_off[v_wax_c]
        old_crops = getattr(self, '_saved_crop_for_cancel', {})
        self.crop_bounds = {k: v for k, v in old_crops.items() if k != vi}
        self.crop_bounds[vi] = (h_lo, h_hi, v_lo, v_hi)
        if hasattr(self, '_saved_crop_for_cancel'):
            delattr(self, '_saved_crop_for_cancel')
        self.crop_mode = False
        self._crop_start = None; self._crop_rect = None; self._crop_view = None
        self.btn_crop.config(text="Crop Views (drag rectangle)")

        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
        self._setup_sliders()
        save_crop_bounds(self.corr_config, self.crop_bounds)
        save_corrections(self.corr_json_path, self.corr_config)
        self.display_all()
        self.crop_status_var.set(f"Cropped {self.VIEW_NAMES[vi]}")

    def _on_motion(self, event):
        if self.data is None or event.inaxes is None:
            return
        if self.crop_mode and self._crop_start is not None and self._crop_rect is not None:
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                x0, y0 = self._crop_start
                self._crop_rect.set_xy((min(x0, x), min(y0, y)))
                self._crop_rect.set_width(abs(x - x0))
                self._crop_rect.set_height(abs(y - y0))
                self.fig.canvas.draw_idle()
            return
        ax = event.inaxes
        if hasattr(ax, '_vi'):
            vi = ax._vi
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                _, h_wax, v_wax = self.SLICE_CFG[vi]
                if self.ebz_set:
                    self.status_var.set(
                        f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[h_wax]}={x:+.2f}  "
                        f"{self.WORLD_LABELS[v_wax]}={y:+.2f} mm  (EBZ-relative)")
                else:
                    self.status_var.set(
                        f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[h_wax]}={x:.2f}  "
                        f"{self.WORLD_LABELS[v_wax]}={y:.2f} mm")

    # ================================================================ EBZ
    def _set_ebz_to_crosshair(self):
        if self.data is None:
            return
        self.ebz_world = self.cursor_world.copy()
        self.ebz_ap_var.set(round(self.ebz_world[1], 3))
        self.ebz_dv_var.set(round(self.ebz_world[2], 3))
        self.ebz_ml_var.set(round(self.ebz_world[0], 3))
        self.ebz_set = True
        self.btn_reset_ebz.config(state="normal")
        self.display_all()

    def _set_ebz_manual(self):
        if self.data is None:
            return
        try:
            self.ebz_world = np.array([self.ebz_ml_var.get(), self.ebz_ap_var.get(), self.ebz_dv_var.get()])
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
        if self.ebz_pick_armed:
            self._disarm_ebz_pick()
        else:
            self.ebz_pick_armed = True
            self.ebz_pick_label_var.set("EBZ PICK ACTIVE — right-click to set, or click button to cancel")
            self.btn_ebz_pick.config(text="Cancel EBZ Pick")
            if self.crop_mode:
                self._exit_crop_mode()

    def _disarm_ebz_pick(self):
        self.ebz_pick_armed = False
        self.ebz_pick_label_var.set("")
        self.btn_ebz_pick.config(text="Pick EBZ (right-click)")

    # ================================================================ Cropping
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

        if (new_h_hi - new_h_lo) >= full_h_span * 1.01 and            abs(new_v_hi - new_v_lo) >= full_v_span * 1.01:
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

    # ================================================================ Interpolation
    def _on_interp_change(self, event=None):
        order_map = {"Nearest (order 0)": 0, "Linear (order 1)": 1, "Cubic (order 3)": 3}
        self.interp_order = order_map.get(self.interp_var.get(), 3)
        if self.data is not None:
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
    def _load_chamber_file(self):
        fn = filedialog.askopenfilename(title="Select monkey_specific.py",
                                        filetypes=[("Python", "*.py"), ("All", "*.*")])
        if not fn:
            return
        self._load_chamber_from_path(fn)

    def _load_chamber_from_path(self, fn):
        """Load a monkey_specific.py by absolute path. Safe to call before a volume is loaded."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("monkey_specific", fn)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            screws_ebz = mod.get_screw_hole_coords()
            self._chamber_params['ref_screw_idx'] = mod.get_reference_screw_idx()
            self._chamber_params['center_of_rotation_offset'] = mod.get_center_of_rotation_offset()
            self._chamber_params['is_fit_circle'] = mod.get_is_fit_circle()
            if hasattr(mod, 'get_chamber_depth'):
                self._chamber_params['chamber_depth'] = mod.get_chamber_depth()

            self.chamber_state['screws_ebz'] = screws_ebz
            self.chamber_state['cor_offset'] = self._chamber_params['center_of_rotation_offset']
            self._chamber_path = fn  # remembered so _save_defaults can persist it
            self._refit_chamber()

            self.btn_toggle_chamber.config(state="normal")
            if self.pen_store.connected:
                self.btn_add_pen.config(state="normal")

            if hasattr(mod, 'get_electrode_target'):
                mode, coords = mod.get_electrode_target()
                if mode == 'angles':
                    self.pen_az_var.set(coords[0]); self.pen_el_var.set(coords[1]); self.pen_dist_var.set(coords[2])

            if self.data is not None:
                self.display_all()
        except Exception as e:
            messagebox.showerror("Error loading chamber file", str(e))
            import traceback; traceback.print_exc()

    def _refit_chamber(self):
        screws_ebz = self.chamber_state['screws_ebz']
        if screws_ebz is None:
            return
        ebz = self.ebz_world if self.ebz_set else np.zeros(3)
        screws_world = screws_ebz + ebz

        center, origin, x, y, normal = fit_chamber(
            screws_world,
            self._chamber_params['ref_screw_idx'],
            self._chamber_params['center_of_rotation_offset'],
            self._chamber_params['is_fit_circle'])

        self.chamber_state.update({
            'loaded': True, 'center': center, 'origin': origin,
            'x': x, 'y': y, 'normal': normal,
        })
        self.chamber_info_var.set(
            f"Chamber: {len(screws_ebz)} screwholes, origin="
            f"[{origin[0]:.1f}, {origin[1]:.1f}, {origin[2]:.1f}] mm")

    def _toggle_chamber(self):
        self.chamber_show = not self.chamber_show
        self.btn_toggle_chamber.config(text="Show Chamber" if not self.chamber_show else "Hide Chamber")
        self.display_all()

    # ================================================================ Penetrations (DB)
    def _connect_db(self):
        try:
            self.pen_store.connect()
            self.btn_pen_list.config(state="normal")
            self.btn_toggle_pens.config(state="normal")
            if self.chamber_state['loaded']:
                self.btn_add_pen.config(state="normal")
            n = len(self.pen_store.penetrations)
            self.status_var.set(f"DB connected. {n} penetrations loaded.")
            self.display_all()
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            import traceback; traceback.print_exc()

    def _add_penetration(self):
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return
        if not self.chamber_state['loaded']:
            messagebox.showerror("Error", "Load chamber first."); return
        az = self.pen_az_var.get()
        el = self.pen_el_var.get()
        dist = self.pen_dist_var.get()
        label = self.pen_label_var.get().strip()
        notes = self.pen_notes_var.get().strip()
        color = COLORS[len(self.pen_store.penetrations) % len(COLORS)]
        self.pen_store.add(az, el, dist, label=label, color=color, notes=notes)
        self.display_all()

    def _toggle_pens(self):
        self.pen_show = not self.pen_show
        self.btn_toggle_pens.config(text="Show Penetrations" if not self.pen_show else "Hide Penetrations")
        self.display_all()

    def _show_pen_list(self):
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return
        PenetrationListWindow(self.root, self.pen_store, on_change_callback=self.display_all)

    # ================================================================ Correction matrix
    def _apply_correction(self):
        if self.data is None:
            return
        rx, ry, rz = self.rot_x_var.get(), self.rot_y_var.get(), self.rot_z_var.get()
        tx, ty, tz = self.trans_tx_var.get(), self.trans_ty_var.get(), self.trans_tz_var.get()
        delta = xlate(tx, ty, tz) @ rot_z(rz) @ rot_y(ry) @ rot_x(rx)
        new_corr = delta @ self.correction
        note = self.corr_note_var.get().strip()
        if not note:
            parts = []
            if rx: parts.append(f"Rx={rx}");
            if ry: parts.append(f"Ry={ry}")
            if rz: parts.append(f"Rz={rz}")
            if tx: parts.append(f"Tx={tx}");
            if ty: parts.append(f"Ty={ty}")
            if tz: parts.append(f"Tz={tz}")
            note = ", ".join(parts) if parts else "no-op"
        self.correction = new_corr
        push_correction(self.corr_config, new_corr, note)
        save_corrections(self.corr_json_path, self.corr_config)
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
        self._setup_sliders(); self._update_corr_info()
        for v in (self.rot_x_var, self.rot_y_var, self.rot_z_var,
                  self.trans_tx_var, self.trans_ty_var, self.trans_tz_var):
            v.set(0)
        self.corr_note_var.set("")
        self.display_all()

    def _reset_correction(self):
        if self.data is None:
            return
        self.correction = np.eye(4)
        push_correction(self.corr_config, self.correction, "reset to identity")
        save_corrections(self.corr_json_path, self.corr_config)
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
        self._setup_sliders(); self._update_corr_info(); self.display_all()

    def _load_version(self, idx):
        hist = self.corr_config["correction_history"]
        if 0 <= idx < len(hist):
            self.corr_config["current_index"] = idx
            self.correction = np.array(hist[idx]["matrix"])
            save_corrections(self.corr_json_path, self.corr_config)
            self._recompute()
            self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
            self._setup_sliders(); self._update_corr_info(); self.display_all()

    def _undo(self):
        if self.data is None:
            return
        idx = self.corr_config.get("current_index", 0)
        if idx > 0:
            self._load_version(idx - 1)
        else:
            self.status_var.set("Already at oldest version.")

    def _redo(self):
        if self.data is None:
            return
        idx = self.corr_config.get("current_index", 0)
        if idx < len(self.corr_config.get("correction_history", [])) - 1:
            self._load_version(idx + 1)
        else:
            self.status_var.set("Already at newest version.")

    def _update_corr_info(self):
        if self.corr_config is None:
            return
        idx = self.corr_config.get("current_index", 0)
        n = len(self.corr_config["correction_history"])
        entry = self.corr_config["correction_history"][idx]
        if np.allclose(self.correction, np.eye(4)):
            self.corr_info_var.set("Correction: identity")
        else:
            det = np.linalg.det(self.correction[:3, :3])
            t = self.correction[:3, 3]
            self.corr_info_var.set(f"Correction: det={det:.6f}  T=[{t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}] mm")
        self.corr_ver_var.set(f"Version {idx+1}/{n}  |  {entry.get('timestamp','')}  |  {entry.get('note','')}")

    def _show_history(self):
        if not self.corr_config:
            return
        win = tk.Toplevel(self.root); win.title("Correction History"); win.geometry("850x550")
        frame = ttk.Frame(win); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set, font=("Courier", 10))
        txt.pack(fill=tk.BOTH, expand=True); sb.config(command=txt.yview)
        cur = self.corr_config.get("current_index", 0)
        for i, e in enumerate(self.corr_config["correction_history"]):
            mark = "  << CURRENT" if i == cur else ""
            txt.insert(tk.END, f"--- Version {i+1}{mark} ---\n")
            txt.insert(tk.END, f"  Time: {e.get('timestamp','')}\n  Note: {e.get('note','')}\n")
            for row in np.array(e["matrix"]):
                txt.insert(tk.END, f"    [{row[0]:10.6f} {row[1]:10.6f} {row[2]:10.6f} {row[3]:10.6f}]\n")
            txt.insert(tk.END, "\n")
        jf = ttk.Frame(win); jf.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(jf, text="Jump to:").pack(side=tk.LEFT, padx=3)
        jv = tk.IntVar(value=cur + 1)
        ttk.Entry(jf, textvariable=jv, width=5).pack(side=tk.LEFT, padx=3)
        def jump():
            t = jv.get() - 1
            if 0 <= t < len(self.corr_config["correction_history"]):
                self._load_version(t); win.destroy()
        ttk.Button(jf, text="Jump", command=jump).pack(side=tk.LEFT, padx=3)
        txt.config(state=tk.DISABLED)

    def _show_header(self):
        if self.img is None:
            return
        win = tk.Toplevel(self.root); win.title("Header"); win.geometry("900x700")
        frame = ttk.Frame(win); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set)
        txt.pack(fill=tk.BOTH, expand=True); sb.config(command=txt.yview)
        for label, val in [("NATIVE AFFINE", self.native_affine), ("CORRECTION", self.correction),
                           ("CORRECTED AFFINE", self.corrected_affine)]:
            txt.insert(tk.END, f"=== {label} ===\n{val}\n\n")
        txt.insert(tk.END, f"Voxel sizes: {self.voxel_sizes}\nDims: {self.dim_sizes}\n")
        txt.insert(tk.END, f"Full bbox: {self.full_world_min} to {self.full_world_max}\n")
        if self.crop_bounds:
            txt.insert(tk.END, f"Crops: {self.crop_bounds}\n")
        h = self.img.header
        if hasattr(h, "general_info"):
            txt.insert(tk.END, "\n=== GENERAL INFO ===\n")
            for k, v in sorted(h.general_info.items()):
                txt.insert(tk.END, f"  {k}: {v}\n")
        txt.insert(tk.END, f"\n=== FULL HEADER ===\n{pprint.pformat(h.__dict__)}")
        txt.config(state=tk.DISABLED)
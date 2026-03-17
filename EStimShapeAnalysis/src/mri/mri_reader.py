import numpy as np
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import FuncFormatter
from nibabel.parrec import load as load_parrec
import nibabel as nib
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pprint
import json
import sys


class TriplanarMRIViewer:
    """
    Tri-planar PAR/REC MRI viewer.

    Displays sagittal, coronal, and axial views simultaneously with
    linked crosshairs. Clicking in any view updates the other two.

    Axis mapping (determined from affine):
        Voxel axis 0 (shape[0]) -> R/L  (sagittal index)
        Voxel axis 1 (shape[1]) -> A/P  (coronal index)
        Voxel axis 2 (shape[2]) -> S/I  (axial index)
    """

    def __init__(self, root, default_path=None):
        self.root = root
        self.root.title("PAR/REC Tri-Planar MRI Viewer")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)

        # Data state
        self.img = None
        self.data = None
        self.affine = None
        self.voxel_sizes = None
        self.default_path = default_path

        # Current crosshair position in voxel coordinates [axis0, axis1, axis2]
        self.cursor_vox = [0, 0, 0]
        self.dim_labels = ['R/L', 'A/P', 'S/I']  # updated after affine analysis
        self.dim_sizes = [0, 0, 0]

        # View names and which voxel axis each view slices through
        # Sagittal: fix axis 0 (R/L), show axes 1,2 (A/P x S/I)
        # Coronal:  fix axis 1 (A/P), show axes 0,2 (R/L x S/I)
        # Axial:    fix axis 2 (S/I), show axes 0,1 (R/L x A/P)
        self.view_names = ['Sagittal', 'Coronal', 'Axial']
        self.slice_axes = [0, 1, 2]  # which axis is "into the screen"
        self.horiz_axes = [1, 0, 0]  # which axis maps to image columns
        self.vert_axes = [2, 2, 1]  # which axis maps to image rows

        # EBZ state
        self.ebz_set = False
        self.ebz_vox = [0, 0, 0]  # EBZ in voxel coordinates
        self.ebz_world = [0.0, 0.0, 0.0]  # EBZ in world (mm) coordinates

        # Slice positions in world coords per axis
        self.world_coords_per_axis = [None, None, None]

        # Dynamics
        self.current_dynamic = 0
        self.dynamics = 1
        self.has_dynamics = False

        self.setup_ui()

    # ------------------------------------------------------------------ UI
    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Top: file controls ---
        ctrl = ttk.Frame(main_frame)
        ctrl.pack(fill=tk.X, padx=5, pady=3)

        ttk.Label(ctrl, text="PAR File:").grid(row=0, column=0, sticky=tk.W, padx=3)
        self.file_path_var = tk.StringVar()
        if self.default_path:
            self.file_path_var.set(self.default_path)
        ttk.Entry(ctrl, textvariable=self.file_path_var, width=60).grid(row=0, column=1, sticky='we', padx=3)
        ttk.Button(ctrl, text="Browse…", command=self.browse_file).grid(row=0, column=2, padx=3)
        ttk.Button(ctrl, text="Load", command=self.load_and_visualize).grid(row=0, column=3, padx=3)
        ttk.Button(ctrl, text="Save Default", command=self.save_default_path).grid(row=0, column=4, padx=3)
        ctrl.columnconfigure(1, weight=1)

        # --- Status ---
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var).pack(fill=tk.X, padx=5)

        # --- EBZ controls ---
        ebz = ttk.LabelFrame(main_frame, text="EBZ (External Brain Zero)")
        ebz.pack(fill=tk.X, padx=5, pady=3)

        ttk.Label(ebz, text="AP (mm):").grid(row=0, column=0, padx=3, pady=2)
        self.ebz_ap_var = tk.DoubleVar(value=0)
        ttk.Entry(ebz, textvariable=self.ebz_ap_var, width=10).grid(row=0, column=1, padx=3)

        ttk.Label(ebz, text="DV (mm):").grid(row=0, column=2, padx=3, pady=2)
        self.ebz_dv_var = tk.DoubleVar(value=0)
        ttk.Entry(ebz, textvariable=self.ebz_dv_var, width=10).grid(row=0, column=3, padx=3)

        ttk.Label(ebz, text="ML (mm):").grid(row=0, column=4, padx=3, pady=2)
        self.ebz_ml_var = tk.DoubleVar(value=0)
        ttk.Entry(ebz, textvariable=self.ebz_ml_var, width=10).grid(row=0, column=5, padx=3)

        self.set_ebz_btn = ttk.Button(ebz, text="Set EBZ", command=self.set_ebz, state=tk.DISABLED)
        self.set_ebz_btn.grid(row=0, column=6, padx=3)
        self.reset_ebz_btn = ttk.Button(ebz, text="Reset EBZ", command=self.reset_ebz, state=tk.DISABLED)
        self.reset_ebz_btn.grid(row=0, column=7, padx=3)
        self.set_ebz_cursor_btn = ttk.Button(ebz, text="Set EBZ to Crosshair", command=self.set_ebz_to_crosshair,
                                             state=tk.DISABLED)
        self.set_ebz_cursor_btn.grid(row=0, column=8, padx=3)

        self.cursor_info_var = tk.StringVar(value="Crosshair: —")
        ttk.Label(ebz, textvariable=self.cursor_info_var).grid(row=1, column=0, columnspan=9, sticky=tk.W, padx=5,
                                                               pady=2)

        ttk.Label(ebz, text="Left-click any view to move crosshair. Right-click to set EBZ at crosshair.",
                  font=("", 9, "italic")).grid(row=2, column=0, columnspan=9, sticky=tk.W, padx=5)

        # --- Figure: 3 subplots ---
        self.fig_frame = ttk.Frame(main_frame)
        self.fig_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)

        self.fig = Figure(figsize=(14, 5), dpi=100)
        self.fig.subplots_adjust(left=0.04, right=0.98, top=0.93, bottom=0.07, wspace=0.25)
        self.axes = [self.fig.add_subplot(1, 3, i + 1) for i in range(3)]

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.fig_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.fig_frame)
        self.toolbar.update()

        # Mouse events
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)

        # --- Slice sliders (one per axis) ---
        slider_frame = ttk.Frame(main_frame)
        slider_frame.pack(fill=tk.X, padx=5, pady=3)

        self.slice_vars = []
        self.slice_scales = []
        self.slice_labels = []
        for i, name in enumerate(self.view_names):
            ttk.Label(slider_frame, text=f"{name} slice:").grid(row=i, column=0, sticky=tk.W, padx=3, pady=1)
            var = tk.IntVar(value=0)
            scale = ttk.Scale(slider_frame, from_=0, to=0, orient=tk.HORIZONTAL, variable=var,
                              command=lambda val, idx=i: self.on_slider(idx))
            scale.grid(row=i, column=1, sticky='we', padx=3)
            lbl = ttk.Label(slider_frame, text="0/0", width=12)
            lbl.grid(row=i, column=2, padx=3)
            self.slice_vars.append(var)
            self.slice_scales.append(scale)
            self.slice_labels.append(lbl)
        slider_frame.columnconfigure(1, weight=1)

        # Dynamic slider (hidden by default)
        self.dyn_frame = ttk.Frame(slider_frame)
        self.dyn_frame.grid(row=3, column=0, columnspan=3, sticky='we')
        ttk.Label(self.dyn_frame, text="Dynamic:").grid(row=0, column=0, sticky=tk.W, padx=3)
        self.dyn_var = tk.IntVar(value=0)
        self.dyn_scale = ttk.Scale(self.dyn_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                   variable=self.dyn_var, command=self.on_dynamic_slider)
        self.dyn_scale.grid(row=0, column=1, sticky='we', padx=3)
        self.dyn_label = ttk.Label(self.dyn_frame, text="0/0", width=12)
        self.dyn_label.grid(row=0, column=2, padx=3)
        self.dyn_frame.columnconfigure(1, weight=1)
        self.dyn_frame.grid_remove()

        # Header info button
        self.header_btn = ttk.Button(slider_frame, text="Show Header Info", command=self.show_header_info,
                                     state=tk.DISABLED)
        self.header_btn.grid(row=4, column=0, padx=3, pady=3, sticky=tk.W)

    # ------------------------------------------------------------------ File I/O
    def browse_file(self):
        initial_dir = None
        if self.default_path:
            initial_dir = os.path.dirname(self.default_path) if not os.path.isdir(
                self.default_path) else self.default_path
        fn = filedialog.askopenfilename(title="Select PAR File",
                                        filetypes=[('PAR Files', '*.PAR *.par'), ('All', '*.*')],
                                        initialdir=initial_dir)
        if fn:
            self.file_path_var.set(fn)

    def check_rec_file(self, par_file):
        base = os.path.splitext(par_file)[0]
        return os.path.exists(base + '.REC') or os.path.exists(base + '.rec')

    def save_default_path(self):
        current_path = self.file_path_var.get().strip()
        if not current_path:
            messagebox.showerror("Error", "No file path to save.")
            return
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mri_viewer_config.json')
        try:
            config = {'default_path': current_path}
            if self.ebz_set:
                config['ebz_world'] = self.ebz_world
            with open(config_file, 'w') as f:
                json.dump(config, f)
            msg = f"Default path saved: {current_path}"
            if self.ebz_set:
                msg += f"\nEBZ saved: AP={self.ebz_world[1]:.2f}, DV={self.ebz_world[2]:.2f}, ML={self.ebz_world[0]:.2f} mm"
            messagebox.showinfo("Saved", msg)
            self.default_path = current_path
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ------------------------------------------------------------------ Loading
    def load_and_visualize(self):
        par_file = self.file_path_var.get().strip()
        if not par_file:
            messagebox.showerror("Error", "Select a PAR file.");
            return
        if not os.path.exists(par_file):
            messagebox.showerror("Error", f"{par_file} not found.");
            return
        if not par_file.upper().endswith('.PAR'):
            if not messagebox.askyesno("Warning", "Not a .PAR extension. Continue?"):
                return
        if not self.check_rec_file(par_file):
            messagebox.showerror("Error", "Corresponding .REC file not found.");
            return

        try:
            self.status_var.set(f"Loading {par_file}…")
            self.root.update()

            self.img = load_parrec(par_file, strict_sort=True)
            raw = self.img.get_fdata()
            self.affine = self.img.affine
            self.voxel_sizes = nib.affines.voxel_sizes(self.affine)

            # Handle 3D vs 4D
            if raw.ndim == 4:
                self.data = raw
                self.has_dynamics = True
                self.dynamics = raw.shape[3]
            elif raw.ndim == 3:
                self.data = raw
                self.has_dynamics = False
                self.dynamics = 1
            else:
                raise ValueError(f"Unexpected ndim={raw.ndim}")

            self.dim_sizes = list(self.data.shape[:3])

            # Determine axis labels from affine
            self._determine_axis_labels()

            # Precompute world coordinates along each axis
            self._compute_world_coords()

            # Initialise crosshair to volume centre
            self.cursor_vox = [s // 2 for s in self.dim_sizes]

            # Update sliders
            for i in range(3):
                self.slice_scales[i].configure(from_=0, to=self.dim_sizes[self.slice_axes[i]] - 1)
                self.slice_vars[i].set(self.cursor_vox[self.slice_axes[i]])

            if self.has_dynamics:
                self.dyn_scale.configure(from_=0, to=self.dynamics - 1)
                self.dyn_var.set(0)
                self.dyn_frame.grid()
            else:
                self.dyn_frame.grid_remove()

            # Enable EBZ controls
            self.set_ebz_btn.config(state=tk.NORMAL)
            self.set_ebz_cursor_btn.config(state=tk.NORMAL)
            self.header_btn.config(state=tk.NORMAL)

            self.display_all()
            self.status_var.set(f"Loaded {os.path.basename(par_file)}  —  shape {self.data.shape[:3]}, "
                                f"voxel {self.voxel_sizes[0]:.3f}×{self.voxel_sizes[1]:.3f}×{self.voxel_sizes[2]:.3f} mm")

        except Exception as e:
            self.status_var.set("Error loading file")
            messagebox.showerror("Error", str(e))
            import traceback;
            traceback.print_exc()

    def _determine_axis_labels(self):
        """Determine which world axis each voxel axis maps to."""
        world_names = ['R/L', 'A/P', 'S/I']
        labels = []
        for vax in range(3):
            col = self.affine[:3, vax]
            dominant = int(np.argmax(np.abs(col)))
            labels.append(world_names[dominant])
        self.dim_labels = labels
        print(f"Axis mapping: {list(zip(range(3), labels, self.dim_sizes))}")

    def _compute_world_coords(self):
        """For each voxel axis, compute the world coordinate at each index."""
        self.world_coords_per_axis = []
        for ax in range(3):
            coords = []
            for i in range(self.dim_sizes[ax]):
                vox = [0, 0, 0, 1]
                vox[ax] = i
                world = self.affine @ np.array(vox)
                coords.append(world[:3].copy())
            self.world_coords_per_axis.append(np.array(coords))

    def vox_to_world(self, vox):
        """Convert voxel [i,j,k] to world [x,y,z] mm."""
        v = np.array([*vox, 1.0])
        return (self.affine @ v)[:3]

    def world_to_vox(self, world):
        """Convert world [x,y,z] mm to voxel [i,j,k]."""
        inv = np.linalg.inv(self.affine)
        v = np.array([*world, 1.0])
        return (inv @ v)[:3]

    # ------------------------------------------------------------------ Display
    def get_slice(self, view_idx):
        """
        Extract a 2D slice for the given view.
        Returns (image_2d, h_label, v_label, h_ax, v_ax).
        """
        fix_ax = self.slice_axes[view_idx]
        h_ax = self.horiz_axes[view_idx]
        v_ax = self.vert_axes[view_idx]
        idx = self.cursor_vox[fix_ax]
        idx = np.clip(idx, 0, self.dim_sizes[fix_ax] - 1)

        # Build indexing tuple
        slicer = [slice(None)] * 3
        slicer[fix_ax] = idx
        if self.has_dynamics:
            slicer.append(self.current_dynamic)

        img2d = self.data[tuple(slicer)]

        # img2d axes are the remaining two in order. We need to know which
        # numpy axis of img2d corresponds to h_ax and v_ax.
        # After fixing fix_ax, the remaining axes in order are the non-fixed ones.
        remaining = [a for a in range(3) if a != fix_ax]
        # img2d.shape[0] = remaining[0], img2d.shape[1] = remaining[1]

        # We want: rows = v_ax, cols = h_ax
        if remaining[0] == h_ax and remaining[1] == v_ax:
            img2d = img2d.T  # transpose so rows=v_ax, cols=h_ax
        # else remaining[0]==v_ax, remaining[1]==h_ax -> already correct

        return img2d, self.dim_labels[h_ax], self.dim_labels[v_ax], h_ax, v_ax

    def display_all(self):
        """Redraw all three views."""
        if self.data is None:
            return

        for vi in range(3):
            ax = self.axes[vi]
            ax.clear()

            img2d, h_label, v_label, h_ax, v_ax = self.get_slice(vi)

            # Display with origin at top-left; we'll flip if needed for
            # conventional orientation
            im = ax.imshow(img2d, cmap='gray', aspect='equal', origin='upper',
                           interpolation='nearest')

            # Contrast
            try:
                nz = img2d[img2d > 0]
                if len(nz) > 0:
                    vmin, vmax = np.percentile(nz, [1, 99])
                    im.set_clim(vmin, vmax)
            except:
                pass

            # Crosshair lines
            ch = self.cursor_vox[h_ax]
            cv = self.cursor_vox[v_ax]
            ax.axvline(ch, color='lime', linewidth=0.7, alpha=0.6)
            ax.axhline(cv, color='lime', linewidth=0.7, alpha=0.6)

            # EBZ marker
            if self.ebz_set:
                eh = self.ebz_vox[h_ax]
                ev = self.ebz_vox[v_ax]
                ax.plot(eh, ev, 'r*', markersize=8)
                # Dashed EBZ axes
                ax.axvline(eh, color='red', linewidth=0.5, alpha=0.4, linestyle='--')
                ax.axhline(ev, color='red', linewidth=0.5, alpha=0.4, linestyle='--')

            # Title with world coordinate of the fixed axis
            fix_ax = self.slice_axes[vi]
            fix_idx = self.cursor_vox[fix_ax]
            if self.world_coords_per_axis[fix_ax] is not None:
                # Dominant world component for this axis
                col = self.affine[:3, fix_ax]
                dom = int(np.argmax(np.abs(col)))
                world_val = self.world_coords_per_axis[fix_ax][fix_idx][dom]
                if self.ebz_set:
                    ebz_world_val = self.world_coords_per_axis[fix_ax][self.ebz_vox[fix_ax]][dom]
                    rel = world_val - ebz_world_val
                    title = f"{self.view_names[vi]}  {self.dim_labels[fix_ax]}={fix_idx}  ({rel:+.2f} mm from EBZ)"
                else:
                    title = f"{self.view_names[vi]}  {self.dim_labels[fix_ax]}={fix_idx}  ({world_val:.2f} mm)"
            else:
                title = f"{self.view_names[vi]}  {self.dim_labels[fix_ax]}={fix_idx}"

            ax.set_title(title, fontsize=10)
            ax.set_xlabel(h_label, fontsize=9)
            ax.set_ylabel(v_label, fontsize=9)
            ax.tick_params(labelsize=7)

        self.fig.canvas.draw_idle()
        self._update_cursor_info()
        self._sync_sliders()

    def _update_cursor_info(self):
        """Update the text label showing current crosshair position."""
        if self.data is None:
            return
        world = self.vox_to_world(self.cursor_vox)
        txt = (f"Crosshair voxel: [{self.cursor_vox[0]}, {self.cursor_vox[1]}, {self.cursor_vox[2]}]"
               f"   world: [{world[0]:.2f}, {world[1]:.2f}, {world[2]:.2f}] mm")
        if self.ebz_set:
            ebz_w = self.vox_to_world(self.ebz_vox)
            rel = world - ebz_w
            txt += f"   rel EBZ: [{rel[0]:.2f}, {rel[1]:.2f}, {rel[2]:.2f}] mm"
        self.cursor_info_var.set(txt)

    def _sync_sliders(self):
        for i in range(3):
            ax_idx = self.slice_axes[i]
            self.slice_vars[i].set(self.cursor_vox[ax_idx])
            self.slice_labels[i].config(text=f"{self.cursor_vox[ax_idx]}/{self.dim_sizes[ax_idx] - 1}")

    # ------------------------------------------------------------------ Events
    def on_slider(self, view_idx):
        if self.data is None:
            return
        ax_idx = self.slice_axes[view_idx]
        new_val = self.slice_vars[view_idx].get()
        if new_val != self.cursor_vox[ax_idx]:
            self.cursor_vox[ax_idx] = int(new_val)
            self.display_all()

    def on_dynamic_slider(self, *args):
        self.current_dynamic = self.dyn_var.get()
        self.dyn_label.config(text=f"{self.current_dynamic}/{self.dynamics - 1}")
        self.display_all()

    def _identify_view(self, event):
        """Return which view index (0,1,2) the event is in, or None."""
        for i, ax in enumerate(self.axes):
            if event.inaxes == ax:
                return i
        return None

    def on_click(self, event):
        if self.data is None or event.inaxes is None:
            return
        vi = self._identify_view(event)
        if vi is None:
            return

        h_ax = self.horiz_axes[vi]
        v_ax = self.vert_axes[vi]
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        # Clamp to valid range
        new_h = int(np.clip(round(x), 0, self.dim_sizes[h_ax] - 1))
        new_v = int(np.clip(round(y), 0, self.dim_sizes[v_ax] - 1))

        if event.button == 1:  # Left click -> move crosshair
            self.cursor_vox[h_ax] = new_h
            self.cursor_vox[v_ax] = new_v
            self.display_all()
        elif event.button == 3:  # Right click -> set EBZ to current crosshair
            self.cursor_vox[h_ax] = new_h
            self.cursor_vox[v_ax] = new_v
            self.set_ebz_to_crosshair()

    def on_motion(self, event):
        """Show hover position in status bar."""
        if self.data is None or event.inaxes is None:
            return
        vi = self._identify_view(event)
        if vi is None:
            return
        h_ax = self.horiz_axes[vi]
        v_ax = self.vert_axes[vi]
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        hv = int(np.clip(round(x), 0, self.dim_sizes[h_ax] - 1))
        vv = int(np.clip(round(y), 0, self.dim_sizes[v_ax] - 1))
        self.status_var.set(f"{self.view_names[vi]}  —  {self.dim_labels[h_ax]}={hv}, {self.dim_labels[v_ax]}={vv}")

    # ------------------------------------------------------------------ EBZ
    def set_ebz_to_crosshair(self):
        """Set EBZ to current crosshair position."""
        if self.data is None:
            return
        world = self.vox_to_world(self.cursor_vox)
        self.ebz_vox = list(self.cursor_vox)
        self.ebz_world = list(world)
        self.ebz_ap_var.set(round(world[1], 3))
        self.ebz_dv_var.set(round(world[2], 3))
        self.ebz_ml_var.set(round(world[0], 3))
        self.ebz_set = True
        self.reset_ebz_btn.config(state=tk.NORMAL)
        self.display_all()

    def set_ebz(self):
        """Set EBZ from the manual entry fields (world coordinates)."""
        if self.data is None:
            return
        try:
            # Fields: AP -> world[1], DV -> world[2], ML -> world[0]
            world = np.array([self.ebz_ml_var.get(), self.ebz_ap_var.get(), self.ebz_dv_var.get()])
            vox = self.world_to_vox(world)
            self.ebz_vox = [int(np.clip(round(v), 0, self.dim_sizes[i] - 1)) for i, v in enumerate(vox)]
            self.ebz_world = list(world)
            self.ebz_set = True
            self.reset_ebz_btn.config(state=tk.NORMAL)
            self.display_all()
        except Exception as e:
            messagebox.showerror("EBZ Error", str(e))

    def reset_ebz(self):
        self.ebz_set = False
        self.ebz_vox = [0, 0, 0]
        self.ebz_world = [0, 0, 0]
        self.ebz_ap_var.set(0)
        self.ebz_dv_var.set(0)
        self.ebz_ml_var.set(0)
        self.reset_ebz_btn.config(state=tk.DISABLED)
        self.display_all()

    # ------------------------------------------------------------------ Header
    def show_header_info(self):
        if self.img is None:
            return
        win = tk.Toplevel(self.root)
        win.title("PAR/REC Header")
        win.geometry("900x700")

        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set)
        txt.pack(fill=tk.BOTH, expand=True)
        sb.config(command=txt.yview)

        header = self.img.header
        txt.insert(tk.END, "=== AFFINE MATRIX ===\n")
        txt.insert(tk.END, f"{self.affine}\n\n")
        txt.insert(tk.END, f"Voxel sizes: {self.voxel_sizes}\n")
        txt.insert(tk.END, f"Axis labels: {self.dim_labels}\n")
        txt.insert(tk.END, f"Dimensions: {self.dim_sizes}\n\n")

        if hasattr(header, 'general_info'):
            txt.insert(tk.END, "=== GENERAL INFO ===\n")
            for k, v in sorted(header.general_info.items()):
                txt.insert(tk.END, f"  {k}: {v}\n")
            txt.insert(tk.END, "\n")

        txt.insert(tk.END, "=== FULL HEADER ===\n")
        txt.insert(tk.END, pprint.pformat(header.__dict__))
        txt.config(state=tk.DISABLED)


# ------------------------------------------------------------------ Main
if __name__ == "__main__":
    default_path = sys.argv[1] if len(sys.argv) > 1 else None

    root = tk.Tk()
    app = TriplanarMRIViewer(root, default_path)

    # Load config
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mri_viewer_config.json')
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            saved = config.get('default_path')
            if default_path is None and saved:
                app.default_path = saved
                app.file_path_var.set(saved)
                default_path = saved
            if 'ebz_world' in config:
                ew = config['ebz_world']
                app.ebz_ml_var.set(ew[0])
                app.ebz_ap_var.set(ew[1])
                app.ebz_dv_var.set(ew[2])
        except Exception as e:
            print(f"Config load error: {e}")

    if default_path and os.path.exists(default_path):
        app.load_and_visualize()
        if 'ebz_world' in config:
            app.set_ebz()

    root.mainloop()
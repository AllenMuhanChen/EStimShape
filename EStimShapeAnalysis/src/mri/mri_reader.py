import numpy as np


def save_default_path(self):
    """Save the current file path and EBZ coordinates as defaults"""
    current_path = self.file_path_var.get().strip()
    if not current_path:
        messagebox.showerror("Error", "No file path to save as default.")
        return

    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mri_viewer_config.json')
    try:
        config = {'default_path': current_path}

        # Also save EBZ coordinates if set
        if self.ebz_set:
            config['ebz_coordinates'] = {
                'x': self.ebz_coordinates['x'],
                'y': self.ebz_coordinates['y'],
                'z': self.ebz_coordinates['z']
            }

        with open(config_file, 'w') as f:
            json.dump(config, f)

        # Confirmation message with neuroanatomical terms
        if self.ebz_set:
            messagebox.showinfo("Success",
                                f"Default path saved: {current_path}\n\n"
                                f"Default EBZ coordinates saved:\n"
                                f"AP: {self.ebz_coordinates['x']:.2f}, "
                                f"DV: {self.ebz_coordinates['y']:.2f}, "
                                f"ML: {self.ebz_coordinates['z']:.2f} mm")
        else:
            messagebox.showinfo("Success", f"Default path saved: {current_path}")

        self.default_path = current_path
    except Exception as e:
        messagebox.showerror("Error", f"Could not save default path: {str(e)}")


    par_file = self.file_path_var.get().strip()

    if not par_file:
        messagebox.showerror("Error", "Please select a PAR file.")
        return

    if not os.path.exists(par_file):
        messagebox.showerror("Error", f"File {par_file} does not exist.")
        return

    if not par_file.upper().endswith('.PAR'):
        if not messagebox.askyesno("Warning",
                                   f"File {par_file} does not have a .PAR extension.\nDo you want to continue?"):
            return

    if not self.check_rec_file(par_file):
        messagebox.showerror("Error", f"Corresponding REC file for {par_file} not found.")
        return

    try:
        self.status_var.set(f"Loading {par_file}...")
        self.root.update()

        # Load the PAR/REC file
        self.img = load_parrec(par_file)
        self.data = self.img.get_fdata()

        # Store the affine matrix for coordinate transformations
        self.affine = self.img.affine
        print("Affine matrix loaded:", self.affine)

        # Get dimensions
        if len(self.data.shape) == 4:
            self.slices, rows, cols, self.dynamics = self.data.shape
            self.has_dynamics = True
        elif len(self.data.shape) == 3:
            self.slices, rows, cols = self.data.shape
            self.dynamics = 1
            self.has_dynamics = False
        else:
            raise ValueError("Unexpected data dimensions. Expected 3D or 4D data.")

        # Extract slice position information from header
        self.slice_positions = []
        try:
            # Generate slice positions based on affine matrix
            # This should work regardless of header structure
            self.slice_positions = []
            for i in range(self.slices):
                voxel_coords = np.array([0, 0, i, 1])
                world_coords = np.dot(self.affine, voxel_coords)
                self.slice_positions.append(float(world_coords[2]))
            print(f"Generated {len(self.slice_positions)} slice positions from affine matrix")

            # Try to get slice thickness from header
            try:
                header = self.img.header
                if hasattr(header, 'general_info') and isinstance(header.general_info, dict):
                    self.slice_thickness = header.general_info.get('slice_thickness', None)
                    if self.slice_thickness:
                        print(f"Slice thickness: {self.slice_thickness} mm")
            except Exception as e:
                print(f"Could not get slice thickness: {str(e)}")
                self.slice_thickness = None

        except Exception as e:
            print(f"Could not generate slice positions: {str(e)}")
            self.slice_positions = None

        # Initialize slice to middle
        self.current_slice = self.slices // 2
        self.current_dynamic = 0

        # Update UI controls
        self.slice_var.set(self.current_slice)
        self.slice_scale.configure(from_=0, to=self.slices - 1)
        self.slice_label.config(text=f"{self.current_slice}/{self.slices - 1}")

        if self.has_dynamics:
            self.dynamic_var.set(self.current_dynamic)
            self.dynamic_scale.configure(from_=0, to=self.dynamics - 1)
            self.dynamic_label.config(text=f"{self.current_dynamic}/{self.dynamics - 1}")
            self.show_dynamic_controls()
        else:
            self.hide_dynamic_controls()

        # Enable EBZ buttons
        self.set_ebz_button.config(state=tk.NORMAL)
        self.extract_ebz_button.config(state=tk.NORMAL)
        self.set_z_button.config(state=tk.NORMAL)
        self.set_z_mid_button.config(state=tk.NORMAL)
        if self.ebz_set:
            self.reset_ebz_button.config(state=tk.NORMAL)

        # Display the initial image
        self.display_current_slice()

        # Add a debug button to show all header information
        debug_button = ttk.Button(self.slice_control_frame, text="Show Header Info",
                                  command=self.show_header_info)
        debug_button.grid(row=0, column=3, padx=5, pady=5)

        self.status_var.set(f"Loaded {par_file}. Dimensions: {self.data.shape}")
    except Exception as e:
        self.status_var.set("Error loading file")
        messagebox.showerror("Error", f"Error visualizing file: {str(e)}")
        import numpy as np


import matplotlib

matplotlib.use('TkAgg')  # Use TkAgg backend for better integration with Tkinter
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from nibabel.parrec import load as load_parrec
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import pprint
import json
import sys


class MRIViewer:
    def __init__(self, root, default_path=None):
        self.root = root
        self.root.title("PAR/REC MRI Viewer")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)

        # Variables to store data
        self.img = None
        self.data = None
        self.current_slice = 0
        self.current_dynamic = 0
        self.slices = 0
        self.dynamics = 0
        self.has_dynamics = False
        self.default_path = default_path

        # EBZ (External Brain Zero) coordinates
        self.ebz_set = False
        self.ebz_coordinates = {"x": 0, "y": 0, "z": 0}  # In mm
        self.affine = None  # To store the affine matrix

        self.setup_ui()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top control section
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # File path entry and browse button
        ttk.Label(control_frame, text="PAR File:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)

        self.file_path_var = tk.StringVar()
        # Set default path if provided
        if self.default_path:
            self.file_path_var.set(self.default_path)

        file_entry = ttk.Entry(control_frame, textvariable=self.file_path_var, width=60)
        file_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)

        browse_button = ttk.Button(control_frame, text="Browse...", command=self.browse_file)
        browse_button.grid(column=2, row=0, sticky=tk.W, padx=5, pady=5)

        # Load button
        load_button = ttk.Button(control_frame, text="Load and Visualize", command=self.load_and_visualize)
        load_button.grid(column=3, row=0, sticky=tk.W, padx=5, pady=5)

        # Save default path button
        save_default_button = ttk.Button(control_frame, text="Save as Default", command=self.save_default_path)
        save_default_button.grid(column=4, row=0, sticky=tk.W, padx=5, pady=5)

        # Configure control frame grid
        control_frame.columnconfigure(1, weight=1)

        # Status label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(fill=tk.X, padx=5, pady=5)

        # EBZ control frame
        self.ebz_frame = ttk.LabelFrame(main_frame, text="EBZ (External Brain Zero) Coordinates")
        self.ebz_frame.pack(fill=tk.X, padx=5, pady=5)

        # EBZ coordinate inputs with neuroanatomical labels
        ttk.Label(self.ebz_frame, text="AP (mm):").grid(row=0, column=0, padx=5, pady=5)
        self.ebz_x_var = tk.DoubleVar(value=0)
        ttk.Entry(self.ebz_frame, textvariable=self.ebz_x_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.ebz_frame, text="DV (mm):").grid(row=0, column=2, padx=5, pady=5)
        self.ebz_y_var = tk.DoubleVar(value=0)
        ttk.Entry(self.ebz_frame, textvariable=self.ebz_y_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(self.ebz_frame, text="ML (mm):").grid(row=0, column=4, padx=5, pady=5)
        self.ebz_z_var = tk.DoubleVar(value=0)
        ttk.Entry(self.ebz_frame, textvariable=self.ebz_z_var, width=10).grid(row=0, column=5, padx=5, pady=5)

        # Button to set EBZ
        self.set_ebz_button = ttk.Button(self.ebz_frame, text="Set EBZ", command=self.set_ebz, state=tk.DISABLED)
        self.set_ebz_button.grid(row=0, column=6, padx=5, pady=5)

        # Button to reset EBZ
        self.reset_ebz_button = ttk.Button(self.ebz_frame, text="Reset EBZ", command=self.reset_ebz, state=tk.DISABLED)
        self.reset_ebz_button.grid(row=0, column=7, padx=5, pady=5)

        # Add button to extract EBZ AP,DV from current cursor position (keeping ML)
        self.extract_ebz_button = ttk.Button(self.ebz_frame, text="Extract AP,DV from View",
                                             command=self.extract_ebz_from_view, state=tk.DISABLED)
        self.extract_ebz_button.grid(row=0, column=8, padx=5, pady=5)

        # Add button to set ML to current slice
        self.set_z_button = ttk.Button(self.ebz_frame, text="Set ML to Current Slice",
                                       command=self.set_z_to_current_slice, state=tk.DISABLED)
        self.set_z_button.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

        # Add button to set ML to middle slice
        self.set_z_mid_button = ttk.Button(self.ebz_frame, text="Set ML to Middle Slice",
                                           command=self.set_z_to_middle_slice, state=tk.DISABLED)
        self.set_z_mid_button.grid(row=1, column=3, columnspan=3, padx=5, pady=5, sticky=tk.W)

        # Current cursor position label
        self.cursor_position_var = tk.StringVar(value="Cursor: AP=N/A, DV=N/A, ML=N/A mm")
        ttk.Label(self.ebz_frame, textvariable=self.cursor_position_var).grid(row=2, column=0, columnspan=9, padx=5,
                                                                              pady=5, sticky=tk.W)

        # Instructions for setting EBZ
        instructions = "Right-click on image to set AP,DV coordinates. Use buttons to set ML coordinate to current or middle slice."
        ttk.Label(self.ebz_frame, text=instructions, font=("", 9, "italic")).grid(row=3, column=0, columnspan=9, padx=5,
                                                                                  pady=0, sticky=tk.W)

        # Frame for matplotlib figure
        self.figure_frame = ttk.Frame(main_frame)
        self.figure_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create matplotlib figure and canvas (initially empty)
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.figure_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.figure_frame)
        self.toolbar.update()

        # Slice control frame
        self.slice_control_frame = ttk.Frame(main_frame)
        self.slice_control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Slice navigation controls (initially hidden)
        self.slice_var = tk.IntVar(value=0)
        self.dynamic_var = tk.IntVar(value=0)

        # Slice label and scale
        ttk.Label(self.slice_control_frame, text="Slice:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.slice_scale = ttk.Scale(self.slice_control_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                     variable=self.slice_var, command=self.update_slice)
        self.slice_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.slice_label = ttk.Label(self.slice_control_frame, text="0/0")
        self.slice_label.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)

        # Dynamic controls (initially hidden)
        ttk.Label(self.slice_control_frame, text="Dynamic:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.dynamic_scale = ttk.Scale(self.slice_control_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                       variable=self.dynamic_var, command=self.update_dynamic)
        self.dynamic_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.dynamic_label = ttk.Label(self.slice_control_frame, text="0/0")
        self.dynamic_label.grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # Configure slice control frame grid
        self.slice_control_frame.columnconfigure(1, weight=1)

        # Hide dynamic controls initially
        self.hide_dynamic_controls()

        # Set up mouse move event to track cursor position
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        # Set up mouse click event to select EBZ
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click)

    def set_z_to_current_slice(self):
        """Set ML coordinate to current slice position"""
        if self.slice_positions and len(self.slice_positions) > self.current_slice:
            ml_pos = self.slice_positions[self.current_slice]
            self.ebz_z_var.set(ml_pos)
            self.status_var.set(f"Set ML coordinate to current slice: {ml_pos:.2f} mm")

    def set_z_to_middle_slice(self):
        """Set ML coordinate to middle slice position"""
        if self.slice_positions and len(self.slice_positions) > 0:
            middle_slice_idx = len(self.slice_positions) // 2
            middle_slice_ml = self.slice_positions[middle_slice_idx]
            self.ebz_z_var.set(middle_slice_ml)
            self.status_var.set(
                f"Set ML coordinate to middle slice: {middle_slice_ml:.2f} mm (Slice {middle_slice_idx})")

    def on_mouse_move(self, event):
        """Update cursor position when mouse moves over the image"""
        if not hasattr(self, 'img') or self.img is None or not event.inaxes:
            return

        # Get x, y coordinates in the plot
        x, y = event.xdata, event.ydata

        if x is None or y is None:
            return

        # If EBZ is set, calculate relative coordinates
        if self.ebz_set:
            # EBZ marker world coordinates have already been calculated during initial setting
            ebz_x, ebz_y = self.ebz_pixel_coords  # Store these when setting EBZ

            # Calculate relative coordinates
            relative_x = x - ebz_x
            relative_y = y - ebz_y

            # Update cursor position
            self.cursor_position_var.set(f"Cursor: AP={relative_x:.1f} px, DV={relative_y:.1f} px")
        else:
            # No EBZ, just show pixel coordinates
            self.cursor_position_var.set(f"Cursor: X={x:.1f} px, Y={y:.1f} px")

    def on_mouse_click(self, event):
        if not hasattr(self, 'img') or self.img is None or not event.inaxes:
            return

        # Only process if right mouse button (button 3) is clicked
        if event.button == 3:  # Right-click
            x, y = event.xdata, event.ydata

            if x is None or y is None:
                return

            # Ask user to confirm EBZ coordinates
            if messagebox.askyesno("Set EBZ Coordinates",
                                   f"Set EBZ at pixel coordinates:\n"
                                   f"X = {x:.2f}\n"
                                   f"Y = {y:.2f}"):
                # Set the coordinates
                self.ebz_x_var.set(x)
                self.ebz_y_var.set(y)

                # Store the pixel coordinates for relative tracking
                self.ebz_pixel_coords = (x, y)

                # If not previously set, set ML to middle slice
                if not self.ebz_set and self.slice_positions and len(self.slice_positions) > 0:
                    middle_slice_idx = len(self.slice_positions) // 2
                    middle_slice_ml = self.slice_positions[middle_slice_idx]
                    offset = 1.855  # Offset from middle slice to EBZ (where true EBZ is)
                    self.ebz_z_var.set(middle_slice_ml + offset)
                    # self.ebz_z_var.set(middle_slice_ml-)

                # Apply the EBZ settings
                self.set_ebz()

        # Optional: keep the existing slice display logic
        self.display_current_slice()
    def extract_ebz_from_view(self):
        """Extract EBZ AP,DV coordinates from the current view center, ML coordinate remains unchanged"""
        if not hasattr(self, 'img') or self.img is None:
            return

        if self.affine is not None:
            # Get the dimensions of the current slice
            if self.has_dynamics:
                height, width = self.data[self.current_slice, :, :, self.current_dynamic].shape
            else:
                height, width = self.data[self.current_slice, :, :].shape

            # Center point of the current view
            center_x, center_y = width / 2, height / 2

            # Create a voxel coordinate array with the current slice
            voxel_coords = np.array([center_x, center_y, self.current_slice, 1])

            # Apply the affine transformation to get RAS+ coordinates
            world_coords = np.dot(self.affine, voxel_coords)

            # Get the first 3 elements (x, y, z) in mm and convert to AP, DV, ML
            ap_mm, dv_mm, ml_mm = world_coords[0], -world_coords[1], world_coords[2]

            # Set only the AP and DV EBZ coordinate variables
            self.ebz_x_var.set(ap_mm)
            self.ebz_y_var.set(dv_mm)

            # Keep existing ML coordinate or set to middle slice if not set
            if not self.ebz_set:
                # ML coordinate relative to middle slice
                if self.slice_positions and len(self.slice_positions) > 0:
                    middle_slice_idx = len(self.slice_positions) // 2
                    middle_slice_ml = self.slice_positions[middle_slice_idx]
                    self.ebz_z_var.set(middle_slice_ml)

            # Inform the user
            messagebox.showinfo("EBZ Coordinates",
                                f"Extracted EBZ AP,DV coordinates from view center:\nAP={ap_mm:.2f}, DV={dv_mm:.2f} mm\n"
                                f"ML coordinate is set to: {self.ebz_z_var.get():.2f} mm")

    def set_ebz(self):
        """Set the EBZ coordinates with comprehensive validation"""
        try:
            # Retrieve coordinates with error checking
            x = self.ebz_x_var.get()
            y = self.ebz_y_var.get()
            z = self.ebz_z_var.get()

            # Validate coordinates (optional: add more specific validation if needed)
            if not all(isinstance(coord, (int, float)) for coord in [x, y, z]):
                raise ValueError("Coordinates must be numeric")

            # Store coordinates in a consistent format
            self.ebz_coordinates = {
                "x": float(x),  # AP
                "y": float(y),  # DV
                "z": float(z)  # ML
            }

            # Validate against current image (if loaded)
            if self.img is not None and self.affine is not None:
                # Optional: Add additional sanity checks
                # For example, check if coordinates are within reasonable range of the image
                self._validate_ebz_coordinates()

            # Mark EBZ as set
            self.ebz_set = True

            # Update status and UI
            status_msg = (f"EBZ set to AP={self.ebz_coordinates['x']:.2f}, "
                          f"DV={self.ebz_coordinates['y']:.2f}, "
                          f"ML={self.ebz_coordinates['z']:.2f} mm")
            self.status_var.set(status_msg)

            # Update buttons
            self.reset_ebz_button.config(state=tk.NORMAL)

            # Redisplay current slice to reflect new EBZ
            self.display_current_slice()

        except ValueError as e:
            messagebox.showerror("EBZ Setting Error", str(e))
            self.ebz_set = False

    def _validate_ebz_coordinates(self):
        """
        Perform sanity checks on EBZ coordinates

        This method can be expanded to include more sophisticated validation
        based on the specific characteristics of the loaded image.
        """
        if self.img is None or self.affine is None:
            return

        # Get image dimensions in world coordinates
        # This provides a rough bounds check
        image_dims = self.data.shape

        # Convert image corner coordinates to world space
        corners = [
            [0, 0, 0, 1],
            [image_dims[0], 0, 0, 1],
            [0, image_dims[1], 0, 1],
            [0, 0, image_dims[2], 1]
        ]

        world_corners = [np.dot(self.affine, corner)[:3] for corner in corners]

        # Calculate rough bounds
        x_bounds = [min(c[0] for c in world_corners), max(c[0] for c in world_corners)]
        y_bounds = [min(c[1] for c in world_corners), max(c[1] for c in world_corners)]
        z_bounds = [min(c[2] for c in world_corners), max(c[2] for c in world_corners)]

        # Check if EBZ coordinates are within a reasonable range
        x, y, z = self.ebz_coordinates['x'], self.ebz_coordinates['y'], self.ebz_coordinates['z']

        warnings = []
        if not (x_bounds[0] - 50 <= x <= x_bounds[1] + 50):
            warnings.append(f"AP coordinate {x} is far from expected range {x_bounds}")
        if not (y_bounds[0] - 50 <= y <= y_bounds[1] + 50):
            warnings.append(f"DV coordinate {y} is far from expected range {y_bounds}")
        if not (z_bounds[0] - 50 <= z <= z_bounds[1] + 50):
            warnings.append(f"ML coordinate {z} is far from expected range {z_bounds}")

        # Optionally warn user about potentially incorrect coordinates
        if warnings:
            warning_msg = "Potential EBZ coordinate issues:\n" + "\n".join(warnings)
            messagebox.showwarning("EBZ Coordinate Warning", warning_msg)

    def reset_ebz(self):
        """Reset EBZ coordinates with clear state management"""
        # Reset coordinate variables
        self.ebz_x_var.set(0)
        self.ebz_y_var.set(0)
        self.ebz_z_var.set(0)

        # Reset coordinate dictionary
        self.ebz_coordinates = {"x": 0, "y": 0, "z": 0}

        # Clear EBZ set flag
        self.ebz_set = False

        # Update UI
        self.status_var.set("EBZ reset to origin")
        self.reset_ebz_button.config(state=tk.DISABLED)

        # Redisplay current slice without EBZ offset
        self.display_current_slice()
    def save_default_path(self):
        """Save the current file path and EBZ coordinates as defaults"""
        current_path = self.file_path_var.get().strip()
        if not current_path:
            messagebox.showerror("Error", "No file path to save as default.")
            return

        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mri_viewer_config.json')
        try:
            config = {'default_path': current_path}

            # Also save EBZ coordinates if set
            if self.ebz_set:
                config['ebz_coordinates'] = {
                    'x': self.ebz_coordinates['x'],
                    'y': self.ebz_coordinates['y'],
                    'z': self.ebz_coordinates['z']
                }

            with open(config_file, 'w') as f:
                json.dump(config, f)

            # Confirmation message
            if self.ebz_set:
                messagebox.showinfo("Success",
                                    f"Default path saved: {current_path}\n\n"
                                    f"Default EBZ coordinates saved:\n"
                                    f"X: {self.ebz_coordinates['x']:.2f}, "
                                    f"Y: {self.ebz_coordinates['y']:.2f}, "
                                    f"Z: {self.ebz_coordinates['z']:.2f} mm")
            else:
                messagebox.showinfo("Success", f"Default path saved: {current_path}")

            self.default_path = current_path
        except Exception as e:
            messagebox.showerror("Error", f"Could not save default path: {str(e)}")

    def hide_dynamic_controls(self):
        # Hide dynamic controls
        for widget in self.slice_control_frame.grid_slaves():
            if int(widget.grid_info()["row"]) == 1:
                widget.grid_remove()

    def show_dynamic_controls(self):
        # Show dynamic controls
        for widget in self.slice_control_frame.grid_slaves():
            if int(widget.grid_info()["row"]) == 1:
                widget.grid()

    def browse_file(self):
        filetypes = [('PAR Files', '*.PAR *.par'), ('All Files', '*.*')]

        # Start in the default directory if one was set
        initial_dir = None
        if self.default_path:
            if os.path.isdir(self.default_path):
                initial_dir = self.default_path
            else:
                initial_dir = os.path.dirname(self.default_path)

        filename = filedialog.askopenfilename(
            title="Select PAR File",
            filetypes=filetypes,
            initialdir=initial_dir
        )
        if filename:
            self.file_path_var.set(filename)

    def check_rec_file(self, par_file):
        """Check if the corresponding REC file exists for the given PAR file."""
        rec_base = os.path.splitext(par_file)[0]  # Get filename without extension
        possible_rec_files = [
            rec_base + '.REC',
            rec_base + '.rec',
        ]

        for rec_file in possible_rec_files:
            if os.path.exists(rec_file):
                return True

        return False

    def load_and_visualize(self):
        par_file = self.file_path_var.get().strip()

        if not par_file:
            messagebox.showerror("Error", "Please select a PAR file.")
            return

        if not os.path.exists(par_file):
            messagebox.showerror("Error", f"File {par_file} does not exist.")
            return

        if not par_file.upper().endswith('.PAR'):
            if not messagebox.askyesno("Warning",
                                       f"File {par_file} does not have a .PAR extension.\nDo you want to continue?"):
                return

        if not self.check_rec_file(par_file):
            messagebox.showerror("Error", f"Corresponding REC file for {par_file} not found.")
            return

        try:
            self.status_var.set(f"Loading {par_file}...")
            self.root.update()

            # Load the PAR/REC file
            self.img = load_parrec(par_file, strict_sort=True)
            self.data = self.img.get_fdata()

            # Store the affine matrix for coordinate transformations
            self.affine = self.img.affine
            print("Affine matrix loaded:", self.affine)

            # Get dimensions
            if len(self.data.shape) == 4:
                self.slices, rows, cols, self.dynamics = self.data.shape
                self.has_dynamics = True
            elif len(self.data.shape) == 3:
                self.slices, rows, cols = self.data.shape
                self.dynamics = 1
                self.has_dynamics = False
            else:
                raise ValueError("Unexpected data dimensions. Expected 3D or 4D data.")

            # Extract slice position information from header
            self.slice_positions = []
            try:
                # Generate slice positions based on affine matrix
                # This should work regardless of header structure
                self.slice_positions = []
                for i in range(self.slices):
                    voxel_coords = np.array([0, 0, i, 1])
                    world_coords = np.dot(self.affine, voxel_coords)
                    self.slice_positions.append(float(world_coords[2]))
                print(f"Generated {len(self.slice_positions)} slice positions from affine matrix")

                # Try to get slice thickness from header
                try:
                    header = self.img.header
                    if hasattr(header, 'general_info') and isinstance(header.general_info, dict):
                        self.slice_thickness = header.general_info.get('slice_thickness', None)
                        if self.slice_thickness:
                            print(f"Slice thickness: {self.slice_thickness} mm")
                except Exception as e:
                    print(f"Could not get slice thickness: {str(e)}")
                    self.slice_thickness = None

            except Exception as e:
                print(f"Could not generate slice positions: {str(e)}")
                self.slice_positions = None

            # Initialize slice to middle
            self.current_slice = self.slices // 2
            self.current_dynamic = 0

            # Update UI controls
            self.slice_var.set(self.current_slice)
            self.slice_scale.configure(from_=0, to=self.slices - 1)
            self.slice_label.config(text=f"{self.current_slice}/{self.slices - 1}")

            if self.has_dynamics:
                self.dynamic_var.set(self.current_dynamic)
                self.dynamic_scale.configure(from_=0, to=self.dynamics - 1)
                self.dynamic_label.config(text=f"{self.current_dynamic}/{self.dynamics - 1}")
                self.show_dynamic_controls()
            else:
                self.hide_dynamic_controls()

            # Enable EBZ buttons
            self.set_ebz_button.config(state=tk.NORMAL)
            self.extract_ebz_button.config(state=tk.NORMAL)
            if self.ebz_set:
                self.reset_ebz_button.config(state=tk.NORMAL)

            # Display the initial image
            self.display_current_slice()

            # Add a debug button to show all header information
            debug_button = ttk.Button(self.slice_control_frame, text="Show Header Info",
                                      command=self.show_header_info)
            debug_button.grid(row=0, column=3, padx=5, pady=5)

            self.status_var.set(f"Loaded {par_file}. Dimensions: {self.data.shape}")
        except Exception as e:
            self.status_var.set("Error loading file")
            messagebox.showerror("Error", f"Error visualizing file: {str(e)}")

    def show_header_info(self):
        """Display all available header information in a new window."""
        if self.img is None or self.img.header is None:
            messagebox.showinfo("Info", "No header information available.")
            return

        # Create a new window
        header_window = tk.Toplevel(self.root)
        header_window.title("PAR/REC Header Information")
        header_window.geometry("900x700")

        # Create a frame with scrollbars
        frame = ttk.Frame(header_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create a text widget
        text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text.pack(fill=tk.BOTH, expand=True)

        scrollbar.config(command=text.yview)

        # Get header information
        header = self.img.header

        # Insert header information
        text.insert(tk.END, "PAR/REC Header Information:\n\n")

        # First, show the most useful information for slice positions
        text.insert(tk.END, "=== SLICE POSITION INFORMATION ===\n\n")

        # Show general info about slices
        if hasattr(header, 'general_info'):
            text.insert(tk.END, "General Info:\n")
            for key, value in header.general_info.items():
                if 'slice' in key.lower() or 'thick' in key.lower() or 'gap' in key.lower() or 'pos' in key.lower() or 'off' in key.lower():
                    text.insert(tk.END, f"  {key}: {value}\n")
            text.insert(tk.END, "\n")

        # Show image definitions with slice positions
        if hasattr(header, 'image_defs') and header.image_defs:
            # Show full details for first 5 slices
            text.insert(tk.END, "Slice Position Info (first 5 slices):\n")
            for i, img_def in enumerate(header.image_defs[:5]):
                text.insert(tk.END, f"  Slice {i}:\n")
                for key, value in img_def.items():
                    if 'slice' in key.lower() or 'offcentre' in key.lower() or 'pos' in key.lower() or 'ang' in key.lower():
                        text.insert(tk.END, f"    {key}: {value}\n")
            text.insert(tk.END, "\n")

            # Show relevant position data for all slices
            text.insert(tk.END, "All Slice Positions (offcentre values in mm):\n")
            for i, img_def in enumerate(header.image_defs):
                if 'slice_offcentre' in img_def:
                    offcentre = img_def['slice_offcentre']
                    text.insert(tk.END, f"  Slice {i}: {offcentre}\n")
            text.insert(tk.END, "\n")

        # Then show a summary of the header structure
        text.insert(tk.END, "=== HEADER STRUCTURE OVERVIEW ===\n\n")

        # Basic header attributes
        for attr in ['general_info', 'image_defs', 'dimension_info']:
            if hasattr(header, attr):
                value = getattr(header, attr)
                if attr == 'general_info':
                    # Show general_info in full
                    text.insert(tk.END, f"{attr}:\n")
                    for k, v in value.items():
                        text.insert(tk.END, f"  {k}: {v}\n")
                    text.insert(tk.END, "\n")
                elif attr == 'image_defs':
                    # Just show the count for image_defs
                    text.insert(tk.END, f"{attr}: {len(value)} items\n\n")
                else:
                    text.insert(tk.END, f"{attr}: {value}\n\n")

        # Show affine matrix
        if hasattr(self.img, 'affine'):
            text.insert(tk.END, "Affine Matrix (relates voxel indices to mm coordinates):\n")
            text.insert(tk.END, f"{self.img.affine}\n\n")

        # Show full header dump
        text.insert(tk.END, "=== COMPLETE HEADER DUMP ===\n\n")
        text.insert(tk.END, f"{pprint.pformat(header.__dict__)}\n\n")

        # Show EBZ information if set
        if self.ebz_set:
            text.insert(tk.END, "=== EBZ INFORMATION ===\n\n")
            text.insert(tk.END, f"EBZ coordinates: X={self.ebz_coordinates['x']:.2f}, "
                                f"Y={self.ebz_coordinates['y']:.2f}, "
                                f"Z={self.ebz_coordinates['z']:.2f} mm\n\n")

        # Make the text widget read-only
        text.config(state=tk.DISABLED)

    def update_slice(self, *args):
        self.current_slice = self.slice_var.get()
        self.slice_label.config(text=f"{self.current_slice}/{self.slices - 1}")
        self.display_current_slice()

    def update_dynamic(self, *args):
        self.current_dynamic = self.dynamic_var.get()
        self.dynamic_label.config(text=f"{self.current_dynamic}/{self.dynamics - 1}")
        self.display_current_slice()

    def display_current_slice(self):
        if self.data is None:
            return

        # Clear the figure
        self.fig.clear()

        # Create new axes
        ax = self.fig.add_subplot(111)

        try:
            # Get current slice data
            if self.has_dynamics:
                img_data = self.data[self.current_slice, :, :, self.current_dynamic]
            else:
                img_data = self.data[self.current_slice, :, :]

            # Display the image
            img_display = ax.imshow(np.flipud(img_data), cmap='gray', aspect='equal')

            # Adjust contrast
            try:
                vmin = np.percentile(img_data, 2)
                vmax = np.percentile(img_data, 98)
                if np.isfinite(vmin) and np.isfinite(vmax):
                    img_display.set_clim(vmin, vmax)
            except Exception as e:
                print(f"Could not adjust contrast: {str(e)}")

            # Add colorbar
            self.fig.colorbar(img_display, ax=ax)

            # If EBZ is set, add marker and axes
            if self.ebz_set:
                # Get image dimensions
                rows, cols = img_data.shape

                # Plot EBZ as a red star
                star_y = self.ebz_pixel_coords[1]
                star_x = self.ebz_pixel_coords[0]

                ax.plot(star_x, star_y, 'r*', markersize=10)
                # ax.text(star_x, star_y - 10, "EBZ", color='red',
                #         fontsize=10, ha='center', va='bottom', weight='bold')

                # Draw X-axis (horizontal green line)
                x_line = np.linspace(0, cols - 1, cols)
                ax.plot(x_line, [star_y] * cols, 'g-', linewidth=1, alpha=0.5)

                # Draw Y-axis (vertical green line)
                y_line = np.linspace(0, rows - 1, rows)
                ax.plot([star_x] * rows, y_line, 'g-', linewidth=1, alpha=0.5)

                # Set up custom tick locator
                from matplotlib.ticker import FuncFormatter

                def ap_tick_formatter(x, pos):
                    # Convert pixel coordinate to mm offset from EBZ
                    offset = (x - star_x)
                    return f'{offset:.0f}'

                def dv_tick_formatter(y, pos):
                    # Convert pixel coordinate to mm offset from EBZ
                    # Flip sign because image y-coordinate is inverted
                    offset = -(y - star_y)
                    return f'{offset:.0f}'

                # Set x-axis ticks and labels
                ax.xaxis.set_major_formatter(FuncFormatter(ap_tick_formatter))
                ax.yaxis.set_major_formatter(FuncFormatter(dv_tick_formatter))

                # Set axis labels
                ax.set_xlabel('AP (mm)')
                ax.set_ylabel('DV (mm)')

            # Construct title
            title = f'Slice {self.current_slice}/{self.slices - 1}'
            if self.has_dynamics:
                title += f', Dynamic {self.current_dynamic}/{self.dynamics - 1}'

            if self.slice_positions and len(self.slice_positions) > self.current_slice:
                ml_pos_mm = self.slice_positions[self.current_slice]
                if self.ebz_set:
                    rel_ml_pos = ml_pos_mm - self.ebz_coordinates['z']
                    title += f', ML: {rel_ml_pos:.2f} mm from EBZ'
                else:
                    title += f', ML: {ml_pos_mm:.2f} mm'

            if self.ebz_set:
                title += f' (EBZ: AP={self.ebz_coordinates["x"]:.1f}, DV={self.ebz_coordinates["y"]:.1f}, ML={self.ebz_coordinates["z"]:.1f} mm)'

            ax.set_title(title)

        except Exception as e:
            print(f"Error displaying slice: {str(e)}")
            ax.text(0.5, 0.5, f"Error displaying slice:\n{str(e)}",
                    ha='center', va='center', transform=ax.transAxes, color='red', fontsize=12)

        # Update the canvas
        self.canvas.draw()
if __name__ == "__main__":

    
    # Set up the default path
    default_path = None
    
    # Check if a path was provided as a command-line argument
    if len(sys.argv) > 1:
        default_path = sys.argv[1]
    
    # Initialize the application
    root = tk.Tk()
    app = MRIViewer(root, default_path)
    
    # Try to load saved default path from config file if no command line argument
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mri_viewer_config.json')
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                saved_default_path = config.get('default_path')
    
                # Load saved EBZ coordinates if available
                if 'ebz_coordinates' in config:
                    ebz = config.get('ebz_coordinates')
                    app.ebz_x_var.set(ebz.get('x', 0))
                    app.ebz_y_var.set(ebz.get('y', 0))
                    app.ebz_z_var.set(ebz.get('z', 0))
                    # Don't set EBZ yet, wait until file is loaded
    
                # If no command line path was provided, use the saved default path
                if default_path is None and saved_default_path:
                    app.default_path = saved_default_path
                    app.file_path_var.set(saved_default_path)
                    default_path = saved_default_path
        except Exception as e:
            print(f"Error loading config: {str(e)}")
    
    # If a default path was provided and it exists, automatically load it
    if default_path and os.path.exists(default_path):
        app.load_and_visualize()
    
        # After loading, set EBZ if coordinates were loaded from config
        if 'ebz_coordinates' in config:
            app.set_ebz()
    
    root.mainloop()
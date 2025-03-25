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

    def save_default_path(self):
        """Save the current file path as the default"""
        current_path = self.file_path_var.get().strip()
        if not current_path:
            messagebox.showerror("Error", "No file path to save as default.")
            return

        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mri_viewer_config.json')
        try:
            config = {'default_path': current_path}
            with open(config_file, 'w') as f:
                json.dump(config, f)
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
            self.img = load_parrec(par_file)
            self.data = self.img.get_fdata()

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
                # Get slice positions from the header's image_defs
                header = self.img.header
                image_defs = header.image_defs

                if image_defs is not None and len(image_defs) > 0:
                    # Extract the z-component (index 2) of the slice offset center
                    self.slice_positions = [float(slice_def['slice_offcentre'][2]) for slice_def in image_defs]
                    print(f"Extracted {len(self.slice_positions)} slice positions")

                    # Get slice thickness for additional info
                    self.slice_thickness = header.general_info.get('slice_thickness', None)
                    if self.slice_thickness:
                        print(f"Slice thickness: {self.slice_thickness} mm")
                else:
                    print("No image_defs found in header")
                    self.slice_positions = None
            except Exception as e:
                print(f"Could not extract slice positions: {str(e)}")
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

        # Get the current slice data
        if self.has_dynamics:
            img_data = self.data[self.current_slice, :, :, self.current_dynamic]
            title = f'Slice {self.current_slice}/{self.slices - 1}, Dynamic {self.current_dynamic}/{self.dynamics - 1}'
        else:
            img_data = self.data[self.current_slice, :, :]
            title = f'Slice {self.current_slice}/{self.slices - 1}'

        # Add position information if available
        if self.slice_positions is not None and len(self.slice_positions) > self.current_slice:
            # Get the position in mm
            slice_pos_mm = self.slice_positions[self.current_slice]
            title += f', Position: {slice_pos_mm:.2f} mm'

            # Add thickness information if available
            if hasattr(self, 'slice_thickness') and self.slice_thickness is not None:
                title += f', Thickness: {self.slice_thickness:.2f} mm'

        ax.set_title(title)

        # Display the image
        img_display = ax.imshow(img_data, cmap='gray')

        # Adjust display range to improve contrast
        vmin = np.percentile(img_data, 2)
        vmax = np.percentile(img_data, 98)
        img_display.set_clim(vmin, vmax)

        # Add a colorbar
        self.fig.colorbar(img_display, ax=ax)

        # Update the canvas
        self.canvas.draw()


if __name__ == "__main__":
    import sys

    # Set up the default path
    default_path = None

    # Check if a path was provided as a command-line argument
    if len(sys.argv) > 1:
        default_path = sys.argv[1]

    # You can also hardcode a default path here if needed
    # default_path = "/path/to/your/default/directory/file.PAR"

    # Initialize the application
    root = tk.Tk()
    app = MRIViewer(root, default_path)

    # Try to load saved default path from config file if no command line argument
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mri_viewer_config.json')
    if default_path is None and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                default_path = config.get('default_path')
                if default_path:
                    app.default_path = default_path
                    app.file_path_var.set(default_path)
        except Exception as e:
            print(f"Error loading config: {str(e)}")

    # If a default path was provided and it exists, automatically load it
    if default_path and os.path.exists(default_path):
        app.load_and_visualize()

    root.mainloop()
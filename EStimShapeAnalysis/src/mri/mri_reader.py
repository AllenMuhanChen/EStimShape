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


class MRIViewer:
    def __init__(self, root):
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
        file_entry = ttk.Entry(control_frame, textvariable=self.file_path_var, width=60)
        file_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)

        browse_button = ttk.Button(control_frame, text="Browse...", command=self.browse_file)
        browse_button.grid(column=2, row=0, sticky=tk.W, padx=5, pady=5)

        # Load button
        load_button = ttk.Button(control_frame, text="Load and Visualize", command=self.load_and_visualize)
        load_button.grid(column=3, row=0, sticky=tk.W, padx=5, pady=5)

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
        filename = filedialog.askopenfilename(
            title="Select PAR File",
            filetypes=filetypes
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
                # Get slice positions from the header
                header = self.img.header
                self.slice_positions = header.get_slice_positions()
                print(f"Extracted {len(self.slice_positions)} slice positions")
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
        header_window.geometry("800x600")

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

        # Try to get all available attributes and methods
        for attr in dir(header):
            if not attr.startswith('_'):  # Skip private attributes
                try:
                    value = getattr(header, attr)
                    if callable(value):
                        try:
                            # Try to call method with no arguments
                            result = value()
                            text.insert(tk.END, f"{attr}:\n")
                            text.insert(tk.END, f"{pprint.pformat(result)}\n\n")
                        except:
                            # Skip methods that require arguments
                            pass
                    else:
                        text.insert(tk.END, f"{attr}: {value}\n\n")
                except:
                    pass

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
            slice_pos = self.slice_positions[self.current_slice]
            if isinstance(slice_pos, (list, tuple)) and len(slice_pos) >= 3:
                # If it's a 3D position, use just the axis most likely to represent slice position
                # Usually this is the z-axis (index 2)
                pos_value = slice_pos[2]
                title += f', Position: {pos_value:.2f} mm'
            elif isinstance(slice_pos, (int, float)):
                title += f', Position: {slice_pos:.2f} mm'

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
    root = tk.Tk()
    app = MRIViewer(root)
    root.mainloop()
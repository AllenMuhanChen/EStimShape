from ordered_set import OrderedSet
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict

from src.analysis import compile_current_context, analyze_raw_data
from src.eyecal import plot_eyecal, apply_eyecal
from src.pga.app import run_ga, start_new_ga, process_first_gen, run_cluster_app, calculate_spontaneous_firing_rate, \
    run_rwa, plot_rwa, transfer_eye_cal_params, abandon_generation, process_last_gen, recalculate_ga, run_tree_graph_app
from src.startup import db_factory, setup_xper_properties_and_dirs, backup, startup_system


class ScriptRunnerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Script Runner")

        # Dictionary to store parameter entry widgets
        self.param_entries = {}

        # Organized scripts by sections
        self.scripts = {
            "Running GA": {
                "Startup System": {
                    "func": startup_system.main,
                    "params": []
                },
                "Plot Eye Calibration": {
                    "func": plot_eyecal.main,
                    "params": []
                },
                "Start New GA": {
                    "func": start_new_ga.main,
                    "params": []
                },
                "Run 1st Gen of GA": {
                    "func": run_ga.main,
                    "params": ["R", "G", "B"]
                },
                "Process First Gen": {
                    "func": process_first_gen.main,
                    "params": []
                },
                "Run Cluster App": {
                    "func": run_cluster_app.main,
                    "params": []
                },
                "Calculate Spontaneous Firing Rate": {
                    "func": calculate_spontaneous_firing_rate.main,
                    "params": []
                },
                "Run Next Gen of GA": {
                    "func": run_ga.main,
                    "params": ["R", "G", "B"]
                },
                "Process Last Generation": {
                    "func": process_last_gen.main,
                    "params": []
                }
            },
            "GA Utilities": {
                "Abandon Generation": {
                    "func": abandon_generation.main,
                    "params": []
                },
                "Recalculate GA": {
                    "func": recalculate_ga.main,
                    "params": []
                },
                "Tree Graph": {
                    "func": run_tree_graph_app.main,
                    "params": []
                },
            },
            "Other Tools": {
                "Transfer Eye Calibration & RF Info": {
                    "func": transfer_eye_cal_params.main,
                    "params": []
                },
                "Backup Data": {
                    "func": backup.main,
                    "params": []
                },
                "Apply Eye Cal Params": {
                    "func": apply_eyecal.main,
                    "params": []
                }
            },
            "Live Analysis": {
                "Run RWA": {
                    "func": run_rwa.main,
                    "params": []
                },
                "Plot RWA": {
                    "func": plot_rwa.main,
                    "params": []
                }
            },
            "Post Run": {
                "Compile And Export to Data Repository:": {
                    "func": compile_current_context.main,
                    "params": []
                },
                "Analyze All Raw Data:": {
                    "func": analyze_raw_data.main,
                    "params":[]
                }
            },
        }

        self.create_interface()

    def create_interface(self):
        # Create a main frame with scrollbar
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create canvas and scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create parameter entries first (for scripts that need them)
        self.create_parameter_entries(scrollable_frame)

        # Create section buttons
        self.create_section_buttons(scrollable_frame)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def create_parameter_entries(self, parent):
        """Create parameter entry widgets for all scripts that need them"""
        # Collect all unique parameters
        all_params = OrderedSet()
        for section_scripts in self.scripts.values():
            for script_info in section_scripts.values():
                all_params.update(script_info["params"])

        if all_params:
            # Create parameters section
            param_frame = tk.LabelFrame(parent, text="Parameters", font=("Arial", 12, "bold"))
            param_frame.pack(fill="x", padx=5, pady=10)

            row = 0
            for param in all_params:
                label = tk.Label(param_frame, text=f"Enter {param.capitalize()}:")
                label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
                entry = tk.Entry(param_frame, width=20)
                entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
                self.param_entries[param] = entry
                row += 1

    def create_section_buttons(self, parent):
        """Create buttons organized by sections"""
        for section_name, section_scripts in self.scripts.items():
            # Create section frame
            section_frame = tk.LabelFrame(parent, text=section_name, font=("Arial", 12, "bold"))
            section_frame.pack(fill="x", padx=5, pady=10)

            row = 0
            for script_name, script_info in section_scripts.items():
                # Create script button
                button_frame = tk.Frame(section_frame)
                button_frame.pack(fill="x", padx=10, pady=2)

                script_label = tk.Label(button_frame, text=script_name, width=35, anchor="w")
                script_label.pack(side="left", padx=(0, 10))

                # Show required parameters if any
                if script_info["params"]:
                    params_text = f"(Requires: {', '.join(script_info['params'])})"
                    params_label = tk.Label(button_frame, text=params_text,
                                            font=("Arial", 8), fg="gray")
                    params_label.pack(side="left", padx=(0, 10))

                run_button = tk.Button(button_frame, text="Run",
                                       command=lambda si=script_info, sn=script_name: self.run_script(si, sn),
                                       bg="lightblue", width=8)
                run_button.pack(side="right")

    def run_script(self, script_info: Dict, script_name: str):
        """Run a script with its parameters"""
        func = script_info["func"]
        params = script_info["params"]

        args = []
        for param in params:
            entry = self.param_entries.get(param)
            if entry:
                value = entry.get().strip()
                if value:
                    args.append(value)
                else:
                    messagebox.showwarning("Warning", f"Please enter a value for {param}.")
                    return
            else:
                messagebox.showerror("Error", f"Parameter entry for {param} not found.")
                return

        try:
            result = func(*args)
            if result:
                messagebox.showinfo("Success", f"{script_name} completed successfully!\n\nResult: {result}")
            else:
                messagebox.showinfo("Success", f"{script_name} completed successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run {script_name}:\n\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x800")
    app = ScriptRunnerApp(root)
    root.mainloop()
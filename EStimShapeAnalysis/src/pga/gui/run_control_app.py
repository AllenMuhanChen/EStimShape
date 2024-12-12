import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, Optional, List

from src.eyecal import plot_eyecal
from src.pga.app import run_ga, start_new_ga, process_first_gen, run_cluster_app, calculate_spontaneous_firing_rate, run_rwa, plot_rwa, transfer_eye_cal_params
from src.startup import db_factory, setup_xper_properties_and_dirs


class ScriptRunnerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Script Runner")

        # Dictionary to store parameter entry widgets
        self.param_entries = {}

        self.scripts = {
            "DB Factory": {
                "func": db_factory.main,
                "params": []
            },
            "Setup Properties & Dirs": {
                "func": setup_xper_properties_and_dirs.main,
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
            "Run RWA": {
                "func": run_rwa.main,
                "params": []
            },
            "Plot RWA": {
                "func": plot_rwa.main,
                "params": []
            },
            "Transfer Eye Calibration": {
                "func": transfer_eye_cal_params.main,
                "params": []
            },
            # Add more scripts here with their parameters
        }

        self.create_action_buttons()

    def create_action_buttons(self):
        row = 0
        for script_name, script_info in self.scripts.items():
            if script_info["params"]:
                label = tk.Label(self.root, text=f"{script_name} Parameters:")
                label.grid(row=row, column=0, padx=10, pady=10, columnspan=2)
                row += 1
                for param in script_info["params"]:
                    if param not in self.param_entries:
                        label = tk.Label(self.root, text=f"Enter {param.capitalize()}:")
                        label.grid(row=row, column=0, padx=10, pady=10)
                        entry = tk.Entry(self.root)
                        entry.grid(row=row, column=1, padx=10, pady=10)
                        self.param_entries[param] = entry
                        row += 1

            action_label = tk.Label(self.root, text=script_name)
            action_label.grid(row=row, column=0, padx=10, pady=10)

            action_button = tk.Button(self.root, text="Run", command=lambda si=script_info: self.run_action(si))
            action_button.grid(row=row, column=1, padx=10, pady=10)
            row += 1

    def run_action(self, script_info: Dict):
        func = script_info["func"]
        params = script_info["params"]

        args = []
        for param in params:
            entry = self.param_entries.get(param)
            if entry:
                value = entry.get()
                if value:
                    args.append(value)
                else:
                    messagebox.showwarning("Warning", f"Please enter a value for {param}.")
                    return

        try:
            result = func(*args)
            messagebox.showinfo("Info", result)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run script: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ScriptRunnerApp(root)
    root.mainloop()

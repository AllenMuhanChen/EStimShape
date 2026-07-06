from ordered_set import OrderedSet
import importlib
import multiprocessing as mp
import queue
import sys
import traceback
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict

from src.analysis import compile_current_context, analyze_raw_data, analyze_current_context
from src.analysis.ga import raw_channel_candidacy_analysis, ga_raster_analysis, baseline_analysis, plot_top_n, \
    plot_variants_delta_gui, lfp_analysis, stimulus_pca_analysis
from src.eyecal import plot_eyecal, apply_eyecal
from src.pga.app import run_ga, start_new_ga, process_first_gen, run_cluster_app, calculate_spontaneous_firing_rate, \
    run_rwa, plot_rwa, transfer_eye_cal_params, abandon_generation, process_last_gen, recalculate_ga, \
    run_tree_graph_app, run_delta_side_test, run_cluster_app_pc_figure
from src.startup import db_factory, setup_xper_properties_and_dirs, backup, startup_system


# ---------------------------------------------------------------------------
# Worker process entry point — must be a top-level function so 'spawn' can
# pickle it. Redirects stdout/stderr to a Queue, then calls the target.
# ---------------------------------------------------------------------------

class _QueueStream:
    def __init__(self, q: mp.Queue, tag: str):
        self.q = q
        self.tag = tag

    def write(self, s: str):
        if s:
            try:
                self.q.put((self.tag, s))
            except Exception:
                pass

    def flush(self):
        pass


def _run_script_worker(module_name: str, func_name: str, args: list,
                       q: mp.Queue, in_q: mp.Queue):
    sys.stdout = _QueueStream(q, 'out')
    sys.stderr = _QueueStream(q, 'err')

    # Replace builtins.input so scripts that read from stdin route their
    # prompt through the panel's Entry widget.
    import builtins

    def _panel_input(prompt: str = '') -> str:
        if prompt:
            sys.stdout.write(prompt)
            sys.stdout.flush()
        q.put(('input', ''))
        try:
            line = in_q.get()
        except (EOFError, OSError):
            raise EOFError("input channel closed")
        sys.stdout.write(line + '\n')
        sys.stdout.flush()
        return line

    builtins.input = _panel_input

    try:
        mod = importlib.import_module(module_name)
        func = getattr(mod, func_name)
        result = func(*args)
        msg = f'completed (returned {result!r})' if result else 'completed'
        q.put(('done_ok', msg))
    except SystemExit as e:
        q.put(('done_exit', f'exited (code {e.code})'))
    except BaseException as e:
        sys.stderr.write(traceback.format_exc())
        q.put(('done_err', f'failed: {e}'))


class ScriptPanel:
    """Collapsible panel on the right side showing one running script's
    stdout/stderr, with Minimize and End buttons."""

    BODY_HEIGHT = 12  # text widget rows

    def __init__(self, parent: tk.Widget, script_name: str,
                 process: mp.Process, q: mp.Queue, in_q: mp.Queue,
                 on_close):
        self.process = process
        self.q = q
        self.in_q = in_q
        self.script_name = script_name
        self.on_close = on_close
        self.minimized = False
        self._finished = False
        self._awaiting_input = False

        self.frame = tk.LabelFrame(parent, text=script_name,
                                   font=("Arial", 10, "bold"))
        self.frame.pack(fill="x", padx=4, pady=4)

        header = tk.Frame(self.frame)
        header.pack(fill="x", padx=4, pady=2)

        self.status_label = tk.Label(header, text="running…",
                                     fg="darkgreen", font=("Arial", 9))
        self.status_label.pack(side="left")

        self.close_button = tk.Button(header, text="✕", width=2,
                                      command=self._close)
        self.close_button.pack(side="right", padx=2)

        self.end_button = tk.Button(header, text="End", width=5,
                                    bg="lightcoral", command=self._end)
        self.end_button.pack(side="right", padx=2)

        self.min_button = tk.Button(header, text="–", width=2,
                                    command=self.toggle_minimize)
        self.min_button.pack(side="right", padx=2)

        self.body = tk.Frame(self.frame)
        self.body.pack(fill="both", expand=True, padx=4, pady=2)

        self.text = ScrolledText(self.body, height=self.BODY_HEIGHT,
                                 wrap="word", font=("Courier", 9),
                                 state="disabled", bg="black", fg="white")
        self.text.tag_configure("err", foreground="salmon")
        self.text.tag_configure("sys", foreground="lightyellow")
        self.text.tag_configure("in",  foreground="lightblue")
        self.text.pack(fill="both", expand=True)

        # stdin input row — hidden until the worker calls input()
        self.input_frame = tk.Frame(self.body)
        self.input_prompt = tk.Label(self.input_frame, text="stdin →",
                                     fg="lightblue", bg="black",
                                     font=("Courier", 9))
        self.input_prompt.pack(side="left")
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(self.input_frame, textvariable=self.input_var,
                                    bg="black", fg="white",
                                    insertbackground="white",
                                    font=("Courier", 9))
        self.input_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.input_entry.bind("<Return>", lambda e: self._submit_input())
        self.input_send = tk.Button(self.input_frame, text="Send",
                                    command=self._submit_input)
        self.input_send.pack(side="right")

    def toggle_minimize(self):
        if self.minimized:
            self.body.pack(fill="both", expand=True, padx=4, pady=2)
            self.min_button.config(text="–")
        else:
            self.body.pack_forget()
            self.min_button.config(text="▢")
        self.minimized = not self.minimized

    def append(self, tag: str, s: str):
        self.text.config(state="normal")
        self.text.insert("end", s, tag if tag in ("err", "sys", "in") else None)
        self.text.see("end")
        self.text.config(state="disabled")

    def request_input(self):
        if self._awaiting_input:
            return
        self._awaiting_input = True
        self.input_frame.pack(fill="x", pady=(4, 0))
        self.input_entry.focus_set()

    def _submit_input(self):
        if not self._awaiting_input:
            return
        line = self.input_var.get()
        self.input_var.set("")
        self.input_frame.pack_forget()
        self._awaiting_input = False
        try:
            self.in_q.put(line)
        except (EOFError, OSError):
            pass

    def _end(self):
        if self.process.is_alive():
            self.append("sys", "\n[End requested — terminating…]\n")
            self.process.terminate()
            self.frame.after(2000, self._kill_if_alive)

    def _kill_if_alive(self):
        if self.process.is_alive():
            self.append("sys", "[Still alive after terminate — killing…]\n")
            self.process.kill()

    def mark_finished(self, msg: str):
        if self._finished:
            return
        self._finished = True
        self.status_label.config(text=msg, fg="gray")
        self.end_button.config(state="disabled")

    def _close(self):
        if self.process.is_alive():
            if not messagebox.askyesno(
                    "Script still running",
                    f"{self.script_name} is still running. Terminate and close?"):
                return
            self.process.terminate()
            self.process.join(timeout=1.0)
            if self.process.is_alive():
                self.process.kill()
        self.frame.destroy()
        self.on_close(self)


class ScriptRunnerApp:
    POLL_INTERVAL_MS = 100

    def __init__(self, root):
        self.root = root
        self.root.title("Script Runner")

        # Dictionary to store parameter entry widgets
        self.param_entries = {}

        # Active script panels (one per running/finished process)
        self.panels: list = []

        # mp context — 'spawn' avoids Tk/fork interaction issues
        self.mp_ctx = mp.get_context('spawn')

        self.root.protocol("WM_DELETE_WINDOW", self._on_root_close)

        self.scripts = {
            "Before GA":{
                "Startup System": {
                    "func": startup_system.main,
                    "params": []
                },
                "Plot Eye Calibration": {
                    "func": plot_eyecal.main,
                    "params": []
                },
            },
            "Running GA": {
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
                },
                "Run Delta Side Tests": {
                    "func": run_delta_side_test.main,
                    "params": []
                }

            },
            "Live Analysis": {
                "GA Candidacy Analysis": {
                    "func": raw_channel_candidacy_analysis.main,
                    "params": []
                },
                "GA Raster": {
                    "func": ga_raster_analysis.main,
                    "params": []
                },
                "LFP Analysis":{
                    "func": lfp_analysis.main,
                    "params": []
                },
                "Analyze Current Context": {
                    "func": analyze_current_context.main,
                    "params": []
                },
                "Baseline Analysis": {
                    "func": baseline_analysis.main,
                    "params": []
                },
                "Plot Top N": {
                    "func": plot_top_n.main,
                    "params": []
                },
                "Variant-Delta GUI": {
                    "func": plot_variants_delta_gui.main,
                    "params": []
                },
                "Cluster PCA Analysis": {
                    "func": run_cluster_app_pc_figure.main,
                    "params": []
                },
                "Stimulus-PCA Analysis": {
                    "func": stimulus_pca_analysis.main,
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

        }
        # Organized scripts by sections

        self.create_interface()

    def create_interface(self):
        # Horizontal split: left = script buttons, right = running-script panels
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = tk.Frame(paned)
        right_frame = tk.LabelFrame(paned, text="Running Scripts",
                                    font=("Arial", 11, "bold"))
        paned.add(left_frame, weight=1)
        paned.add(right_frame, weight=1)

        # --- Left side: scrollable list of script buttons ----------------
        left_canvas = tk.Canvas(left_frame, highlightthickness=0)
        left_scroll = ttk.Scrollbar(left_frame, orient="vertical",
                                    command=left_canvas.yview)
        scrollable_frame = tk.Frame(left_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        left_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scroll.set)

        self.create_parameter_entries(scrollable_frame)
        self.create_section_buttons(scrollable_frame)

        left_canvas.pack(side="left", fill="both", expand=True)
        left_scroll.pack(side="right", fill="y")

        self._bind_mousewheel(left_canvas)

        # --- Right side: scrollable container of ScriptPanels ------------
        right_canvas = tk.Canvas(right_frame, highlightthickness=0)
        right_scroll = ttk.Scrollbar(right_frame, orient="vertical",
                                     command=right_canvas.yview)
        self.panels_container = tk.Frame(right_canvas)
        self.panels_container.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )
        self._right_window_id = right_canvas.create_window(
            (0, 0), window=self.panels_container, anchor="nw")
        right_canvas.bind(
            "<Configure>",
            lambda e: right_canvas.itemconfigure(self._right_window_id,
                                                 width=e.width))
        right_canvas.configure(yscrollcommand=right_scroll.set)
        right_canvas.pack(side="left", fill="both", expand=True)
        right_scroll.pack(side="right", fill="y")

        self._bind_mousewheel(right_canvas)

        # Begin draining queues from worker processes
        self.root.after(self.POLL_INTERVAL_MS, self._poll_panels)

    @staticmethod
    def _bind_mousewheel(canvas: tk.Canvas) -> None:
        """Cross-platform mousewheel scrolling.

        Linux sends Button-4 / Button-5; Windows + macOS send <MouseWheel>
        with event.delta. bind_all is necessary because the canvas's child
        widgets (the buttons / labels packed inside) eat the event before it
        reaches the canvas. We swap bindings on Enter/Leave so each canvas
        only scrolls when the cursor is over it.
        """
        def _on_wheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _enter(_e):
            canvas.bind_all("<MouseWheel>", _on_wheel)
            canvas.bind_all("<Button-4>", _on_wheel)
            canvas.bind_all("<Button-5>", _on_wheel)

        def _leave(_e):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _enter)
        canvas.bind("<Leave>", _leave)

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
        """Spawn a worker process running the script and attach a panel for
        its console output."""
        func = script_info["func"]
        params = script_info["params"]

        args = []
        for param in params:
            entry = self.param_entries.get(param)
            if entry is None:
                messagebox.showerror("Error", f"Parameter entry for {param} not found.")
                return
            value = entry.get().strip()
            if not value:
                messagebox.showwarning("Warning", f"Please enter a value for {param}.")
                return
            args.append(value)

        module_name = func.__module__
        func_name = func.__name__

        q: mp.Queue = self.mp_ctx.Queue()
        in_q: mp.Queue = self.mp_ctx.Queue()
        process = self.mp_ctx.Process(
            target=_run_script_worker,
            args=(module_name, func_name, args, q, in_q),
            daemon=True,
        )
        process.start()

        panel = ScriptPanel(self.panels_container, script_name,
                            process=process, q=q, in_q=in_q,
                            on_close=self._remove_panel)
        panel.append("sys", f"[Started PID {process.pid}: "
                            f"{module_name}.{func_name}({', '.join(args)})]\n")
        self.panels.append(panel)

    def _poll_panels(self):
        """Drain each panel's queue and update its status."""
        for panel in list(self.panels):
            try:
                while True:
                    tag, payload = panel.q.get_nowait()
                    if tag == 'done_ok':
                        panel.mark_finished(payload)
                        messagebox.showinfo(
                            "Success",
                            f"{panel.script_name} {payload}!")
                    elif tag == 'done_err':
                        panel.mark_finished(payload)
                        messagebox.showerror(
                            "Error",
                            f"{panel.script_name} {payload}")
                    elif tag == 'done_exit':
                        panel.mark_finished(payload)
                    elif tag == 'input':
                        panel.request_input()
                    else:
                        panel.append(tag, payload)
            except queue.Empty:
                pass
            except (EOFError, OSError):
                pass

            if not panel.process.is_alive() and not panel._finished:
                # Process died without sending a 'done' (e.g. killed).
                code = panel.process.exitcode
                panel.mark_finished(f"exited (code {code})")

        self.root.after(self.POLL_INTERVAL_MS, self._poll_panels)

    def _remove_panel(self, panel: ScriptPanel):
        if panel in self.panels:
            self.panels.remove(panel)

    def _on_root_close(self):
        for panel in list(self.panels):
            if panel.process.is_alive():
                panel.process.terminate()
        for panel in list(self.panels):
            panel.process.join(timeout=0.5)
            if panel.process.is_alive():
                panel.process.kill()
        self.root.destroy()


if __name__ == "__main__":
    mp.freeze_support()
    root = tk.Tk()
    root.geometry("1200x800")
    app = ScriptRunnerApp(root)
    root.mainloop()
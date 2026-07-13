import os
import tkinter as tk
from tkinter import ttk

import pandas as pd
from PIL import Image, ImageOps, ImageTk

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.response_spec import ResponseSpec
from src.pga.stim_types import StimType
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from clat.util.connection import Connection


def main():
    channel = "GA"  # "GA", "Cluster", a single channel name, or a list of channel names
    data_type = "GA" if channel == "GA" else "mua"
    analysis = PlotVariants(save_included_variants=False, data_type=data_type)
    compiled_data = None
    # compiled_data = analysis.compile_and_export()
    session_id,_ = read_session_id_and_date_from_db_name(context.ga_database)

    analysis.run(session_id, channel=channel, compiled_data=compiled_data)


class PlotVariants(PlotTopNAnalysis):
    threshold = 0.75

    def __init__(self, save_included_variants=False, **kwargs):
        super().__init__(**kwargs)
        self.save_included_variants = save_included_variants

    def analyze(self, channel, compiled_data=None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        spec = ResponseSpec(channel, use_baseline_correction=self.use_baseline_correction)
        try:
            prepared = spec.apply(compiled_data, spike_rates_col=self.spike_rates_col)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        compiled_data = prepared.data
        response_col = prepared.response_col

        # Collapse to one row per stimulus: mean response plus the descriptive
        # columns we need for layout and labelling. compiled_data has one row
        # per presentation, so a stimulus can appear multiple times.
        stim_summary = (
            compiled_data
            .groupby('StimSpecId', as_index=False)
            .agg({
                response_col: 'mean',
                'GenId': 'first',
                'Lineage': 'first',
                'ParentId': 'first',
                'StimType': 'first',
                'ThumbnailPath': 'first',
            })
        )

        # The variants whose production history we want to trace, one row each.
        variants = self.filter_for_variants(stim_summary).copy()
        variants = variants[variants['ParentId'].notna()]
        if variants.empty:
            print("No variants found to plot")
            return

        # One plot row per parent that produced variants. Within a row the
        # columns run left-to-right by generation (chronological) and, within a
        # generation, by response (highest first, then decreasing).
        variants = variants.sort_values(
            ['ParentId', 'GenId', response_col],
            ascending=[True, True, False],
            kind='stable',
        )
        variants['ColIndex'] = variants.groupby('ParentId').cumcount() + 1
        variants['ParentGroup'] = variants['ParentId']
        variants['RowType'] = 'Variant'

        # The left-most column (ColIndex 0) of each row is the parent's own
        # image. Only parents that actually produced variants get a row.
        parent_ids = variants['ParentId'].unique()
        parents = stim_summary[stim_summary['StimSpecId'].isin(parent_ids)].copy()
        parents['ColIndex'] = 0
        parents['ParentGroup'] = parents['StimSpecId']
        parents['RowType'] = 'Parent'

        plot_data = pd.concat([parents, variants], ignore_index=True)
        print(f"Plotting {len(parents)} parents and {len(variants)} variants "
              f"across {plot_data['ParentGroup'].nunique()} rows")

        # Hypothesized components (shown in the labels) live in their own table.
        hypo_map = self._load_hypothesized_comps(
            plot_data['StimSpecId'].dropna().unique())

        # Render in a scrollable native window (Tkinter canvas) rather than a
        # giant rasterized image: scrolling just moves the viewport, so it stays
        # responsive with thousands of stimuli.
        title = (f"{prepared.channel_label}{prepared.baseline_suffix} "
                 f"- variant history by parent")
        self._show_variant_history(plot_data, response_col, hypo_map, title)

        if self.save_included_variants:
            self._save_included_variants_to_db(compiled_data, response_col)

    def filter_for_variants(self, compiled_data):
        variants_data = compiled_data[
            compiled_data['StimType'].isin([StimType.REGIME_ESTIM_VARIANTS.value])]
        return variants_data

    def _load_hypothesized_comps(self, stim_ids):
        """Return ``{stim_id: "<parent hypothesized comp text>"}`` for the given stims.

        Reads the *parent* hypothesized comp(s) - i.e. which of the parent's
        components this stim preserved, in the parent's numbering
        (``parent_hypothesized_comps``) - not the stim's own comps in its own
        numbering (``hypothesized_comp``). Read from the HypothesizedComp table
        (older DBs call it StimCompsToPreserve, with column
        ``parent_comps_preserved``). Stims without a row are simply omitted.
        """
        result: dict[int, str] = {}
        try:
            conn = Connection(context.ga_database)
            conn.execute("SHOW TABLES LIKE 'HypothesizedComp'")
            if conn.fetch_one():
                table, col = "HypothesizedComp", "parent_hypothesized_comps"
            else:
                table, col = "StimCompsToPreserve", "parent_comps_preserved"
            for sid in stim_ids:
                conn.execute(
                    f"SELECT {col} FROM {table} WHERE stim_id = %s",
                    (int(sid),))
                row = conn.fetch_one()
                if row is None:
                    continue
                value = row[0] if isinstance(row, (list, tuple)) else row
                text = str(value).strip() if value is not None else ""
                if text:
                    result[int(sid)] = text
        except Exception as exc:
            print(f"Could not read hypothesized comps: {exc}")
        return result

    def _show_variant_history(self, plot_data, response_col, hypo_map, title):
        """Show the per-parent variant history in a scrollable Tkinter window.

        Each row is one parent (leftmost cell = the parent's own image);
        remaining cells are its variants, already ordered by generation then
        response. Thumbnails are drawn as canvas image items, so scrolling just
        moves the viewport (fast even with thousands of stimuli) rather than
        re-rasterizing everything the way matplotlib does. Ctrl+wheel re-renders
        at a larger/smaller thumbnail size. Labels sit *below* each thumbnail so
        they never cover the shape, and include gen id, stim id, response and
        hypothesized comp.
        """
        resp = pd.to_numeric(plot_data[response_col], errors='coerce')
        vmin = float(resp.min()) if resp.notna().any() else 0.0
        vmax = float(resp.max()) if resp.notna().any() else 1.0

        row_values = sorted(plot_data['ParentGroup'].unique())
        row_pos = {p: i for i, p in enumerate(row_values)}

        # Per-stimulus arrays for fast iteration during render.
        records = list(zip(
            plot_data['ParentGroup'].tolist(),
            plot_data['ColIndex'].tolist(),
            plot_data['ThumbnailPath'].tolist(),
            resp.tolist(),
            plot_data['GenId'].tolist(),
            plot_data['StimSpecId'].tolist(),
        ))

        root = tk.Tk()
        root.title(title)
        root.geometry("1500x850")

        status = tk.StringVar(value="scroll: wheel / shift+wheel   |   zoom: ctrl+wheel or +/-")
        tk.Label(root, textvariable=status, anchor="w", fg="gray").pack(
            side="bottom", fill="x", padx=8)

        canvas = tk.Canvas(root, background="white")
        v_scroll = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        h_scroll = ttk.Scrollbar(root, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)

        # thumb = image side incl. border, in px; the only thing zoom changes.
        state = {"thumb": 150}
        src_cache: dict[str, object] = {}   # path -> full-res PIL RGB (or None)
        photo_cache: dict[tuple, ImageTk.PhotoImage] = {}  # keep refs alive

        def border_hex(v):
            if vmax > vmin and v == v:  # v == v is False for NaN
                t = max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
            else:
                t = 0.5
            return f"#{int(255 * t):02x}0000"

        def get_photo(path, v, thumb):
            key = (path, thumb, border_hex(v))
            cached = photo_cache.get(key)
            if cached is not None:
                return cached
            src = src_cache.get(path, False)
            if src is False:
                try:
                    with Image.open(path) as im:
                        src = im.convert("RGB")
                except Exception:
                    src = None
                src_cache[path] = src
            if src is None:
                return None
            bw = max(2, int(thumb * 0.08))
            inner = max(1, thumb - 2 * bw)
            img = ImageOps.expand(src.resize((inner, inner), Image.LANCZOS),
                                  border=bw, fill=border_hex(v))
            photo = ImageTk.PhotoImage(img)
            photo_cache[key] = photo
            return photo

        def render():
            canvas.delete("all")
            photo_cache.clear()  # drop stale-size photos so memory doesn't grow
            thumb = state["thumb"]
            # Fonts scale with the thumbnail so labels stay readable at any zoom.
            font_size = max(9, thumb // 10)
            line_h = font_size + 4
            label_h = 4 * line_h + 6  # up to 4 label lines under each thumbnail
            cell_w = thumb + max(40, thumb // 4)  # horizontal gap between columns
            cell_h = thumb + label_h
            label_font = ("Arial", font_size)
            parent_font = ("Arial", max(11, thumb // 8), "bold")
            gutter = max(120, thumb)  # left strip for the "parent N" labels
            for parent_group, col, path, v, gen, sid in records:
                i = row_pos[parent_group]
                x = gutter + int(col) * cell_w
                y = 10 + i * cell_h
                photo = get_photo(path, v, thumb)
                if photo is not None:
                    canvas.create_image(x + thumb / 2, y + thumb / 2,
                                        image=photo, anchor="center")
                else:
                    canvas.create_rectangle(x, y, x + thumb, y + thumb,
                                            outline="gray", dash=(2, 2))
                    canvas.create_text(x + thumb / 2, y + thumb / 2,
                                       text="(no image)", fill="gray", font=label_font)
                # Generation on its own line, then stim id, response, and
                # (when present) hypothesized comp.
                lines = [f"gen {int(gen)}" if pd.notna(gen) else "gen ?"]
                if pd.notna(sid):
                    lines.append(f"#{int(sid)}")
                lines.append(f"r={v:.0f}" if v == v else "r=NA")
                hc = hypo_map.get(int(sid)) if pd.notna(sid) else None
                if hc:
                    lines.append(f"hc={hc}")
                canvas.create_text(x + thumb / 2, y + thumb + 2, anchor="n",
                                   text="\n".join(lines), font=label_font,
                                   justify="center")
            # Parent id labels down the left gutter.
            for parent_group, i in row_pos.items():
                y = 10 + i * cell_h
                canvas.create_text(gutter - 10, y + thumb / 2, anchor="e",
                                   text=f"parent\n{int(parent_group)}",
                                   font=parent_font, justify="right")
            canvas.configure(scrollregion=canvas.bbox("all"))
            status.set(f"{len(records)} stimuli, {len(row_pos)} parents   |   "
                       f"thumb {thumb}px   |   scroll: wheel / shift+wheel   "
                       f"|   zoom: ctrl+wheel or +/-")

        def zoom(factor):
            new = int(state["thumb"] * factor)
            new = max(40, min(600, new))
            if new != state["thumb"]:
                state["thumb"] = new
                status.set("rendering...")
                root.update_idletasks()
                render()

        # Wheel handling (Windows/macOS send <MouseWheel>; X11 sends Button-4/5).
        def _wheel_dir(event):
            if getattr(event, "num", None) == 4:
                return 1
            if getattr(event, "num", None) == 5:
                return -1
            return 1 if event.delta > 0 else -1

        def on_wheel(event):
            canvas.yview_scroll(-_wheel_dir(event), "units")

        def on_shift_wheel(event):
            canvas.xview_scroll(-_wheel_dir(event), "units")

        def on_ctrl_wheel(event):
            zoom(1.25 if _wheel_dir(event) > 0 else 1 / 1.25)

        canvas.bind_all("<MouseWheel>", on_wheel)
        canvas.bind_all("<Shift-MouseWheel>", on_shift_wheel)
        canvas.bind_all("<Control-MouseWheel>", on_ctrl_wheel)
        canvas.bind_all("<Button-4>", on_wheel)
        canvas.bind_all("<Button-5>", on_wheel)
        canvas.bind_all("<Shift-Button-4>", on_shift_wheel)
        canvas.bind_all("<Shift-Button-5>", on_shift_wheel)
        canvas.bind_all("<Control-Button-4>", on_ctrl_wheel)
        canvas.bind_all("<Control-Button-5>", on_ctrl_wheel)
        root.bind("<plus>", lambda _e: zoom(1.25))
        root.bind("<KP_Add>", lambda _e: zoom(1.25))
        root.bind("<minus>", lambda _e: zoom(1 / 1.25))
        root.bind("<KP_Subtract>", lambda _e: zoom(1 / 1.25))

        render()

        # Closing a window holding thousands of PhotoImages triggers a very slow
        # synchronous teardown (Tk destroys every item, then the interpreter GCs
        # every cached image). This viewer's process has nothing else to do, so
        # skip the graceful teardown and let the OS reclaim everything at once.
        root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))
        root.mainloop()

    def _save_included_variants_to_db(self, compiled_data, response_col):
        """Save included variants to the GA database."""
        try:
            conn = Connection(context.ga_database)

            # Manual exclusions
            manual_exclusions = []

            # Create table
            create_table_sql = """
                               CREATE TABLE IF NOT EXISTS IncludedVariants \
                               ( \
                                   stim_id           BIGINT PRIMARY KEY, \
                                   response          DOUBLE, \
                                   threshold_used    DOUBLE, \
                                   manually_excluded BOOLEAN   DEFAULT FALSE, \
                                   exclusion_reason  VARCHAR(255), \
                                   date_added        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                               ) \
                               """
            conn.execute(create_table_sql)
            print("\n=== DATABASE SAVING ===")
            print("Ensured IncludedVariants table exists")

            # Clear existing
            conn.execute("DELETE FROM IncludedVariants")
            print("Cleared existing IncludedVariants entries")

            # Filter for variants
            variants = self.filter_for_variants(compiled_data)

            if variants.empty:
                print("No variants found to save")
                return

            # Group by StimSpecId and get mean response (deduplicate)
            variants_grouped = variants.groupby('StimSpecId')[response_col].mean().reset_index()

            # Calculate threshold (60% of max)
            max_response = variants_grouped[response_col].max()
            threshold = self.threshold * max_response
            print(f"Max response: {max_response:.2f}, Threshold (60%): {threshold:.2f}")

            # Filter by threshold
            included = variants_grouped[variants_grouped[response_col] >= threshold]

            print(f"Found {len(included)} variants above threshold")

            # Insert
            insert_sql = """
                         INSERT INTO IncludedVariants
                         (stim_id, response, threshold_used, manually_excluded, exclusion_reason)
                         VALUES (%s, %s, %s, %s, %s) \
                         """

            for _, row in included.iterrows():
                stim_id = int(row['StimSpecId'])
                excluded = stim_id in manual_exclusions
                exclusion_reason = "Manually excluded via analysis script" if excluded else None

                conn.execute(insert_sql, (
                    stim_id,
                    float(row[response_col]),
                    threshold,
                    excluded,
                    exclusion_reason
                ))

            print(f"Saved {len(included)} variants to IncludedVariants table")

            excluded_count = sum(1 for _, row in included.iterrows()
                                 if int(row['StimSpecId']) in manual_exclusions)
            if excluded_count > 0:
                print(f"Marked {excluded_count} variants as manually excluded")

        except Exception as e:
            print(f"Warning: Could not save to database: {e}")


if __name__ == "__main__":
    main()
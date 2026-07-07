import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from PIL import Image, ImageOps

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.response_spec import ResponseSpec
from src.pga.stim_types import StimType
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from clat.util.connection import Connection


def main():
    channel = "GA"  # "GA", "Cluster", a single channel name, or a list of channel names
    analysis = PlotVariants(save_included_variants=False)
    compiled_data = None
    # compiled_data = analysis.compile_and_export()
    session_id = "260512_0"
    data_type = "GA" if channel == "GA" else "raw"
    analysis.run(session_id, data_type, channel, compiled_data=compiled_data)


class PlotVariants(PlotTopNAnalysis):
    threshold = 0.75

    def __init__(self, save_included_variants=False, use_baseline_correction=False):
        super().__init__(use_baseline_correction=use_baseline_correction)
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

        # Render as a native, interactive matplotlib window rather than a giant
        # rasterized image: pan, box-zoom (toolbar) and scroll-to-zoom all work,
        # and because thumbnails sit in data coordinates, zooming magnifies them.
        title = (f"{prepared.channel_label}{prepared.baseline_suffix} "
                 f"- variant history by parent")
        self._show_variant_history(plot_data, response_col, hypo_map, title)

        if self.save_included_variants:
            self._save_included_variants_to_db(compiled_data, response_col)

    def filter_for_variants(self, compiled_data):
        variants_data = compiled_data[
            compiled_data['StimType'].isin([StimType.REGIME_ESTIM_VARIANTS.value, StimType.REGIME_ESTIM_DELTA.value])]
        return variants_data

    def _load_hypothesized_comps(self, stim_ids):
        """Return ``{stim_id: "<hypothesized_comp text>"}`` for the given stims.

        Read from the HypothesizedComp table (older DBs still call it
        StimCompsToPreserve). Stims without a row are simply omitted.
        """
        result: dict[int, str] = {}
        try:
            conn = Connection(context.ga_database)
            conn.execute("SHOW TABLES LIKE 'HypothesizedComp'")
            table = "HypothesizedComp" if conn.fetch_one() else "StimCompsToPreserve"
            for sid in stim_ids:
                conn.execute(
                    f"SELECT hypothesized_comp FROM {table} WHERE stim_id = %s",
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

    @staticmethod
    def _use_interactive_backend():
        """Switch to a real GUI window backend when stuck on a non-interactive one.

        PyCharm intercepts plots into SciView (``module://backend_interagg``),
        which draws the whole figure as a single downscaled bitmap - blurry and
        not zoomable. A native Tk/Qt window renders crisply and supports
        pan/zoom. No-op if we're already on an interactive GUI backend (or none
        is available). You can also just untick PyCharm's Settings > Tools >
        Python Plots > "Show plots in tool window".
        """
        import matplotlib
        current = matplotlib.get_backend().lower()
        needs_switch = ('interagg' in current or 'inline' in current
                        or current == 'agg')
        if not needs_switch:
            return
        for backend in ("TkAgg", "QtAgg", "Qt5Agg", "MacOSX"):
            try:
                plt.switch_backend(backend)
                print(f"Switched matplotlib backend to {backend} "
                      f"for an interactive window.")
                return
            except Exception:
                continue
        print("Could not find an interactive matplotlib backend; "
              "the plot may render in PyCharm's SciView.")

    def _show_variant_history(self, plot_data, response_col, hypo_map, title):
        """Draw the per-parent variant history as an interactive matplotlib window.

        Each row is one parent (leftmost cell = the parent's own image at
        ColIndex 0); the remaining cells are its variants, already ordered by
        generation then response. Thumbnails are placed in data coordinates so
        the toolbar/scroll zoom magnifies them, and each label sits *below* its
        thumbnail so it never covers the shape.
        """
        # Get out of PyCharm's SciView (which renders one blurry static bitmap)
        # into a real, crisp, zoomable GUI window.
        self._use_interactive_backend()

        row_values = sorted(plot_data['ParentGroup'].unique())
        row_pos = {p: i for i, p in enumerate(row_values)}
        n_rows = len(row_values)
        max_col = int(plot_data['ColIndex'].max())

        resp = pd.to_numeric(plot_data[response_col], errors='coerce').to_numpy()
        has_resp = np.isfinite(resp).any()
        vmin = float(np.nanmin(resp)) if has_resp else 0.0
        vmax = float(np.nanmax(resp)) if has_resp else 1.0

        # Cell geometry (data units). Rows are pitched wider than the image so
        # the gap underneath holds the label without touching the next row.
        row_pitch = 1.45
        img_w, img_h = 0.9, 1.0
        # Render thumbnails at a high resolution so zooming in stays crisp.
        thumb_px, border_px = 300, 30

        groups = plot_data['ParentGroup'].to_numpy()
        cols = plot_data['ColIndex'].to_numpy()
        paths = plot_data['ThumbnailPath'].to_numpy()
        gens = plot_data['GenId'].to_numpy()
        sids = plot_data['StimSpecId'].to_numpy()

        fig_w = min(3 + max_col * 1.1, 55)
        fig_h = min(2 + n_rows * 1.3, 90)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=11)

        def border_rgb(v):
            if vmax > vmin and np.isfinite(v):
                t = max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
            else:
                t = 0.5
            return (int(255 * t), 0, 0)

        img_cache: dict[str, object] = {}
        for k in range(len(plot_data)):
            j = int(cols[k])
            i = row_pos[groups[k]]
            top = -(i * row_pitch)
            bottom = top - img_h
            x0 = j + (1 - img_w) / 2
            x1 = x0 + img_w
            v = float(resp[k])

            path = paths[k]
            if path not in img_cache:
                try:
                    with Image.open(path) as im:
                        img_cache[path] = im.convert('RGB').resize(
                            (thumb_px, thumb_px), Image.LANCZOS)
                except Exception:
                    img_cache[path] = None
            img = img_cache[path]
            if img is not None:
                bordered = ImageOps.expand(img, border=border_px, fill=border_rgb(v))
                ax.imshow(np.asarray(bordered),
                          extent=[x0, x1, bottom, top], zorder=1)

            # Label below the thumbnail so it never overlaps the shape.
            sid = sids[k]
            gen = gens[k]
            header = []
            if not pd.isna(gen):
                header.append(f"g{int(gen)}")
            if not pd.isna(sid):
                header.append(f"#{int(sid)}")
            lines = [" ".join(header)]
            lines.append(f"r={v:.0f}" if np.isfinite(v) else "r=NA")
            hc = hypo_map.get(int(sid)) if not pd.isna(sid) else None
            if hc:
                lines.append(f"hc={hc}")
            ax.text((x0 + x1) / 2, bottom - 0.04, "\n".join(lines),
                    ha='center', va='top', fontsize=5, linespacing=1.05, zorder=3)

        # Parent id label at the far left of each row.
        for parent, i in row_pos.items():
            top = -(i * row_pitch)
            ax.text(-0.15, top - img_h / 2, f"parent\n{int(parent)}",
                    ha='right', va='center', fontsize=6, fontweight='bold')

        ax.set_xlim(-1.7, max_col + 1.2)
        ax.set_ylim(-((n_rows - 1) * row_pitch) - img_h - 0.7, 0.7)

        # Scroll wheel zooms centered on the cursor, on top of the toolbar's
        # pan and box-zoom.
        def on_scroll(event):
            if event.inaxes != ax or event.xdata is None:
                return
            base = 1.25
            scale = (1 / base) if event.button == 'up' else base
            x0l, x1l = ax.get_xlim()
            y0l, y1l = ax.get_ylim()
            xd, yd = event.xdata, event.ydata
            ax.set_xlim(xd - (xd - x0l) * scale, xd + (x1l - xd) * scale)
            ax.set_ylim(yd - (yd - y0l) * scale, yd + (y1l - yd) * scale)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect('scroll_event', on_scroll)
        plt.tight_layout()
        plt.show()

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
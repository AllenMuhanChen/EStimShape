"""
Probe analysis for one session, outside the explorer: every channel top -> bottom,
one column of coloured dots per per-channel quantity. Same columns and figure as the
explorer's "Probe analysis" module (src/analysis/ga/explorer/modules/).

Edit the settings at the top of main(), then run. The figure is shown and saved into
a new timestamped folder with a config.json of the settings.

Columns (see probe_columns.py for what each one is and which old script it replaces):
  Tuning        pref_freq, orient_freq, pref_orient, pref_color, iso, solid, solid_sig
  Correlation   corr_each (ρ vs each GA channel), corr_ga_avg (ρ vs GA average +
                contiguous extent at ρ threshold), corr_estim_avg (ρ vs estim average)
  Delta/top-N   corr_dv, corr_topn, dprime
  Models        rwa, axis
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.probe_analysis.probe_columns import COLUMNS, build_blocks
from src.analysis.probe_analysis.probe_data import ProbeData, parse_estim_spec
from src.analysis.probe_analysis.probe_figure import draw_probe_figure


def main():
    # ---------------------------------------------------------------- settings
    SESSION_ID = None            # e.g. "260702_0"; None = the session context.py points at
    # Columns to show (True = on). Order here is the order in the figure.
    SHOW = {
        'pref_freq': True,
        'orient_freq': True,
        'pref_orient': True,
        'pref_color': True,
        'iso': True,
        'solid': True,
        'solid_sig': True,
        'corr_each': True,
        'corr_ga_avg': False,
        'corr_estim_avg': False,
        'corr_dv': False,
        'corr_topn': False,
        'dprime': False,
        'rwa': False,
        'axis': False,
    }
    ESTIM_SPEC = "none"          # hatch estim channels: "none", "all", spec ids "3,5",
                                 # or channels "A-008, A-022"
    Y_LABELS = 'channel'         # 'channel', 'depth' (mm) or 'both'
    OPTIONS = dict(
        corr_reference='GA',     # 'GA' = every GA channel, or 'A-022, A-008'
        corr_method='spearman',  # 'spearman' or 'pearson'
        vector_type='ga_mean_response',
        group_leave_one_out=True,
        rho_threshold=0.5,       # ρ threshold for the GA-average extent
        n_misses_to_stop=2,
        top_n=20,
        included_only=True,
        axis_strategy='multi_prototype_pca',
        iso_frequencies=None,    # None = every tested frequency, or e.g. [12]
    )
    FONT_SIZE = 11
    SAVE_ROOT = "/home/connorlab/Documents/plots"   # <root>/<session>/probe_analysis/<time>/
    # -------------------------------------------------------------------------

    run_probe_analysis(SESSION_ID, [k for k, on in SHOW.items() if on],
                       estim_spec=ESTIM_SPEC, y_labels=Y_LABELS, options=OPTIONS,
                       font_size=FONT_SIZE, save_root=SAVE_ROOT)


def run_probe_analysis(session_id, column_keys, *, estim_spec="none", y_labels='channel',
                       options=None, font_size=11, save_root=None, show=True, data=None):
    """Build, show and save the probe figure. Returns (fig, blocks, out_dir); out_dir
    is None when nothing was saved. Pass ``data`` (a ProbeData) to reuse loaded data;
    the session context must then already be applied."""
    import matplotlib.pyplot as plt
    from src.startup import context
    from src.startup.apply_session_context import apply_session_context

    if session_id is None:
        from src.repository.export_to_repository import read_session_id_and_date_from_db_name
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    elif data is None:
        apply_session_context(session_id)
    unknown = [k for k in column_keys if k not in {c.key for c in COLUMNS}]
    if unknown:
        raise ValueError(f"Unknown column(s) {unknown}; see probe_columns.COLUMNS")

    data = data or ProbeData(session_id)
    estim, estim_label = [], ""
    if (estim_spec or "none").strip().lower() != "none":
        estim, estim_label = parse_estim_spec(estim_spec, data.estim_channels_by_spec())
    opts = dict(options or {}, estim_channels=estim)
    blocks, skipped = build_blocks(column_keys, data, opts)
    for label, why in skipped:
        print(f"{session_id}: {label} not shown: {why}")
    for b in blocks:
        if b.note:
            print(f"{session_id}: {b.note}")
    if not blocks:
        raise RuntimeError(f"{session_id}: none of the columns {column_keys} have data")

    title = session_id + (f"  (estim {estim_label})" if estim_label else "")
    fig = draw_probe_figure(blocks, data.channel_strs(), data.ga_channels(),
                            estim_channels=estim, title=title, y_labels=y_labels,
                            font_size=font_size, figure=lambda **kw: plt.figure(**kw))
    out_dir = None
    if save_root:
        out_dir = os.path.join(save_root, session_id, "probe_analysis",
                               datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(out_dir, exist_ok=False)
        with open(os.path.join(out_dir, "config.json"), "w") as f:
            json.dump({'session_id': session_id, 'columns': list(column_keys),
                       'estim_spec': estim_spec, 'estim_channels': estim,
                       'y_labels': y_labels, 'options': opts,
                       'not_shown': dict(skipped),
                       'notes': [b.note for b in blocks if b.note]},
                      f, indent=2, default=str)
        for ext in ('png', 'svg'):
            fig.savefig(os.path.join(out_dir, f"probe_analysis.{ext}"), dpi=200)
        print(f"Saved to {out_dir}")
    if show:
        plt.show()
    return fig, blocks, out_dir


if __name__ == "__main__":
    main()

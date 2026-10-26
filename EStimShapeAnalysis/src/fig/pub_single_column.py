"""
pub_single_column.py
--------------------
Publication figure: all channels top → bottom, coloured by one chosen column, with
depth along the probe on the y axis and the estim channels hatched.

Drawn by src/analysis/probe_analysis (the explorer's "Probe analysis" module has the
same columns as toggles, and its 'Y axis labels: depth' / 'EStim spec' settings give
the same figure).

Usage: edit the settings at the top of main(), then run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.analysis.probe_analysis.probe_analysis import run_probe_analysis


def main():
    # ---------------------------------------------------------------- settings
    SESSION_ID = "260426_0"
    SAVE_ROOT = "/home/connorlab/Documents/plots"   # <root>/<session>/probe_analysis/<time>/
    # The ONE column to show, e.g.
    #   'corr_each'  Spearman ρ vs REFERENCE_CHANNEL (GA mean response vectors)
    #   'solid'      solid preference index
    #   'iso'        isochromatic preference (set ISO_FREQUENCIES to pick one)
    #   'corr_dv'    z-scored ρ vs REFERENCE_CHANNEL on the delta/variant stims
    #   'corr_topn'  z-scored ρ vs REFERENCE_CHANNEL on the top-N GA stims
    COLUMN = 'corr_each'
    REFERENCE_CHANNEL = "A-022"
    ISO_FREQUENCIES = [12.0]
    TOP_N = 20
    ESTIM = "A-008, A-022"       # hatched: channels, estim spec ids ("3,5"), "all" or "none"
    FONT_SIZE = 12
    # -------------------------------------------------------------------------

    run_probe_analysis(SESSION_ID, [COLUMN], estim_spec=ESTIM, y_labels='depth',
                       options=dict(corr_reference=REFERENCE_CHANNEL,
                                    iso_frequencies=ISO_FREQUENCIES, top_n=TOP_N),
                       font_size=FONT_SIZE, save_root=SAVE_ROOT)


if __name__ == "__main__":
    main()

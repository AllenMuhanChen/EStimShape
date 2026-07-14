#!/usr/bin/env python3
"""Quick look at parts-based / prototype decompositions of the penetration
metrics — NMF and Archetypal Analysis (AA) — at a few component counts.

Unlike PCA/FA/ICA these produce *positive-only* components: instead of one
bipolar axis ("+ = brain, − = sulcus") you get one component per prototype
(ideally sulcus / WM / GM), and each depth bin's scores read as a soft
membership. This script fits them and dumps the interpretable outputs:

  * the loadings (which features define each component), printed + bar chart
  * the top / most-distinctive features per component
  * per-session depth profiles of each component score
  * a score-variance scree

It deliberately skips the MRI trajectory optimisation in run_per_session —
the point here is just to see whether the components line up with tissue
types. Once a recipe looks good, promote it to a TissuePipeline and run the
full pipeline via run_per_session / run_pooled.

Run:  python -m src.analysis.penetrations.explore_decompositions
"""
import os
from typing import Optional

import numpy as np

from clat.util.connection import Connection

from src.analysis.penetrations.pca_predict import (
    load_and_perform_pca,
    get_loadings_df,
)
from src.analysis.penetrations.penetration_plots import (
    PLOT_BASE_DIR,
    plot_loadings,
    plot_depth_profiles_overlaid,
    plot_scree,
)

# (method, n_components) recipes to fit and compare.
RECIPES = [
    ('nmf', 3),
    ('nmf', 4),
    ('aa', 3),
    ('aa', 4),
]


def _print_component_interpretation(loadings_df, top_n: int = 6) -> None:
    """For each component, print the features that define it — both the raw
    loading and its deviation from the cross-component mean (what makes this
    component *distinctive*, which is the more useful lens for AA archetypes)."""
    comps = list(loadings_df.columns)
    mean_across = loadings_df.mean(axis=1)
    for comp in comps:
        col = loadings_df[comp]
        distinctive = (col - mean_across).sort_values(ascending=False)
        print(f"\n  {comp}:")
        print(f"    highest loading      : "
              + ", ".join(f"{f}={col[f]:.2f}" for f in col.sort_values(ascending=False).index[:top_n]))
        print(f"    most distinctive (+) : "
              + ", ".join(f"{f}=+{distinctive[f]:.2f}" for f in distinctive.index[:top_n]))
        print(f"    most distinctive (−) : "
              + ", ".join(f"{f}={distinctive[f]:.2f}" for f in distinctive.index[-top_n:]))


def explore(
        conn: Connection,
        table_name: str = "PenetrationMetrics",
        exclude_sessions: Optional[list] = None,
        within_session_normalize: bool = True,
        pc_smooth_sigma: float = 2.0,
        exclude_features: Optional[list] = None,
) -> None:
    base = os.path.join(PLOT_BASE_DIR, "decomp_explore")
    os.makedirs(base, exist_ok=True)
    print(f"Plots → {base}")

    for method, k in RECIPES:
        tag = f"{method}_{k}"
        print("\n" + "=" * 70)
        print(f"{method.upper()}  |  n_components = {k}")
        print("=" * 70)

        df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(
            conn, table_name,
            exclude_sessions=exclude_sessions,
            within_session_normalize=within_session_normalize,
            pc_smooth_sigma=pc_smooth_sigma,
            n_components=k,
            decomp_method=method,
            use_varimax=False,
            exclude_features=exclude_features,
        )

        loadings_df = get_loadings_df(pca, feature_columns)
        print("\nLoadings (feature × component):")
        print(loadings_df.round(3))
        _print_component_interpretation(loadings_df)

        save_dir = os.path.join(base, tag)
        os.makedirs(save_dir, exist_ok=True)
        plot_scree(pca, save_dir=save_dir)
        plot_loadings(pca, feature_columns, n_pcs=k, save_dir=save_dir)
        plot_depth_profiles_overlaid(df, pca, n_pcs=k, save_dir=save_dir)
        print(f"\n  saved plots → {save_dir}")


if __name__ == "__main__":
    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )
    exclude_sessions = ["260331_0", "260402_0", "260520_0", "260423_0", "260611_0"]

    explore(
        conn,
        exclude_sessions=exclude_sessions,
        within_session_normalize=True,
        pc_smooth_sigma=2.0,
        exclude_features=None,
    )

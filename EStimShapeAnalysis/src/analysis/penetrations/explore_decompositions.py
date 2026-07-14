#!/usr/bin/env python3
"""Quick look at parts-based / prototype decompositions of the penetration
metrics — NMF and Archetypal Analysis (AA) — at a few component counts.

Unlike PCA/FA/ICA these produce *positive-only* components: instead of one
bipolar axis ("+ = brain, − = sulcus") you get one component per prototype
(ideally sulcus / WM / GM), and each depth bin's scores read as a soft
membership. This script fits them and dumps the interpretable outputs with
fully labelled, self-explanatory plots (the shared PCA plotters are
deliberately NOT reused — their "PC1 (14.1%)" titles are wrong for NMF/AA).

For each (method, K) it writes three figures, each with a title + a "how to
read" caption:

  loadings.png        — what each component IS (its feature signature)
  depth_profiles.png  — where each component turns on along depth, per session
  component_spread.png — how much each component varies (a rough importance)

plus a printed table of the most-distinctive features per component.

It skips the MRI trajectory optimisation in run_per_session — the point is
just to see whether the components line up with tissue types. Once a recipe
looks good, promote it to a TissuePipeline and run the full pipeline.

Run:  python -m src.analysis.penetrations.explore_decompositions
"""
import os
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt

from clat.util.connection import Connection

from src.analysis.penetrations.pca_predict import (
    load_and_perform_pca,
    get_loadings_df,
)
from src.analysis.penetrations.penetration_plots import (
    PLOT_BASE_DIR,
    _save_fig,
    _setup_depth_yaxis,
)

# (method, n_components) recipes to fit and compare.
RECIPES = [
    ('nmf', 3),
    ('nmf', 4),
    ('aa', 3),
    ('aa', 4),
]

_METHOD_NAME = {'nmf': 'NMF', 'aa': 'Archetypal Analysis'}

# What a "component", its loadings, and its scores MEAN for each method — shown
# as the "how to read" caption so the figures are self-explanatory.
_HOWTO = {
    'nmf': {
        'component': 'additive part',
        'loadings': ("Loadings = feature weights, all ≥ 0. A depth bin is a weighted "
                     "SUM of these parts. A tall bar = a feature that switches this "
                     "component ON."),
        'score':    ("Score = how strongly this part is present at each depth (≥ 0). "
                     "A tissue-type part should be HIGH over that tissue and ~0 elsewhere."),
        'loading_x': 'feature weight (≥ 0)',
    },
    'aa': {
        'component': 'archetype (extreme prototype)',
        'loadings': ("Loadings = the archetype's own feature profile — what a 'pure' "
                     "example of this prototype looks like (scaled 0–1). A depth bin is "
                     "a convex MIX of the archetypes."),
        'score':    ("Score = membership weight for this archetype at each depth (0–1, "
                     "the K scores at a depth sum to 1). ~1 = a pure example of this "
                     "prototype; a boundary bin splits its weight between two archetypes."),
        'loading_x': 'archetype value (scaled 0–1)',
    },
}


def _component_label(method: str, i: int) -> str:
    return f"{'Archetype' if method == 'aa' else 'NMF part'} {i + 1}"


def _print_component_interpretation(loadings_df, method, top_n: int = 6) -> None:
    """For each component, print the features that define it — both the raw
    loading and its deviation from the cross-component mean (what makes this
    component *distinctive*, the more useful lens for AA archetypes)."""
    comps = list(loadings_df.columns)
    mean_across = loadings_df.mean(axis=1)
    for i, comp in enumerate(comps):
        col = loadings_df[comp]
        distinctive = (col - mean_across).sort_values(ascending=False)
        print(f"\n  {_component_label(method, i)} ({comp}):")
        print(f"    highest loading      : "
              + ", ".join(f"{f}={col[f]:.2f}" for f in col.sort_values(ascending=False).index[:top_n]))
        print(f"    most distinctive (+) : "
              + ", ".join(f"{f}=+{distinctive[f]:.2f}" for f in distinctive.index[:top_n]))
        print(f"    most distinctive (−) : "
              + ", ".join(f"{f}={distinctive[f]:.2f}" for f in distinctive.index[-top_n:]))


def _plot_loadings(pca, feature_columns, method, k, save_dir):
    howto = _HOWTO[method]
    share = pca.explained_variance_ratio_ * 100
    n_features = len(feature_columns)
    fig, axes = plt.subplots(1, k, figsize=(4 * k, 6), sharey=True)
    if k == 1:
        axes = [axes]
    y = np.arange(n_features)
    for i, ax in enumerate(axes):
        load = pca.components_[i]
        top_feat = feature_columns[int(np.argmax(load))]
        ax.barh(y, load, color='steelblue', alpha=0.8)
        ax.set_yticks(y)
        if i == 0:
            ax.set_yticklabels(feature_columns, fontsize=8)
        ax.set_title(f"{_component_label(method, i)}\n"
                     f"(score spread {share[i]:.0f}% · top: {top_feat})", fontsize=9)
        ax.set_xlabel(howto['loading_x'], fontsize=8)
        ax.grid(True, alpha=0.3, axis='x')
    fig.suptitle(f"{_METHOD_NAME[method]}  (K={k})  —  what each {howto['component']} IS",
                 fontsize=13)
    fig.text(0.5, 0.005, "How to read:  " + howto['loadings'],
             ha='center', va='bottom', fontsize=8, wrap=True)
    plt.tight_layout(rect=[0, 0.06, 1, 0.97])
    _save_fig(save_dir, 'loadings.png')
    plt.show()


def _plot_depth_profiles(df, method, k, save_dir):
    howto = _HOWTO[method]
    sessions = list(df['session_id'].unique())
    n = len(sessions)
    cmap = plt.cm.tab10 if n <= 10 else (plt.cm.tab20 if n <= 20 else plt.cm.viridis)
    colors = dict(zip(sessions, cmap(np.linspace(0, 1, n))))
    all_depths = df['depth_under_chamber_mm'].values
    lo, hi = all_depths.min(), all_depths.max()

    fig, axes = plt.subplots(1, k, figsize=(4.5 * k, 6), sharey=True)
    if k == 1:
        axes = [axes]
    for i, ax in enumerate(axes):
        pc_col = f'PC{i + 1}'
        for s in sessions:
            sd = df[df['session_id'] == s].sort_values('depth_under_chamber_mm')
            if len(sd):
                ax.plot(sd[pc_col].values, sd['depth_under_chamber_mm'].values,
                        'o-', color=colors[s], lw=1.3, ms=3, alpha=0.7, label=s)
        ax.set_title(_component_label(method, i), fontsize=10)
        ax.set_xlabel("score (activation)" if method == 'nmf' else "membership (0–1)",
                      fontsize=8)
        if i == 0:
            ax.set_ylabel("Depth under chamber (mm)")
        ax.set_ylim(hi + 0.5, lo - 0.5)   # shallow at top, deep at bottom
        _setup_depth_yaxis(ax, all_depths)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='center right',
               bbox_to_anchor=(1.08, 0.5), fontsize=7, title='session')
    fig.suptitle(f"{_METHOD_NAME[method]}  (K={k})  —  where each "
                 f"{howto['component']} turns on along depth", fontsize=13)
    fig.text(0.5, 0.005, "How to read:  " + howto['score'] + "  Each line is one penetration.",
             ha='center', va='bottom', fontsize=8, wrap=True)
    plt.tight_layout(rect=[0, 0.06, 0.93, 0.97])
    _save_fig(save_dir, 'depth_profiles.png')
    plt.show()


def _plot_component_spread(pca, method, k, save_dir):
    share = pca.explained_variance_ratio_ * 100
    labels = [_component_label(method, i) for i in range(k)]
    fig, ax = plt.subplots(figsize=(1.6 * k + 2, 4.5))
    ax.bar(labels, share, color='slategray', alpha=0.85)
    ax.set_ylabel("share of total score variance (%)")
    ax.set_title(f"{_METHOD_NAME[method]}  (K={k})  —  component score spread")
    ax.tick_params(axis='x', rotation=20, labelsize=8)
    fig.text(0.5, 0.005,
             "How to read:  a rough 'which component carries the most signal' — NOT "
             "explained variance. NMF/AA are not variance-ranked, so ordering is only "
             "indicative.", ha='center', va='bottom', fontsize=8, wrap=True)
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    _save_fig(save_dir, 'component_spread.png')
    plt.show()


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
        print(f"{_METHOD_NAME[method]}  |  K = {k}")
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
        _print_component_interpretation(loadings_df, method)

        save_dir = os.path.join(base, tag)
        os.makedirs(save_dir, exist_ok=True)
        _plot_loadings(pca, feature_columns, method, k, save_dir)
        _plot_depth_profiles(df, method, k, save_dir)
        _plot_component_spread(pca, method, k, save_dir)
        print(f"\n  saved → {save_dir}")
        print(f"    loadings.png         — what each {_HOWTO[method]['component']} is")
        print(f"    depth_profiles.png   — where each turns on along depth (per session)")
        print(f"    component_spread.png — rough per-component signal size")


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

#!/usr/bin/env python3
"""Post-hoc *relational* analysis of a fitted decomposition (default: AA, K=7).

`explore_decompositions.py` fits the archetypes and shows what each one IS and
where it turns on. This script asks the next question — how the archetypes
relate to each other in space — WITHOUT using any hand-assigned tissue labels,
so it can independently confirm or contradict a guess like "PC2 & PC7 are both
WM" or "these three PCs are the GM layers".

Two complementary analyses, both on the *fractional* archetype scores (never the
argmax "winning tissue"):

  1. ADJACENCY — "who borders whom" along depth.
     Cortex is layered, so tissue types form a chain: superficial ↔ layer IV ↔
     deep ↔ WM. If an archetype is a cortical layer it should sit next to the
     same neighbours across penetrations. We measure, order-agnostically (a
     probe may enter from either end), which archetypes abut each other MORE
     than chance, then seriate the archetypes into the 1D order their adjacency
     implies — that ordering is the candidate layer sequence.
     Robust to tangential penetrations: a probe stuck in 1–2 layers only ever
     contributes to those pairs and cannot fabricate a chain.

  2. CO-OCCURRENCE — "who stacks on whom" at the same depth.
     Two archetypes that are really the SAME tissue (e.g. two WM prototypes)
     rise and fall together within the same depth bins. Because AA scores are
     compositional (they sum to 1, forcing a spurious negative correlation) we
     use a centred-log-ratio (CLR) transform + proportionality, plus an
     independent line of evidence — how similar the two archetypes' feature
     signatures are. Archetypes that agree on both are candidate "same tissue".

Writes captioned, self-explanatory figures to
  PLOT_BASE_DIR/decomp_neighbors/<method>_<k>/

Run:  python -m src.analysis.penetrations.neighbor_correlations
"""
import os
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from scipy.cluster.hierarchy import linkage, dendrogram, optimal_leaf_ordering
from scipy.spatial.distance import squareform

from clat.util.connection import Connection

from src.analysis.penetrations.pca_predict import (
    load_and_perform_pca,
    get_loadings_df,
)
from src.analysis.penetrations.penetration_plots import PLOT_BASE_DIR, _save_fig

# Which fitted decomposition(s) to analyse. Keep this in sync with whatever
# recipe you're studying in explore_decompositions.py.
RECIPES = [('aa', 7)]

# Permutation-null resampling for the adjacency enrichment.
N_PERM = 2000
RNG = np.random.default_rng(0)

# Small pseudocount for the CLR transform (scores can be exactly 0 after the
# non-negativity clip); added then renormalised before taking logs.
CLR_EPS = 1e-3

_METHOD_NAME = {'nmf': 'NMF', 'aa': 'Archetypal Analysis', 'gmm': 'Gaussian Mixture'}


def _label(i: int) -> str:
    return f"A{i + 1}"          # neutral: Archetype i+1 == PC(i+1). No tissue guess.


# ---------------------------------------------------------------------------
# Shared: per-penetration fractional score matrix
# ---------------------------------------------------------------------------

def _score_matrix(sd, k):
    """(n_depth, k) non-negative fractional scores for one penetration, rows
    renormalised to sum to 1 and already sorted shallow→deep by the caller.

    Matches plot_penetration_composition: AA memberships sum to 1 in principle
    but per-PC depth smoothing perturbs the sum, so we renormalise per bin."""
    S = np.clip(np.column_stack([sd[f'PC{i + 1}'].values for i in range(k)]), 0, None)
    row = S.sum(axis=1, keepdims=True)
    row[row == 0] = 1.0
    return S / row


def _iter_penetrations(df, k, min_bins=2):
    """Yield (session_id, S) with S the depth-sorted fractional score matrix."""
    for s in df['session_id'].unique():
        sd = df[df['session_id'] == s].sort_values('depth_under_chamber_mm')
        if len(sd) < min_bins:
            continue
        yield s, _score_matrix(sd, k)


# ---------------------------------------------------------------------------
# ANALYSIS 1 — vertical adjacency ("who borders whom")
# ---------------------------------------------------------------------------

def _soft_adjacency(S):
    """Symmetric soft co-adjacency (k, k) from one depth-ordered sequence of
    fractional score vectors: Σ over consecutive bins of sᵢ⊗sᵢ₊₁ (+ transpose).
    Diagonal = same-archetype continuity; off-diagonal = between-archetype
    boundaries. Uses the full fractions, never an argmax."""
    if len(S) < 2:
        return np.zeros((S.shape[1], S.shape[1]))
    a = S[:-1].T @ S[1:]
    return a + a.T


def _argmax_blocks(S):
    """Contiguous runs of the same dominant (argmax) archetype, as a list of
    index arrays. Only used to define the *blocks* whose ORDER the null shuffles
    — the adjacency values themselves stay fractional."""
    dom = S.argmax(axis=1)
    blocks, start = [], 0
    for i in range(1, len(dom)):
        if dom[i] != dom[i - 1]:
            blocks.append(np.arange(start, i))
            start = i
    blocks.append(np.arange(start, len(dom)))
    return blocks


def _adjacency_for_order(S, blocks, order):
    """Soft adjacency after reconstituting the bin sequence with the blocks in
    `order`. Within-block adjacencies are unchanged (blocks stay intact); only
    which blocks abut is randomised — so the null isolates ordering, preserving
    layer thickness / smoothness."""
    seq = np.concatenate([blocks[b] for b in order])
    return _soft_adjacency(S[seq])


def adjacency_enrichment(df, k, n_perm=N_PERM):
    """Observed soft adjacency vs a block-order-permutation null, pooled over
    penetrations. Returns (obs, z, obs_offdiag_normalised).

    Null model: within each penetration, hold the multiset of argmax-defined
    blocks fixed and randomly permute their ORDER; recompute pooled adjacency;
    repeat n_perm times. z = (obs − mean_null) / std_null, computed per matrix
    cell. A positive off-diagonal z means archetypes a,b abut MORE than a random
    layer ordering would give — evidence they are genuine spatial neighbours.

    Why this null:
      * A probe that only spans 1–2 layers has ≤1 block boundary; permuting its
        blocks changes nothing, so it can't invent a chain (tangential-robust).
      * It controls for how often two archetypes even co-occur in a penetration,
        and for layer thickness, isolating pure ordering preference.
    """
    pens = [(s, S, _argmax_blocks(S)) for s, S in _iter_penetrations(df, k)]
    obs = np.zeros((k, k))
    for _, S, blocks in pens:
        obs += _adjacency_for_order(S, blocks, np.arange(len(blocks)))

    null = np.zeros((n_perm, k, k))
    for p in range(n_perm):
        acc = np.zeros((k, k))
        for _, S, blocks in pens:
            order = RNG.permutation(len(blocks))
            acc += _adjacency_for_order(S, blocks, order)
        null[p] = acc

    mean, std = null.mean(0), null.std(0)
    std[std < 1e-12] = np.nan            # deterministic cells (≤2 blocks) → undefined z
    z = (obs - mean) / std
    z[np.isnan(z)] = 0.0

    off = obs.copy()
    np.fill_diagonal(off, 0.0)
    denom = off.sum()
    off_norm = off / denom if denom > 0 else off
    return obs, z, off_norm


# ---- seriation: turn the adjacency into a 1D layer ordering -----------------

def _spectral_order(affinity):
    """Fiedler (spectral) seriation: order nodes so that strongly-adjacent
    archetypes land next to each other on a line — the layer-chain hypothesis.
    Uses the 2nd eigenvector of the normalised graph Laplacian."""
    W = np.array(affinity, float)
    np.fill_diagonal(W, 0.0)
    W = np.clip(W, 0, None)
    d = W.sum(1)
    dinv = 1.0 / np.sqrt(np.where(d > 0, d, 1.0))
    Ln = np.eye(len(W)) - (dinv[:, None] * W * dinv[None, :])
    vals, vecs = np.linalg.eigh(Ln)
    return np.argsort(vecs[:, 1])        # Fiedler vector


# ---------------------------------------------------------------------------
# ANALYSIS 2 — same-depth co-occurrence ("who stacks on whom" / same tissue)
# ---------------------------------------------------------------------------

def _clr(S, eps=CLR_EPS):
    """Centred-log-ratio of the fractional scores. Removes the sum-to-1
    constraint that otherwise forces spurious negative correlations between
    compositional parts."""
    Sp = S + eps
    Sp = Sp / Sp.sum(axis=1, keepdims=True)
    logS = np.log(Sp)
    return logS - logS.mean(axis=1, keepdims=True)


def cooccurrence(df, k, loadings_df):
    """Three (k, k) 'same tissue?' affinities:

      clr_corr : Pearson correlation of CLR-transformed scores across all depth
                 bins — do the two archetypes rise & fall together (compositional-
                 bias-corrected)?
      rho_prop : Lovell/Quinn proportionality ρ on the CLR scores,
                 1 − Var(clrᵢ − clrⱼ) / (Var(clrᵢ)+Var(clrⱼ)); +1 = perfectly
                 proportional. A robustness companion to clr_corr.
      sig_sim  : Pearson correlation between the two archetypes' feature
                 SIGNATURES (rows of the loadings) — do they look alike,
                 independent of where they turn on?

    Spatial evidence (clr_corr / rho_prop) and signature evidence (sig_sim)
    agreeing is a strong 'same tissue' call. Combined = mean of clr_corr & sig_sim.
    """
    clr_all = np.vstack([_clr(S) for _, S in _iter_penetrations(df, k)])

    clr_corr = np.corrcoef(clr_all.T)

    var = clr_all.var(0)
    rho = np.ones((k, k))
    for i in range(k):
        for j in range(k):
            if i != j:
                d = (clr_all[:, i] - clr_all[:, j]).var()
                rho[i, j] = 1.0 - d / (var[i] + var[j] + 1e-12)

    L = loadings_df.values.T             # (k, n_features)
    sig_sim = np.corrcoef(L)

    combined = 0.5 * (clr_corr + sig_sim)
    np.fill_diagonal(combined, 1.0)
    return clr_corr, rho, sig_sim, combined


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _annotated_heatmap(ax, M, labels, cmap, vmin, vmax, order=None, cbar_label=''):
    idx = order if order is not None else np.arange(len(labels))
    Mo = M[np.ix_(idx, idx)]
    lab = [labels[i] for i in idx]
    cmap = plt.get_cmap(cmap).copy()
    cmap.set_bad('0.85')                 # masked (e.g. diagonal) cells → light grey
    im = ax.imshow(Mo, cmap=cmap, vmin=vmin, vmax=vmax, aspect='equal')
    ax.set_xticks(range(len(lab)))
    ax.set_yticks(range(len(lab)))
    ax.set_xticklabels(lab, fontsize=9)
    ax.set_yticklabels(lab, fontsize=9)
    for a in range(len(lab)):
        for b in range(len(lab)):
            v = Mo[a, b]
            if not np.isfinite(v):
                continue
            ax.text(b, a, f"{v:.2f}", ha='center', va='center', fontsize=7,
                    color='white' if abs(v - (vmin + vmax) / 2) > (vmax - vmin) * 0.30 else 'black')
    cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label(cbar_label, fontsize=8)
    return im


def plot_adjacency(obs, z, off_norm, k, method, save_dir):
    labels = [_label(i) for i in range(k)]
    order = _spectral_order(np.clip(z, 0, None))

    # The self-continuity DIAGONAL (a layer continuing into itself) is always
    # strongly positive and would dominate the colour scale; mask it so the
    # off-diagonal "who borders whom" signal — the actual question — gets full
    # contrast. Scale is set from off-diagonal magnitudes only.
    z_off = z.copy()
    np.fill_diagonal(z_off, np.nan)
    zmax = max(1e-6, np.nanmax(np.abs(z_off)))

    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    _annotated_heatmap(axes[0], off_norm, labels, 'magma', 0.0,
                       max(1e-6, off_norm.max()), order=order,
                       cbar_label='fraction of all boundaries')
    axes[0].set_title("Observed boundary sharing\n(off-diagonal, fraction of all "
                      "between-archetype adjacencies)", fontsize=10)
    _annotated_heatmap(axes[1], z_off, labels, 'RdBu_r', -zmax, zmax, order=order,
                       cbar_label='z vs. block-order null')
    axes[1].set_title("Adjacency ENRICHMENT (z, diagonal masked)\n+ = border each "
                      "other more than chance ordering", fontsize=10)
    fig.suptitle(f"{_METHOD_NAME[method]}  (K={k})  —  which archetypes border which "
                 f"along depth  (rows/cols seriated into the implied layer order)",
                 fontsize=13)
    fig.text(0.5, 0.005,
             "How to read:  each depth bin's neighbours contribute their FRACTIONAL "
             "scores (no winner-take-all). Enrichment compares observed abutment to a "
             "null that shuffles the ORDER of argmax layer-blocks within each "
             "penetration (holding block sizes fixed) — so + means a genuine spatial "
             "neighbour, robust to probes that only span a few layers. Axis order is "
             "the 1D seriation of the enrichment graph: read it as the candidate "
             "superficial↔…↔WM chain (direction is arbitrary).",
             ha='center', va='bottom', fontsize=8, wrap=True)
    plt.tight_layout(rect=[0, 0.10, 1, 0.95])
    _save_fig(save_dir, 'adjacency_enrichment.png')
    plt.show()

    _plot_chain(z, order, k, method, save_dir)
    return order


def _plot_chain(z, order, k, method, save_dir):
    """Archetypes laid out in seriated (candidate-layer) order.

    Two edge sets:
      * BACKBONE — every consecutive pair in the seriation, always drawn on the
        line (solid if its enrichment > 0, thin grey-dashed if the link is weak).
        This is the proposed layer sequence.
      * LONG-RANGE — non-adjacent pairs whose enrichment is still strong, drawn
        as arcs ABOVE the line. These would CONTRADICT a clean 1D chain (a
        strong arc jumping over a node ⇒ the ordering isn't purely linear).
    Width/colour of every edge = adjacency enrichment z.
    """
    labels = [_label(i) for i in range(k)]
    x = {node: rank for rank, node in enumerate(order)}
    zmax = max(1e-6, float(np.nanmax(np.clip(z, 0, None))))
    off = z.copy()
    np.fill_diagonal(off, -np.inf)
    pos_vals = off[np.isfinite(off) & (off > 0)]
    long_thr = np.nanpercentile(pos_vals, 70) if pos_vals.size else np.inf

    fig, ax = plt.subplots(figsize=(1.9 * k + 2, 4.8))

    def _edge(i, j, rad, dashed=False):
        w = max(z[i, j], 0.0)
        style = dict(arrowstyle='-', alpha=0.8)
        if dashed:
            style.update(lw=1.0, color='0.7', linestyle='--')
        else:
            style.update(lw=1.0 + 5 * w / zmax, color=plt.cm.viridis(w / zmax))
        ax.add_patch(FancyArrowPatch((x[i], 0), (x[j], 0),
                                     connectionstyle=f"arc3,rad={rad}", **style))

    # backbone: consecutive in seriated order
    for r in range(k - 1):
        i, j = order[r], order[r + 1]
        _edge(i, j, rad=-0.05, dashed=(z[i, j] <= 0))
    # long-range contradictions: |rank diff| >= 2 and strongly enriched
    for a in range(k):
        for b in range(a + 1, k):
            i, j = order[a], order[b]
            if b - a >= 2 and z[i, j] > long_thr:
                _edge(i, j, rad=0.12 * (b - a))

    for node in order:
        ax.scatter([x[node]], [0], s=950, c='white', edgecolors='black', zorder=3)
        ax.text(x[node], 0, labels[node], ha='center', va='center', fontsize=10, zorder=4)
    ax.set_xlim(-0.7, k - 0.3)
    ax.set_ylim(-0.7, 1.7)
    ax.axis('off')
    ax.set_title(f"{_METHOD_NAME[method]} (K={k}) — inferred layer chain\n"
                 "backbone = seriated order · arcs above = long-range (chain-breaking) "
                 "links · width = enrichment", fontsize=11)
    fig.text(0.5, 0.01, "Read the row of nodes as the candidate superficial↔…↔WM "
             "sequence (direction arbitrary). A dashed backbone link = a weak join; a "
             "strong arc jumping over a node = evidence the layering isn't a clean 1D "
             "chain there.", ha='center', va='bottom', fontsize=8, wrap=True)
    plt.tight_layout(rect=[0, 0.06, 1, 0.92])
    _save_fig(save_dir, 'layer_chain.png')
    plt.show()


def _clustermap(M, k, title, caption, filename, save_dir, vmin=-1, vmax=1):
    """Reordered heatmap + top dendrogram from hierarchical clustering of a
    'same tissue' affinity matrix."""
    labels = [_label(i) for i in range(k)]
    dist = np.clip(1.0 - M, 0, 2)
    dist = 0.5 * (dist + dist.T)
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    Z = optimal_leaf_ordering(linkage(condensed, method='average'), condensed)

    fig = plt.figure(figsize=(7.5, 8.2))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 4], hspace=0.05)
    axd = fig.add_subplot(gs[0])
    dn = dendrogram(Z, labels=labels, ax=axd, color_threshold=0,
                    above_threshold_color='0.4')
    axd.set_xticks([])
    axd.set_yticks([])
    for spine in axd.spines.values():
        spine.set_visible(False)
    order = dn['leaves']

    axh = fig.add_subplot(gs[1])
    _annotated_heatmap(axh, M, labels, 'RdBu_r', vmin, vmax, order=order,
                       cbar_label='affinity')
    axh.set_title('')
    fig.suptitle(title, fontsize=12)
    fig.text(0.5, 0.01, caption, ha='center', va='bottom', fontsize=8, wrap=True)
    # NB: colorbar + dendrogram axes aren't tight_layout-compatible, so set
    # margins manually instead (avoids a spurious warning + wrong sizing).
    fig.subplots_adjust(top=0.92, bottom=0.12, left=0.10, right=0.98)
    _save_fig(save_dir, filename)
    plt.show()


def plot_cooccurrence(clr_corr, sig_sim, combined, k, method, save_dir):
    _clustermap(clr_corr, k,
                f"{_METHOD_NAME[method]} (K={k}) — spatial co-occurrence "
                "(CLR-corrected)",
                "How to read:  correlation of CLR-transformed fractional scores across "
                "all depth bins. + (red) = the two archetypes rise & fall together in "
                "the same bins → candidate SAME tissue. CLR removes the sum-to-1 bias "
                "that would otherwise make everything look anti-correlated.",
                'cooccurrence_clr.png', save_dir)
    _clustermap(sig_sim, k,
                f"{_METHOD_NAME[method]} (K={k}) — feature-signature similarity",
                "How to read:  correlation between the two archetypes' feature "
                "signatures (their loading vectors). + = they LOOK alike regardless of "
                "where they occur. Independent of the spatial evidence — agreement "
                "with co-occurrence is a strong same-tissue call.",
                'cooccurrence_signature.png', save_dir)
    _clustermap(combined, k,
                f"{_METHOD_NAME[method]} (K={k}) — combined same-tissue affinity",
                "How to read:  mean of spatial co-occurrence (CLR-corr) and signature "
                "similarity. Tight clusters = archetypes that behave AND look like the "
                "same tissue (e.g. two prototypes of one tissue type).",
                'cooccurrence_combined.png', save_dir)


# ---------------------------------------------------------------------------
# Printed interpretation
# ---------------------------------------------------------------------------

def _print_adjacency(z, order, k):
    print("\n  ADJACENCY — top neighbours per archetype (z vs. chance ordering):")
    for i in range(k):
        nb = [(j, z[i, j]) for j in range(k) if j != i]
        nb.sort(key=lambda t: -t[1])
        top = ", ".join(f"{_label(j)}={zz:+.1f}" for j, zz in nb[:3])
        print(f"    {_label(i)}:  {top}")
    chain = " ↔ ".join(_label(i) for i in order)
    print(f"\n  Seriated layer chain (direction arbitrary):  {chain}")


def _print_cooccurrence(clr_corr, rho, sig_sim, combined, k):
    print("\n  CO-OCCURRENCE — top same-tissue partner per archetype "
          "(combined, with the 3 lines of evidence for that partner):")
    for i in range(k):
        pa = [(j, combined[i, j]) for j in range(k) if j != i]
        j, comb = max(pa, key=lambda t: t[1])
        print(f"    {_label(i)} → {_label(j)}:  combined={comb:+.2f}  "
              f"(spatial CLR={clr_corr[i, j]:+.2f}, proportionality ρ={rho[i, j]:+.2f}, "
              f"signature={sig_sim[i, j]:+.2f})")


# ---------------------------------------------------------------------------
# Public entry point — call this from explore_decompositions.py so both the
# adjacency and co-occurrence analyses run on the SAME fit / parameters, in the
# same invocation.
# ---------------------------------------------------------------------------

def analyze_relations(df, loadings_df, method, k, save_dir, n_perm=N_PERM,
                      verbose=True):
    """Run both relational analyses on an already-fitted decomposition.

    Parameters mirror what `explore_decompositions.py` already has in hand after
    `load_and_perform_pca`: `df` (with PC1..PCk membership columns), the
    `loadings_df`, the method/K, and the recipe's `save_dir`.
    """
    if verbose:
        print(f"\nAdjacency enrichment ({n_perm} block-order permutations) ...")
    obs, z, off_norm = adjacency_enrichment(df, k, n_perm=n_perm)
    order = plot_adjacency(obs, z, off_norm, k, method, save_dir)
    if verbose:
        _print_adjacency(z, order, k)

    if verbose:
        print("\nCo-occurrence / same-tissue affinity ...")
    clr_corr, rho, sig_sim, combined = cooccurrence(df, k, loadings_df)
    plot_cooccurrence(clr_corr, sig_sim, combined, k, method, save_dir)
    if verbose:
        _print_cooccurrence(clr_corr, rho, sig_sim, combined, k)

    if verbose:
        print(f"\n  relational figures → {save_dir}")
        print("    adjacency_enrichment.png  — who borders whom (seriated)")
        print("    layer_chain.png           — inferred layer chain graph")
        print("    cooccurrence_clr.png      — same-bin co-occurrence (compositional)")
        print("    cooccurrence_signature.png— feature-signature similarity")
        print("    cooccurrence_combined.png — combined same-tissue affinity")
    return dict(adjacency_z=z, order=order, combined=combined)


# ---------------------------------------------------------------------------
# Standalone driver (same parameters as explore_decompositions.py's __main__)
# ---------------------------------------------------------------------------

def run(
        conn: Connection,
        table_name: str = "PenetrationMetrics",
        exclude_sessions: Optional[list] = None,
        within_session_normalize: bool = False,
        pc_smooth_sigma: float = 2.0,
        exclude_features: Optional[list] = None,
) -> None:
    base = os.path.join(PLOT_BASE_DIR, "decomp_neighbors")
    os.makedirs(base, exist_ok=True)
    print(f"Plots → {base}")

    for method, k in RECIPES:
        tag = f"{method}_{k}"
        print("\n" + "=" * 70)
        print(f"{_METHOD_NAME[method]}  |  K = {k}  —  relational analysis")
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

        save_dir = os.path.join(base, tag)
        os.makedirs(save_dir, exist_ok=True)

        analyze_relations(df, loadings_df, method, k, save_dir)


if __name__ == "__main__":
    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )
    # Mirror explore_decompositions.py's __main__ so the archetypes analysed
    # here are exactly the ones you've been looking at.
    exclude_sessions = ["260327_0", "260331_0", "260402_0", "260520_0", "260423_0"]
    run(
        conn,
        exclude_sessions=exclude_sessions,
        within_session_normalize=False,
        pc_smooth_sigma=2.0,
        exclude_features=["amplitude", "band_power_delta_theta",
                          "band_power_alpha_beta", "band_power_gamma"],
    )

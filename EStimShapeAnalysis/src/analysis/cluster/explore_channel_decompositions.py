#!/usr/bin/env python3
"""Explore how the 32 recording channels cluster by neural response — using the
same parts-based / prototype / soft-clustering techniques as the penetration
``explore_decompositions`` (NMF, Archetypal Analysis, Gaussian Mixture), plus
KMeans / Ward baselines — as an *alternative to the PCA + manual-lasso* workflow
in ``run_cluster_app``.

WHY
---
The GA cluster app (``cluster_app`` / ``run_cluster_app``) loads a response
vector per channel from ``MUAChannelResponses`` (avg spikes/s to each GA
stimulus), z-scores each channel, PCA-reduces, and lets you lasso channels into
clusters by hand. The clusters then feed the estim-isolation score
(``cluster_isolation_score`` → ``EStimParameterData`` →
``analyze_estim_isolation_effect``): we want to stimulate inside a single
response cluster so the artificial activation stays functionally local.

This script asks whether an *automatic* decomposition finds the same structure,
and which method + K best carves the probe into functionally-coherent, ideally
spatially-contiguous groups. It is a look-first tool: it FITS several methods
over a range of K and dumps comparison plots + model-selection diagnostics. It
does NOT write anything to the repository — once a recipe looks good we decide
which per-channel / per-cluster metrics to save and wire them into
``analyze_estim_isolation_effect`` (see the note at the bottom of this file).

Like ``run_cluster_app`` it operates on the ONE experiment in ``context``.

WHAT EACH METHOD GIVES YOU (for K groups)
-----------------------------------------
  kmeans   : hard partition in PCA space. The plain baseline.
  ward     : hierarchical (Ward) hard partition — respects a dendrogram, tends
             to give compact, balanced groups. Good when you suspect nested
             structure along the probe.
  gmm      : soft clustering. Each channel gets a posterior membership over K
             Gaussians (sum to 1); the hard call is the argmax. Uniquely, GMM
             hands you a principled automatic K via BIC/AIC (see below).
  nmf      : non-negative parts. Each channel is an additive mix of K response
             "parts"; hard call = strongest part. Needs X >= 0 (MinMax-scaled).
  aa       : archetypal analysis. Each channel is a convex mix of K extreme
             response prototypes; hard call = dominant archetype. Also MinMax.

HOW TO CHOOSE K — THE AUTOMATIC METHODS
---------------------------------------
There is no single "correct" K; each criterion encodes a different definition of
"good clustering". This script computes the standard ones and shows them
together so you can pick where they agree:

  * BIC / AIC  (GMM only, PRINCIPLED DEFAULT).
      GMM is an actual probability model, so we can score each K by penalised
      likelihood: BIC = -2·loglik + p·ln(n). Pick K at the MINIMUM BIC. This is
      the closest thing to a rigorous automatic answer and is the one I'd trust
      first. AIC penalises complexity less (tends to pick larger K); when they
      disagree, BIC is the conservative choice.
  * Silhouette  (any hard partition, the go-to geometric criterion).
      Mean over channels of (b - a) / max(a, b), a = mean intra-cluster dist,
      b = mean nearest-other-cluster dist. Ranges [-1, 1]; pick K at the MAXIMUM.
      Works for kmeans/ward/gmm/nmf/aa alike (computed on the space each method
      clusters in), so it's the common yardstick across methods.
  * Gap statistic  (Tibshirani et al.).
      Compares within-cluster dispersion to that expected under a uniform null.
      The smallest K with Gap(K) >= Gap(K+1) - s(K+1) is the recommendation — it
      is the one criterion that can justify K = 1 (no real clusters), a genuine
      possibility worth knowing about here.
  * Calinski-Harabasz (higher=better) and Davies-Bouldin (lower=better).
      Cheap variance-ratio / cluster-overlap indices; shown as tie-breakers.
  * Reconstruction elbow + cophenetic stability  (NMF / AA).
      NMF/AA aren't partitions, so we also track reconstruction error vs K (look
      for the elbow) and, for NMF, the cophenetic correlation of the consensus
      matrix across random restarts (Brunet et al.): the largest K that stays
      near 1.0 is a stable factorisation.

Recommendation in practice: read BIC for GMM and silhouette for everyone else;
use the gap statistic as the reality check on whether K should be small (or 1).
The printed summary lists each method's auto-K and the consensus.

Run:  python -m src.analysis.cluster.explore_channel_decompositions
"""
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm

from clat.intan.channels import Channel

from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.decomposition import PCA, NMF
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                             davies_bouldin_score)
from sklearn.preprocessing import MinMaxScaler

from src.cluster.probe_mapping import DBCChannelMapper
from src.pga.app.run_cluster_app import DbDataLoader
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context
# Reuse the self-contained archetypal-analysis solver from the penetration
# decomposition code so both worlds share one AA implementation.
from src.analysis.penetrations.pca_predict import _archetypal_analysis

PLOT_BASE_DIR = "/home/connorlab/Documents/plots"

# Range of K (number of clusters / components / archetypes) to sweep.
K_RANGE = list(range(2, 9))

# How many PCA components the distance-based methods (kmeans/ward/gmm) cluster
# in. Reducing first denoises and keeps GMM well-conditioned (32 channels can't
# support a full covariance in hundreds of stimulus dims). Capped at
# n_channels - 1 and at the stimulus count at runtime.
N_PCA_FOR_CLUSTERING = 10

# GMM covariance model. 'diag' is the safe default for this sample size;
# 'spherical' is even more constrained, 'full' needs many channels per cluster.
GMM_COVARIANCE_TYPE = 'diag'

# Restarts for NMF cophenetic stability (Brunet consensus). Kept modest so the
# sweep stays fast; raise for a more stable estimate.
NMF_STABILITY_RUNS = 20

# Reproducibility for every stochastic step (KMeans/GMM/NMF/AA inits, gap refs).
SEED = 42

_METHOD_NAME = {
    'kmeans': 'KMeans',
    'ward': 'Agglomerative (Ward)',
    'gmm': 'Gaussian Mixture',
    'nmf': 'NMF',
    'aa': 'Archetypal Analysis',
}

# Methods whose hard call comes from a soft membership (so we can draw a
# membership heatmap and a "composition" strip for them).
_SOFT_METHODS = {'gmm', 'nmf', 'aa'}


# ---------------------------------------------------------------------------
# Data + preprocessing
# ---------------------------------------------------------------------------

@dataclass
class ChannelData:
    """Everything the methods need, computed once.

    channels   : ordered list of Channel (rows of every matrix below).
    X          : (n_channels, n_stims) per-channel z-scored responses. Clustering
                 on this space is about response-profile SHAPE, not firing rate —
                 the same normalization ``cluster_app`` uses.
    X_red      : (n_channels, n_pca) PCA projection of X, whitened for scale.
                 What kmeans/ward/gmm cluster in.
    X_nonneg   : (n_channels, n_stims) MinMax-scaled X in [0, 1], for NMF/AA.
    coords2d   : (n_channels, 2) PCA(2) of X — a FIXED layout so every method's
                 scatter is directly comparable.
    depth_um   : (n_channels,) physical depth of each channel on the probe.
    var_ratio  : explained-variance ratio of the clustering PCA (for the scree).
    """
    channels: list
    X: np.ndarray
    X_red: np.ndarray
    X_nonneg: np.ndarray
    coords2d: np.ndarray
    depth_um: np.ndarray
    var_ratio: np.ndarray


def _zscore_per_channel(values: list) -> np.ndarray:
    """Per-channel z-score, matching ClusterApplicationWindow.reduce_data: each
    channel's response vector is centered and scaled by its own std (constant /
    singleton channels pass through unchanged)."""
    normed = []
    for v in values:
        v = np.asarray(v, dtype=float)
        if len(v) > 1 and np.std(v) > 1e-10:
            normed.append((v - np.mean(v)) / np.std(v))
        else:
            normed.append(v)
    return np.vstack(normed)


def load_channel_data(
        data_loader: DbDataLoader,
        channel_mapper: DBCChannelMapper,
        n_pca_for_clustering: int = N_PCA_FOR_CLUSTERING,
) -> ChannelData:
    """Load per-channel response vectors for the current experiment and build the
    matrices every method consumes. Channels with no data are dropped."""
    data_for_channels = data_loader.load_data_for_channels()
    data_for_channels = {ch: v for ch, v in data_for_channels.items()
                         if len(v) > 0}
    channels = list(data_for_channels.keys())
    if len(channels) < 3:
        raise RuntimeError(
            f"Only {len(channels)} channels have response data — need >= 3 to "
            "cluster. Has the GA run / MUA detection produced responses yet?")

    # Guard against ragged vectors (a channel with a different stim count would
    # break the vstack); trim everything to the shared length.
    lengths = {len(v) for v in data_for_channels.values()}
    if len(lengths) > 1:
        n = min(lengths)
        print(f"  WARN: channels have differing stim counts {sorted(lengths)}; "
              f"truncating all to the shared {n} stimuli.")
        data_for_channels = {ch: v[:n] for ch, v in data_for_channels.items()}

    X = _zscore_per_channel(list(data_for_channels.values()))
    n_channels, n_stims = X.shape
    print(f"Loaded {n_channels} channels x {n_stims} stimuli.")

    # PCA space for the distance-based methods (whitened so all retained PCs
    # weigh equally — otherwise PC1 dominates the Euclidean metric).
    n_pca = max(2, min(n_pca_for_clustering, n_channels - 1, n_stims))
    pca = PCA(n_components=n_pca, whiten=True, random_state=SEED)
    X_red = pca.fit_transform(X)

    # Fixed 2-D layout for all scatters (unwhitened PCA reads more naturally).
    coords2d = PCA(n_components=2, random_state=SEED).fit_transform(X)

    X_nonneg = MinMaxScaler().fit_transform(X)

    depth_um = np.array([channel_mapper.get_coordinates(ch)[1] for ch in channels],
                        dtype=float)

    return ChannelData(
        channels=channels, X=X, X_red=X_red, X_nonneg=X_nonneg,
        coords2d=coords2d, depth_um=depth_um,
        var_ratio=pca.explained_variance_ratio_,
    )


# ---------------------------------------------------------------------------
# One fitted (method, K) result
# ---------------------------------------------------------------------------

@dataclass
class Fit:
    method: str
    k: int
    labels: np.ndarray                 # (n_channels,) hard cluster id in [0, K)
    space: np.ndarray                  # the representation silhouette is scored on
    memberships: Optional[np.ndarray] = None   # (n_channels, K) soft, or None
    bic: Optional[float] = None
    aic: Optional[float] = None
    recon_error: Optional[float] = None
    extra: dict = field(default_factory=dict)


def _fit_method(method: str, data: ChannelData, k: int) -> Fit:
    """Fit one method at one K and return a uniform Fit record."""
    if method == 'kmeans':
        model = KMeans(n_clusters=k, n_init=10, random_state=SEED)
        labels = model.fit_predict(data.X_red)
        return Fit(method, k, labels, data.X_red,
                   extra={'inertia': float(model.inertia_)})

    if method == 'ward':
        labels = AgglomerativeClustering(n_clusters=k, linkage='ward').fit_predict(data.X_red)
        return Fit(method, k, labels, data.X_red)

    if method == 'gmm':
        gmm = GaussianMixture(n_components=k, covariance_type=GMM_COVARIANCE_TYPE,
                              reg_covar=1e-4, n_init=5, random_state=SEED)
        gmm.fit(data.X_red)
        memberships = gmm.predict_proba(data.X_red)
        labels = memberships.argmax(axis=1)
        return Fit(method, k, labels, data.X_red, memberships=memberships,
                   bic=float(gmm.bic(data.X_red)), aic=float(gmm.aic(data.X_red)))

    if method == 'nmf':
        nmf = NMF(n_components=k, init='nndsvda', random_state=SEED, max_iter=2000)
        W = nmf.fit_transform(data.X_nonneg)          # (n_channels, K) >= 0
        labels = W.argmax(axis=1)
        return Fit(method, k, labels, data.X_nonneg, memberships=_row_normalize(W),
                   recon_error=float(nmf.reconstruction_err_))

    if method == 'aa':
        A, Z = _archetypal_analysis(data.X_nonneg, k, seed=SEED)   # A: (n, K) convex
        labels = A.argmax(axis=1)
        recon = float(np.sqrt(np.sum((data.X_nonneg - A @ Z) ** 2)))
        return Fit(method, k, labels, data.X_nonneg, memberships=A, recon_error=recon)

    raise ValueError(f"Unknown method {method!r}")


def _row_normalize(W: np.ndarray) -> np.ndarray:
    row = W.sum(axis=1, keepdims=True)
    row[row == 0] = 1.0
    return W / row


# ---------------------------------------------------------------------------
# Model-selection scores
# ---------------------------------------------------------------------------

def _partition_scores(fit: Fit) -> dict:
    """Geometric cluster-quality indices for a hard partition. Returns NaNs when
    the partition is degenerate (a single occupied cluster, or one channel per
    cluster) so those K don't masquerade as good."""
    labels, space = fit.labels, fit.space
    n_labels = len(set(labels))
    out = {'silhouette': np.nan, 'calinski_harabasz': np.nan, 'davies_bouldin': np.nan}
    if 1 < n_labels < len(labels):
        out['silhouette'] = float(silhouette_score(space, labels))
        out['calinski_harabasz'] = float(calinski_harabasz_score(space, labels))
        out['davies_bouldin'] = float(davies_bouldin_score(space, labels))
    return out


def gap_statistic(space: np.ndarray, k_range: list,
                  cluster_fn: Callable[[np.ndarray, int], np.ndarray],
                  n_refs: int = 10, seed: int = SEED) -> dict:
    """Tibshirani gap statistic for a hard-clustering function.

    Gap(K) = E*[log W_K] - log W_K, where W_K is the pooled within-cluster sum of
    squares and E* is the mean over ``n_refs`` uniform reference datasets drawn in
    the bounding box of ``space``. The recommended K is the smallest K with
    Gap(K) >= Gap(K+1) - s(K+1) (s = ref std, inflated by sqrt(1 + 1/n_refs)).

    Returns {'k': [...], 'gap': [...], 's': [...], 'best_k': K}. This is the one
    criterion that can return the smallest K in the range as "no strong cluster
    structure", which is worth knowing before trusting any partition.
    """
    rng = np.random.default_rng(seed)
    lo, hi = space.min(axis=0), space.max(axis=0)

    def pooled_wss(X, labels):
        total = 0.0
        for c in np.unique(labels):
            pts = X[labels == c]
            if len(pts) > 1:
                total += float(((pts - pts.mean(axis=0)) ** 2).sum())
        return total

    gaps, ss = [], []
    for k in k_range:
        log_wk = np.log(pooled_wss(space, cluster_fn(space, k)) + 1e-12)
        ref_logs = []
        for _ in range(n_refs):
            ref = rng.uniform(lo, hi, size=space.shape)
            ref_logs.append(np.log(pooled_wss(ref, cluster_fn(ref, k)) + 1e-12))
        ref_logs = np.asarray(ref_logs)
        gaps.append(float(ref_logs.mean() - log_wk))
        ss.append(float(ref_logs.std() * np.sqrt(1.0 + 1.0 / n_refs)))

    best_k = k_range[-1]
    for i in range(len(k_range) - 1):
        if gaps[i] >= gaps[i + 1] - ss[i + 1]:
            best_k = k_range[i]
            break
    return {'k': list(k_range), 'gap': gaps, 's': ss, 'best_k': int(best_k)}


def _kmeans_labels(X: np.ndarray, k: int) -> np.ndarray:
    return KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X)


def nmf_cophenetic(X_nonneg: np.ndarray, k: int, n_runs: int = NMF_STABILITY_RUNS,
                   seed: int = SEED) -> float:
    """Brunet cophenetic correlation for NMF at rank K: a stability score in
    [0, 1]. Run NMF ``n_runs`` times with different seeds, build the consensus
    matrix C (fraction of runs in which channels i, j share a hard cluster), then
    correlate the consensus distances (1 - C) with the cophenetic distances of an
    average-linkage tree on them. Near 1.0 = the K-part factorisation is stable
    across restarts; a sharp drop marks over-factorising."""
    from scipy.cluster.hierarchy import linkage, cophenet
    from scipy.spatial.distance import squareform

    n = X_nonneg.shape[0]
    consensus = np.zeros((n, n))
    rng = np.random.default_rng(seed)
    for _ in range(n_runs):
        s = int(rng.integers(0, 1_000_000))
        W = NMF(n_components=k, init='random', random_state=s,
                max_iter=1000).fit_transform(X_nonneg)
        labels = W.argmax(axis=1)
        consensus += (labels[:, None] == labels[None, :]).astype(float)
    consensus /= n_runs

    dist = 1.0 - consensus
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    if condensed.size == 0 or np.allclose(condensed, 0):
        return 1.0
    coph_corr, _ = cophenet(linkage(condensed, method='average'), condensed)
    return float(coph_corr)


# ---------------------------------------------------------------------------
# Sweep: fit every method across K, collect selection scores
# ---------------------------------------------------------------------------

@dataclass
class MethodSweep:
    method: str
    fits: dict                 # k -> Fit
    scores: dict               # k -> {metric: value}
    gap: Optional[dict] = None
    cophenetic: Optional[dict] = None   # k -> value (NMF only)
    auto_k: dict = field(default_factory=dict)   # criterion -> recommended K


def _auto_k_from_scores(sweep: MethodSweep) -> dict:
    """Per-criterion recommended K for one method: min BIC/AIC, max silhouette /
    Calinski-Harabasz, min Davies-Bouldin, gap rule, and the recon-error elbow
    for NMF/AA."""
    ks = sorted(sweep.fits)
    auto = {}

    def _argbest(metric, best):
        vals = [(k, sweep.scores[k].get(metric)) for k in ks]
        vals = [(k, v) for k, v in vals if v is not None and not np.isnan(v)]
        if not vals:
            return None
        return int(best(vals, key=lambda kv: kv[1])[0])

    auto['silhouette'] = _argbest('silhouette', max)
    auto['calinski_harabasz'] = _argbest('calinski_harabasz', max)
    auto['davies_bouldin'] = _argbest('davies_bouldin', min)

    bic = [(k, sweep.fits[k].bic) for k in ks if sweep.fits[k].bic is not None]
    if bic:
        auto['bic'] = int(min(bic, key=lambda kv: kv[1])[0])
    aic = [(k, sweep.fits[k].aic) for k in ks if sweep.fits[k].aic is not None]
    if aic:
        auto['aic'] = int(min(aic, key=lambda kv: kv[1])[0])

    if sweep.gap is not None:
        auto['gap'] = sweep.gap['best_k']

    # Reconstruction-error elbow (NMF/AA): largest curvature of error vs K.
    recon = [(k, sweep.fits[k].recon_error) for k in ks
             if sweep.fits[k].recon_error is not None]
    if len(recon) >= 3:
        auto['recon_elbow'] = _elbow_k([k for k, _ in recon], [v for _, v in recon])

    return auto


def _elbow_k(ks: list, values: list) -> int:
    """Kneedle-lite: the K of maximum distance from the straight line joining the
    first and last (K, value) points — the classic 'elbow' of a monotone curve."""
    ks = np.asarray(ks, dtype=float)
    v = np.asarray(values, dtype=float)
    p1, p2 = np.array([ks[0], v[0]]), np.array([ks[-1], v[-1]])
    line = p2 - p1
    line = line / (np.linalg.norm(line) + 1e-12)
    dists = []
    for i in range(len(ks)):
        pt = np.array([ks[i], v[i]]) - p1
        proj = pt @ line
        dists.append(np.linalg.norm(pt - proj * line))
    return int(ks[int(np.argmax(dists))])


def sweep_method(method: str, data: ChannelData, k_range: list = K_RANGE,
                 compute_gap: bool = True) -> MethodSweep:
    fits, scores = {}, {}
    for k in k_range:
        fit = _fit_method(method, data, k)
        fits[k] = fit
        scores[k] = _partition_scores(fit)

    sweep = MethodSweep(method=method, fits=fits, scores=scores)

    # Gap statistic uses each method's own clustering geometry where cheap; for
    # kmeans/ward/gmm the space is X_red. NMF/AA cluster in X_nonneg but their
    # argmax partition there is what we gap-test.
    if compute_gap:
        space = data.X_red if method in ('kmeans', 'ward', 'gmm') else data.X_nonneg
        sweep.gap = gap_statistic(space, k_range, _kmeans_labels)

    if method == 'nmf':
        sweep.cophenetic = {k: nmf_cophenetic(data.X_nonneg, k) for k in k_range}

    sweep.auto_k = _auto_k_from_scores(sweep)
    return sweep


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _cluster_colors(k: int):
    return cm.get_cmap('tab10', 10)(np.arange(k) % 10)


def _channel_label(ch: Channel) -> str:
    return str(ch).split('.')[-1]


def _plot_probe_map(ax, data: ChannelData, labels: np.ndarray, title: str):
    """The 32 channels drawn at their physical depth on the probe, colored by
    cluster. THE isolation-relevant view: a good clustering makes each color a
    contiguous depth band, so a central estim site stays inside one cluster."""
    colors = _cluster_colors(labels.max() + 1)
    x = np.zeros(len(labels))
    ax.scatter(x, data.depth_um, c=[colors[l] for l in labels], s=140,
               edgecolors='black', linewidths=0.5, zorder=3)
    for i in range(len(labels)):
        ax.annotate(_channel_label(data.channels[i]),
                    (x[i], data.depth_um[i]), xytext=(9, 0),
                    textcoords='offset points', va='center', fontsize=6)
    ax.set_xlim(-0.6, 0.9)
    ax.set_xticks([])
    ax.set_ylabel("depth on probe (µm)")
    ax.set_title(title, fontsize=9)
    ax.margins(y=0.02)


def _plot_scatter(ax, data: ChannelData, labels: np.ndarray, title: str):
    """Channels in the shared PCA(2) layout, colored by cluster."""
    colors = _cluster_colors(labels.max() + 1)
    ax.scatter(data.coords2d[:, 0], data.coords2d[:, 1],
               c=[colors[l] for l in labels], s=80, edgecolors='black',
               linewidths=0.5)
    for i in range(len(labels)):
        ax.annotate(_channel_label(data.channels[i]),
                    (data.coords2d[i, 0], data.coords2d[i, 1]), xytext=(4, 4),
                    textcoords='offset points', fontsize=6, alpha=0.8)
    ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
    ax.set_title(title, fontsize=9)
    ax.axhline(0, color='gray', lw=0.5, alpha=0.4)
    ax.axvline(0, color='gray', lw=0.5, alpha=0.4)


def _plot_membership_heatmap(ax, data: ChannelData, fit: Fit):
    """Soft memberships (channels x components), channels ordered by depth so
    contiguous depth bands of membership are visible."""
    order = np.argsort(-data.depth_um)
    M = fit.memberships[order]
    im = ax.imshow(M, aspect='auto', cmap='viridis', vmin=0, vmax=1)
    ax.set_xticks(range(fit.k))
    ax.set_xticklabels([f"{i + 1}" for i in range(fit.k)], fontsize=7)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([_channel_label(data.channels[i]) for i in order], fontsize=5)
    ax.set_xlabel("component"); ax.set_ylabel("channel (shallow→deep)")
    ax.set_title(f"{_METHOD_NAME[fit.method]} K={fit.k} memberships", fontsize=9)
    return im


def plot_method_detail(data: ChannelData, sweep: MethodSweep, k: int, save_dir: str):
    """Per-(method, K) figure: probe map + PCA scatter (+ membership heatmap for
    soft methods)."""
    fit = sweep.fits[k]
    is_soft = fit.memberships is not None
    ncols = 3 if is_soft else 2
    fig, axes = plt.subplots(1, ncols, figsize=(4.6 * ncols, 7.5),
                             gridspec_kw={'width_ratios': [1.4, 2] + ([2] if is_soft else [])})
    name = _METHOD_NAME[fit.method]
    _plot_probe_map(axes[0], data, fit.labels, f"{name} K={k}\nprobe map")
    _plot_scatter(axes[1], data, fit.labels, f"{name} K={k}\nresponse PCA space")
    if is_soft:
        im = _plot_membership_heatmap(axes[2], data, fit)
        fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04, label='membership')
    fig.suptitle(f"{name}  —  session {context.ga_database}", fontsize=12)
    fig.text(0.5, 0.005,
             "Probe map = physical depth colored by cluster (contiguous bands ⇒ "
             "spatially-localizable clusters).  Scatter = channels in shared "
             "response-PCA layout.",
             ha='center', va='bottom', fontsize=8, wrap=True)
    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    _save(save_dir, f"{fit.method}_K{k}_detail.png")
    plt.close(fig)


def plot_method_comparison(data: ChannelData, sweeps: dict, k_for_method: dict,
                           save_dir: str):
    """One probe map per method at its auto-selected K, side by side — the
    at-a-glance 'do the methods agree on where the clusters are' figure."""
    methods = list(sweeps)
    fig, axes = plt.subplots(1, len(methods), figsize=(2.3 * len(methods) + 1, 7.5),
                             sharey=True)
    if len(methods) == 1:
        axes = [axes]
    for ax, m in zip(axes, methods):
        k = k_for_method[m]
        _plot_probe_map(ax, data, sweeps[m].fits[k].labels,
                        f"{_METHOD_NAME[m]}\nK={k}")
    fig.suptitle(f"Channel clustering by method (auto-K)  —  {context.ga_database}",
                 fontsize=12)
    plt.tight_layout(rect=[0, 0.02, 1, 0.95])
    _save(save_dir, "method_comparison_probe_maps.png")
    plt.close(fig)


def plot_k_selection(data: ChannelData, sweeps: dict, save_dir: str):
    """The 'how to choose K' figure. One row per criterion:

      row 1  BIC / AIC          (GMM)          — MIN is best
      row 2  silhouette         (all methods)  — MAX is best
      row 3  gap statistic      (per method)   — first K past the knee
      row 4  reconstruction err (NMF/AA) + NMF cophenetic stability

    Each panel marks the recommended K so agreement (or lack of it) is obvious.
    """
    ks = K_RANGE
    fig, axes = plt.subplots(4, 1, figsize=(9, 15))

    # --- BIC / AIC (GMM) ---
    ax = axes[0]
    if 'gmm' in sweeps:
        s = sweeps['gmm']
        bic = [s.fits[k].bic for k in ks]
        aic = [s.fits[k].aic for k in ks]
        ax.plot(ks, bic, 'o-', label='BIC', color='C0')
        ax.plot(ks, aic, 's--', label='AIC', color='C1')
        if 'bic' in s.auto_k:
            ax.axvline(s.auto_k['bic'], color='C0', ls=':', alpha=0.7,
                       label=f"BIC pick K={s.auto_k['bic']}")
        ax.legend(fontsize=8)
    ax.set_title("GMM penalised likelihood — pick K at the MINIMUM "
                 "(BIC = principled automatic default)", fontsize=10)
    ax.set_xlabel("K"); ax.set_ylabel("BIC / AIC (lower better)")
    ax.grid(alpha=0.3)

    # --- silhouette (all) ---
    ax = axes[1]
    for i, (m, s) in enumerate(sweeps.items()):
        sil = [s.scores[k]['silhouette'] for k in ks]
        ax.plot(ks, sil, 'o-', color=f"C{i}", label=_METHOD_NAME[m])
        best = s.auto_k.get('silhouette')
        if best is not None:
            ax.scatter([best], [s.scores[best]['silhouette']], color=f"C{i}",
                       s=140, edgecolors='black', zorder=5)
    ax.set_title("Silhouette — pick K at the MAXIMUM (marked). Common yardstick "
                 "across methods.", fontsize=10)
    ax.set_xlabel("K"); ax.set_ylabel("silhouette (higher better)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # --- gap statistic (per method) ---
    ax = axes[2]
    for i, (m, s) in enumerate(sweeps.items()):
        if s.gap is None:
            continue
        ax.errorbar(s.gap['k'], s.gap['gap'], yerr=s.gap['s'], fmt='o-',
                    color=f"C{i}", capsize=3, label=f"{_METHOD_NAME[m]} "
                    f"(K={s.gap['best_k']})", alpha=0.8)
        ax.axvline(s.gap['best_k'], color=f"C{i}", ls=':', alpha=0.5)
    ax.set_title("Gap statistic — first K past the knee (can justify small K / "
                 "K=1 = no real clusters)", fontsize=10)
    ax.set_xlabel("K"); ax.set_ylabel("gap (higher better)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # --- reconstruction error + NMF cophenetic ---
    ax = axes[3]
    for i, (m, s) in enumerate(sweeps.items()):
        recon = [s.fits[k].recon_error for k in ks]
        if all(r is not None for r in recon):
            ax.plot(ks, recon, 'o-', color=f"C{i}", label=f"{_METHOD_NAME[m]} recon err")
            elbow = s.auto_k.get('recon_elbow')
            if elbow is not None:
                ax.axvline(elbow, color=f"C{i}", ls=':', alpha=0.6)
    ax.set_xlabel("K"); ax.set_ylabel("reconstruction error (lower better)")
    ax.set_title("NMF/AA reconstruction elbow  +  NMF cophenetic stability "
                 "(right axis, higher=more stable)", fontsize=10)
    ax.grid(alpha=0.3)
    if 'nmf' in sweeps and sweeps['nmf'].cophenetic is not None:
        ax2 = ax.twinx()
        coph = [sweeps['nmf'].cophenetic[k] for k in ks]
        ax2.plot(ks, coph, '^--', color='black', label='NMF cophenetic')
        ax2.set_ylabel("cophenetic corr (0–1)")
        ax2.set_ylim(0, 1.02)
        ax2.legend(loc='lower left', fontsize=8)
    ax.legend(loc='upper right', fontsize=8)

    fig.suptitle(f"Choosing K  —  session {context.ga_database}", fontsize=13)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    _save(save_dir, "k_selection.png")
    plt.close(fig)


def _save(save_dir: str, fname: str):
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, fname)
    plt.savefig(path, dpi=140, bbox_inches='tight')
    print(f"  saved {path}")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def _print_auto_k_summary(sweeps: dict, k_for_method: dict):
    print("\n" + "=" * 70)
    print("AUTO-K SUMMARY  (recommended number of clusters per criterion)")
    print("=" * 70)
    header = f"{'method':<22}" + "".join(f"{c:>12}" for c in
             ('bic', 'aic', 'silhouette', 'gap', 'recon_elbow'))
    print(header)
    for m, s in sweeps.items():
        row = f"{_METHOD_NAME[m]:<22}"
        for c in ('bic', 'aic', 'silhouette', 'gap', 'recon_elbow'):
            v = s.auto_k.get(c)
            row += f"{('-' if v is None else v):>12}"
        print(row)
    print("\nChosen K per method (BIC for GMM, silhouette otherwise):")
    for m in sweeps:
        print(f"  {_METHOD_NAME[m]:<22} K = {k_for_method[m]}")
    all_k = list(k_for_method.values())
    consensus = max(set(all_k), key=all_k.count)
    print(f"\nConsensus K across methods: {consensus}")
    print("Trust BIC (GMM) first; use silhouette agreement and the gap "
          "statistic as the reality check.")


def _chosen_k(sweep: MethodSweep) -> int:
    """The single K to draw the detail/comparison figure at: BIC when the method
    has it (GMM), else silhouette, else the middle of the range."""
    for crit in ('bic', 'silhouette', 'gap', 'recon_elbow'):
        if sweep.auto_k.get(crit) is not None:
            return sweep.auto_k[crit]
    return K_RANGE[len(K_RANGE) // 2]


def explore(
        data_loader: DbDataLoader,
        channel_mapper: DBCChannelMapper,
        methods: list = ('kmeans', 'ward', 'gmm', 'nmf', 'aa'),
        k_range: list = K_RANGE,
        session_id: Optional[str] = None,
) -> dict:
    """Fit every method across ``k_range`` for the current experiment and write
    the comparison + K-selection figures. Returns the {method: MethodSweep} dict
    so a caller can inspect labels/memberships programmatically."""
    if session_id is None:
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    save_dir = os.path.join(PLOT_BASE_DIR, session_id, "channel_decomp_explore")
    print(f"Plots → {save_dir}")

    data = load_channel_data(data_loader, channel_mapper)

    sweeps = {}
    for m in methods:
        print(f"\n{'=' * 70}\n{_METHOD_NAME[m]}\n{'=' * 70}")
        sweeps[m] = sweep_method(m, data, k_range)
        print(f"  auto-K: {sweeps[m].auto_k}")

    k_for_method = {m: _chosen_k(s) for m, s in sweeps.items()}

    plot_k_selection(data, sweeps, save_dir)
    plot_method_comparison(data, sweeps, k_for_method, save_dir)
    for m, s in sweeps.items():
        # Draw the auto-K plus its neighbours so K sensitivity is visible.
        for k in sorted({k_for_method[m] - 1, k_for_method[m], k_for_method[m] + 1}
                        & set(k_range)):
            plot_method_detail(data, s, k, save_dir)

    _print_auto_k_summary(sweeps, k_for_method)
    print(f"\nDone. Figures in {save_dir}")
    return sweeps


def main():
    data_loader = DbDataLoader(context.ga_config.connection())
    channel_mapper = DBCChannelMapper("A")
    explore(data_loader, channel_mapper)


if __name__ == '__main__':
    main()


# ===========================================================================
# NEXT STEP — feeding this into analyze_estim_isolation_effect (not done here)
# ===========================================================================
# Once a (method, K) recipe looks right, the metrics worth saving per
# (session_id, estim_spec_id) into EStimParameterData (alongside the existing
# estim_min/mean_isolation_um) are, per active estim channel e:
#
#   * cluster-purity isolation: does e's soft membership (GMM posterior / AA
#     convex weight / NMF part) agree with its estim-channel neighbours? A
#     high, shared membership ⇒ the stimulated set codes alike.
#   * membership margin: max membership − 2nd max, averaged/min over active
#     channels — a soft analogue of the current hard-cluster split penalty that
#     degrades gracefully at cluster boundaries instead of flipping.
#   * silhouette of the active estim channels under the chosen partition.
#
# These would be computed by a small exporter mirroring
# cluster_isolation_score.save_per_spec_isolation_scores, then surfaced as new
# columns/aliases in analyze_estim_isolation_effect.ISOLATION_COLUMNS so the
# existing effect-vs-isolation correlation machinery picks them up unchanged.

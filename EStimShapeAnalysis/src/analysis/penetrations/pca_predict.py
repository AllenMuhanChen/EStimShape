"""PCA / Factor Analysis on penetration metrics + tissue-class prediction.

Two responsibilities:

1. Load PenetrationMetrics into a feature matrix, fit one PCA (or FA) over the
   pooled data, optionally varimax-rotate the top K components, and add PC
   columns to the dataframe.

2. Define `TissueModel` (collections of `TissueClass` + `Evidence`) and
   `compute_tissue_confidence`, which turns PC scores into per-row tissue-class
   probabilities and a single tissue_score in [0, 1].

The `TissuePredictor` protocol at the bottom is the API hook used by
run_pooled.py to compare alternative prediction methods (different TissueModels,
GMMs, logistic regressions, etc.) on the same PC scores.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Protocol

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.stats import pearsonr
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from clat.util.connection import Connection


DECOMPOSITION_METHOD = 'pca'   # 'pca' | 'fa' | 'ica' (factor analysis)
USE_VARIMAX = True             # applies to both PCA and FA
WM_THRESHOLD = 0.0             # z-score WM signal must exceed before counting as WM evidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _within_session_zscore(X: pd.DataFrame, session_ids: pd.Series) -> pd.DataFrame:
    """
    Z-score each feature within each session to remove session-level offsets.
    Preserves within-session depth gradients while eliminating between-session
    mean differences caused by gain, impedance, or tissue-composition bias.
    NaN positions are preserved. Constant columns within a session → 0.
    """
    X_norm = X.copy().astype(float)
    for session in session_ids.unique():
        mask = session_ids == session
        group = X.loc[mask]
        mu = group.mean(skipna=True)
        sigma = group.std(skipna=True, ddof=1).replace(0.0, np.nan)
        normed = ((group - mu) / sigma).fillna(0.0)
        normed[group.isna()] = np.nan
        X_norm.loc[mask] = normed
    return X_norm


def _varimax(Phi, gamma=1.0, q=1000, tol=1e-8):
    """
    Varimax rotation of loadings matrix Phi (n_features × n_components).
    Returns (rotated_loadings, rotation_matrix R) where rotated = Phi @ R.
    Orthogonal rotation — preserves total explained variance across the k components.
    """
    p, k = Phi.shape
    R = np.eye(k)
    d = 0.0
    for _ in range(q):
        d_old = d
        Lambda = Phi @ R
        u, s, vh = np.linalg.svd(
            Phi.T @ (Lambda ** 3 - (gamma / p) * Lambda @ np.diag(np.diag(Lambda.T @ Lambda)))
        )
        R = u @ vh
        d = np.sum(s)
        if d_old != 0 and d / d_old < 1 + tol:
            break
    return Phi @ R, R


class _DecompositionAdapter:
    """Wraps any decomposer (FactorAnalysis, FastICA, ...) to expose the same
    components_ / explained_variance_ratio_ interface that downstream code
    (loadings plots, tissue models) expects from sklearn PCA."""
    def __init__(self, decomposer, X_scores: np.ndarray):
        self.components_ = decomposer.components_
        score_var = np.var(X_scores, axis=0)
        total = score_var.sum() if score_var.sum() > 0 else 1.0
        self.explained_variance_ratio_ = score_var / total
        self._inner = decomposer


# Backwards-compat alias.
_FactorAnalysisAdapter = _DecompositionAdapter


def _add_nmf_complements(X_scaled, feature_columns, which):
    """Append 1 - x complement columns so NMF can represent "low feature" as a
    positive loading (it otherwise only encodes "high").

    X_scaled must be in [0, 1] (MinMax space) so the complement stays >= 0.
    `which` is 'all' (complement every feature) or a list of feature names.
    Returns (X_expanded, feature_columns_expanded). Complements are named
    `<feat>__low`; a high value there means the feature is LOW.
    """
    names = list(feature_columns)
    idx = {f: i for i, f in enumerate(feature_columns)}
    if which == 'all':
        targets = list(feature_columns)
    else:
        targets = [f for f in which if f in idx]
        missing = [f for f in which if f not in idx]
        if missing:
            print(f"  nmf_complement: unknown features ignored: {missing}")
    if not targets:
        return X_scaled, names
    comp = np.column_stack([1.0 - X_scaled[:, idx[f]] for f in targets])
    X_expanded = np.column_stack([X_scaled, comp])
    names = names + [f"{f}__low" for f in targets]
    print(f"  NMF complement: added {len(targets)} inverted feature(s) "
          f"→ {X_expanded.shape[1]} total columns")
    return X_expanded, names


# ---------------------------------------------------------------------------
# Archetypal analysis (self-contained — no external dependency)
# ---------------------------------------------------------------------------

class _ArchetypeModel:
    """Minimal shim exposing `.components_` (the archetypes) so an AA fit can be
    wrapped by `_DecompositionAdapter` and flow through the loadings/scree code
    exactly like a PCA/NMF result."""
    def __init__(self, archetypes: np.ndarray):
        self.components_ = archetypes


def _simplex_project(V: np.ndarray) -> np.ndarray:
    """Project each ROW of V onto the probability simplex {x >= 0, sum = 1}.

    Vectorised Duchi et al. (2008) algorithm. Used to keep the archetypal-
    analysis weight matrices convex after each gradient step.
    """
    V = np.asarray(V, dtype=float)
    n, d = V.shape
    U = np.sort(V, axis=1)[:, ::-1]
    cssv = np.cumsum(U, axis=1) - 1.0
    ind = np.arange(1, d + 1)
    cond = (U - cssv / ind) > 0
    rho = cond.sum(axis=1)
    theta = cssv[np.arange(n), rho - 1] / rho
    return np.maximum(V - theta[:, None], 0.0)


def _archetypal_analysis(
        X: np.ndarray,
        n_archetypes: int,
        n_iter: int = 400,
        tol: float = 1e-7,
        seed: int = 42,
) -> tuple:
    """Archetypal analysis:  X ≈ A @ Z,  Z = B @ X, with the rows of both A and
    B constrained to the probability simplex (non-negative, sum to 1).

    Each archetype (row of Z) is a convex combination of real data points — an
    "extreme" prototype — and each sample (row of A) is a convex mixture of
    archetypes. Unlike PCA there is no negative end: a component is present
    (weight up to 1) or absent (0), so with k archetypes you get one axis per
    prototype (e.g. sulcus / WM / GM) and A reads as a soft membership.

    Projected-gradient with an adaptive step size and backtracking, so the
    reconstruction error decreases monotonically (Mørup & Hansen PCHA style).

    Returns
    -------
    (A, Z) : A is (n_samples, k) convex scores; Z is (k, n_features) archetypes.
    """
    rng = np.random.default_rng(seed)
    n, m = X.shape
    k = int(n_archetypes)

    # Initialise archetypes at k distinct data rows; weights roughly uniform.
    idx = rng.choice(n, size=k, replace=False)
    B = np.zeros((k, n)); B[np.arange(k), idx] = 1.0
    Z = B @ X
    A = _simplex_project(rng.random((n, k)))

    def rss(A_, Z_):
        R = X - A_ @ Z_
        return float(np.sum(R * R))

    prev = rss(A, Z)
    muA = muB = 1.0
    for _ in range(n_iter):
        # --- update A with Z fixed:  grad = 2 (A Z - X) Zᵀ ---
        G = 2.0 * (A @ Z - X) @ Z.T
        step = muA / (np.linalg.norm(G) / np.sqrt(n) + 1e-12)
        A_new = _simplex_project(A - step * G)
        r = rss(A_new, Z)
        if r <= prev:
            A, prev, muA = A_new, r, muA * 1.2
        else:
            muA *= 0.5

        # --- update B (hence Z = B X) with A fixed:
        #     L = ||X - A B X||²;  grad_Z = 2 Aᵀ (A Z - X);  grad_B = grad_Z Xᵀ ---
        gB = (2.0 * A.T @ (A @ Z - X)) @ X.T
        step = muB / (np.linalg.norm(gB) / np.sqrt(k) + 1e-12)
        B_new = _simplex_project(B - step * gB)
        Z_new = B_new @ X
        r = rss(A, Z_new)
        if r <= prev:
            B, Z, prev, muB = B_new, Z_new, r, muB * 1.2
        else:
            muB *= 0.5

        if muA < 1e-10 and muB < 1e-10:
            break
    return A, Z


# ---------------------------------------------------------------------------
# Pooled decomposition over all sessions
# ---------------------------------------------------------------------------

def load_and_perform_pca(
        conn: Connection,
        table_name: str = "PenetrationMetrics",
        exclude_sessions: Optional[list] = None,
        within_session_normalize: bool = True,
        pc_smooth_sigma: float = 2.0,
        n_components: Optional[int] = None,
        varimax_n_components: Optional[int] = 6,
        decomp_method: str = DECOMPOSITION_METHOD,
        use_varimax: bool = USE_VARIMAX,
        exclude_features: Optional[list] = None,
        nmf_complement=None,
):
    """Load data and run a pooled decomposition across all sessions.

    Parameters
    ----------
    decomp_method : {'pca', 'fa', 'ica', 'nmf', 'aa', 'gmm'}
        - 'pca'  : sklearn PCA (linear, orthogonal, ranked by variance).
        - 'fa'   : sklearn FactorAnalysis (latent-variable model).
        - 'ica'  : sklearn FastICA (independent components — already
                   sparse-like; varimax is ignored when use_varimax=True).
        - 'nmf'  : sklearn NMF — non-negative, parts-based. Each component is
                   an additive feature signature and scores are >= 0, so a
                   component is "present" (high) or "absent" (~0) rather than a
                   two-ended axis. Features are MinMax-scaled to [0, 1] instead
                   of StandardScaler'd (NMF requires X >= 0). Varimax ignored.
        - 'aa'   : Archetypal analysis (self-contained) — X ≈ A·Z with A and the
                   archetype weights convex. Each archetype is an extreme
                   prototype (e.g. pure sulcus / WM / GM) and each row of A is a
                   soft membership summing to 1. Also MinMax-scaled; varimax
                   ignored. explained_variance_ratio_ is a score-variance
                   heuristic for NMF/AA, not true explained variance.
        - 'gmm'  : Gaussian Mixture Model — soft clustering. components_ are the
                   cluster means (SIGNED, StandardScaler space, so direction is
                   captured natively — no feature inversion needed), and scores
                   are per-bin posterior memberships (>= 0, sum to 1). Uses
                   StandardScaler (Gaussian assumption); varimax ignored.
    n_components : total number of components to extract. None means:
        all features for PCA; varimax_n_components (or all features) for
        FA / ICA. Set this explicitly to decouple "how many components"
        from "how many to varimax-rotate".
    varimax_n_components : how many of the extracted components get
        varimax-rotated. Defaults to 6; capped at n_components. Ignored
        for ICA (already a rotation method).
    use_varimax : enable varimax rotation. Has no effect for ICA.
    exclude_features : list of column names to drop from the feature
        matrix before fitting. Useful when iterating to see how a single
        metric (or group of metrics) influences the components. The
        primary keys (session_id, depth_under_chamber_mm) and r_squared
        are always excluded; this extends that list.
    nmf_complement : NMF-only. NMF can only encode "feature is high" (loadings
        are >= 0), so a "low X -> tissue" pattern has no positive loading to
        land on. This appends a complement column (1 - x, in the [0,1] MinMax
        space) so "low" becomes a high value NMF can load on positively.
          - None  : off (default).
          - 'all' : double-encode every feature (adds a `<feat>__low` for each);
                    lets NMF discover which end of each feature matters.
          - list  : add `<feat>__low` only for the named features.
        The original column `<feat>` still means "high"; `<feat>__low` means
        "low". Ignored for every method except NMF.

    Returns
    -------
    (df_with_PCs, pca_or_adapter, X_pca, feature_columns, scaler)
        df has PC1..PCk columns added, where k = n_components actually used.
    """
    conn.execute(f"SELECT * FROM {table_name}")
    results = conn.fetch_all()

    conn.execute(f"DESCRIBE {table_name}")
    columns = [row[0] for row in conn.fetch_all()]

    df = pd.DataFrame(results, columns=columns)
    if exclude_sessions is not None:
        df = df[~df['session_id'].isin(exclude_sessions)].copy()

    print(f"Loaded {len(df)} rows with columns: {list(df.columns)}")

    pk_columns = ['session_id', 'depth_under_chamber_mm']
    exclude_columns = pk_columns + ['r_squared']
    if exclude_features:
        user_excluded = list(exclude_features)
        unknown = [c for c in user_excluded if c not in df.columns]
        if unknown:
            print(f"  WARNING: exclude_features contains columns not in the "
                  f"table — ignoring: {unknown}")
        exclude_columns = exclude_columns + [c for c in user_excluded if c in df.columns]
        print(f"  User-excluded features: "
              f"{[c for c in user_excluded if c in df.columns]}")
    feature_columns = [
        col for col in df.columns
        if col not in exclude_columns
           and pd.api.types.is_numeric_dtype(df[col])
    ]

    print(f"Feature columns for decomposition ({len(feature_columns)}): "
          f"{feature_columns}")

    X = df[feature_columns].copy()
    X = X.fillna(X.mean())

    valid_mask = ~X.isna().any(axis=1)
    X = X[valid_mask]
    df_valid = df[valid_mask].copy()

    print(f"Using {len(X)} rows after handling missing values")

    if within_session_normalize:
        print("\nApplying within-session z-score normalization ...")
        X = _within_session_zscore(X, df_valid['session_id'])
        print(f"  Grand mean after normalization: {X.mean().mean():+.4f}  (should be ≈ 0)")

    if decomp_method in ('nmf', 'aa'):
        # NMF needs X >= 0, and both NMF and AA want features on comparable
        # scales. MinMaxScaler maps each feature to [0, 1]; combined with the
        # optional within-session z-score above this keeps session harmonisation
        # while satisfying the non-negativity constraint. (StandardScaler would
        # produce negatives and break NMF.)
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
    else:
        scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # NMF-only: append inverted (1 - x) columns so "low feature" hypotheses can
    # load positively. feature_columns is extended to match so loadings line up.
    if decomp_method == 'nmf' and nmf_complement:
        X_scaled, feature_columns = _add_nmf_complements(
            X_scaled, feature_columns, nmf_complement)

    # Resolve n_components.
    n_features = X_scaled.shape[1]
    if n_components is None:
        if decomp_method == 'pca':
            n_components_eff = n_features
        else:
            n_components_eff = varimax_n_components or n_features
    else:
        n_components_eff = min(int(n_components), n_features)

    if decomp_method == 'pca':
        print(f"\nUsing PCA (n_components={n_components_eff}) ...")
        pca = PCA(n_components=n_components_eff if n_components is not None else None)
        X_pca = pca.fit_transform(X_scaled)
    elif decomp_method == 'fa':
        print(f"\nUsing Factor Analysis (n_components={n_components_eff}) ...")
        fa = FactorAnalysis(n_components=n_components_eff, random_state=42)
        X_pca = fa.fit_transform(X_scaled)
        pca = _DecompositionAdapter(fa, X_pca)
    elif decomp_method == 'ica':
        from sklearn.decomposition import FastICA
        print(f"\nUsing FastICA (n_components={n_components_eff}) ...")
        ica = FastICA(n_components=n_components_eff, random_state=42,
                      max_iter=2000, tol=1e-4, whiten='unit-variance')
        X_pca = ica.fit_transform(X_scaled)
        pca = _DecompositionAdapter(ica, X_pca)
        if use_varimax:
            print("  (ignoring use_varimax=True — ICA components are already rotated)")
            use_varimax = False
    elif decomp_method == 'nmf':
        from sklearn.decomposition import NMF
        print(f"\nUsing NMF (n_components={n_components_eff}) ...")
        nmf = NMF(n_components=n_components_eff, init='nndsvda',
                  random_state=42, max_iter=2000)
        X_pca = nmf.fit_transform(X_scaled)          # scores W >= 0
        pca = _DecompositionAdapter(nmf, X_pca)      # components_ = H (parts)
        if use_varimax:
            print("  (ignoring use_varimax=True — NMF gives non-negative parts; "
                  "rotation would reintroduce signed/cancelling components)")
            use_varimax = False
    elif decomp_method == 'aa':
        print(f"\nUsing Archetypal Analysis (n_components={n_components_eff}) ...")
        A, Z = _archetypal_analysis(X_scaled, n_components_eff)
        X_pca = A                                    # convex mixture weights >= 0
        pca = _DecompositionAdapter(_ArchetypeModel(Z), X_pca)  # components_ = archetypes
        if use_varimax:
            print("  (ignoring use_varimax=True — AA components are archetypes; "
                  "rotation is not applicable)")
            use_varimax = False
    elif decomp_method == 'gmm':
        print(f"\nUsing Gaussian Mixture Model (n_components={n_components_eff}) ...")
        gmm = GaussianMixture(n_components=n_components_eff, covariance_type='full',
                              reg_covar=1e-4, n_init=10, random_state=42)
        gmm.fit(X_scaled)
        X_pca = gmm.predict_proba(X_scaled)          # (n, K) posterior memberships, sum to 1
        # components_ = cluster means (SIGNED, in StandardScaler space): a cluster's
        # mean is above/below each feature's average, so direction is captured
        # natively — no feature inversion needed (unlike NMF).
        pca = _DecompositionAdapter(_ArchetypeModel(gmm.means_), X_pca)
        if use_varimax:
            print("  (ignoring use_varimax=True — GMM components are clusters, "
                  "not rotatable loadings)")
            use_varimax = False
    else:
        raise ValueError(
            f"Unknown decomp_method {decomp_method!r}. "
            f"Choose 'pca', 'fa', 'ica', 'nmf', 'aa', or 'gmm'.")

    if use_varimax and varimax_n_components and varimax_n_components > 1:
        n_rot = min(varimax_n_components, X_pca.shape[1])
        loadings_k = pca.components_[:n_rot].T
        _, R = _varimax(loadings_k)
        X_pca_rot = X_pca[:, :n_rot] @ R
        order = np.argsort(-np.var(X_pca_rot, axis=0))
        X_pca_rot = X_pca_rot[:, order]
        X_pca[:, :n_rot] = X_pca_rot
        print(f"\nVarimax rotation applied to first {n_rot} components "
              f"(re-ordered by variance).")

    for i in range(X_pca.shape[1]):
        df_valid[f'PC{i + 1}'] = X_pca[:, i]

    if pc_smooth_sigma > 0:
        print(f"\nSmoothing PC scores per session (σ={pc_smooth_sigma} depth bins) ...")
        pc_cols = [f'PC{i + 1}' for i in range(X_pca.shape[1])]
        for session in df_valid['session_id'].unique():
            mask = df_valid['session_id'] == session
            sdata = df_valid.loc[mask].sort_values('depth_under_chamber_mm')
            for pc_col in pc_cols:
                smoothed = gaussian_filter1d(sdata[pc_col].values.astype(float),
                                             sigma=pc_smooth_sigma)
                df_valid.loc[sdata.index, pc_col] = smoothed

    print("\nExplained variance ratio:")
    cumulative = 0
    for i, var in enumerate(pca.explained_variance_ratio_):
        cumulative += var
        print(f"  PC{i + 1}: {var:.3f} ({var * 100:.1f}%) | Cumulative: {cumulative * 100:.1f}%")

    return df_valid, pca, X_pca, feature_columns, scaler


def get_loadings_df(pca: PCA, feature_columns: list) -> pd.DataFrame:
    """Get PCA loadings as a DataFrame."""
    return pd.DataFrame(
        pca.components_.T,
        columns=[f'PC{i + 1}' for i in range(len(pca.components_))],
        index=feature_columns,
    )


def get_feature_correlations(
        df: pd.DataFrame,
        feature_columns: list,
        n_pcs: Optional[int] = None,
) -> pd.DataFrame:
    """Calculate correlations between original features and PC scores."""
    pc_columns = [col for col in df.columns if col.startswith('PC')]
    if n_pcs is not None:
        pc_columns = pc_columns[:n_pcs]

    results = []
    for pc_col in pc_columns:
        for feature in feature_columns:
            if feature in df.columns:
                valid = df[[pc_col, feature]].dropna()
                if len(valid) > 2:
                    r, p = pearsonr(valid[pc_col], valid[feature])
                    results.append({
                        'PC': pc_col,
                        'Feature': feature,
                        'Correlation': r,
                        'p_value': p,
                    })
    return pd.DataFrame(results)


def print_feature_correlations(corr_df: pd.DataFrame):
    """Print feature correlations in a nice format."""
    print("\n" + "=" * 60)
    print("FEATURE CORRELATIONS WITH PCs")
    print("=" * 60)
    for pc in corr_df['PC'].unique():
        pc_data = corr_df[corr_df['PC'] == pc].copy()
        pc_data = pc_data.sort_values('Correlation', key=abs, ascending=False)
        print(f"\n{pc}:")
        for _, row in pc_data.iterrows():
            sig = '*' if row['p_value'] < 0.05 else ''
            sig = '**' if row['p_value'] < 0.01 else sig
            sig = '***' if row['p_value'] < 0.001 else sig
            print(f"  {row['Feature']:<25} r = {row['Correlation']:>7.3f} (p = {row['p_value']:<8.4f}) {sig}")


# ---------------------------------------------------------------------------
# Cortex (second-stage) PCA
# ---------------------------------------------------------------------------

def run_cortex_pca(
        df_conf: pd.DataFrame,
        feature_columns: list,
        n_pcs: int = 4,
        tissue_score_min: float = 0.3,
        tissue_score_max: float = 0.75,
        save_dir: Optional[str] = None,
) -> Optional[dict]:
    """
    Second-stage PCA on cortical gray-matter bins only.
    Plotting is performed by penetration_plots.plot_cortex_pca_diagnostics
    after this function returns.
    """
    if 'tissue_score' not in df_conf.columns:
        print("run_cortex_pca: tissue_score column missing — run compute_tissue_confidence first.")
        return None

    mask = (df_conf['tissue_score'] >= tissue_score_min) & \
           (df_conf['tissue_score'] <= tissue_score_max)
    df_ctx = df_conf[mask].copy()
    n_ctx = int(mask.sum())
    print(f"\nCortex PCA: {n_ctx} / {len(df_conf)} bins in "
          f"tissue_score [{tissue_score_min}, {tissue_score_max}]")

    if n_ctx < max(10, len(feature_columns)):
        print("  Too few cortical bins — skipping cortex PCA.")
        return None

    X = df_ctx[feature_columns].copy()
    X = X.fillna(X.mean())
    valid = ~X.isna().any(axis=1)
    X = X[valid]
    df_ctx = df_ctx[valid].copy()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca_ctx = PCA()
    X_pca = pca_ctx.fit_transform(X_scaled)

    n_pcs_act = min(n_pcs, X_pca.shape[1])
    for i in range(n_pcs_act):
        df_ctx[f'CPC{i + 1}'] = X_pca[:, i]

    print("\nCortex PCA explained variance:")
    cum = 0.0
    for i, v in enumerate(pca_ctx.explained_variance_ratio_[:n_pcs_act]):
        cum += v
        print(f"  CPC{i + 1}: {v:.3f} ({v * 100:.1f}%)  cumulative {cum * 100:.1f}%")

    # Delegate plotting to penetration_plots (kept here as a soft dep to avoid cycles
    # if a caller only wants the fit).
    if save_dir is not None:
        from src.analysis.penetrations.penetration_plots import plot_cortex_pca_diagnostics
        plot_cortex_pca_diagnostics(
            df_ctx, pca_ctx, feature_columns, n_pcs_act,
            tissue_score_min, tissue_score_max, save_dir,
        )

    return {
        'pca': pca_ctx,
        'df_ctx': df_ctx,
        'feature_columns': feature_columns,
        'X_pca': X_pca,
        'scaler': scaler,
        'n_pcs': n_pcs_act,
    }


# ---------------------------------------------------------------------------
# Tissue model + per-row classification
# ---------------------------------------------------------------------------

@dataclass
class Evidence:
    """One PC's contribution to a tissue class logit.

    sign=+1  means high PC value → supports this class.
    sign=-1  means low  PC value → supports this class.
    weight   scales the contribution relative to other evidence in the same class.
    """
    pc: str
    sign: int = 1
    weight: float = 1.0


@dataclass
class TissueClass:
    """One tissue class with its 1-D score and list of PC evidence.

    combine='avg'  (default) : weighted average of evidence terms → one sigmoid.
                               Evidence terms cancel each other (AND-like).
    combine='or'             : noisy-OR — each term independently → sigmoid,
                               then 1 − ∏(1 − p_i).  Any strong positive term
                               is sufficient; absent terms don't cancel.
    """
    name: str
    score: float
    evidence: List[Evidence] = field(default_factory=list)
    threshold: float = 0.0
    combine: str = 'avg'


@dataclass
class TissueModel:
    """Complete tissue model: an ordered list of TissueClass objects."""
    classes: List[TissueClass]

    def all_pcs(self) -> List[str]:
        seen, pcs = set(), []
        for tc in self.classes:
            for ev in tc.evidence:
                if ev.pc not in seen:
                    seen.add(ev.pc)
                    pcs.append(ev.pc)
        return pcs


# PC1: + = brain, − = sulcus
# PC2: + = GM,    − = WM
# PC4: + = sulcus, − = brain
MODEL_PCA_V1 = TissueModel([
    TissueClass('wm',     score=1.0, combine='avg', threshold=0.5, evidence=[
        Evidence('PC2', sign=-1),
        Evidence('PC4', sign=-1),
        Evidence('PC3', sign=1),
        Evidence('PC5', sign=1),
    ]),
    TissueClass('gm',     score=0.5, combine='avg', threshold=0.5, evidence=[
        Evidence('PC2', sign=+1),
        Evidence('PC4', sign=-1),
        Evidence('PC3', sign=-1),
        Evidence('PC5', sign=-1),
    ]),
    TissueClass('sulcus', score=0.0, combine='or', threshold=0.5, evidence=[
        Evidence('PC4', sign=+1),
    ]),
])


# 2-component model for varimax_n_components=2 runs.
# PC1: + = sulcus, − = GM
# PC2: + = WM,     − = GM
MODEL_PCA_V2 = TissueModel([
    TissueClass('wm',     score=1.0, evidence=[
        Evidence('PC1', sign=+1),
        Evidence('PC2', sign=-1),
    ]),
    TissueClass('gm',     score=0.5, evidence=[
        Evidence('PC1', sign=+1),
        Evidence('PC2', sign=+1),
    ]),
    TissueClass('sulcus', score=0.0, evidence=[
        Evidence('PC1', sign=-1),
    ]),
])

# FOR USE WITH PCA WITH FOOF PREPROCESSING
MODEL_PCA_V3 = TissueModel([
    TissueClass('wm', score=1.0, evidence=[
        Evidence('PC1', sign=-1),
        Evidence('PC2', sign=+1),
    ]),
    TissueClass('gm', score=0.5, evidence=[
        Evidence('PC1', sign=+1),
        Evidence('PC2', sign=+1),
    ]),
    TissueClass('sulcus', score=0.0, evidence=[
        Evidence('PC2', sign=-1),
    ]),
])

# For PCA with Varimax, 4 pcs
MODEL_PCA_V4 = TissueModel([
    TissueClass('wm',     score=1.0, evidence=[
        Evidence('PC1', sign=+1),
        Evidence('PC2', sign=-1),
        Evidence('PC3', sign=+1),
        Evidence('PC4', sign=-1),
    ]),
    TissueClass('gm',     score=0.5, evidence=[
        Evidence('PC1', sign=+1),
        Evidence('PC2', sign=+1),
        Evidence('PC3', sign=+1),
        Evidence('PC4', sign=+1),
    ]),
    TissueClass('sulcus', score=0.0, evidence=[
        Evidence('PC3', sign=-1),
        Evidence('PC1', sign=-1)
    ]),
])

MODEL_ICA_V1 = TissueModel([
    TissueClass('wm', score=1.0, evidence=[
        Evidence('PC1', sign=+1),
        Evidence('PC2', sign=+1)
    ]),
    TissueClass('gm', score=0.5, evidence=[
        Evidence('PC1', sign=-1),
        Evidence('PC2', sign=+1)
    ]),
    TissueClass('sulcus', score=0.0, evidence=[
        Evidence('PC2', sign=-1),
    ])
])
# Legacy column-mapping dicts (kept for backward compat with old call sites)
_TISSUE_CONF_PCA              = dict(wm_col='PC1', wm2_col='PC3', wm2_sign=1,  gm_col='PC2', sulcus_col='PC4')
_TISSUE_CONF_FA_VARIMAX       = dict(wm_col='PC2', wm2_col='PC3', wm2_sign=-1, gm_col='PC1', sulcus_col='PC5')
_TISSUE_CONF_FA_NO_VARIMAX    = dict(wm_col='PC2', wm2_col=None,               gm_col='PC1', sulcus_col='PC5')


def _gmm_brain_threshold(pc1_values: np.ndarray) -> float:
    """Fit a 2-component GMM to PC1 and return crossover point P(brain) = 0.5."""
    gmm = GaussianMixture(n_components=2, random_state=42, n_init=5)
    gmm.fit(pc1_values.reshape(-1, 1))

    brain_comp  = int(np.argmax(gmm.means_.flatten()))
    x = np.linspace(pc1_values.min(), pc1_values.max(), 10_000).reshape(-1, 1)
    p_brain_x   = gmm.predict_proba(x)[:, brain_comp]

    crossings = np.where(np.diff(p_brain_x > 0.5))[0]
    threshold = float(x[crossings[0]]) if len(crossings) > 0 else 0.0
    print(f"  GMM brain threshold (PC1 = {threshold:.3f}): "
          f"means={gmm.means_.flatten().round(2)}, "
          f"weights={gmm.weights_.round(2)}")
    return threshold


def compute_tissue_confidence(
        df: pd.DataFrame,
        model: Optional[TissueModel] = None,
        # legacy kwargs
        wm_col: str = 'PC1',
        wm2_col: Optional[str] = 'PC3',
        wm2_sign: int = 1,
        gm_col: str = 'PC2',
        sulcus_col: str = 'PC4',
        wm_threshold: float = WM_THRESHOLD,
) -> pd.DataFrame:
    """
    Flexible tissue classification using a TissueModel, or legacy column kwargs.

    Adds columns:
      p_<classname>    : softmax probability for each class
      tissue_score     : weighted sum of class scores by probability (0–1)
      tissue_confidence: max class probability
    """
    from scipy.special import expit as _sigmoid

    df = df.copy()

    if model is not None:
        pc_stds = {pc: df[pc].std() for pc in model.all_pcs()}

        class_logits = []
        for tc in model.classes:
            n_ev = len(tc.evidence)
            if n_ev == 0:
                class_logits.append(np.zeros(len(df)))
                continue

            ev_logits = np.stack([
                ev.sign * ev.weight * df[ev.pc].values / max(pc_stds[ev.pc], 1e-9)
                for ev in tc.evidence
            ], axis=1)

            if tc.combine == 'or':
                class_logit = ev_logits.max(axis=1) - tc.threshold
            else:
                weights = np.array([ev.weight for ev in tc.evidence])
                class_logit = (ev_logits * weights).sum(axis=1) / weights.sum() - tc.threshold

            class_logits.append(class_logit)

        logits_arr = np.stack(class_logits, axis=1)

        shifted = logits_arr - logits_arr.max(axis=1, keepdims=True)
        exp_l   = np.exp(shifted)
        probs_arr = exp_l / exp_l.sum(axis=1, keepdims=True)

        for i, tc in enumerate(model.classes):
            df[f'p_{tc.name}'] = probs_arr[:, i]

        df['tissue_score']      = sum(tc.score * probs_arr[:, i]
                                      for i, tc in enumerate(model.classes))
        df['tissue_confidence'] = probs_arr.max(axis=1)
        return df

    # legacy path
    std_wm     = df[wm_col].std()
    std_gm     = df[gm_col].std()
    std_sulcus = df[sulcus_col].std()

    if wm2_col is not None:
        std_wm2  = df[wm2_col].std()
        wm_score = (df[wm_col].values / std_wm + wm2_sign * df[wm2_col].values / std_wm2) / 2
    else:
        wm_score = df[wm_col].values / std_wm

    gm_score     = df[gm_col].values     / std_gm
    sulcus_score = df[sulcus_col].values / std_sulcus

    c_wm     = _sigmoid(wm_score     - wm_threshold)
    c_gm     = _sigmoid(gm_score)
    c_sulcus = _sigmoid(sulcus_score)

    total = c_wm + c_gm + c_sulcus
    p_wm     = c_wm     / total
    p_gm     = c_gm     / total
    p_sulcus = c_sulcus / total

    df['p_wm']     = p_wm
    df['p_gm']     = p_gm
    df['p_sulcus'] = p_sulcus

    df['tissue_score']      = 1.0 * p_wm + 0.5 * p_gm
    df['tissue_confidence'] = np.stack([p_wm, p_gm, p_sulcus], axis=1).max(axis=1)
    return df


# ---------------------------------------------------------------------------
# TissuePredictor / TissuePipeline — API for run_pooled comparisons + run_per_session
# ---------------------------------------------------------------------------

class TissuePredictor(Protocol):
    """A callable that adds `tissue_score` (and optional p_* / tissue_confidence)
    columns to a dataframe already containing PC scores.

    Implementations need:
      - .name : short identifier shown in plots and tables
      - .predict(df) -> df : returns a NEW dataframe with prediction columns added
    """
    name: str

    def predict(self, df: pd.DataFrame) -> pd.DataFrame: ...


@dataclass
class TissueModelPredictor:
    """Adapter: wrap a `TissueModel` as a `TissuePredictor`.

    Note: as of the TissuePipeline refactor this only handles the
    (PC scores -> tissue scores) half. Prefer TissuePipeline when you
    also need to specify the decomposition recipe — that's the unit
    that plugs into run_pooled.compare_pipelines_on_corrections and
    run_per_session.run_analysis.
    """
    name: str
    model: TissueModel

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        return compute_tissue_confidence(df, model=self.model)


@dataclass
class TissuePipeline:
    """A complete tissue-prediction recipe: raw features -> decomposition -> tissue scores.

    Owns every choice that affects predictions, so two pipelines with
    different decomp methods (e.g. PCA-V2 vs ICA-V1) can be compared
    side-by-side in a single run_pooled call — each fits its own
    decomposition independently.

    Fields
    ------
    name              : short identifier used in plot labels / save_dir / summary.
    model             : TissueModel (or None to skip the prediction step, e.g.
                        for decomposition-only diagnostic runs).
    decomp_method     : 'pca' | 'fa' | 'ica'.
    n_components      : total components to extract. None preserves the
                        per-method default (all features for PCA;
                        varimax_n_components for FA/ICA).
    varimax_n_components : how many to varimax-rotate. None means rotate all
                        n_components.
    use_varimax       : enable varimax. Has no effect for ICA.
    within_session_normalize : z-score features per session before decomposition.
    pc_smooth_sigma   : gaussian smoothing of PC scores vs depth (per session).
    exclude_features  : column names to drop from the feature matrix.

    Methods
    -------
    fit_decomposition(conn, ...) -> (df_with_PCs, pca, X_pca, feature_columns, scaler)
    predict(df_with_PCs)         -> df_with_tissue_score
    fit_and_predict(conn, ...)   -> the two above in one shot, returns a dict.
    """
    name: str
    model: Optional[TissueModel] = None
    decomp_method: str = 'pca'
    n_components: Optional[int] = None
    varimax_n_components: Optional[int] = None
    use_varimax: bool = True
    within_session_normalize: bool = False
    pc_smooth_sigma: float = 2.0
    exclude_features: list = field(default_factory=list)

    def fit_decomposition(
            self,
            conn: Connection,
            table_name: str = "PenetrationMetrics",
            exclude_sessions: Optional[list] = None,
    ):
        return load_and_perform_pca(
            conn, table_name,
            exclude_sessions=exclude_sessions,
            within_session_normalize=self.within_session_normalize,
            pc_smooth_sigma=self.pc_smooth_sigma,
            n_components=self.n_components,
            varimax_n_components=self.varimax_n_components,
            decomp_method=self.decomp_method,
            use_varimax=self.use_varimax,
            exclude_features=self.exclude_features,
        )

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.model is None:
            raise RuntimeError(
                f"TissuePipeline {self.name!r} has model=None — call "
                "fit_decomposition only, or set a TissueModel before predicting."
            )
        return compute_tissue_confidence(df, model=self.model)

    def fit_and_predict(
            self,
            conn: Connection,
            table_name: str = "PenetrationMetrics",
            exclude_sessions: Optional[list] = None,
    ) -> dict:
        df, pca, X_pca, feature_columns, scaler = self.fit_decomposition(
            conn, table_name, exclude_sessions,
        )
        out = {'df': df, 'pca': pca, 'X_pca': X_pca,
               'feature_columns': feature_columns, 'scaler': scaler}
        if self.model is not None:
            out['df'] = self.predict(df)
        return out

    def tag(self) -> str:
        """Compact filename-safe tag describing the decomposition config."""
        norm_tag = 'T' if self.within_session_normalize else 'F'
        vm_tag   = 'T' if self.use_varimax else 'F'
        ncomp = self.n_components if self.n_components is not None else (
            self.varimax_n_components or 'all')
        parts = [self.decomp_method, f"{ncomp}pcs",
                 f"vm{vm_tag}", f"norm{norm_tag}",
                 f"sig{self.pc_smooth_sigma:.1f}"]
        if self.exclude_features:
            parts.append(f"excl{len(self.exclude_features)}")
        return "_".join(str(p) for p in parts)

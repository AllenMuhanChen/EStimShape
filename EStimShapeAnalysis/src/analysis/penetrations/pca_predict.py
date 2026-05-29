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


DECOMPOSITION_METHOD = 'pca'   # 'pca' | 'fa'  (factor analysis)
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
):
    """Load data and run a pooled decomposition across all sessions.

    Parameters
    ----------
    decomp_method : {'pca', 'fa', 'ica'}
        - 'pca'  : sklearn PCA (linear, orthogonal, ranked by variance).
        - 'fa'   : sklearn FactorAnalysis (latent-variable model).
        - 'ica'  : sklearn FastICA (independent components — already
                   sparse-like; varimax is ignored when use_varimax=True).
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

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

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
    else:
        raise ValueError(
            f"Unknown decomp_method {decomp_method!r}. "
            f"Choose 'pca', 'fa', or 'ica'.")

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
    TissueClass('wm',     score=1.0, combine='or', evidence=[
        Evidence('PC2', sign=-1),
        Evidence('PC4', sign=+1),
    ]),
    TissueClass('gm',     score=0.5, evidence=[
        Evidence('PC2', sign=+1),
        Evidence('PC4', sign=-1),
    ]),
    TissueClass('sulcus', score=0.0, evidence=[
        Evidence('PC3', sign=-1),
    ]),
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
# TissuePredictor abstraction — API hook for run_pooled predictor comparison
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
    """Adapter: wrap a `TissueModel` as a `TissuePredictor`."""
    name: str
    model: TissueModel

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        return compute_tissue_confidence(df, model=self.model)

import importlib.util
import json
import os
from typing import Optional

from sklearn.mixture import GaussianMixture

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.ndimage import map_coordinates, gaussian_filter1d
from scipy.special import softmax as _softmax, expit as _sigmoid
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA, FactorAnalysis
from scipy.stats import pearsonr
from itertools import combinations

from clat.util.connection import Connection

OPTIMIZATIONS_path = "/home/connorlab/Documents/MRI/optimizations"

MRI_VIEWER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../../mri/mri_viewer_config.json')


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


DECOMPOSITION_METHOD = 'pca'   # 'pca' | 'fa'  (factor analysis)
USE_VARIMAX = True             # applies to both PCA and FA
WM_THRESHOLD = 0.5            # z-score WM signal must exceed before counting as WM evidence
                               # raise to reduce WM overestimation (0.0 = old behavior)

# Tissue model column mapping — pick the right dict for your decomp_method + varimax setting
# wm2_col=None → use wm_col alone (no second WM indicator)
_TISSUE_CONF_PCA              = dict(wm_col='PC1', wm2_col='PC3', wm2_sign=1,  gm_col='PC2', sulcus_col='PC4')
_TISSUE_CONF_FA_VARIMAX       = dict(wm_col='PC2', wm2_col='PC3', wm2_sign=-1, gm_col='PC1', sulcus_col='PC5')
_TISSUE_CONF_FA_NO_VARIMAX    = dict(wm_col='PC2', wm2_col=None,               gm_col='PC1', sulcus_col='PC5')

# Per-session az/el/depth correction (added on top of global daz/del/ddepth)
ENABLE_PER_SESSION_CORRECTIONS = True
SESSION_CORR_BOUNDS = dict(daz=1.0, del_=1.0, ddepth=0.5)  # ± max effective correction
SESSION_CORR_L2_WEIGHT = 0.05  # λ on Σ(delta_i / bound_i)²; raise to suppress, lower to allow


class _FactorAnalysisAdapter:
    """Wraps FactorAnalysis to expose the same components_/explained_variance_ratio_ interface as PCA."""
    def __init__(self, fa: FactorAnalysis, X_scores: np.ndarray):
        self.components_ = fa.components_   # shape (n_components, n_features)
        self.noise_variance_ = fa.noise_variance_
        # Pseudo-explained variance: fraction of total score variance per factor
        score_var = np.var(X_scores, axis=0)
        total = score_var.sum() if score_var.sum() > 0 else 1.0
        self.explained_variance_ratio_ = score_var / total


def load_and_perform_pca(
        conn: Connection,
        table_name: str = "PenetrationMetrics",
        exclude_sessions: Optional[list] = None,
        within_session_normalize: bool = True,
        pc_smooth_sigma: float = 2.0,
        varimax_n_components: int = 6,
        decomp_method: str = DECOMPOSITION_METHOD,   # 'pca' | 'fa'
        use_varimax: bool = USE_VARIMAX,
):
    """Load data and perform PCA (or Factor Analysis), returning all necessary objects."""
    conn.execute(f"SELECT * FROM {table_name}")
    results = conn.fetch_all()

    conn.execute(f"DESCRIBE {table_name}")
    columns = [row[0] for row in conn.fetch_all()]

    df = pd.DataFrame(results, columns=columns)
    # exclude any sessions we want to ignore (e.g. outliers or sessions with known issues)
    if exclude_sessions is not None:
        df = df[~df['session_id'].isin(exclude_sessions)].copy()

    print(f"Loaded {len(df)} rows with columns: {list(df.columns)}")

    pk_columns = ['session_id', 'depth_under_chamber_mm']
    exclude_columns = pk_columns + ['r_squared']  # r_squared = fit quality, not tissue biology
    feature_columns = [
        col for col in df.columns
        if col not in exclude_columns
           and pd.api.types.is_numeric_dtype(df[col])
    ]

    print(f"Feature columns for PCA: {feature_columns}")

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

    if decomp_method == 'fa':
        n_factors = varimax_n_components if varimax_n_components else X_scaled.shape[1]
        print(f"\nUsing Factor Analysis (n_factors={n_factors}) ...")
        fa = FactorAnalysis(n_components=n_factors, random_state=42)
        X_pca = fa.fit_transform(X_scaled)
        pca = _FactorAnalysisAdapter(fa, X_pca)
    else:
        print("\nUsing PCA ...")
        pca = PCA()
        X_pca = pca.fit_transform(X_scaled)

    if use_varimax and varimax_n_components and varimax_n_components > 1:
        n_rot = min(varimax_n_components, X_pca.shape[1])
        loadings_k = pca.components_[:n_rot].T          # (n_features, n_rot)
        _, R = _varimax(loadings_k)
        X_pca_rot = X_pca[:, :n_rot] @ R
        # Re-order rotated components by descending variance so PC1 stays dominant
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

    # Print explained variance
    print("\nExplained variance ratio:")
    cumulative = 0
    for i, var in enumerate(pca.explained_variance_ratio_):
        cumulative += var
        print(f"  PC{i + 1}: {var:.3f} ({var * 100:.1f}%) | Cumulative: {cumulative * 100:.1f}%")

    return df_valid, pca, X_pca, feature_columns, scaler


def get_loadings_df(pca: PCA, feature_columns: list) -> pd.DataFrame:
    """Get PCA loadings as a DataFrame."""
    loadings = pd.DataFrame(
        pca.components_.T,
        columns=[f'PC{i + 1}' for i in range(len(pca.components_))],
        index=feature_columns
    )
    return loadings


def get_feature_correlations(
        df: pd.DataFrame,
        feature_columns: list,
        n_pcs: int = None
) -> pd.DataFrame:
    """
    Calculate correlations between original features and PC scores.

    Args:
        df: DataFrame with PC values and original features
        feature_columns: List of original feature names
        n_pcs: Number of PCs to analyze (default: all)

    Returns:
        DataFrame with correlation coefficients and p-values
    """
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
                        'p_value': p
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


def plot_pca_scatter(
        df: pd.DataFrame,
        pca: PCA,
        X_pca: np.ndarray,
        plot_components: list = None
):
    """Plot PCA scatter plots colored by session."""
    if plot_components is None:
        plot_components = [0, 1]

    sessions = df['session_id'].unique()
    n_sessions = len(sessions)

    if n_sessions <= 10:
        colors = plt.cm.tab10(np.linspace(0, 1, n_sessions))
    elif n_sessions <= 20:
        colors = plt.cm.tab20(np.linspace(0, 1, n_sessions))
    else:
        colors = plt.cm.viridis(np.linspace(0, 1, n_sessions))

    session_to_color = dict(zip(sessions, colors))

    pc_pairs = list(combinations(plot_components, 2))
    n_plots = len(pc_pairs)

    if n_plots == 1:
        fig, axes = plt.subplots(1, 1, figsize=(10, 8))
        axes = [axes]
    elif n_plots <= 3:
        fig, axes = plt.subplots(1, n_plots, figsize=(6 * n_plots, 5))
    else:
        n_cols = 3
        n_rows = (n_plots + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
        axes = axes.flatten()

    for idx, (pc_i, pc_j) in enumerate(pc_pairs):
        ax = axes[idx]

        for session in sessions:
            mask = df['session_id'] == session
            ax.scatter(
                X_pca[mask.values, pc_i],
                X_pca[mask.values, pc_j],
                c=[session_to_color[session]],
                label=session,
                alpha=0.7,
                edgecolors='none',
                s=50
            )

        var_i = pca.explained_variance_ratio_[pc_i] * 100
        var_j = pca.explained_variance_ratio_[pc_j] * 100
        ax.set_xlabel(f'PC{pc_i + 1} ({var_i:.1f}%)')
        ax.set_ylabel(f'PC{pc_j + 1} ({var_j:.1f}%)')
        ax.set_title(f'PC{pc_i + 1} vs PC{pc_j + 1}')

    for idx in range(n_plots, len(axes)):
        axes[idx].set_visible(False)

    handles, labels = axes[0].get_legend_handles_labels()
    if n_sessions <= 15:
        fig.legend(handles, labels, loc='center right', bbox_to_anchor=(1.12, 0.5))
    else:
        fig.legend(handles, labels, loc='center right', bbox_to_anchor=(1.15, 0.5), fontsize=7)

    plt.suptitle('PenetrationMetrics PCA', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig('penetration_metrics_pca.png', dpi=150, bbox_inches='tight')
    plt.show()


def plot_scree(pca: PCA):
    """Plot scree plot showing explained variance by component."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    n_components = len(pca.explained_variance_ratio_)
    x = range(1, n_components + 1)

    ax1.bar(x, pca.explained_variance_ratio_ * 100, alpha=0.7, color='steelblue')
    ax1.set_xlabel('Principal Component')
    ax1.set_ylabel('Explained Variance (%)')
    ax1.set_title('Variance Explained by Each PC')
    ax1.set_xticks(x)

    cumulative = np.cumsum(pca.explained_variance_ratio_) * 100
    ax2.plot(x, cumulative, 'o-', color='steelblue', linewidth=2, markersize=8)
    ax2.axhline(y=80, color='r', linestyle='--', alpha=0.5, label='80% threshold')
    ax2.axhline(y=95, color='g', linestyle='--', alpha=0.5, label='95% threshold')
    ax2.set_xlabel('Number of Principal Components')
    ax2.set_ylabel('Cumulative Explained Variance (%)')
    ax2.set_title('Cumulative Variance Explained')
    ax2.set_xticks(x)
    ax2.legend()
    ax2.set_ylim([0, 105])

    plt.tight_layout()
    plt.savefig('penetration_metrics_scree.png', dpi=150, bbox_inches='tight')
    plt.show()


def plot_loadings(
        pca: PCA,
        feature_columns: list,
        n_pcs: int = 4
):
    """Visualize PC loadings as horizontal bar charts."""
    n_pcs = min(n_pcs, len(pca.components_))
    n_features = len(feature_columns)

    fig, axes = plt.subplots(1, n_pcs, figsize=(4 * n_pcs, 6), sharey=True)
    if n_pcs == 1:
        axes = [axes]

    for pc_idx, ax in enumerate(axes):
        loadings = pca.components_[pc_idx]
        var_explained = pca.explained_variance_ratio_[pc_idx] * 100

        colors = ['steelblue' if l >= 0 else 'coral' for l in loadings]

        y_pos = np.arange(n_features)
        ax.barh(y_pos, loadings, color=colors, alpha=0.7)

        ax.axvline(x=0, color='black', linewidth=0.8)
        ax.set_yticks(y_pos)
        if pc_idx == 0:
            ax.set_yticklabels(feature_columns)

        ax.set_title(f'PC{pc_idx + 1} ({var_explained:.1f}%)')
        ax.set_xlabel('Loading')
        ax.grid(True, alpha=0.3, axis='x')

    plt.suptitle('PCA Loadings', fontsize=14)
    plt.tight_layout()
    plt.savefig('pca_loadings.png', dpi=150, bbox_inches='tight')
    plt.show()


def plot_correlation_heatmap(
        corr_df: pd.DataFrame,
        feature_columns: list
):
    """Plot heatmap of feature-PC correlations."""
    pivot = corr_df.pivot(index='Feature', columns='PC', values='Correlation')
    pivot = pivot.reindex(feature_columns)

    fig, ax = plt.subplots(figsize=(10, 8))

    im = ax.imshow(pivot.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.iloc[i, j]
            color = 'white' if abs(val) > 0.5 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=color, fontsize=9)

    plt.colorbar(im, ax=ax, label='Correlation')
    ax.set_title('Feature-PC Correlations')

    plt.tight_layout()
    plt.savefig('feature_pc_correlation_heatmap.png', dpi=150, bbox_inches='tight')
    plt.show()


def plot_depth_profiles_by_session(
        df: pd.DataFrame,
        pca: PCA,
        n_pcs: int = None,
        sessions: list = None,
        figsize_per_session: tuple = (12, 6)
):
    """Plot depth profiles for each session showing PC values vs depth."""
    if sessions is None:
        sessions = df['session_id'].unique()

    pc_columns = [col for col in df.columns if col.startswith('PC')]
    if n_pcs is None:
        n_pcs = min(len(pc_columns), 6)
    n_pcs = min(n_pcs, len(pc_columns))

    pc_columns = pc_columns[:n_pcs]
    pc_colors = plt.cm.Set1(np.linspace(0, 1, n_pcs))

    for session in sessions:
        session_data = df[df['session_id'] == session].copy()
        session_data = session_data.sort_values('depth_under_chamber_mm')

        if len(session_data) == 0:
            print(f"No data for session {session}")
            continue

        depths = session_data['depth_under_chamber_mm'].values

        fig, axes = plt.subplots(1, n_pcs, figsize=figsize_per_session, sharey=True)
        if n_pcs == 1:
            axes = [axes]

        for i, (pc_col, ax) in enumerate(zip(pc_columns, axes)):
            values = session_data[pc_col].values
            var_explained = pca.explained_variance_ratio_[i] * 100

            ax.plot(values, depths, 'o-', color=pc_colors[i], linewidth=1.5, markersize=5, alpha=0.8)
            ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

            ax.set_xlabel(f'{pc_col} ({var_explained:.1f}%)')
            if i == 0:
                ax.set_ylabel('Depth under chamber (mm)')

            ax.set_ylim(depths.max() + 0.5, depths.min() - 0.5)
            _setup_depth_yaxis(ax, depths)

        fig.suptitle(f'Session: {session}', fontsize=14)
        plt.tight_layout()
        plt.savefig(f'depth_profile_{session}.png', dpi=150, bbox_inches='tight')
        plt.show()


def plot_depth_profiles_all_sessions(
        df: pd.DataFrame,
        pca: PCA,
        n_pcs: int = None,
        sessions: list = None
):
    """Plot depth profiles for all sessions on a single figure."""
    if sessions is None:
        sessions = df['session_id'].unique()

    n_sessions = len(sessions)

    pc_columns = [col for col in df.columns if col.startswith('PC')]
    if n_pcs is None:
        n_pcs = min(len(pc_columns), 6)
    n_pcs = min(n_pcs, len(pc_columns))

    pc_columns = pc_columns[:n_pcs]

    if n_sessions <= 10:
        session_colors = plt.cm.tab10(np.linspace(0, 1, n_sessions))
    elif n_sessions <= 20:
        session_colors = plt.cm.tab20(np.linspace(0, 1, n_sessions))
    else:
        session_colors = plt.cm.viridis(np.linspace(0, 1, n_sessions))

    session_to_color = dict(zip(sessions, session_colors))

    fig, axes = plt.subplots(n_sessions, n_pcs, figsize=(3 * n_pcs, 3 * n_sessions))

    if n_sessions == 1:
        axes = axes.reshape(1, -1)
    if n_pcs == 1:
        axes = axes.reshape(-1, 1)

    for row, session in enumerate(sessions):
        session_data = df[df['session_id'] == session].copy()
        session_data = session_data.sort_values('depth_under_chamber_mm')

        if len(session_data) == 0:
            continue

        depths = session_data['depth_under_chamber_mm'].values
        color = session_to_color[session]

        for col, pc_col in enumerate(pc_columns):
            ax = axes[row, col]
            values = session_data[pc_col].values

            ax.plot(values, depths, 'o-', color=color, linewidth=1.5, markersize=4, alpha=0.8)
            ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

            if row == 0:
                var_explained = pca.explained_variance_ratio_[col] * 100
                ax.set_title(f'{pc_col} ({var_explained:.1f}%)')

            if col == 0:
                ax.set_ylabel(f'{session}\nDepth (mm)', fontsize=8)

            if row == n_sessions - 1:
                ax.set_xlabel('PC Value')

            ax.set_ylim(depths.max() + 0.5, depths.min() - 0.5)
            _setup_depth_yaxis(ax, depths)

    plt.suptitle('Depth Profiles by Session', fontsize=14, y=1.01)
    plt.tight_layout()
    plt.savefig('depth_profiles_all_sessions.png', dpi=150, bbox_inches='tight')
    plt.show()


def plot_depth_profiles_overlaid(
        df: pd.DataFrame,
        pca: PCA,
        n_pcs: int = None,
        sessions: list = None,
        align_depths: bool = False
):
    """Plot depth profiles with all sessions overlaid on the same axes."""
    if sessions is None:
        sessions = df['session_id'].unique()

    n_sessions = len(sessions)

    pc_columns = [col for col in df.columns if col.startswith('PC')]
    if n_pcs is None:
        n_pcs = min(len(pc_columns), 6)
    n_pcs = min(n_pcs, len(pc_columns))

    pc_columns = pc_columns[:n_pcs]

    if n_sessions <= 10:
        session_colors = plt.cm.tab10(np.linspace(0, 1, n_sessions))
    elif n_sessions <= 20:
        session_colors = plt.cm.tab20(np.linspace(0, 1, n_sessions))
    else:
        session_colors = plt.cm.viridis(np.linspace(0, 1, n_sessions))

    session_to_color = dict(zip(sessions, session_colors))

    n_cols = n_pcs
    n_rows = 1

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 5 * n_rows))
    if n_pcs == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    all_depths = df['depth_under_chamber_mm'].values
    global_min = all_depths.min()
    global_max = all_depths.max()

    for col, pc_col in enumerate(pc_columns):
        ax = axes[col]

        for session in sessions:
            session_data = df[df['session_id'] == session].copy()
            session_data = session_data.sort_values('depth_under_chamber_mm')

            if len(session_data) == 0:
                continue

            depths = session_data['depth_under_chamber_mm'].values
            values = session_data[pc_col].values

            if align_depths:
                depths = (depths - depths.min()) / (depths.max() - depths.min() + 1e-10)

            ax.plot(values, depths, 'o-', color=session_to_color[session],
                    linewidth=1.5, markersize=4, alpha=0.7, label=session)

        ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

        var_explained = pca.explained_variance_ratio_[col] * 100
        ax.set_title(f'{pc_col} ({var_explained:.1f}%)')
        ax.set_xlabel('PC Value')

        if col % n_cols == 0:
            if align_depths:
                ax.set_ylabel('Normalized Depth')
            else:
                ax.set_ylabel('Depth under chamber (mm)')

        if align_depths:
            ax.set_ylim(1.05, -0.05)
        else:
            ax.set_ylim(global_max + 0.5, global_min - 0.5)

        _setup_depth_yaxis(ax, all_depths)

    for idx in range(n_pcs, len(axes)):
        axes[idx].set_visible(False)

    handles, labels = axes[0].get_legend_handles_labels()
    if n_sessions <= 10:
        fig.legend(handles, labels, loc='center right', bbox_to_anchor=(1.1, 0.5))
    else:
        fig.legend(handles, labels, loc='center right', bbox_to_anchor=(1.12, 0.5), fontsize=7)

    plt.suptitle('Depth Profiles - All Sessions Overlaid', fontsize=14, y=1.01)
    plt.tight_layout()

    suffix = '_aligned' if align_depths else ''
    plt.savefig(f'depth_profiles_overlaid{suffix}.png', dpi=150, bbox_inches='tight')
    plt.show()


def _gmm_brain_threshold(pc1_values: np.ndarray) -> float:
    """
    Fit a 2-component GMM to PC1 and return the crossover point where
    P(brain component | PC1) = 0.5.  The brain component is the one with
    the higher mean (more signal = brain).
    """
    gmm = GaussianMixture(n_components=2, random_state=42, n_init=5)
    gmm.fit(pc1_values.reshape(-1, 1))

    brain_comp  = int(np.argmax(gmm.means_.flatten()))
    x = np.linspace(pc1_values.min(), pc1_values.max(), 10_000).reshape(-1, 1)
    p_brain_x   = gmm.predict_proba(x)[:, brain_comp]

    # crossover: first x where p_brain crosses 0.5 (searching from left)
    crossings = np.where(np.diff(p_brain_x > 0.5))[0]
    threshold = float(x[crossings[0]]) if len(crossings) > 0 else 0.0
    print(f"  GMM brain threshold (PC1 = {threshold:.3f}): "
          f"means={gmm.means_.flatten().round(2)}, "
          f"weights={gmm.weights_.round(2)}")
    return threshold


def compute_tissue_confidence(
        df: pd.DataFrame,
        wm_col: str = 'PC1',
        wm2_col: Optional[str] = 'PC3',  # None = use wm_col alone; axonal/waveform WM indicator
        wm2_sign: int = 1,               # +1 if high wm2_col = WM; -1 if low wm2_col = WM
        gm_col: str = 'PC2',
        sulcus_col: str = 'PC4',
        wm_threshold: float = WM_THRESHOLD,  # WM z-score must exceed this to register confidence
) -> pd.DataFrame:
    """
    3-class softmax tissue model.

    WM logit is wm_col alone, or the average of wm_col and wm2_col (if provided):
      wm_col     (default PC1): primary WM indicator
      wm2_col    (default PC3): secondary WM indicator; None to omit
      wm2_sign                : +1 = high wm2_col means WM; -1 = low wm2_col means WM
      gm_col     (default PC2): gray matter indicator
      sulcus_col (default PC4): sulcus/CSF indicator

    Pass _TISSUE_CONF_PCA / _TISSUE_CONF_FA_VARIMAX / _TISSUE_CONF_FA_NO_VARIMAX
    via **kwargs to select the right mapping for your decomp_method.

    Adds columns:
      p_wm, p_gm, p_sulcus : class probabilities (sum to 1 per row)
      tissue_score          : 0 = sulcus, 0.5 = GM, 1.0 = WM
      tissue_confidence     : max class probability (1 = certain, ~0.33 = ambiguous)
    """
    df = df.copy()
    std_wm     = df[wm_col].std()
    std_gm     = df[gm_col].std()
    std_sulcus = df[sulcus_col].std()

    # Raw z-scored signal per tissue type
    if wm2_col is not None:
        std_wm2  = df[wm2_col].std()
        wm_score = (df[wm_col].values / std_wm + wm2_sign * df[wm2_col].values / std_wm2) / 2
    else:
        wm_score = df[wm_col].values / std_wm

    gm_score     = df[gm_col].values     / std_gm
    sulcus_score = df[sulcus_col].values / std_sulcus

    # Sigmoid maps z-scores to (0, 1): negatives give low confidence, positives give high.
    # wm_threshold shifts the WM sigmoid — WM gets 50% raw confidence at that z-score,
    # so raising it makes WM harder to win (reduces overestimation).
    c_wm     = _sigmoid(wm_score     - wm_threshold)
    c_gm     = _sigmoid(gm_score)
    c_sulcus = _sigmoid(sulcus_score)

    # Normalize to probabilities
    total = c_wm + c_gm + c_sulcus
    p_wm     = c_wm     / total
    p_gm     = c_gm     / total
    p_sulcus = c_sulcus / total

    df['p_wm']     = p_wm
    df['p_gm']     = p_gm
    df['p_sulcus'] = p_sulcus

    # 1D tissue score: sulcus=0, GM=0.5, WM=1.0
    # WM/sulcus ambiguity (p_gm≈0) naturally lands near 0 or 1 depending on winner —
    # it does NOT falsely read as 0.5 (GM) the way a simple weighted average would.
    df['tissue_score']      = 1.0 * p_wm + 0.5 * p_gm
    df['tissue_confidence'] = np.stack([p_wm, p_gm, p_sulcus], axis=1).max(axis=1)
    return df


def plot_tissue_confidence_by_session(
        df: pd.DataFrame,
        pca: PCA = None,
        sessions: list = None,
        strip_width: float = 0.4,
        n_pcs: int = 4,
) -> None:
    """
    For each session plot a grayscale depth strip showing tissue confidence:
      black  (~0.0) = sulcus
      gray   (~0.5) = gray matter
      white  (~1.0) = white matter

    If pca is provided, appends a PC profiles panel (PC1–n_pcs, all colours).
    Produces one combined figure with all sessions side by side and saves it,
    then shows individual per-session figures.
    """
    if sessions is None:
        sessions = sorted(df['session_id'].unique())

    n_sessions = len(sessions)
    show_pcs = pca is not None

    panels_per_session = 3 if show_pcs else 2
    width_ratios_unit  = [strip_width, 1, 1.2] if show_pcs else [strip_width, 1]

    # ── Combined figure (all sessions as columns) ──────────────────────────
    fig_all, axes_all = plt.subplots(
        1, n_sessions * panels_per_session,
        figsize=((2 + (1.2 if show_pcs else 0)) * n_sessions + 1, 10),
        gridspec_kw={'width_ratios': width_ratios_unit * n_sessions},
    )
    axes_all = np.array(axes_all).reshape(n_sessions, panels_per_session)

    for col_idx, session in enumerate(sessions):
        sdata = df[df['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
        if sdata.empty:
            continue

        depths = sdata['depth_under_chamber_mm'].values
        scores = sdata['tissue_score'].values

        _draw_tissue_strip(axes_all[col_idx, 0], depths, scores, title=session)
        _draw_tissue_line(axes_all[col_idx, 1], depths, scores)
        if show_pcs:
            _draw_pc_profiles(axes_all[col_idx, 2], sdata, depths, pca, n_pcs)

        if col_idx > 0:
            axes_all[col_idx, 0].set_ylabel('')

    fig_all.suptitle('Tissue Confidence by Session\n'
                     '(black=sulcus, gray=gray matter, white=white matter)',
                     fontsize=12)
    plt.tight_layout()
    plt.savefig('tissue_confidence_all_sessions.png', dpi=150, bbox_inches='tight')
    plt.show()

    # ── Per-session figures ────────────────────────────────────────────────
    for session in sessions:
        sdata = df[df['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
        if sdata.empty:
            continue

        depths = sdata['depth_under_chamber_mm'].values
        scores = sdata['tissue_score'].values

        fig, axes = plt.subplots(
            1, panels_per_session,
            figsize=((4 + (2 if show_pcs else 0)), 10),
            gridspec_kw={'width_ratios': width_ratios_unit},
            sharey=True,
        )
        _draw_tissue_strip(axes[0], depths, scores, title=session)
        _draw_tissue_line(axes[1], depths, scores)
        if show_pcs:
            _draw_pc_profiles(axes[2], sdata, depths, pca, n_pcs)

        fig.suptitle(f'Tissue Confidence — {session}\n'
                     '(black=sulcus, gray=gray matter, white=white matter)',
                     fontsize=11)
        plt.tight_layout()
        plt.savefig(f'tissue_confidence_{session}.png', dpi=150, bbox_inches='tight')
        plt.show()


def _setup_depth_yaxis(ax: plt.Axes, depths: np.ndarray,
                       label_interval_mm: float = 0.5,
                       tick_interval_mm: float = 0.1) -> None:
    """Dense minor ticks every tick_interval_mm; labelled major ticks every label_interval_mm."""
    from matplotlib.ticker import MultipleLocator
    ax.yaxis.set_major_locator(MultipleLocator(label_interval_mm))
    ax.yaxis.set_minor_locator(MultipleLocator(tick_interval_mm))
    ax.tick_params(axis='y', which='major', length=6, labelsize=9)
    ax.tick_params(axis='y', which='minor', length=2, labelsize=0)
    ax.grid(True, which='major', alpha=0.3)
    ax.grid(True, which='minor', alpha=0.1)


def _draw_tissue_strip(
        ax: plt.Axes,
        depths: np.ndarray,
        scores: np.ndarray,
        title: str = '',
        vmax: float = 1.0,
) -> None:
    """Render scores as a grayscale imshow strip with depth on the y-axis.

    Interpolates to a fine uniform depth grid so that imshow pixel rows map
    correctly to physical depth positions even when the input depth bins are
    irregularly spaced or some bins are missing.
    """
    from scipy.interpolate import interp1d

    if len(depths) >= 2:
        n_fine = max(500, len(depths) * 20)
        d_fine = np.linspace(depths[0], depths[-1], n_fine)
        f = interp1d(depths, scores, kind='linear', bounds_error=False,
                     fill_value=(scores[0], scores[-1]))
        strip = f(d_fine).reshape(-1, 1)
    else:
        strip = scores.reshape(-1, 1)
        d_fine = depths

    ax.imshow(
        strip,
        aspect='auto',
        cmap='gray',
        vmin=0,
        vmax=vmax,
        origin='upper',
        extent=[0, 1, d_fine[-1], d_fine[0]],
    )
    ax.set_xticks([])
    ax.set_ylabel('Depth under chamber (mm)')
    ax.set_xlabel('')
    ax.set_title(title, fontsize=8, rotation=45, ha='right')
    _setup_depth_yaxis(ax, depths)


def _draw_tissue_line(
        ax: plt.Axes,
        depths: np.ndarray,
        scores: np.ndarray,
) -> None:
    """Line plot of tissue_score vs depth, coloured by score value."""
    ax.plot(scores, depths, 'o-', color='dimgray', linewidth=1.5, markersize=4)
    ax.axvline(0.25, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.axvline(0.75, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel('Tissue Score\n(0=sulcus, 0.5=GM, 1.0=WM)')
    ax.invert_yaxis()
    _setup_depth_yaxis(ax, depths)

    for score_val, label in [(0.0, 'Sulcus'), (0.5, 'Gray'), (1.0, 'WM')]:
        ax.axvline(score_val, color='lightgray', linewidth=0.5, linestyle=':')


def _draw_pc_profiles(
        ax: plt.Axes,
        sdata: pd.DataFrame,
        depths: np.ndarray,
        pca: PCA,
        n_pcs: int = 4,
) -> None:
    """Plot PC1–n_pcs vs depth on a single axis, one colour per PC."""
    pc_colors = plt.cm.Set1(np.linspace(0, 1, n_pcs))
    pc_columns = [f'PC{i + 1}' for i in range(n_pcs) if f'PC{i + 1}' in sdata.columns]
    for i, pc_col in enumerate(pc_columns):
        var_pct = pca.explained_variance_ratio_[i] * 100
        ax.plot(sdata[pc_col].values, depths,
                'o-', color=pc_colors[i], linewidth=1.5, markersize=4, alpha=0.8,
                label=f'{pc_col} ({var_pct:.0f}%)')
    ax.axvline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.set_xlabel('PC Value')
    ax.set_title('PC Profiles')
    ax.invert_yaxis()
    _setup_depth_yaxis(ax, depths)
    ax.legend(fontsize=7, loc='best')


def load_mri_pipeline(config_path: str = MRI_VIEWER_CONFIG_PATH) -> dict:
    """
    Load MRI volume, correction matrix, and chamber geometry for trajectory sampling.

    Returns a dict with keys: data, inv_corrected, origin, x, y, normal, cor_offset.
    """
    from src.mri.volume import load_volume
    from src.mri.correction import load_corrections
    from src.mri.chamber import fit_chamber

    with open(config_path) as f:
        cfg = json.load(f)

    par_path = cfg['default_path']
    ebz_world = np.array(cfg['ebz_world'])
    monkey_specific_path = cfg['monkey_specific_path']

    data, native_affine, voxel_sizes, img = load_volume(par_path)
    if data.ndim == 4:
        data = data[..., 0]

    # Strip file extension before appending suffix — matches viewer's _corr_json_for()
    mri_corr_path = os.path.splitext(par_path)[0] + '_corrections.json'
    mri_corr, _ = load_corrections(mri_corr_path)
    print(f"  MRI correction: {mri_corr_path}")
    print(f"  MRI correction matrix:\n{np.round(mri_corr, 4)}")
    corrected_affine = mri_corr @ native_affine
    inv_corrected = np.linalg.inv(corrected_affine)

    spec = importlib.util.spec_from_file_location('monkey_specific', monkey_specific_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    screws_ebz = np.array(mod.get_screw_hole_coords())
    ref_idx = mod.get_reference_screw_idx()
    cor_offset = mod.get_center_of_rotation_offset()
    is_fit_circle = mod.get_is_fit_circle()

    ch_corr_path = os.path.splitext(monkey_specific_path)[0] + '_chamber_corrections.json'
    ch_corr, _ = load_corrections(ch_corr_path)
    print(f"  Chamber correction: {ch_corr_path}")
    print(f"  Chamber correction matrix:\n{np.round(ch_corr, 4)}")

    # Always use raw screws as the optimization baseline — ignore any previously saved
    # optimization results so every run starts from the same original position.
    # Manual viewer corrections (ch_corr) are stored for reference but not applied here.
    screws_raw = screws_ebz + ebz_world
    center, origin, x, y, normal = fit_chamber(screws_raw, ref_idx, cor_offset, is_fit_circle)

    return {
        'data': data,
        'inv_corrected': inv_corrected,
        'origin': origin,
        'x': x,
        'y': y,
        'normal': normal,
        'cor_offset': cor_offset,
        # raw screws (no correction applied) — optimizer always starts from here
        'screws_world_base': screws_raw,
        'ref_idx': ref_idx,
        'is_fit_circle': is_fit_circle,
        'ch_corr': ch_corr,
        'ch_corr_path': ch_corr_path,
        'monkey_specific_path': monkey_specific_path,
    }


def sample_mri_along_trajectory(
        mri_pipeline: dict,
        az_deg: float,
        el_deg: float,
        depths_mm: np.ndarray,
) -> np.ndarray:
    """Sample MRI voxel intensities at specified depths along a trajectory."""
    from src.mri.chamber import calc_penetration_target

    data = mri_pipeline['data']
    inv_corrected = mri_pipeline['inv_corrected']
    origin = mri_pipeline['origin']
    x = mri_pipeline['x']
    y = mri_pipeline['y']
    normal = mri_pipeline['normal']
    cor_offset = mri_pipeline['cor_offset']

    max_dist = float(np.max(depths_mm)) + 1.0
    _, direction, top_pt = calc_penetration_target(
        origin, az_deg, el_deg, max_dist, x, y, normal, cor_offset
    )

    pts = np.array([top_pt + d * direction for d in depths_mm])
    ones = np.ones((len(pts), 1))
    vox_coords = (inv_corrected @ np.hstack([pts, ones]).T).T[:, :3]

    values = map_coordinates(data, vox_coords.T, order=1, mode='constant', cval=0.0)
    return values.astype(float)


def get_penetration_for_session(conn: Connection, session_id: str) -> Optional[dict]:
    """Query the Penetrations table for a session's trajectory angles."""
    for pen_type in ('actual', 'planned_tip', 'planned'):
        conn.execute(
            "SELECT az_deg, el_deg, dist_mm FROM Penetrations "
            "WHERE session_id = %s AND pen_type = %s LIMIT 1",
            (session_id, pen_type),
        )
        rows = conn.fetch_all()
        if rows:
            az, el, dist = rows[0]
            return {'az_deg': float(az), 'el_deg': float(el),
                    'dist_mm': float(dist), 'pen_type': pen_type}
    return None


def compute_mri_comparison(
        df: pd.DataFrame,
        conn: Connection,
        mri_pipeline: dict,
        daz: float = 0.0,
        del_: float = 0.0,
        ddepth: float = 0.0,
) -> pd.DataFrame:
    """
    Add MRI intensity sampled along each session's trajectory.

    Optional offsets applied to all sessions: daz/del_ (degrees) and ddepth (mm).

    Adds columns:
      mri_raw        : raw voxel intensity at each depth
      mri_normalized : clipped to 99th-percentile then scaled so
                       max(mri_normalized) == max(tissue_score) per session
    """
    df = df.copy()
    df['mri_raw'] = np.nan
    df['mri_normalized'] = np.nan

    for session_id in df['session_id'].unique():
        pen = get_penetration_for_session(conn, session_id)
        if pen is None:
            print(f"  Warning: no penetration found for session {session_id}, skipping MRI.")
            continue

        mask = df['session_id'] == session_id
        depths = df.loc[mask, 'depth_under_chamber_mm'].values + ddepth
        mri_vals = sample_mri_along_trajectory(
            mri_pipeline, pen['az_deg'] + daz, pen['el_deg'] + del_, depths
        )
        df.loc[mask, 'mri_raw'] = mri_vals
        df.loc[mask, 'mri_normalized'] = mri_vals  # native values, no scaling

        print(f"  {session_id} ({pen['pen_type']}): "
              f"MRI [{mri_vals.min():.0f}–{mri_vals.max():.0f}]")

    return df


def _weighted_pearson_r(ts: np.ndarray, mri_vals: np.ndarray,
                        confidence: np.ndarray = None) -> float:
    """
    Weighted Pearson r between tissue_score and MRI raw values.

    MRI is normalized internally (99th percentile of positives, scaled to ts max).
    Weights default to tissue_confidence if provided, else abs(2*ts - 1).
    """
    pos = mri_vals[mri_vals > 0]
    if len(pos) < 3:
        return np.nan
    mri_ref = float(np.percentile(pos, 99))
    ts_max = float(ts.max())
    if mri_ref <= 0 or ts_max <= 0:
        return np.nan

    mri_norm = np.clip(mri_vals, 0.0, mri_ref) / mri_ref * ts_max
    w = confidence if confidence is not None else np.abs(2.0 * ts - 1.0)
    w_sum = w.sum()
    if w_sum == 0:
        return np.nan

    ts_wm = (w * ts).sum() / w_sum
    mri_wm = (w * mri_norm).sum() / w_sum
    ts_c = ts - ts_wm
    mri_c = mri_norm - mri_wm
    num = (w * ts_c * mri_c).sum()
    denom = np.sqrt((w * ts_c ** 2).sum() * (w * mri_c ** 2).sum())
    return float(num / denom) if denom > 0 else np.nan


def compute_trajectory_fit_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weighted Pearson r between tissue_score and mri_normalized per session.
    Returns a DataFrame indexed by session_id with columns: fit_score, n_points.
    """
    records = []
    for session_id in df['session_id'].unique():
        mask = df['session_id'] == session_id
        sdata = df[mask].dropna(subset=['tissue_score', 'mri_normalized'])
        n = len(sdata)

        if n < 3:
            records.append({'session_id': session_id, 'fit_score': np.nan, 'n_points': n})
            continue

        ts = sdata['tissue_score'].values
        mri = sdata['mri_normalized'].values
        conf = sdata['tissue_confidence'].values if 'tissue_confidence' in sdata.columns else None
        r = _weighted_pearson_r(ts, mri, conf)
        records.append({'session_id': session_id, 'fit_score': r, 'n_points': n})

    result = pd.DataFrame(records).set_index('session_id')
    print("\nTrajectory fit scores (weighted Pearson r, tissue_score vs MRI):")
    print(result.to_string())
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Transformation optimisation
# ─────────────────────────────────────────────────────────────────────────────

_OPT_PARAM_NAMES = [
    'tx_mm', 'ty_mm', 'tz_mm',           # chamber translation
    'rx_deg', 'ry_deg', 'rz_deg',         # chamber rotation
    'scale',                               # isotropic chamber scale (default 1)
    'daz_deg', 'del_deg',                 # global az/el offset for all penetrations
    'ddepth_mm',                          # global depth offset for all penetrations
]
_OPT_X0 = np.array([0., 0., 0.,   0., 0., 0.,   1.0,   0., 0.,   0.])


def _apply_chamber_params(params: np.ndarray, mri_pipeline: dict):
    """Return (origin, x, y, normal) after applying optimisation params to chamber."""
    from src.mri.chamber import fit_chamber
    from src.mri.correction import rot_x, rot_y, rot_z, xlate

    tx, ty, tz, rx, ry, rz, scale, *_ = params
    scale = float(np.clip(scale, 0.5, 2.0))  # prevent degenerate collapse
    screws = mri_pipeline['screws_world_base']
    centroid = screws.mean(axis=0)

    corr = xlate(tx, ty, tz) @ rot_z(rz) @ rot_y(ry) @ rot_x(rx)
    R, t = corr[:3, :3], corr[:3, 3]
    screws_scaled = (screws - centroid) * scale + centroid
    screws_new = (R @ screws_scaled.T).T + t

    _, origin, x, y, normal = fit_chamber(
        screws_new,
        mri_pipeline['ref_idx'],
        mri_pipeline['cor_offset'],
        mri_pipeline['is_fit_circle'],
    )
    return origin, x, y, normal


def _tanh_bound(raw: float, bound: float) -> float:
    """Map unconstrained raw value to (-bound, +bound) via tanh reparameterization."""
    return bound * float(np.tanh(raw))


def optimize_trajectory_alignment(
        df_conf: pd.DataFrame,
        conn: Connection,
        mri_pipeline: dict,
        maxiter: int = 2000,
) -> dict:
    """
    Find the rigid-body + scale + angle + depth correction that maximises the
    mean weighted Pearson r between tissue_score and MRI across all sessions.

    Parameters (10 total):
        tx, ty, tz  (mm)   — additional translation of chamber screws
        rx, ry, rz  (deg)  — additional rotation of chamber screws
        scale              — isotropic scale of screw positions about centroid
        daz, del    (deg)  — global az / el offset added to every penetration
        ddepth      (mm)   — global depth offset added to all depth values

    Returns dict with keys: params, param_names, result, score_before, score_after
    """
    from src.mri.chamber import calc_penetration_target

    # Pre-fetch penetration angles and depth arrays once (avoid DB hits in loop)
    session_info = {}
    for session_id in df_conf['session_id'].unique():
        pen = get_penetration_for_session(conn, session_id)
        if pen is None:
            continue
        mask = df_conf['session_id'] == session_id
        session_info[session_id] = {
            'az': pen['az_deg'],
            'el': pen['el_deg'],
            'depths': df_conf.loc[mask, 'depth_under_chamber_mm'].values.copy(),
            'ts': df_conf.loc[mask, 'tissue_score'].values.copy(),
            'confidence': df_conf.loc[mask, 'tissue_confidence'].values.copy()
                if 'tissue_confidence' in df_conf.columns else None,
        }

    if not session_info:
        raise RuntimeError("No sessions with penetration data found.")

    data = mri_pipeline['data']
    inv_corrected = mri_pipeline['inv_corrected']
    cor_offset = mri_pipeline['cor_offset']

    # Build full parameter vector — core 10 globals + optional 3*N per-session deltas
    session_ids = list(session_info.keys())
    n_sess = len(session_ids)

    if ENABLE_PER_SESSION_CORRECTIONS:
        per_sess_names = []
        for sid in session_ids:
            per_sess_names += [f'daz_{sid}', f'del_{sid}', f'ddepth_{sid}']
        full_param_names = _OPT_PARAM_NAMES + per_sess_names
        full_x0 = np.concatenate([_OPT_X0, np.zeros(3 * n_sess)])
        print(f"  Per-session corrections enabled: {n_sess} sessions × 3 params "
              f"(bounds: ±{SESSION_CORR_BOUNDS['daz']}° az, "
              f"±{SESSION_CORR_BOUNDS['del_']}° el, "
              f"±{SESSION_CORR_BOUNDS['ddepth']} mm depth)")
    else:
        full_param_names = _OPT_PARAM_NAMES
        full_x0 = _OPT_X0.copy()

    best = {'score': -np.inf, 'params': full_x0.copy(), 'iter': 0}
    call_count = [0]

    def score_for_params(params, include_reg=True):
        try:
            origin, x_vec, y_vec, normal = _apply_chamber_params(params, mri_pipeline)
        except Exception:
            return np.inf

        _, _, _, _, _, _, _, daz, del_, ddepth = params[:10]
        per_sess_raw = params[10:].reshape(-1, 3) if ENABLE_PER_SESSION_CORRECTIONS else None

        total_r, n_ok = 0.0, 0
        reg_sum = 0.0

        for i, sid in enumerate(session_ids):
            sdata = session_info[sid]

            if per_sess_raw is not None:
                daz_i  = _tanh_bound(per_sess_raw[i, 0], SESSION_CORR_BOUNDS['daz'])
                del_i  = _tanh_bound(per_sess_raw[i, 1], SESSION_CORR_BOUNDS['del_'])
                ddep_i = _tanh_bound(per_sess_raw[i, 2], SESSION_CORR_BOUNDS['ddepth'])
                reg_sum += (daz_i  / SESSION_CORR_BOUNDS['daz'])  ** 2
                reg_sum += (del_i  / SESSION_CORR_BOUNDS['del_']) ** 2
                reg_sum += (ddep_i / SESSION_CORR_BOUNDS['ddepth']) ** 2
            else:
                daz_i = del_i = ddep_i = 0.0

            depths = sdata['depths'] + ddepth + ddep_i
            if depths.max() <= 0:
                continue
            try:
                _, direction, top_pt = calc_penetration_target(
                    origin, sdata['az'] + daz + daz_i, sdata['el'] + del_ + del_i,
                    float(depths.max()) + 1.0, x_vec, y_vec, normal, cor_offset,
                )
                pts = top_pt + depths[:, None] * direction[None, :]
                ones = np.ones((len(pts), 1))
                vox = (inv_corrected @ np.hstack([pts, ones]).T).T[:, :3]
                mri_vals = map_coordinates(data, vox.T, order=1,
                                           mode='constant', cval=0.0).astype(float)
            except Exception:
                continue

            r = _weighted_pearson_r(sdata['ts'], mri_vals, sdata['confidence'])
            if not np.isnan(r):
                total_r += r
                n_ok += 1

        if n_ok == 0:
            return np.inf
        loss = -(total_r / n_ok)
        if include_reg and ENABLE_PER_SESSION_CORRECTIONS:
            loss += SESSION_CORR_L2_WEIGHT * reg_sum
        return loss

    def callback_nelder(xk):
        call_count[0] += 1
        s_pure = -score_for_params(xk, include_reg=False)
        if s_pure > best['score']:
            best['score'] = s_pure
            best['params'] = xk.copy()
            best['iter'] = call_count[0]
            tx, ty, tz, rx, ry, rz, sc, daz, del_, ddepth = xk[:10]
            print(f"  [{call_count[0]:4d}] score={s_pure:.4f}  "
                  f"t=({tx:.2f},{ty:.2f},{tz:.2f})  "
                  f"r=({rx:.2f},{ry:.2f},{rz:.2f})  "
                  f"scale={sc:.3f}  daz={daz:.2f}  del={del_:.2f}  ddepth={ddepth:.2f}")
            if ENABLE_PER_SESSION_CORRECTIONS and len(xk) > 10:
                per = xk[10:].reshape(-1, 3)
                eff_daz  = np.array([_tanh_bound(v, SESSION_CORR_BOUNDS['daz'])  for v in per[:, 0]])
                eff_del  = np.array([_tanh_bound(v, SESSION_CORR_BOUNDS['del_']) for v in per[:, 1]])
                eff_ddep = np.array([_tanh_bound(v, SESSION_CORR_BOUNDS['ddepth']) for v in per[:, 2]])
                print(f"         max|Δaz|={np.abs(eff_daz).max():.2f}°  "
                      f"max|Δel|={np.abs(eff_del).max():.2f}°  "
                      f"max|Δdep|={np.abs(eff_ddep).max():.2f}mm")

    score_before = -score_for_params(full_x0, include_reg=False)
    print(f"\nOptimising over {len(session_info)} sessions  "
          f"(initial mean r = {score_before:.4f}) ...")

    maxiter_adj = maxiter + 500 * n_sess if ENABLE_PER_SESSION_CORRECTIONS else maxiter
    result = minimize(
        score_for_params,
        full_x0,
        method='Nelder-Mead',
        callback=callback_nelder,
        options={'maxiter': maxiter_adj, 'xatol': 1e-3, 'fatol': 1e-4,
                 'adaptive': True, 'disp': True},
    )

    score_after = -score_for_params(result.x, include_reg=False)
    print(f"\nOptimisation done: {result.message}")
    print(f"  mean r: {score_before:.4f} → {score_after:.4f}  "
          f"(Δ = {score_after - score_before:+.4f})")
    print("\nOptimised global parameters:")
    for name, val in zip(_OPT_PARAM_NAMES, result.x[:10]):
        print(f"  {name:<14s} = {val:+.4f}")

    # Decode per-session corrections to effective (bounded) values
    per_session_corrections = {}
    if ENABLE_PER_SESSION_CORRECTIONS and len(result.x) > 10:
        per = result.x[10:].reshape(-1, 3)
        for i, sid in enumerate(session_ids):
            per_session_corrections[sid] = dict(
                daz_deg   = _tanh_bound(per[i, 0], SESSION_CORR_BOUNDS['daz']),
                del_deg   = _tanh_bound(per[i, 1], SESSION_CORR_BOUNDS['del_']),
                ddepth_mm = _tanh_bound(per[i, 2], SESSION_CORR_BOUNDS['ddepth']),
            )
        print("\nPer-session corrections (effective, deg/mm):")
        for sid, c in per_session_corrections.items():
            print(f"  {str(sid):<20s}  daz={c['daz_deg']:+.3f}°  "
                  f"del={c['del_deg']:+.3f}°  ddepth={c['ddepth_mm']:+.3f}mm")

    return {
        'params': result.x,
        'param_names': full_param_names,
        'result': result,
        'score_before': score_before,
        'score_after': score_after,
        'per_session_corrections': per_session_corrections,
        'session_ids': session_ids,
    }


def apply_optimized_pipeline(mri_pipeline: dict, opt_result: dict) -> tuple:
    """
    Build a corrected pipeline and extract angle/depth offsets from opt_result.

    Returns (new_pipeline, daz, del_, ddepth) ready to pass to compute_mri_comparison.
    """
    params = opt_result['params']
    _, _, _, _, _, _, _, daz, del_, ddepth = params[:10]

    origin, x, y, normal = _apply_chamber_params(params, mri_pipeline)
    new_pipeline = dict(mri_pipeline)
    new_pipeline['origin'] = origin
    new_pipeline['x'] = x
    new_pipeline['y'] = y
    new_pipeline['normal'] = normal

    return new_pipeline, float(daz), float(del_), float(ddepth)


def save_optimized_params(
        opt_result: dict,
        mri_pipeline: dict,
) -> str:
    """
    Save optimisation result to a timestamped file for later comparison.

    Does NOT modify _chamber_corrections.json or _pen_offsets.json — call
    apply_pca_opt_result(path, mri_pipeline) explicitly to push a chosen
    result into the viewer files.

    Returns the path of the saved result file.
    """
    import datetime
    from src.mri.correction import rot_x, rot_y, rot_z, xlate

    params = opt_result['params']
    tx, ty, tz, rx, ry, rz, scale, daz, del_, ddepth = params[:10]
    scale = float(np.clip(scale, 0.5, 2.0))
    monkey_specific_path = mri_pipeline['monkey_specific_path']

    # Build 4x4 affine from raw screws (no existing correction composed in,
    # since the optimizer always starts from raw screws)
    corr = xlate(tx, ty, tz) @ rot_z(rz) @ rot_y(ry) @ rot_x(rx)
    R_d = corr[:3, :3]
    t_d = corr[:3, 3]
    centroid = mri_pipeline['screws_world_base'].mean(axis=0)
    M = np.eye(4)
    M[:3, :3] = scale * R_d
    M[:3, 3] = (1.0 - scale) * R_d @ centroid + t_d

    results_dir = OPTIMIZATIONS_path
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    result_path = os.path.join(results_dir, f'opt_{timestamp}.json')

    result_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'score_before': float(opt_result['score_before']),
        'score_after': float(opt_result['score_after']),
        'params': {name: float(val)
                   for name, val in zip(opt_result['param_names'], params)},
        'chamber_correction_4x4': M.tolist(),
        'daz_deg': float(daz),
        'del_deg': float(del_),
        'ddepth_mm': float(ddepth),
        'per_session_corrections': opt_result.get('per_session_corrections', {}),
        'session_corr_bounds': SESSION_CORR_BOUNDS,
        'session_corr_l2_weight': SESSION_CORR_L2_WEIGHT,
    }
    with open(result_path, 'w') as f:
        json.dump(result_data, f, indent=2)

    print(f"  Result saved → {result_path}")
    print(f"  score: {opt_result['score_before']:.4f} → {opt_result['score_after']:.4f}")
    print(f"  daz={daz:+.4f}°  del={del_:+.4f}°  ddepth={ddepth:+.4f} mm")
    print(f"  To apply: apply_pca_opt_result('{result_path}', mri_pipeline)")
    return result_path


def apply_pca_opt_result(result_path: str, mri_pipeline: dict) -> None:
    """
    Apply a saved PCA optimisation result to the MRI viewer files.

    Writes:
      _chamber_corrections.json  — new 4x4 affine (viewer picks this up on next load)
      _pen_offsets.json          — daz/del_/ddepth offsets
    """
    from src.mri.correction import push_correction, save_corrections, load_corrections

    with open(result_path) as f:
        result = json.load(f)

    monkey_specific_path = mri_pipeline['monkey_specific_path']
    ch_corr_path = mri_pipeline['ch_corr_path']

    M = np.array(result['chamber_correction_4x4'])
    note = (f"PCA opt applied from {os.path.basename(result_path)} "
            f"(r {result['score_before']:.4f}→{result['score_after']:.4f})")
    _, ch_corr_cfg = load_corrections(ch_corr_path)
    push_correction(ch_corr_cfg, M, note=note)
    save_corrections(ch_corr_path, ch_corr_cfg)
    print(f"  Chamber correction updated → {ch_corr_path}")

    pen_offsets_path = os.path.splitext(monkey_specific_path)[0] + '_pen_offsets.json'
    offsets = {
        'timestamp': result['timestamp'],
        'note': note,
        'daz_deg': result['daz_deg'],
        'del_deg': result['del_deg'],
        'ddepth_mm': result['ddepth_mm'],
        'score_before': result['score_before'],
        'score_after': result['score_after'],
        'per_session_corrections': result.get('per_session_corrections', {}),
    }
    with open(pen_offsets_path, 'w') as f:
        json.dump(offsets, f, indent=2)
    print(f"  Pen offsets updated → {pen_offsets_path}")


def plot_mri_comparison_by_session(
        df: pd.DataFrame,
        fit_scores: Optional[pd.DataFrame] = None,
        sessions: list = None,
        strip_width: float = 0.4,
) -> None:
    """
    Per-session figure: MRI grayscale strip | tissue confidence strip | overlay line.

    Both strips share the same grayscale scale (0=black, max tissue_score=white).
    """
    if sessions is None:
        sessions = sorted(df['session_id'].unique())

    n_sessions = len(sessions)
    has_conf = 'tissue_confidence' in df.columns

    # Combined figure: MRI | tissue_score | [confidence] | line
    n_cols_per = 4 if has_conf else 3
    col_ratios = ([strip_width, strip_width, strip_width, 1] if has_conf
                  else [strip_width, strip_width, 1])
    fig_all, all_axes = plt.subplots(
        1, n_sessions * n_cols_per,
        figsize=((3.0 + n_cols_per) * n_sessions, 10),
        gridspec_kw={'width_ratios': col_ratios * n_sessions},
    )
    if n_sessions == 1:
        all_axes = np.array(all_axes)
    ax_groups = [all_axes[i * n_cols_per:(i + 1) * n_cols_per] for i in range(n_sessions)]

    for idx, session in enumerate(sessions):
        sdata = df[df['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
        if sdata.empty:
            continue

        depths = sdata['depth_under_chamber_mm'].values
        ts = sdata['tissue_score'].values
        conf = sdata['tissue_confidence'].values if has_conf else None
        mri_norm = sdata['mri_normalized'].values
        mri_vmax = float(np.nanmax(mri_norm)) if np.any(np.isfinite(mri_norm)) else 1.0

        if has_conf:
            ax_mri, ax_ts, ax_conf, ax_line = ax_groups[idx]
            _draw_tissue_strip(ax_conf, depths, conf, title='Confidence', vmax=1.0)
        else:
            ax_mri, ax_ts, ax_line = ax_groups[idx]

        _draw_tissue_strip(ax_mri, depths, mri_norm, title=f'{session}\nMRI', vmax=mri_vmax)
        _draw_tissue_strip(ax_ts, depths, ts, title='Tissue', vmax=1.0)
        _draw_mri_tissue_line(ax_line, depths, ts, mri_norm, fit_scores, session, conf)

        if idx > 0:
            ax_mri.set_ylabel('')
            ax_ts.set_ylabel('')

    fig_all.suptitle('MRI vs Tissue Confidence\n(black=sulcus, gray=GM, white=WM)',
                     fontsize=12)
    plt.tight_layout()
    plt.savefig('mri_vs_tissue_confidence_all_sessions.png', dpi=150, bbox_inches='tight')
    plt.show()

    # Per-session figures
    for session in sessions:
        sdata = df[df['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
        if sdata.empty:
            continue

        depths = sdata['depth_under_chamber_mm'].values
        ts = sdata['tissue_score'].values
        conf = sdata['tissue_confidence'].values if has_conf else None
        mri_norm = sdata['mri_normalized'].values
        mri_vmax = float(np.nanmax(mri_norm)) if np.any(np.isfinite(mri_norm)) else 1.0

        fig, axes = plt.subplots(
            1, n_cols_per,
            figsize=(2 + n_cols_per * 1.5, 10),
            gridspec_kw={'width_ratios': col_ratios},
        )
        if has_conf:
            ax_mri, ax_ts, ax_conf, ax_line = axes
            _draw_tissue_strip(ax_conf, depths, conf, title='Confidence', vmax=1.0)
        else:
            ax_mri, ax_ts, ax_line = axes

        _draw_tissue_strip(ax_mri, depths, mri_norm, title='MRI', vmax=mri_vmax)
        _draw_tissue_strip(ax_ts, depths, ts, title='Tissue score', vmax=1.0)
        _draw_mri_tissue_line(ax_line, depths, ts, mri_norm, fit_scores, session, conf)

        fig.suptitle(f'MRI vs Tissue Confidence — {session}', fontsize=11)
        plt.tight_layout()
        plt.savefig(f'mri_vs_tissue_confidence_{session}.png', dpi=150, bbox_inches='tight')
        plt.show()


def _draw_mri_tissue_line(
        ax: plt.Axes,
        depths: np.ndarray,
        tissue_score: np.ndarray,
        mri_vals: np.ndarray,
        fit_scores: Optional[pd.DataFrame],
        session_id: str,
        confidence: np.ndarray = None,
) -> None:
    """
    Tissue score and optional confidence (left axis, [0-1]) and MRI native values
    (top axis) vs depth. Each signal uses its own scale.
    """
    ax.plot(tissue_score, depths, 'k-o', markersize=3, linewidth=1.5, label='Tissue score')
    if confidence is not None:
        ax.plot(confidence, depths, color='dimgray', linestyle=':', linewidth=1.2,
                markersize=2, marker='s', label='Confidence')
    ax.set_xlim(-0.05, 1.1)
    ax.set_xlabel('Score [0–1]', color='black')
    ax.tick_params(axis='x', colors='black')
    ax.invert_yaxis()
    _setup_depth_yaxis(ax, depths)

    if not np.all(np.isnan(mri_vals)):
        ax2 = ax.twiny()
        ax2.plot(mri_vals, depths, color='steelblue', linestyle='--',
                 linewidth=1.5, markersize=3, marker='o', label='MRI')
        ax2.set_xlabel('MRI (native)', color='steelblue')
        ax2.tick_params(axis='x', colors='steelblue')
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc='lower right')
    else:
        ax.legend(fontsize=7, loc='lower right')

    if fit_scores is not None and session_id in fit_scores.index:
        r = fit_scores.loc[session_id, 'fit_score']
        n = fit_scores.loc[session_id, 'n_points']
        ax.set_title(f'weighted r = {r:.3f}  (n={n})', fontsize=8)


def plot_cortex_pc_scatter(
        df: pd.DataFrame,
        pca: PCA,
        pc1_col: str = 'PC1',
        pc2_col: str = 'PC2',
        pc3_col: str = 'PC3',
        pc4_col: str = 'PC4',
        sessions: list = None,
) -> None:
    """
    Plot PC3 vs PC4 restricted to the brain+cortex quadrant (PC1>0, PC2>0).

    The hypothesis is that PC1+ = brain tissue, PC2+ = gray matter (cortex),
    so filtering to that quadrant isolates cortical depths. PC3 and PC4 within
    that subspace may capture columnar or layer-level variation.

    Two panels:
      left  — coloured by session
      right — coloured by depth under chamber (mm)
    """
    for col in (pc1_col, pc2_col, pc3_col, pc4_col):
        if col not in df.columns:
            print(f"plot_cortex_pc_scatter: column {col!r} not found, skipping.")
            return

    mask = (df[pc1_col] > 0) & (df[pc2_col] > 0)
    sub = df[mask].copy()
    print(f"Cortex subspace: {mask.sum()} / {len(df)} depth-bins pass PC1>0 & PC2>0")
    if len(sub) < 3:
        print("  Too few points, skipping plot.")
        return

    if sessions is None:
        sessions = sorted(sub['session_id'].unique())

    n_sessions = len(sessions)
    if n_sessions <= 10:
        sess_colors = plt.cm.tab10(np.linspace(0, 1, n_sessions))
    elif n_sessions <= 20:
        sess_colors = plt.cm.tab20(np.linspace(0, 1, n_sessions))
    else:
        sess_colors = plt.cm.viridis(np.linspace(0, 1, n_sessions))
    sess_color_map = dict(zip(sessions, sess_colors))

    var3 = pca.explained_variance_ratio_[int(pc3_col[2:]) - 1] * 100
    var4 = pca.explained_variance_ratio_[int(pc4_col[2:]) - 1] * 100

    fig, (ax_sess, ax_depth) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: coloured by session
    for sess in sessions:
        sd = sub[sub['session_id'] == sess]
        if sd.empty:
            continue
        ax_sess.scatter(sd[pc3_col], sd[pc4_col],
                        c=[sess_color_map[sess]], label=sess,
                        alpha=0.75, edgecolors='none', s=60)
    ax_sess.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
    ax_sess.axvline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
    ax_sess.set_xlabel(f'{pc3_col} ({var3:.1f}%)')
    ax_sess.set_ylabel(f'{pc4_col} ({var4:.1f}%)')
    ax_sess.set_title('By session')
    ax_sess.legend(fontsize=7, bbox_to_anchor=(1.01, 1), loc='upper left')
    ax_sess.grid(True, alpha=0.25)

    # Panel 2: coloured by depth
    depths = sub['depth_under_chamber_mm'].values
    sc = ax_depth.scatter(sub[pc3_col], sub[pc4_col],
                          c=depths, cmap='viridis_r', alpha=0.75,
                          edgecolors='none', s=60)
    plt.colorbar(sc, ax=ax_depth, label='Depth under chamber (mm)')
    ax_depth.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
    ax_depth.axvline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
    ax_depth.set_xlabel(f'{pc3_col} ({var3:.1f}%)')
    ax_depth.set_ylabel(f'{pc4_col} ({var4:.1f}%)')
    ax_depth.set_title('By depth')
    ax_depth.grid(True, alpha=0.25)

    fig.suptitle(
        f'PC3 vs PC4 — cortex subspace (PC1>0 & PC2>0)\n'
        f'n = {len(sub)} depth-bins from {n_sessions} sessions',
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig('cortex_pc3_pc4_scatter.png', dpi=150, bbox_inches='tight')
    plt.show()


def run_cortex_pca(
        df_conf: pd.DataFrame,
        feature_columns: list,
        n_pcs: int = 4,
        tissue_score_min: float = 0.3,
        tissue_score_max: float = 0.75,
) -> Optional[dict]:
    """
    Second-stage PCA run on cortical gray-matter bins only.

    Why a separate PCA rather than looking at PC3/PC4 from the global PCA:
    global PCA enforces orthogonality across ALL tissue types (sulcus, WM,
    GM), so PC3/PC4 are constrained to be orthogonal to sulcus↔brain and
    GM↔WM axes.  Any within-cortex structure that partially aligns with
    those axes gets projected out.  Running PCA fresh on the cortical
    subset lets the components freely capture within-cortex variance
    (layer-to-layer or column-to-column) without that constraint.

    Parameters
    ----------
    tissue_score_min / max : gray-matter band.  tissue_score ≈ 0.5 = GM,
        0.0 = sulcus, 1.0 = WM.  Default [0.3, 0.75] keeps GM and excludes
        clear sulcus / WM.

    Returns a dict with keys: pca, df_ctx, feature_columns, X_pca, or None
    if too few bins.
    """
    if 'tissue_score' not in df_conf.columns:
        print("run_cortex_pca: tissue_score column missing — run compute_tissue_confidence first.")
        return None

    mask = (df_conf['tissue_score'] >= tissue_score_min) & \
           (df_conf['tissue_score'] <= tissue_score_max)
    df_ctx = df_conf[mask].copy()
    n_ctx = mask.sum()
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

    # ── Loadings ────────────────────────────────────────────────────────────
    loadings = pd.DataFrame(
        pca_ctx.components_[:n_pcs_act].T,
        columns=[f'CPC{i + 1}' for i in range(n_pcs_act)],
        index=feature_columns,
    )
    fig, axes = plt.subplots(1, n_pcs_act, figsize=(4 * n_pcs_act, 6), sharey=True)
    if n_pcs_act == 1:
        axes = [axes]
    for i, ax in enumerate(axes):
        vals = pca_ctx.components_[i]
        colors = ['steelblue' if v >= 0 else 'coral' for v in vals]
        ax.barh(np.arange(len(feature_columns)), vals, color=colors, alpha=0.7)
        ax.axvline(0, color='black', linewidth=0.8)
        ax.set_yticks(np.arange(len(feature_columns)))
        if i == 0:
            ax.set_yticklabels(feature_columns)
        ax.set_title(f"CPC{i + 1} ({pca_ctx.explained_variance_ratio_[i] * 100:.1f}%)")
        ax.set_xlabel('Loading')
        ax.grid(True, alpha=0.3, axis='x')
    fig.suptitle('Cortex PCA Loadings', fontsize=13)
    plt.tight_layout()
    plt.savefig('cortex_pca_loadings.png', dpi=150, bbox_inches='tight')
    plt.show()

    # ── Depth profiles per session ──────────────────────────────────────────
    sessions = sorted(df_ctx['session_id'].unique())
    n_sessions = len(sessions)
    cpc_cols = [f'CPC{i + 1}' for i in range(n_pcs_act)]
    pc_colors = plt.cm.Set1(np.linspace(0, 1, n_pcs_act))

    fig, axes = plt.subplots(1, n_sessions,
                             figsize=(3.5 * n_sessions, 7),
                             sharey=False)
    if n_sessions == 1:
        axes = [axes]

    for ax, session in zip(axes, sessions):
        sd = df_ctx[df_ctx['session_id'] == session].sort_values('depth_under_chamber_mm')
        if sd.empty:
            ax.set_visible(False)
            continue
        depths = sd['depth_under_chamber_mm'].values
        for i, col in enumerate(cpc_cols):
            v = pca_ctx.explained_variance_ratio_[i] * 100
            ax.plot(sd[col].values, depths,
                    'o-', color=pc_colors[i], linewidth=1.5, markersize=4,
                    alpha=0.85, label=f'CPC{i + 1} ({v:.0f}%)')
        ax.axvline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
        ax.set_title(str(session), fontsize=9)
        ax.set_xlabel('Cortex PC value')
        if ax is axes[0]:
            ax.set_ylabel('Depth under chamber (mm)')
        ax.invert_yaxis()
        _setup_depth_yaxis(ax, depths)
        ax.legend(fontsize=7)

    fig.suptitle(
        f'Cortex PCA depth profiles  (tissue_score [{tissue_score_min}–{tissue_score_max}])',
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig('cortex_pca_depth_profiles.png', dpi=150, bbox_inches='tight')
    plt.show()

    # ── Scatter CPC1 vs CPC2 ───────────────────────────────────────────────
    if n_pcs_act >= 2:
        if n_sessions <= 10:
            sess_colors = plt.cm.tab10(np.linspace(0, 1, n_sessions))
        else:
            sess_colors = plt.cm.tab20(np.linspace(0, 1, n_sessions))
        sess_cmap = dict(zip(sessions, sess_colors))

        fig, (ax_s, ax_d) = plt.subplots(1, 2, figsize=(13, 5))
        for sess in sessions:
            sd = df_ctx[df_ctx['session_id'] == sess]
            ax_s.scatter(sd['CPC1'], sd['CPC2'],
                         c=[sess_cmap[sess]], label=sess,
                         alpha=0.75, edgecolors='none', s=55)
        ax_s.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
        ax_s.axvline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
        v1 = pca_ctx.explained_variance_ratio_[0] * 100
        v2 = pca_ctx.explained_variance_ratio_[1] * 100
        ax_s.set_xlabel(f'CPC1 ({v1:.1f}%)')
        ax_s.set_ylabel(f'CPC2 ({v2:.1f}%)')
        ax_s.set_title('By session')
        ax_s.legend(fontsize=7, bbox_to_anchor=(1.01, 1), loc='upper left')
        ax_s.grid(True, alpha=0.25)

        depths_all = df_ctx['depth_under_chamber_mm'].values
        sc = ax_d.scatter(df_ctx['CPC1'], df_ctx['CPC2'],
                          c=depths_all, cmap='viridis_r',
                          alpha=0.75, edgecolors='none', s=55)
        plt.colorbar(sc, ax=ax_d, label='Depth (mm)')
        ax_d.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
        ax_d.axvline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
        ax_d.set_xlabel(f'CPC1 ({v1:.1f}%)')
        ax_d.set_ylabel(f'CPC2 ({v2:.1f}%)')
        ax_d.set_title('By depth')
        ax_d.grid(True, alpha=0.25)

        fig.suptitle(
            f'Cortex PCA  —  CPC1 vs CPC2\n'
            f'n = {len(df_ctx)} bins, tissue_score [{tissue_score_min}–{tissue_score_max}]',
            fontsize=12,
        )
        plt.tight_layout()
        plt.savefig('cortex_pca_scatter.png', dpi=150, bbox_inches='tight')
        plt.show()

    return {
        'pca': pca_ctx,
        'df_ctx': df_ctx,
        'feature_columns': feature_columns,
        'X_pca': X_pca,
        'scaler': scaler,
    }


def run_analysis(conn: Connection, table_name: str = "PenetrationMetrics", n_pcs: int = 4,
                 mri_config_path: str = MRI_VIEWER_CONFIG_PATH, exclude_sessions=None,
                 within_session_normalize: bool = True,
                 swap_tissue_pcs: bool = False,
                 pc_smooth_sigma: float = 2.0,
                 varimax_n_components: int = 6,
                 decomp_method: str = DECOMPOSITION_METHOD,
                 use_varimax: bool = USE_VARIMAX):
    """Run complete PCA analysis with correlations and plots."""

    # Load and perform PCA / Factor Analysis
    df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(
        conn, table_name,
        exclude_sessions=exclude_sessions,
        within_session_normalize=within_session_normalize,
        pc_smooth_sigma=pc_smooth_sigma,
        varimax_n_components=varimax_n_components,
        decomp_method=decomp_method,
        use_varimax=use_varimax,
    )

    # Get and print loadings
    print("\n" + "=" * 60)
    print("PCA LOADINGS")
    print("=" * 60)
    loadings_df = get_loadings_df(pca, feature_columns)
    print(loadings_df.round(3))

    # Get and print feature correlations
    corr_df = get_feature_correlations(df, feature_columns, n_pcs=n_pcs)
    print_feature_correlations(corr_df)

    # Plots
    plot_scree(pca)
    plot_loadings(pca, feature_columns, n_pcs=n_pcs)
    plot_correlation_heatmap(corr_df, feature_columns)
    plot_pca_scatter(df, pca, X_pca, plot_components=list(range(min(n_pcs, 3))))

    # Depth profiles
    # plot_depth_profiles_by_session(df, pca, n_pcs=n_pcs)
    plot_depth_profiles_all_sessions(df, pca, n_pcs=n_pcs)
    plot_depth_profiles_overlaid(df, pca, n_pcs=n_pcs)
    # plot_depth_profiles_overlaid(df, pca, n_pcs=n_pcs, align_depths=True)

    # Tissue confidence — column mapping depends on decomp_method + varimax
    if decomp_method == 'fa':
        tissue_conf = _TISSUE_CONF_FA_VARIMAX if use_varimax else _TISSUE_CONF_FA_NO_VARIMAX
    else:
        tissue_conf = _TISSUE_CONF_PCA
    df_conf = compute_tissue_confidence(df, **tissue_conf)
    plot_tissue_confidence_by_session(df_conf, pca=pca, n_pcs=n_pcs)

    # PC3 vs PC4 in the cortex subspace (PC1>0 and PC2>0)
    plot_cortex_pc_scatter(df_conf, pca)

    # Second-stage PCA on cortical bins only
    cortex_pca_result = run_cortex_pca(df_conf, feature_columns, n_pcs=n_pcs)

    # MRI comparison + optimisation
    fit_scores = None
    opt_result = None
    mri_pipeline = None
    try:
        print("\nLoading MRI pipeline ...")
        mri_pipeline = load_mri_pipeline(mri_config_path)

        print("\n── Initial MRI comparison ──")
        df_conf = compute_mri_comparison(df_conf, conn, mri_pipeline)
        fit_scores = compute_trajectory_fit_scores(df_conf)
        plot_mri_comparison_by_session(df_conf, fit_scores)

        print("\n── Optimising transformation ──")
        opt_result = optimize_trajectory_alignment(df_conf, conn, mri_pipeline)

        print("\n── MRI comparison with optimised transformation ──")
        opt_pipeline, daz, del_, ddepth = apply_optimized_pipeline(mri_pipeline, opt_result)
        df_conf = compute_mri_comparison(df_conf, conn, opt_pipeline,
                                         daz=daz, del_=del_, ddepth=ddepth)
        fit_scores = compute_trajectory_fit_scores(df_conf)
        plot_mri_comparison_by_session(df_conf, fit_scores)

        print("\n── Optimisation complete ──")
        print(f"  score: {opt_result['score_before']:.4f} → {opt_result['score_after']:.4f}")
        answer = input("Save this result? [y/N]: ").strip().lower()
        if answer == 'y':
            opt_result['result_path'] = save_optimized_params(opt_result, mri_pipeline)
        else:
            print("  Result not saved.")

    except Exception as exc:
        import traceback
        print(f"  MRI comparison / optimisation skipped: {exc}")
        traceback.print_exc()

    return {
        'df': df_conf,
        'pca': pca,
        'X_pca': X_pca,
        'feature_columns': feature_columns,
        'loadings': loadings_df,
        'correlations': corr_df,
        'fit_scores': fit_scores,
        'opt_result': opt_result,
        'mri_pipeline': mri_pipeline,
        'cortex_pca': cortex_pca_result,
    }


if __name__ == "__main__":
    conn = Connection(
        database="allen_data_repository",  # Update this
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61"
    )

    exclude_sessions = ["260402_0", "260327_0"]
    results = run_analysis(conn, n_pcs=4, exclude_sessions =exclude_sessions)

    # Access results
    # results['df']              - DataFrame with PC columns added
    # results['pca']             - Fitted PCA object
    # results['X_pca']           - PCA-transformed data
    # results['feature_columns'] - List of feature names
    # results['loadings']        - DataFrame of loadings
    # results['correlations']    - DataFrame of feature-PC correlations
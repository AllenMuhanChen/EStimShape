import importlib.util
import json
import os
from typing import Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import map_coordinates
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.stats import pearsonr
from itertools import combinations

from clat.util.connection import Connection

MRI_VIEWER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../../mri/mri_viewer_config.json')


def load_and_perform_pca(conn: Connection, table_name: str = "PenetrationMetrics"):
    """Load data and perform PCA, returning all necessary objects."""
    conn.execute(f"SELECT * FROM {table_name}")
    results = conn.fetch_all()

    conn.execute(f"DESCRIBE {table_name}")
    columns = [row[0] for row in conn.fetch_all()]

    df = pd.DataFrame(results, columns=columns)

    print(f"Loaded {len(df)} rows with columns: {list(df.columns)}")

    pk_columns = ['session_id', 'depth_under_chamber_mm']
    feature_columns = [
        col for col in df.columns
        if col not in pk_columns
           and pd.api.types.is_numeric_dtype(df[col])
    ]

    print(f"Feature columns for PCA: {feature_columns}")

    X = df[feature_columns].copy()
    X = X.fillna(X.mean())

    valid_mask = ~X.isna().any(axis=1)
    X = X[valid_mask]
    df_valid = df[valid_mask].copy()

    print(f"Using {len(X)} rows after handling missing values")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA()
    X_pca = pca.fit_transform(X_scaled)

    for i in range(X_pca.shape[1]):
        df_valid[f'PC{i + 1}'] = X_pca[:, i]

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
            ax.grid(True, alpha=0.3)

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
            ax.grid(True, alpha=0.3)

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

    n_cols = min(3, n_pcs)
    n_rows = (n_pcs + n_cols - 1) // n_cols

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

        ax.grid(True, alpha=0.3)

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


def compute_tissue_confidence(
        df: pd.DataFrame,
        pc1_col: str = 'PC1',
        pc2_col: str = 'PC2',
) -> pd.DataFrame:
    """
    Compute per-depth tissue confidence scores from PC1 and PC2.

    PC1: negative = sulcus, positive = brain
    PC2: negative = white matter, positive = gray matter

    Adds three columns to a copy of df:
      p_brain      : probability of being brain tissue  (0=sulcus, 1=brain)
      p_gray       : probability of being gray matter   (0=white matter, 1=gray)
      tissue_score : combined grayscale value
                     ~0.0 = sulcus
                     ~0.5 = gray matter
                     ~1.0 = white matter
    """
    def sigmoid(x):
        return 1.0 / (1.0 + np.exp(-x))

    df = df.copy()
    std1 = df[pc1_col].std()
    std2 = df[pc2_col].std()

    df['p_brain'] = sigmoid(df[pc1_col] / std1)
    df['p_gray'] = sigmoid(df[pc2_col] / std2)
    df['tissue_score'] = df['p_brain'] * (1.0 - 0.5 * df['p_gray'])
    return df


def plot_tissue_confidence_by_session(
        df: pd.DataFrame,
        sessions: list = None,
        strip_width: float = 0.4,
) -> None:
    """
    For each session plot a grayscale depth strip showing tissue confidence:
      black  (~0.0) = sulcus
      gray   (~0.5) = gray matter
      white  (~1.0) = white matter

    Produces one combined figure with all sessions side by side and saves it,
    then shows individual per-session figures.
    """
    if sessions is None:
        sessions = sorted(df['session_id'].unique())

    n_sessions = len(sessions)

    # ── Combined figure (all sessions as columns) ──────────────────────────
    fig_all, axes_all = plt.subplots(
        1, n_sessions * 2,
        figsize=(3 * n_sessions, 10),
        gridspec_kw={'width_ratios': [strip_width, 1] * n_sessions},
    )
    if n_sessions == 1:
        axes_all = np.array(axes_all).reshape(1, 2)
    else:
        axes_all = np.array(axes_all).reshape(n_sessions, 2)

    for col_idx, session in enumerate(sessions):
        sdata = df[df['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
        if sdata.empty:
            continue

        depths = sdata['depth_under_chamber_mm'].values
        scores = sdata['tissue_score'].values

        ax_strip = axes_all[col_idx, 0]
        ax_line = axes_all[col_idx, 1]

        _draw_tissue_strip(ax_strip, depths, scores, title=session)
        _draw_tissue_line(ax_line, depths, scores)

        if col_idx > 0:
            ax_strip.set_ylabel('')

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

        fig, (ax_strip, ax_line) = plt.subplots(
            1, 2,
            figsize=(5, 10),
            gridspec_kw={'width_ratios': [strip_width, 1]},
        )
        _draw_tissue_strip(ax_strip, depths, scores, title=session)
        _draw_tissue_line(ax_line, depths, scores)

        fig.suptitle(f'Tissue Confidence — {session}\n'
                     '(black=sulcus, gray=gray matter, white=white matter)',
                     fontsize=11)
        plt.tight_layout()
        plt.savefig(f'tissue_confidence_{session}.png', dpi=150, bbox_inches='tight')
        plt.show()


def _draw_tissue_strip(
        ax: plt.Axes,
        depths: np.ndarray,
        scores: np.ndarray,
        title: str = '',
        vmax: float = 1.0,
) -> None:
    """Render scores as a grayscale imshow strip with depth on the y-axis."""
    n = len(depths)
    strip = scores.reshape(n, 1)

    ax.imshow(
        strip,
        aspect='auto',
        cmap='gray',
        vmin=0,
        vmax=vmax,
        origin='upper',
        extent=[0, 1, depths[-1], depths[0]],
    )
    ax.set_xticks([])
    ax.set_ylabel('Depth under chamber (mm)')
    ax.set_xlabel('')
    ax.set_title(title, fontsize=8, rotation=45, ha='right')


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
    ax.yaxis.set_tick_params(labelleft=False)
    ax.grid(True, alpha=0.3)

    for score_val, label in [(0.0, 'Sulcus'), (0.5, 'Gray'), (1.0, 'WM')]:
        ax.axvline(score_val, color='lightgray', linewidth=0.5, linestyle=':')


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

    mri_corr, _ = load_corrections(par_path + '_corrections.json')
    corrected_affine = mri_corr @ native_affine
    inv_corrected = np.linalg.inv(corrected_affine)

    spec = importlib.util.spec_from_file_location('monkey_specific', monkey_specific_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    screws_ebz = np.array(mod.get_screw_hole_coords())
    ref_idx = mod.get_reference_screw_idx()
    cor_offset = mod.get_center_of_rotation_offset()
    is_fit_circle = mod.get_is_fit_circle()

    ch_corr, _ = load_corrections(monkey_specific_path + '_chamber_corrections.json')
    screws_world = screws_ebz + ebz_world
    if not np.allclose(ch_corr, np.eye(4)):
        R = ch_corr[:3, :3]
        t = ch_corr[:3, 3]
        screws_world = (R @ screws_world.T).T + t

    center, origin, x, y, normal = fit_chamber(screws_world, ref_idx, cor_offset, is_fit_circle)

    return {
        'data': data,
        'inv_corrected': inv_corrected,
        'origin': origin,
        'x': x,
        'y': y,
        'normal': normal,
        'cor_offset': cor_offset,
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

    # order=0: nearest-neighbour — no cross-voxel blending, preserves sharp tissue boundaries
    values = map_coordinates(data, vox_coords.T, order=0, mode='constant', cval=0.0)
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
) -> pd.DataFrame:
    """
    Add MRI intensity sampled along each session's trajectory.

    Adds columns:
      mri_raw        : raw voxel intensity at each depth
      mri_normalized : clipped to 99th-percentile then scaled so
                       max(mri_normalized) == max(tissue_score) per session,
                       with 0=black on both sides

    Uses 99th-percentile rather than absolute max to prevent a single bright
    voxel (skull edge, vessel, artifact) from compressing the whole range and
    hiding soft-tissue / CSF contrast.
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
        depths = df.loc[mask, 'depth_under_chamber_mm'].values
        mri_vals = sample_mri_along_trajectory(mri_pipeline, pen['az_deg'], pen['el_deg'], depths)
        df.loc[mask, 'mri_raw'] = mri_vals

        # Use 99th percentile of positive values so outlier bright voxels don't
        # collapse the contrast; then clip and scale to match tissue_score range.
        pos = mri_vals[mri_vals > 0]
        mri_ref = float(np.percentile(pos, 99)) if len(pos) > 0 else 1.0
        ts_max = float(df.loc[mask, 'tissue_score'].max())
        if mri_ref > 0 and ts_max > 0:
            scaled = np.clip(mri_vals, 0.0, mri_ref) / mri_ref * ts_max
        else:
            scaled = mri_vals.copy()
        df.loc[mask, 'mri_normalized'] = scaled

        print(f"  {session_id} ({pen['pen_type']}): "
              f"MRI raw [{mri_vals.min():.0f}–{mri_vals.max():.0f}], "
              f"99th pct={mri_ref:.0f}, "
              f"mri_norm [{scaled.min():.3f}–{scaled.max():.3f}]")

    return df


def compute_trajectory_fit_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weighted Pearson correlation between tissue_score and mri_normalized per session.

    Weights = abs(2 * tissue_score - 1): 0 at ambiguous mid-gray, 1 at confident
    sulcus or white matter.

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
        w = np.abs(2.0 * ts - 1.0)

        w_sum = w.sum()
        if w_sum == 0:
            records.append({'session_id': session_id, 'fit_score': np.nan, 'n_points': n})
            continue

        ts_wm = (w * ts).sum() / w_sum
        mri_wm = (w * mri).sum() / w_sum
        ts_c = ts - ts_wm
        mri_c = mri - mri_wm
        num = (w * ts_c * mri_c).sum()
        denom = np.sqrt((w * ts_c ** 2).sum() * (w * mri_c ** 2).sum())
        r = float(num / denom) if denom > 0 else np.nan
        records.append({'session_id': session_id, 'fit_score': r, 'n_points': n})

    result = pd.DataFrame(records).set_index('session_id')
    print("\nTrajectory fit scores (weighted Pearson r, tissue_score vs MRI):")
    print(result.to_string())
    return result


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

    # Combined figure
    fig_all, all_axes = plt.subplots(
        1, n_sessions * 3,
        figsize=(4.5 * n_sessions, 10),
        gridspec_kw={'width_ratios': [strip_width, strip_width, 1] * n_sessions},
    )
    if n_sessions == 1:
        all_axes = np.array(all_axes)
    ax_groups = [all_axes[i * 3:(i + 1) * 3] for i in range(n_sessions)]

    for idx, session in enumerate(sessions):
        sdata = df[df['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
        if sdata.empty:
            continue

        depths = sdata['depth_under_chamber_mm'].values
        ts = sdata['tissue_score'].values
        mri_norm = sdata['mri_normalized'].values
        ts_max = ts.max() if ts.max() > 0 else 1.0

        ax_mri, ax_ts, ax_line = ax_groups[idx]

        _draw_tissue_strip(ax_mri, depths, mri_norm, title=f'{session}\nMRI', vmax=ts_max)
        _draw_tissue_strip(ax_ts, depths, ts, title='Tissue', vmax=ts_max)
        _draw_mri_tissue_line(ax_line, depths, ts, mri_norm, fit_scores, session)

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
        mri_norm = sdata['mri_normalized'].values
        ts_max = ts.max() if ts.max() > 0 else 1.0

        fig, (ax_mri, ax_ts, ax_line) = plt.subplots(
            1, 3,
            figsize=(6, 10),
            gridspec_kw={'width_ratios': [strip_width, strip_width, 1]},
        )
        _draw_tissue_strip(ax_mri, depths, mri_norm, title='MRI (norm)', vmax=ts_max)
        _draw_tissue_strip(ax_ts, depths, ts, title='Tissue score', vmax=ts_max)
        _draw_mri_tissue_line(ax_line, depths, ts, mri_norm, fit_scores, session)

        fig.suptitle(f'MRI vs Tissue Confidence — {session}', fontsize=11)
        plt.tight_layout()
        plt.savefig(f'mri_vs_tissue_confidence_{session}.png', dpi=150, bbox_inches='tight')
        plt.show()


def _draw_mri_tissue_line(
        ax: plt.Axes,
        depths: np.ndarray,
        tissue_score: np.ndarray,
        mri_norm: np.ndarray,
        fit_scores: Optional[pd.DataFrame],
        session_id: str,
) -> None:
    """Overlay line plot of tissue_score and MRI along depth."""
    ax.plot(tissue_score, depths, 'k-o', markersize=3, linewidth=1.5, label='Tissue score')
    if not np.all(np.isnan(mri_norm)):
        ax.plot(mri_norm, depths, color='steelblue', linestyle='--',
                linewidth=1.5, markersize=3, marker='o', label='MRI (norm)')

    ts_max = tissue_score.max() if tissue_score.max() > 0 else 1.0
    ax.set_xlim(-0.05, ts_max * 1.1)
    ax.set_xlabel('Score')
    ax.invert_yaxis()
    ax.yaxis.set_tick_params(labelleft=False)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)

    if fit_scores is not None and session_id in fit_scores.index:
        r = fit_scores.loc[session_id, 'fit_score']
        n = fit_scores.loc[session_id, 'n_points']
        ax.set_title(f'weighted r = {r:.3f}  (n={n})', fontsize=8)


def run_analysis(conn: Connection, table_name: str = "PenetrationMetrics", n_pcs: int = 4,
                 mri_config_path: str = MRI_VIEWER_CONFIG_PATH):
    """Run complete PCA analysis with correlations and plots."""

    # Load and perform PCA
    df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(conn, table_name)

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
    plot_depth_profiles_by_session(df, pca, n_pcs=n_pcs)
    plot_depth_profiles_all_sessions(df, pca, n_pcs=n_pcs)
    plot_depth_profiles_overlaid(df, pca, n_pcs=n_pcs)
    plot_depth_profiles_overlaid(df, pca, n_pcs=n_pcs, align_depths=True)

    # Tissue confidence
    df_conf = compute_tissue_confidence(df)
    plot_tissue_confidence_by_session(df_conf)

    # MRI comparison
    fit_scores = None
    try:
        print("\nLoading MRI pipeline ...")
        mri_pipeline = load_mri_pipeline(mri_config_path)
        df_conf = compute_mri_comparison(df_conf, conn, mri_pipeline)
        fit_scores = compute_trajectory_fit_scores(df_conf)
        plot_mri_comparison_by_session(df_conf, fit_scores)
    except Exception as exc:
        print(f"  MRI comparison skipped: {exc}")

    return {
        'df': df_conf,
        'pca': pca,
        'X_pca': X_pca,
        'feature_columns': feature_columns,
        'loadings': loadings_df,
        'correlations': corr_df,
        'fit_scores': fit_scores,
    }


if __name__ == "__main__":
    conn = Connection(
        database="allen_data_repository",  # Update this
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61"
    )

    results = run_analysis(conn, n_pcs=4)

    # Access results
    # results['df']              - DataFrame with PC columns added
    # results['pca']             - Fitted PCA object
    # results['X_pca']           - PCA-transformed data
    # results['feature_columns'] - List of feature names
    # results['loadings']        - DataFrame of loadings
    # results['correlations']    - DataFrame of feature-PC correlations
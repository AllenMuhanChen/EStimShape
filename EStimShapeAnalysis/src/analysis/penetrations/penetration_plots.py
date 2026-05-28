"""Plotting + figure-saving helpers for the penetrations analysis pipeline.

Pure rendering — all functions accept a fitted PCA object and a results
dataframe and write a figure to disk. Run-tag / directory helpers live here
too (`_pca_run_tag`, `_opt_run_tag`, `_make_run_dirs`, `_write_fit_log`).
"""
import datetime
import os
from itertools import combinations
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MultipleLocator
from sklearn.decomposition import PCA


PLOT_BASE_DIR = os.path.expanduser("~/Documents/penetration_optimization_plots")


# ---------------------------------------------------------------------------
# Run-tag / directory / log helpers
# ---------------------------------------------------------------------------

def _save_fig(save_dir: Optional[str], filename: str, dpi: int = 150) -> None:
    """Save current matplotlib figure to save_dir/filename (or just filename if None)."""
    path = os.path.join(save_dir, filename) if save_dir else filename
    plt.savefig(path, dpi=dpi, bbox_inches='tight')


def _pca_run_tag(
        decomp_method: str,
        varimax_n_components: int,
        use_varimax: bool,
        within_session_normalize: bool,
        pc_smooth_sigma: float,
        exclude_sessions=None,
) -> str:
    """Short human-readable tag identifying a PCA configuration."""
    parts = [
        decomp_method,
        f"{varimax_n_components}pcs",
        f"vm{'T' if use_varimax else 'F'}",
        f"norm{'T' if within_session_normalize else 'F'}",
        f"sig{pc_smooth_sigma:.1f}",
    ]
    n_excl = len(exclude_sessions) if exclude_sessions else 0
    if n_excl:
        parts.append(f"excl{n_excl}")
    return "_".join(parts)


def _opt_run_tag(
        softmin_beta: float,
        variance_penalty: float,
        enable_per_session_corrections: bool,
        chamber_dist_penalty: float,
        chamber_param_penalty: float,
        session_corr_penalty: float,
) -> str:
    """Short tag identifying an optimization run (includes timestamp for uniqueness)."""
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    parts = [
        f"beta{softmin_beta:g}",
        f"var{variance_penalty:g}",
        f"sess{'T' if enable_per_session_corrections else 'F'}",
        f"cd{chamber_dist_penalty:g}",
        f"cp{chamber_param_penalty:g}",
    ]
    if enable_per_session_corrections:
        parts.append(f"Ls{session_corr_penalty:g}")
    parts.append(ts)
    return "_".join(parts)


def _make_run_dirs(pca_tag: str, opt_tag: str, base_dir: str = PLOT_BASE_DIR):
    """Create and return (pca_dir, opt_dir)."""
    pca_dir = os.path.join(base_dir, pca_tag)
    opt_dir = os.path.join(pca_dir, opt_tag)
    os.makedirs(pca_dir, exist_ok=True)
    os.makedirs(opt_dir, exist_ok=True)
    return pca_dir, opt_dir


def _write_fit_log(
        opt_dir: str,
        pca_tag: str,
        opt_params: dict,
        opt_result: dict,
        fit_scores=None,
) -> None:
    """Write a human-readable fit summary to opt_dir/fit_log.txt."""
    lines = [
        f"PCA run:  {pca_tag}",
        f"Opt run:  {os.path.basename(opt_dir)}",
        f"Written:  {datetime.datetime.now().isoformat()}",
        "",
        "=== Optimization Settings ===",
    ]
    for k, v in opt_params.items():
        lines.append(f"  {k}: {v}")
    lines += [
        "",
        "=== Results ===",
        f"  Sessions:     {len(opt_result.get('session_ids', []))}",
        f"  Score before: {opt_result.get('score_before', float('nan')):.4f}",
        f"  Score after:  {opt_result.get('score_after',  float('nan')):.4f}",
        f"  Delta:        {opt_result.get('score_after', 0.) - opt_result.get('score_before', 0.):+.4f}",
        f"  Raw before:   {opt_result.get('raw_before',   float('nan')):.4f}",
        f"  Raw after:    {opt_result.get('raw_after',    float('nan')):.4f}",
        f"  Raw delta:    {opt_result.get('raw_after', 0.)   - opt_result.get('raw_before', 0.):+.4f}",
        "",
        "=== Global Parameters ===",
    ]
    params_arr  = opt_result.get('params', [])
    param_names = opt_result.get('param_names', [])
    for name, val in zip(param_names[:9], params_arr[:9]):
        lines.append(f"  {name:<14s} = {float(val):+.4f}")
    per_sess = opt_result.get('per_session_corrections', {})
    if per_sess:
        lines += ["", "=== Per-Session Corrections ===",
                  f"  {'session':<22s} {'daz_deg':>8s} {'del_deg':>8s} {'ddepth_mm':>10s}"]
        for sid, c in per_sess.items():
            lines.append(f"  {str(sid):<22s} {c['daz_deg']:+8.3f} {c['del_deg']:+8.3f} {c['ddepth_mm']:+10.3f}")
    if fit_scores is not None and not fit_scores.empty:
        lines += ["", "=== Trajectory Fit Scores (tissue_score vs MRI) ===",
                  fit_scores.to_string()]
    log_path = os.path.join(opt_dir, "fit_log.txt")
    with open(log_path, 'w') as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Fit log → {log_path}")


# ---------------------------------------------------------------------------
# Depth-axis + tissue-strip primitives
# ---------------------------------------------------------------------------

def _setup_depth_yaxis(ax: plt.Axes, depths: np.ndarray,
                       label_interval_mm: float = 0.5,
                       tick_interval_mm: float = 0.1) -> None:
    """Dense minor ticks every tick_interval_mm; labelled major ticks every label_interval_mm."""
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
    """Render scores as a grayscale imshow strip with depth on the y-axis."""
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
    """Line plot of tissue_score vs depth."""
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


def _draw_mri_tissue_line(
        ax: plt.Axes,
        depths: np.ndarray,
        tissue_score: np.ndarray,
        mri_vals: np.ndarray,
        fit_scores: Optional[pd.DataFrame],
        session_id: str,
        confidence: np.ndarray = None,
) -> None:
    """Tissue score (+ optional confidence) and MRI native values vs depth."""
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


# ---------------------------------------------------------------------------
# PCA-level plots
# ---------------------------------------------------------------------------

def plot_pca_scatter(
        df: pd.DataFrame,
        pca: PCA,
        X_pca: np.ndarray,
        plot_components: list = None,
        save_dir: Optional[str] = None,
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
                s=50,
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
    _save_fig(save_dir, 'pca_scatter.png')
    plt.show()


def plot_scree(pca: PCA, save_dir: Optional[str] = None):
    """Scree plot showing explained variance by component."""
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
    _save_fig(save_dir, 'scree.png')
    plt.show()


def plot_loadings(
        pca: PCA,
        feature_columns: list,
        n_pcs: int = 4,
        save_dir: Optional[str] = None,
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
    _save_fig(save_dir, 'loadings.png')
    plt.show()


def plot_correlation_heatmap(
        corr_df: pd.DataFrame,
        feature_columns: list,
        save_dir: Optional[str] = None,
):
    """Heatmap of feature-PC correlations."""
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
    _save_fig(save_dir, 'correlation_heatmap.png')
    plt.show()


def plot_depth_profiles_by_session(
        df: pd.DataFrame,
        pca: PCA,
        n_pcs: int = None,
        sessions: list = None,
        figsize_per_session: tuple = (12, 6),
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
        sessions: list = None,
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
        align_depths: bool = False,
        save_dir: Optional[str] = None,
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
    _save_fig(save_dir, f'depth_profiles_overlaid{suffix}.png')
    plt.show()


# ---------------------------------------------------------------------------
# Tissue / MRI plots
# ---------------------------------------------------------------------------

def plot_tissue_confidence_by_session(
        df: pd.DataFrame,
        pca: PCA = None,
        sessions: list = None,
        strip_width: float = 0.4,
        n_pcs: int = 4,
        save_dir: Optional[str] = None,
) -> None:
    """Per-session tissue-confidence strip + line + optional PC profiles."""
    if sessions is None:
        sessions = sorted(df['session_id'].unique())

    n_sessions = len(sessions)
    show_pcs = pca is not None

    panels_per_session = 3 if show_pcs else 2
    width_ratios_unit  = [strip_width, 1, 1.2] if show_pcs else [strip_width, 1]

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
    _save_fig(save_dir, 'tissue_confidence_all.png')
    plt.show()

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
        _save_fig(save_dir, f'tissue_confidence_{session}.png')
        plt.show()


def plot_mri_comparison_by_session(
        df: pd.DataFrame,
        fit_scores: Optional[pd.DataFrame] = None,
        sessions: list = None,
        strip_width: float = 0.4,
        save_dir: Optional[str] = None,
) -> None:
    """Per-session figure: MRI strip | tissue strip | overlay line."""
    if sessions is None:
        sessions = sorted(df['session_id'].unique())

    n_sessions = len(sessions)
    has_conf = 'tissue_confidence' in df.columns

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
    _save_fig(save_dir, 'mri_comparison_all.png')
    plt.show()

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
        _save_fig(save_dir, f'mri_comparison_{session}.png')
        plt.show()


def plot_predictor_comparison_by_session(
        predictor_results: dict,
        sessions: list = None,
        strip_width: float = 0.4,
        save_dir: Optional[str] = None,
) -> None:
    """Side-by-side per-session comparison of multiple tissue predictors.

    Layout per session:
        [MRI strip] [Seg strip if present] | (tissue strip + overlay line) per predictor.

    The reference strips (MRI / segmentation) are shared across predictors —
    the corrections file is fixed, so the sampled signals don't change.
    A `seg_tissue_score` column on any predictor's df enables the seg strip.

    Parameters
    ----------
    predictor_results : dict[str, dict]
        Mapping predictor name -> {'df': df_with_signals_and_tissue, 'fit_scores': DataFrame}.
        Every df must share the same depth_under_chamber_mm grid per session.
    """
    if not predictor_results:
        print("plot_predictor_comparison_by_session: no predictors to plot.")
        return

    names = list(predictor_results.keys())
    ref_df = predictor_results[names[0]]['df']
    if sessions is None:
        sessions = sorted(ref_df['session_id'].unique())

    has_mri = 'mri_normalized' in ref_df.columns
    has_seg = 'seg_tissue_score' in ref_df.columns

    n_pred = len(names)
    n_ref = int(has_mri) + int(has_seg)
    panels_per_session = n_ref + 2 * n_pred
    width_ratios_unit = ([strip_width] * n_ref) + [strip_width, 1] * n_pred

    # ── Combined figure ──────────────────────────────────────────────────────
    n_sessions = len(sessions)
    fig_all, all_axes = plt.subplots(
        1, n_sessions * panels_per_session,
        figsize=((1.5 + 2.0 * n_pred) * n_sessions, 10),
        gridspec_kw={'width_ratios': width_ratios_unit * n_sessions},
    )
    if n_sessions * panels_per_session == 1:
        all_axes = np.array([all_axes])
    ax_groups = [all_axes[i * panels_per_session:(i + 1) * panels_per_session]
                 for i in range(n_sessions)]

    for col_idx, session in enumerate(sessions):
        ref_sdata = ref_df[ref_df['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
        if ref_sdata.empty:
            continue
        depths = ref_sdata['depth_under_chamber_mm'].values

        if has_mri:
            mri_norm = ref_sdata['mri_normalized'].values
            mri_vmax = float(np.nanmax(mri_norm)) if np.any(np.isfinite(mri_norm)) else 1.0
        else:
            mri_norm = np.full(len(depths), np.nan)
            mri_vmax = 1.0
        seg_ts = ref_sdata['seg_tissue_score'].values if has_seg else None

        axes = ax_groups[col_idx]
        ref_idx = 0
        if has_mri:
            _draw_tissue_strip(axes[ref_idx], depths, mri_norm,
                               title=f'{session}\nMRI', vmax=mri_vmax)
            ref_idx += 1
        if has_seg:
            _draw_tissue_strip(axes[ref_idx], depths, seg_ts,
                               title=(f'{session}\nSeg' if not has_mri else 'Seg'),
                               vmax=1.0)
            ref_idx += 1

        for j, name in enumerate(names):
            res = predictor_results[name]
            sdata = res['df'][res['df']['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
            if sdata.empty:
                continue
            ts = sdata['tissue_score'].values
            conf = sdata['tissue_confidence'].values if 'tissue_confidence' in sdata.columns else None
            fit_scores = res.get('fit_scores')

            ax_ts   = axes[n_ref + 2 * j]
            ax_line = axes[n_ref + 2 * j + 1]
            _draw_tissue_strip(ax_ts, depths, ts, title=name, vmax=1.0)
            _draw_mri_tissue_line(ax_line, depths, ts, mri_norm, fit_scores, session, conf)

        if col_idx > 0:
            for r in range(n_ref):
                axes[r].set_ylabel('')
            for j in range(n_pred):
                axes[n_ref + 2 * j].set_ylabel('')

    fig_all.suptitle(
        'Predictor comparison (single corrections file)\n'
        '(black=sulcus, gray=GM, white=WM)',
        fontsize=12,
    )
    plt.tight_layout()
    _save_fig(save_dir, 'predictor_comparison_all.png')
    plt.show()

    # ── Per-session figures ──────────────────────────────────────────────────
    for session in sessions:
        ref_sdata = ref_df[ref_df['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
        if ref_sdata.empty:
            continue
        depths = ref_sdata['depth_under_chamber_mm'].values

        if has_mri:
            mri_norm = ref_sdata['mri_normalized'].values
            mri_vmax = float(np.nanmax(mri_norm)) if np.any(np.isfinite(mri_norm)) else 1.0
        else:
            mri_norm = np.full(len(depths), np.nan)
            mri_vmax = 1.0
        seg_ts = ref_sdata['seg_tissue_score'].values if has_seg else None

        fig, axes = plt.subplots(
            1, panels_per_session,
            figsize=(2 + 2.0 * n_pred, 10),
            gridspec_kw={'width_ratios': width_ratios_unit},
        )
        ref_idx = 0
        if has_mri:
            _draw_tissue_strip(axes[ref_idx], depths, mri_norm, title='MRI', vmax=mri_vmax)
            ref_idx += 1
        if has_seg:
            _draw_tissue_strip(axes[ref_idx], depths, seg_ts, title='Seg', vmax=1.0)
            ref_idx += 1

        for j, name in enumerate(names):
            res = predictor_results[name]
            sdata = res['df'][res['df']['session_id'] == session].copy().sort_values('depth_under_chamber_mm')
            if sdata.empty:
                continue
            ts = sdata['tissue_score'].values
            conf = sdata['tissue_confidence'].values if 'tissue_confidence' in sdata.columns else None
            fit_scores = res.get('fit_scores')

            ax_ts   = axes[n_ref + 2 * j]
            ax_line = axes[n_ref + 2 * j + 1]
            _draw_tissue_strip(ax_ts, depths, ts, title=name, vmax=1.0)
            _draw_mri_tissue_line(ax_line, depths, ts, mri_norm, fit_scores, session, conf)

        fig.suptitle(f'Predictor comparison — {session}', fontsize=11)
        plt.tight_layout()
        _save_fig(save_dir, f'predictor_comparison_{session}.png')
        plt.show()


def plot_cortex_pc_scatter(
        df: pd.DataFrame,
        pca: PCA,
        pc1_col: str = 'PC1',
        pc2_col: str = 'PC2',
        pc3_col: str = 'PC3',
        pc4_col: str = 'PC4',
        sessions: list = None,
) -> None:
    """Plot PC3 vs PC4 restricted to the brain+cortex quadrant (PC1>0, PC2>0)."""
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


def plot_cortex_pca_diagnostics(
        df_ctx: pd.DataFrame,
        pca_ctx: PCA,
        feature_columns: list,
        n_pcs_act: int,
        tissue_score_min: float,
        tissue_score_max: float,
        save_dir: Optional[str] = None,
) -> None:
    """Loadings + depth profiles + CPC1 vs CPC2 scatter for run_cortex_pca."""
    # ── Loadings ────────────────────────────────────────────────────────────
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
    _save_fig(save_dir, 'cortex_pca_loadings.png')
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
    _save_fig(save_dir, 'cortex_pca_depth_profiles.png')
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
        _save_fig(save_dir, 'cortex_pca_scatter.png')
        plt.show()

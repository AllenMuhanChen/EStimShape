import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from itertools import combinations

from clat.util.connection import Connection  # Adjust import path as needed


def load_and_plot_pca(
        conn: Connection,
        table_name: str = "PenetrationMetrics",
        n_components: int = None,
        plot_components: list = None
):
    """
    Load all data from PenetrationMetrics table, perform PCA, and plot.
    """
    # Load all data
    conn.execute(f"SELECT * FROM {table_name}")
    results = conn.fetch_all()

    # Get column names from cursor description
    conn.execute(f"DESCRIBE {table_name}")
    columns = [row[0] for row in conn.fetch_all()]

    df = pd.DataFrame(results, columns=columns)

    print(f"Loaded {len(df)} rows with columns: {list(df.columns)}")

    # Identify the primary key columns to exclude from PCA
    pk_columns = ['session_id', 'depth_under_chamber_mm']

    # Get all numeric columns except those in primary key
    feature_columns = [
        col for col in df.columns
        if col not in pk_columns
           and pd.api.types.is_numeric_dtype(df[col])
    ]

    print(f"Feature columns for PCA: {feature_columns}")

    if len(feature_columns) < 2:
        raise ValueError("Need at least 2 feature columns for PCA")

    # Extract features and handle missing values
    X = df[feature_columns].copy()
    X = X.fillna(X.mean())

    valid_mask = ~X.isna().any(axis=1)
    X = X[valid_mask]
    df_valid = df[valid_mask].copy()

    print(f"Using {len(X)} rows after handling missing values")

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Perform PCA
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_scaled)

    # Add PC values to dataframe
    for i in range(X_pca.shape[1]):
        df_valid[f'PC{i + 1}'] = X_pca[:, i]

    # Print explained variance
    print("\nExplained variance ratio:")
    cumulative = 0
    for i, var in enumerate(pca.explained_variance_ratio_):
        cumulative += var
        print(f"  PC{i + 1}: {var:.3f} ({var * 100:.1f}%) | Cumulative: {cumulative * 100:.1f}%")

    # Print feature loadings
    print("\nFeature loadings:")
    header = f"{'Feature':<25}" + "".join([f"{'PC' + str(i + 1):>10}" for i in range(min(5, len(pca.components_)))])
    print(header)
    print("-" * len(header))
    for j, feat in enumerate(feature_columns):
        row = f"{feat:<25}"
        for i in range(min(5, len(pca.components_))):
            row += f"{pca.components_[i][j]:>10.3f}"
        print(row)

    if plot_components is None:
        plot_components = [0, 1]

    sessions = df_valid['session_id'].unique()
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
            mask = df_valid['session_id'] == session
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

    return df_valid, pca, X_pca, feature_columns


def plot_depth_profiles_by_session(
        df: pd.DataFrame,
        pca: PCA,
        n_pcs: int = None,
        sessions: list = None,
        figsize_per_session: tuple = (12, 6)
):
    """
    Plot depth profiles for each session showing PC values vs depth.
    Deeper values (higher numbers) appear lower on the plot.
    """
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

            # Set y-axis so larger depths are at bottom
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
    """
    Plot depth profiles for all sessions on a single figure, one row per session.
    Deeper values (higher numbers) appear lower on the plot.
    """
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

            # Set y-axis so larger depths are at bottom
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
    """
    Plot depth profiles with all sessions overlaid on the same axes.
    Deeper values (higher numbers) appear lower on the plot.
    """
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

    # Get global depth range for consistent y-axis
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

        # Set y-axis so larger depths are at bottom
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


if __name__ == "__main__":
    conn = Connection(
        database="allen_data_repository",  # Update this
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61"
    )

    df, pca, X_pca, features = load_and_plot_pca(conn, plot_components=[0, 1, 2])

    plot_scree(pca)

    plot_depth_profiles_by_session(df, pca, n_pcs=4)

    plot_depth_profiles_all_sessions(df, pca, n_pcs=4)

    # plot_depth_profiles_overlaid(df, pca, n_pcs=4)
    #
    # plot_depth_profiles_overlaid(df, pca, n_pcs=4, align_depths=True)
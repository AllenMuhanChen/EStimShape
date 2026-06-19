"""
Multivariate analysis of EStim degradation: of all the condition dimensions
(estim parameters, derived hyperparameters, behavioral conditions), which best
explain

  - WHETHER a condition degraded            (binary: degraded vs robust)
  - HOW STRONGLY it degraded                 (degradation_strength, continuous)
  - HOW LONG it lasted before degrading      (degradation_onset, continuous)

It builds on analyze_estim_degradation's per-condition tables and applies three
complementary views:

  1) PCA over the standardized numeric dimensions — exposes structure and
     collinearity (the current hyperparameters are products of the base params,
     so they are collinear by construction) and visualizes how the degraded /
     robust groups separate in the dominant directions of variation.

  2) Regularized joint models (RidgeCV for the continuous metrics, L2 logistic
     for degraded-vs-robust) with a cross-validated score (R^2 / AUC). The CV
     score answers "do these dimensions explain the outcome at all?"; the
     standardized coefficients are reported but are collinearity-sensitive and
     should be read as suggestive only.

  3) A per-parameter importance ranking that IS robust to the collinearity:
     - univariate cross-validated score (fit each parameter alone), and
     - random-forest permutation importance (nonlinear, joint).

Because the dataset is per-condition (tens to a few hundred rows) and several
dimensions are collinear, lean on the cross-validated scores and the importance
rankings for conclusions rather than the raw joint coefficients.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV, LogisticRegression
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score

from src.analysis.nafc.estim_hyperparameters import HYPERPARAMETER_NAMES
from src.analysis.nafc.group_analysis.analyze_estim_degradation import (
    DEFAULT_ALGORITHM_LABEL, DEFAULT_EFFECT_THRESHOLD, DEFAULT_MIN_N,
    build_degradation_table, build_condition_classification_table,
    _parameter_columns, _is_numeric_param,
)

# Base estim parameters (everything that is NOT a derived hyperparameter or a
# behavioral condition). Used to split feature sets.
_BASE_ESTIM_PARAMS = {
    'a1', 'num_channels', 'pulse_rate_hz', 'post_trigger_delay',
    'enable_charge_recovery', 'polarity', 'shape',
}

_CONTINUOUS_TARGETS = {
    'degradation_strength': 'Degradation strength (effect after / before)',
    'degradation_onset': 'Degradation onset (# estim-on before cutoff)',
}


def _to_float(x):
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Feature preparation
# ---------------------------------------------------------------------------

def _select_features(df, feature_set='all'):
    """Split the table's parameter columns into (numeric, categorical) names.

    feature_set selects which dimensions to include:
      'all'   - base estim params + derived hyperparameters + behavioral
      'base'  - drop the derived hyperparameters (avoid their collinearity)
      'hyper' - drop the base estim params, keep hyperparameters + behavioral
    """
    params = _parameter_columns(df)
    hyper = set(HYPERPARAMETER_NAMES)
    if feature_set == 'base':
        params = [p for p in params if p not in hyper]
    elif feature_set == 'hyper':
        params = [p for p in params if p not in _BASE_ESTIM_PARAMS]
    elif feature_set != 'all':
        raise ValueError(f"feature_set must be 'all', 'base' or 'hyper', got {feature_set!r}")

    numeric, categorical = [], []
    for p in params:
        vals = df[p].dropna().tolist()
        if not vals:
            continue
        (numeric if _is_numeric_param(vals) else categorical).append(p)
    return numeric, categorical


def prepare_features(df, feature_set='all'):
    """Build a numeric design matrix from the condition table.

    Numeric parameters are mean-imputed and standardized; categorical parameters
    are one-hot encoded (missing becomes its own indicator). Returns (X, col_groups)
    where col_groups maps each original parameter to its design-matrix columns
    (so importance can be aggregated back to the parameter).
    """
    numeric_cols, categorical_cols = _select_features(df, feature_set)
    blocks, col_groups = [], {}

    if numeric_cols:
        num = df[numeric_cols].apply(lambda c: c.map(_to_float)).astype(float)
        num = num.fillna(num.mean()).fillna(0.0)  # second fillna guards all-NaN cols
        scaled = StandardScaler().fit_transform(num.values)
        num_df = pd.DataFrame(scaled, columns=numeric_cols, index=df.index)
        blocks.append(num_df)
        for c in numeric_cols:
            col_groups[c] = [c]

    for c in categorical_cols:
        dummies = pd.get_dummies(df[c].astype('object'), prefix=c, dummy_na=True).astype(float)
        blocks.append(dummies)
        col_groups[c] = list(dummies.columns)

    if not blocks:
        return pd.DataFrame(index=df.index), {}
    return pd.concat(blocks, axis=1), col_groups


def _target_vector(df, target, kind):
    """Outcome vector: 0/1 degraded for binary, numeric (NaN where undefined) else."""
    if kind == 'binary':
        return (df['group'] == 'degraded').astype(int)
    return pd.to_numeric(df[target], errors='coerce')


# ---------------------------------------------------------------------------
# Models and cross-validated scores
# ---------------------------------------------------------------------------

def _make_model(kind):
    if kind == 'binary':
        return LogisticRegression(penalty='l2', C=1.0, max_iter=2000, solver='liblinear')
    return RidgeCV(alphas=np.logspace(-2, 3, 20))


def _cv_score(kind, X, y):
    """Cross-validated AUC (binary) or R^2 (continuous); None if too few samples."""
    n = len(y)
    try:
        if kind == 'binary':
            counts = np.bincount(np.asarray(y, dtype=int))
            min_class = counts.min() if counts.size else 0
            k = int(min(5, min_class))
            if k < 2:
                return None
            cv = StratifiedKFold(n_splits=k, shuffle=True, random_state=0)
            scores = cross_val_score(_make_model(kind), X.values, y.values, cv=cv, scoring='roc_auc')
        else:
            k = int(min(5, n))
            if k < 3:
                return None
            cv = KFold(n_splits=k, shuffle=True, random_state=0)
            scores = cross_val_score(_make_model(kind), X.values, y.values, cv=cv, scoring='r2')
        return float(np.mean(scores))
    except Exception as e:
        print(f"   (CV failed: {e})")
        return None


def joint_model(df, target, kind, feature_set='all'):
    """Fit one regularized model on all features; return coefficients + CV score."""
    X, _ = prepare_features(df, feature_set)
    y = _target_vector(df, target, kind)
    mask = y.notna()
    X, y = X.loc[mask], y.loc[mask]
    if X.shape[0] < 5 or X.shape[1] == 0:
        return None
    model = _make_model(kind)
    model.fit(X.values, y.values)
    coef = model.coef_.ravel()
    return {
        'coefs': dict(zip(X.columns, coef)),
        'cv_score': _cv_score(kind, X, y),
        'n': int(X.shape[0]), 'n_features': int(X.shape[1]),
    }


def univariate_importance(df, target, kind, feature_set='all'):
    """Per-parameter cross-validated score, fitting each parameter on its own.

    Robust to collinearity (each parameter judged alone). Returns a list of
    (parameter, score-or-None) sorted best first.
    """
    X, col_groups = prepare_features(df, feature_set)
    y = _target_vector(df, target, kind)
    mask = y.notna()
    X, y = X.loc[mask], y.loc[mask]

    rows = []
    for feat, cols in col_groups.items():
        cols = [c for c in cols if c in X.columns]
        if not cols:
            continue
        rows.append((feat, _cv_score(kind, X[cols], y)))
    rows.sort(key=lambda r: (r[1] is None, -(r[1] if r[1] is not None else 0.0)))
    return rows


def random_forest_importance(df, target, kind, feature_set='all', n_repeats=20):
    """Random-forest permutation importance, aggregated back to each parameter.

    Returns list of (parameter, importance) sorted high first, or None if there
    are too few rows. Importance is measured on the training data (optimistic but
    fine for ranking)."""
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.inspection import permutation_importance

    X, col_groups = prepare_features(df, feature_set)
    y = _target_vector(df, target, kind)
    mask = y.notna()
    X, y = X.loc[mask], y.loc[mask]
    if X.shape[0] < 8 or X.shape[1] == 0:
        return None

    if kind == 'binary':
        rf = RandomForestClassifier(n_estimators=300, random_state=0)
        scoring = 'roc_auc'
    else:
        rf = RandomForestRegressor(n_estimators=300, random_state=0)
        scoring = 'r2'
    try:
        rf.fit(X.values, y.values)
        pi = permutation_importance(rf, X.values, y.values, n_repeats=n_repeats,
                                    random_state=0, scoring=scoring)
    except Exception as e:
        print(f"   (random forest failed: {e})")
        return None
    per_col = dict(zip(X.columns, pi.importances_mean))
    agg = {feat: float(sum(per_col.get(c, 0.0) for c in cols))
           for feat, cols in col_groups.items()}
    return sorted(agg.items(), key=lambda kv: -kv[1])


# ---------------------------------------------------------------------------
# PCA
# ---------------------------------------------------------------------------

def run_pca(df, feature_set='all', color_by=None, title='', save_path=None,
            n_top_loadings=8):
    """PCA over the standardized design matrix: scree + PC1/PC2 scatter, and print
    the top loadings of the first two components. color_by is a df column used to
    colour the scatter ('group' for degraded/robust, or a continuous metric)."""
    X, _ = prepare_features(df, feature_set)
    if X.shape[0] < 3 or X.shape[1] < 2:
        print("Not enough data/features for PCA.")
        return None

    pca = PCA()
    scores = pca.fit_transform(X.values)
    evr = pca.explained_variance_ratio_
    pc1, pc2 = scores[:, 0], scores[:, 1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    ax1.bar(range(1, len(evr) + 1), evr * 100, color='steelblue', edgecolor='black')
    ax1.set_xlabel('Principal component')
    ax1.set_ylabel('% variance explained')
    ax1.set_title('Scree')
    ax1.grid(True, axis='y', alpha=0.3)

    if color_by is not None and color_by in df.columns and color_by == 'group':
        for grp, color in (('degraded', 'firebrick'), ('robust', 'seagreen')):
            m = (df['group'] == grp).values
            ax2.scatter(pc1[m], pc2[m], label=grp, alpha=0.75, color=color, edgecolor='none')
        ax2.legend(fontsize=8)
    elif color_by is not None and color_by in df.columns:
        cvals = pd.to_numeric(df[color_by], errors='coerce').values
        finite = np.isfinite(cvals)
        ax2.scatter(pc1[~finite], pc2[~finite], color='lightgray', alpha=0.5,
                    edgecolor='none', label='n/a')
        sc = ax2.scatter(pc1[finite], pc2[finite], c=cvals[finite], cmap='viridis',
                         alpha=0.85, edgecolor='none')
        fig.colorbar(sc, ax=ax2, label=color_by)
        if (~finite).any():
            ax2.legend(fontsize=8)
    else:
        ax2.scatter(pc1, pc2, alpha=0.75, color='steelblue', edgecolor='none')

    ax2.set_xlabel(f'PC1 ({evr[0] * 100:.0f}%)')
    ax2.set_ylabel(f'PC2 ({evr[1] * 100:.0f}%)')
    ax2.set_title('Conditions in PC space')
    ax2.grid(True, alpha=0.3)

    fig.suptitle(title or f'PCA of condition dimensions ({X.shape[1]} features)',
                 fontsize=13, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    loadings = pd.DataFrame(pca.components_.T, index=X.columns)
    for pc in range(min(2, loadings.shape[1])):
        top = loadings[pc].abs().sort_values(ascending=False).head(n_top_loadings)
        print(f"  PC{pc + 1} ({evr[pc] * 100:.0f}% var) top loadings:")
        for feat in top.index:
            print(f"     {feat:32s} {loadings.loc[feat, pc]:+.2f}")

    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved to {save_path}")
    plt.show()
    return pca


# ---------------------------------------------------------------------------
# Per-target driver + importance plot
# ---------------------------------------------------------------------------

def _plot_importance(label, score_name, univ, rf, joint_cv, save_path=None):
    panels = 1 + (1 if rf else 0)
    height = 0.42 * max(len(univ), 6) + 1.6
    fig, axes = plt.subplots(1, panels, figsize=(7 * panels, height), squeeze=False)

    ax = axes[0][0]
    feats = [f for f, _ in univ][::-1]
    scores = [(0.0 if s is None else s) for _, s in univ][::-1]
    ax.barh(range(len(feats)), scores, color='steelblue', edgecolor='black')
    ax.set_yticks(range(len(feats)))
    ax.set_yticklabels(feats, fontsize=8)
    baseline = 0.5 if score_name == 'CV AUC' else 0.0
    ax.axvline(baseline, color='gray', linestyle=':', linewidth=1)
    ax.set_xlabel(f'Univariate {score_name}')
    cv_str = 'n/a' if joint_cv is None else f'{joint_cv:.3f}'
    ax.set_title(f'Univariate importance (joint {score_name}={cv_str})', fontsize=10)
    ax.grid(True, axis='x', alpha=0.3)

    if rf:
        ax2 = axes[0][1]
        rfeats = [f for f, _ in rf][::-1]
        rimp = [v for _, v in rf][::-1]
        ax2.barh(range(len(rfeats)), rimp, color='mediumpurple', edgecolor='black')
        ax2.set_yticks(range(len(rfeats)))
        ax2.set_yticklabels(rfeats, fontsize=8)
        ax2.axvline(0.0, color='gray', linestyle=':', linewidth=1)
        ax2.set_xlabel('Permutation importance (drop in score)')
        ax2.set_title('Nonlinear importance (random forest)', fontsize=10)
        ax2.grid(True, axis='x', alpha=0.3)

    fig.suptitle(f'What explains: {label}', fontsize=13, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved to {save_path}")
    plt.show()
    return fig


def analyze_target(df, target, kind, feature_set='all', include_rf=True, save_path=None):
    """Joint model + univariate importance + RF importance for one outcome."""
    label = 'Whether a condition degraded' if kind == 'binary' else _CONTINUOUS_TARGETS[target]
    score_name = 'CV AUC' if kind == 'binary' else 'CV R^2'
    print(f"\n===== {label}  ({kind}) =====")

    jm = joint_model(df, target, kind, feature_set)
    if jm is None:
        print("  Not enough data to model this target.")
        return None
    cv_str = 'n/a' if jm['cv_score'] is None else f"{jm['cv_score']:.3f}"
    print(f"  Joint model: n={jm['n']}, {jm['n_features']} design features, {score_name}={cv_str}")
    print("  Top standardized joint coefficients (regularized; collinearity-sensitive):")
    for feat, c in sorted(jm['coefs'].items(), key=lambda kv: -abs(kv[1]))[:10]:
        print(f"     {feat:32s} {c:+.3f}")

    univ = univariate_importance(df, target, kind, feature_set)
    print(f"  Univariate {score_name} per parameter (collinearity-robust):")
    for feat, s in univ:
        print(f"     {feat:24s} {'n/a' if s is None else f'{s:.3f}'}")

    rf = random_forest_importance(df, target, kind, feature_set) if include_rf else None
    if rf:
        print("  Random-forest permutation importance:")
        for feat, imp in rf:
            print(f"     {feat:24s} {imp:+.4f}")

    _plot_importance(label, score_name, univ, rf, jm['cv_score'], save_path)
    return {'joint': jm, 'univariate': univ, 'rf': rf}


def run(algorithm_label=DEFAULT_ALGORITHM_LABEL, session_id=None, feature_set='all',
        effect_threshold=DEFAULT_EFFECT_THRESHOLD, min_n=DEFAULT_MIN_N,
        include_rf=True, save_dir=None):
    """
    Full multivariate analysis. PCA on the parameter space (coloured by group and by
    degradation strength) plus, for each outcome (degraded-vs-robust, degradation
    strength, degradation onset), a joint regularized model with CV score and a
    collinearity-robust per-parameter importance ranking.
    """
    deg_df = build_degradation_table(algorithm_label, session_id)
    class_df = build_condition_classification_table(
        algorithm_label, effect_threshold=effect_threshold, min_n=min_n,
        session_id=session_id)

    def _path(name):
        return f"{save_dir}/estim_degradation_mv_{name}_{algorithm_label}.png" if save_dir else None

    if not class_df.empty:
        print("\n##### PCA — conditions coloured by degraded vs robust #####")
        run_pca(class_df, feature_set, color_by='group',
                title='PCA of condition dimensions — degraded vs robust',
                save_path=_path('pca_group'))
    if not deg_df.empty:
        print("\n##### PCA — degraded conditions coloured by degradation strength #####")
        run_pca(deg_df, feature_set, color_by='degradation_strength',
                title='PCA of condition dimensions — degradation strength',
                save_path=_path('pca_strength'))

    results = {}
    if not class_df.empty:
        results['degraded'] = analyze_target(
            class_df, 'degraded', 'binary', feature_set, include_rf, _path('degraded'))
    if not deg_df.empty:
        for target in _CONTINUOUS_TARGETS:
            results[target] = analyze_target(
                deg_df, target, 'continuous', feature_set, include_rf, _path(target))
    return results


def main():
    run(
        algorithm_label=DEFAULT_ALGORITHM_LABEL,
        session_id=None,
        feature_set='all',   # 'base' drops the (collinear) hyperparameters; 'hyper' keeps only them
        include_rf=True,
        save_dir="/home/connorlab/Documents/plots/group_analysis/estimshape",
    )


if __name__ == '__main__':
    main()

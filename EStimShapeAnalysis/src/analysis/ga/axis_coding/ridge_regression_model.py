from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.model_selection import ShuffleSplit
from sklearn.metrics import r2_score


class RidgeRegressionAxisModel:
    """
    Ridge regression with cross-validated alpha selection and a separate
    repeated-split CV-R2 estimate. Independent of any selector -- accepts any
    (X, r) pair, so it can also be reused for sum-pool / mean-pool baselines.
    """

    def __init__(
        self,
        alphas: Optional[np.ndarray] = None,
        cv: int = 5,
        n_splits_cv_r2: int = 20,
        test_size: float = 0.2,
        random_state: int = 0,
    ):
        self.alphas = (
            alphas if alphas is not None
            else np.logspace(-3, 4, 20)
        )
        self.cv = cv
        self.n_splits_cv_r2 = n_splits_cv_r2
        self.test_size = test_size
        self.random_state = random_state

        self.alpha_: Optional[float] = None
        self.w_: Optional[np.ndarray] = None
        self.intercept_: Optional[float] = None
        self.train_r2_: Optional[float] = None
        self.cv_r2_mean_: Optional[float] = None
        self.cv_r2_std_: Optional[float] = None
        self.cv_r2_values_: Optional[np.ndarray] = None
        self.feature_names_: Optional[list[str]] = None
        self.n_samples_: int = 0
        self.n_features_: int = 0

    def fit(
        self,
        X: np.ndarray,
        r: np.ndarray,
        feature_names: Optional[list[str]] = None,
    ) -> "RidgeRegressionAxisModel":
        X = np.asarray(X, dtype=np.float64)
        r = np.asarray(r, dtype=np.float64).ravel()
        if X.shape[0] != r.shape[0]:
            raise ValueError(
                f"X has {X.shape[0]} rows but r has {r.shape[0]}"
            )
        self.n_samples_, self.n_features_ = X.shape
        self.feature_names_ = (
            list(feature_names)
            if feature_names is not None
            else [f"f{i}" for i in range(self.n_features_)]
        )

        # 1) Pick alpha by CV on the full dataset.
        cv_for_alpha = min(self.cv, max(self.n_samples_, 2))
        ridge_cv = RidgeCV(alphas=self.alphas, cv=cv_for_alpha)
        ridge_cv.fit(X, r)
        self.alpha_ = float(ridge_cv.alpha_)

        # 2) Refit on all data with that alpha for the saved coefficients.
        final = Ridge(alpha=self.alpha_)
        final.fit(X, r)
        self.w_ = final.coef_.copy()
        self.intercept_ = float(final.intercept_)
        self.train_r2_ = float(final.score(X, r))

        # 3) Repeated random 80/20 splits for held-out R2.
        if self.n_samples_ >= 5:
            splitter = ShuffleSplit(
                n_splits=self.n_splits_cv_r2,
                test_size=self.test_size,
                random_state=self.random_state,
            )
            r2s = []
            for train_idx, test_idx in splitter.split(X):
                model = Ridge(alpha=self.alpha_)
                model.fit(X[train_idx], r[train_idx])
                pred = model.predict(X[test_idx])
                r2s.append(r2_score(r[test_idx], pred))
            self.cv_r2_values_ = np.asarray(r2s, dtype=np.float64)
            self.cv_r2_mean_ = float(self.cv_r2_values_.mean())
            self.cv_r2_std_ = float(self.cv_r2_values_.std(ddof=1))
        else:
            self.cv_r2_values_ = np.array([])
            self.cv_r2_mean_ = float("nan")
            self.cv_r2_std_ = float("nan")

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.w_ is None:
            raise RuntimeError("Model not fit.")
        return X @ self.w_ + self.intercept_

    def top_features(self, k: int = 10) -> list[tuple[str, float]]:
        if self.w_ is None or self.feature_names_ is None:
            return []
        order = np.argsort(-np.abs(self.w_))[:k]
        return [(self.feature_names_[i], float(self.w_[i])) for i in order]

    def summary(self) -> dict:
        return {
            "alpha": self.alpha_,
            "train_r2": self.train_r2_,
            "cv_r2_mean": self.cv_r2_mean_,
            "cv_r2_std": self.cv_r2_std_,
            "cv_r2_values": (
                self.cv_r2_values_.tolist()
                if self.cv_r2_values_ is not None
                else None
            ),
            "n_samples": self.n_samples_,
            "n_features": self.n_features_,
            "top_features": self.top_features(10),
            "feature_names": self.feature_names_,
            "weights": None if self.w_ is None else self.w_.tolist(),
            "intercept": self.intercept_,
        }

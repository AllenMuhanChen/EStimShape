from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class ComponentSelector(ABC):
    """
    Strategy interface for picking ONE component per stimulus given a list of
    encoded component matrices (one (m_i, d) array per stimulus) and a response
    vector. Concrete subclasses define how the selection is learned.
    """

    @abstractmethod
    def fit(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> "ComponentSelector":
        ...

    @abstractmethod
    def select_indices(self, components_per_stim: list[np.ndarray]) -> np.ndarray:
        ...

    def selected_vectors(
        self, components_per_stim: list[np.ndarray]
    ) -> np.ndarray:
        idx = self.select_indices(components_per_stim)
        rows = [components_per_stim[i][idx[i]] for i in range(len(components_per_stim))]
        return np.asarray(rows, dtype=np.float64)

    @abstractmethod
    def summary(self) -> dict:
        ...


class FixedCovarianceSelector(ComponentSelector):
    """
    Pick the component closest to a learned center mu, using a fixed (not learned)
    distance metric. EM-style fit:

        E-step: for each stimulus i, z_i = argmin_j (x_{i,j} - mu)^T M (x_{i,j} - mu)
        M-step: mu <- response-weighted mean of selected components

    With ``metric=None`` (default) the metric is the identity, so distances are
    Euclidean in whatever space the encoder produced (typically z-scored).
    """

    def __init__(
        self,
        metric: Optional[np.ndarray] = None,
        max_iter: int = 50,
        tol: float = 0.01,
        init: str = "response_weighted_mean",
        response_weight_floor: float = 0.0,
    ):
        self.metric = metric
        self.max_iter = max_iter
        self.tol = tol
        self.init = init
        self.response_weight_floor = response_weight_floor

        self.mu_: Optional[np.ndarray] = None
        self.selected_indices_: Optional[np.ndarray] = None
        self.n_iter_: int = 0
        self.converged_: bool = False
        self.history_: list[dict] = []

    # ------------------------------------------------------------------
    # ComponentSelector API
    # ------------------------------------------------------------------

    def fit(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> "FixedCovarianceSelector":
        if len(components_per_stim) == 0:
            raise ValueError("No stimuli passed to FixedCovarianceSelector.fit")

        d = components_per_stim[0].shape[1]
        if self.metric is None:
            metric = np.eye(d)
        else:
            metric = np.asarray(self.metric, dtype=np.float64)
            if metric.shape != (d, d):
                raise ValueError(
                    f"metric shape {metric.shape} does not match feature dim {d}"
                )

        self.mu_ = self._initialize_mu(components_per_stim, responses)
        prev_idx = np.full(len(components_per_stim), -1, dtype=np.int64)

        self.history_.clear()
        self.converged_ = False
        for it in range(self.max_iter):
            idx = self._select_indices(components_per_stim, self.mu_, metric)
            mu_new = self._weighted_mean_of_selected(
                components_per_stim, idx, responses
            )

            n_changed = int(np.sum(idx != prev_idx))
            frac_changed = n_changed / max(len(idx), 1)
            self.history_.append(
                {"iter": it, "n_changed": n_changed, "frac_changed": frac_changed}
            )

            self.mu_ = mu_new
            self.n_iter_ = it + 1
            if it > 0 and frac_changed < self.tol:
                self.converged_ = True
                self.selected_indices_ = idx
                return self
            prev_idx = idx

        # Didn't converge within max_iter; finalize with current mu.
        self.selected_indices_ = self._select_indices(
            components_per_stim, self.mu_, metric
        )
        return self

    def select_indices(self, components_per_stim: list[np.ndarray]) -> np.ndarray:
        if self.mu_ is None:
            raise RuntimeError("Selector not fit. Call fit() first.")
        d = components_per_stim[0].shape[1]
        metric = np.eye(d) if self.metric is None else np.asarray(self.metric)
        return self._select_indices(components_per_stim, self.mu_, metric)

    def summary(self) -> dict:
        return {
            "selector": "FixedCovarianceSelector",
            "metric": "identity" if self.metric is None else "custom",
            "n_iter": self.n_iter_,
            "converged": self.converged_,
            "tol": self.tol,
            "max_iter": self.max_iter,
            "init": self.init,
            "mu": None if self.mu_ is None else self.mu_.tolist(),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _initialize_mu(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> np.ndarray:
        if self.init == "response_weighted_mean":
            # Each component inherits its stimulus's response. mu is the
            # response-weighted mean across all components from all stimuli.
            stacked = []
            weights = []
            for comp_mat, r in zip(components_per_stim, responses):
                if comp_mat.shape[0] == 0:
                    continue
                stacked.append(comp_mat)
                weights.append(np.full(comp_mat.shape[0], r, dtype=np.float64))
            X_all = np.vstack(stacked)
            w_all = np.concatenate(weights)
            return _weighted_mean(X_all, w_all, floor=self.response_weight_floor)

        if self.init == "unweighted_mean":
            stacked = [c for c in components_per_stim if c.shape[0] > 0]
            return np.vstack(stacked).mean(axis=0)

        raise ValueError(f"Unknown init: {self.init}")

    @staticmethod
    def _select_indices(
        components_per_stim: list[np.ndarray],
        mu: np.ndarray,
        metric: np.ndarray,
    ) -> np.ndarray:
        idx = np.empty(len(components_per_stim), dtype=np.int64)
        for i, X in enumerate(components_per_stim):
            if X.shape[0] == 0:
                idx[i] = -1
                continue
            diff = X - mu[None, :]
            # Mahalanobis-like distance under the given metric (precision matrix).
            dists = np.einsum("nd,de,ne->n", diff, metric, diff)
            idx[i] = int(np.argmin(dists))
        return idx

    @staticmethod
    def _weighted_mean_of_selected(
        components_per_stim: list[np.ndarray],
        idx: np.ndarray,
        responses: np.ndarray,
    ) -> np.ndarray:
        rows = []
        weights = []
        for i, j in enumerate(idx):
            if j < 0:
                continue
            rows.append(components_per_stim[i][j])
            weights.append(float(responses[i]))
        X = np.asarray(rows, dtype=np.float64)
        w = np.asarray(weights, dtype=np.float64)
        return _weighted_mean(X, w)


def _weighted_mean(X: np.ndarray, w: np.ndarray, floor: float = 0.0) -> np.ndarray:
    """
    Response-weighted mean. If all weights are non-positive (e.g. the channel
    didn't fire at all), fall back to the unweighted mean so the selector still
    produces a valid mu instead of exploding.
    """
    if X.shape[0] == 0:
        raise ValueError("Cannot compute weighted mean of empty array.")
    w = np.asarray(w, dtype=np.float64)
    if floor > 0:
        w = np.clip(w, floor, None)
    total = w.sum()
    if not np.isfinite(total) or total <= 0:
        return X.mean(axis=0)
    return (w[:, None] * X).sum(axis=0) / total

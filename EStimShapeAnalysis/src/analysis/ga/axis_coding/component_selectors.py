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
        """Return the hard-selected (argmin/argmax) component index per stimulus."""
        ...

    def selected_vectors(
        self, components_per_stim: list[np.ndarray]
    ) -> np.ndarray:
        """
        Return one vector per stimulus for ridge regression.

        With temperature=0 (hard) this is the single nearest component.
        With temperature>0 (soft) this is the softmax-weighted average of all
        components, so the feature vector passed to ridge regression smoothly
        interpolates between components rather than snapping to one.
        """
        idx = self.select_indices(components_per_stim)
        rows = [components_per_stim[i][idx[i]] for i in range(len(components_per_stim))]
        return np.asarray(rows, dtype=np.float64)

    @abstractmethod
    def summary(self) -> dict:
        ...


class FixedCovarianceSelector(ComponentSelector):
    """
    Pick the component closest to a learned center mu, using a fixed (not
    learned) distance metric. EM-style fit:

        E-step : compute assignment weights per component per stimulus
                 (hard argmin when temperature=0, softmax(-dist/τ) when τ>0)
        M-step : mu <- response-weighted mean of soft-selected vectors

    ``temperature=0`` (default) is the hard case — the selected vector is the
    single nearest component.  ``temperature>0`` produces a soft-weighted
    average of all components per stimulus, where the weights decay with
    distance to mu.  Higher temperature → less enforcement of proximity → the
    regression sees something closer to mean-pool.

    With ``metric=None`` (default) the metric is the identity, so distances
    are Euclidean in the z-scored space produced by the encoder.  Pass a (d,d)
    precision matrix to tilt the distance toward certain dimensions.

    Convergence is tracked by the relative change in mu between iterations.
    """

    def __init__(
        self,
        metric: Optional[np.ndarray] = None,
        max_iter: int = 50,
        tol: float = 0.01,
        init: str = "response_weighted_mean",
        response_weight_floor: float = 0.0,
        temperature: float = 0.0,
    ):
        self.metric = metric
        self.max_iter = max_iter
        self.tol = tol
        self.init = init
        self.response_weight_floor = response_weight_floor
        self.temperature = temperature

        self.mu_: Optional[np.ndarray] = None
        self.metric_: Optional[np.ndarray] = None   # active metric (may be learned by subclass)
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
        self.metric_ = np.eye(d) if self.metric is None else np.asarray(self.metric, dtype=np.float64)
        if self.metric_.shape != (d, d):
            raise ValueError(
                f"metric shape {self.metric_.shape} does not match feature dim {d}"
            )

        self.mu_ = self._initialize_mu(components_per_stim, responses)

        self.history_.clear()
        self.converged_ = False

        for it in range(self.max_iter):
            # E-step: soft-weighted vector per stimulus under current (mu, metric)
            soft_selected = self._soft_selected_vectors(
                components_per_stim, self.mu_, self.metric_
            )

            # M-step: update mu (and optionally metric for subclasses)
            mu_new, metric_new = self._m_step(
                soft_selected, responses, self.mu_, self.metric_
            )

            dmu = float(
                np.linalg.norm(mu_new - self.mu_)
                / (np.linalg.norm(self.mu_) + 1e-12)
            )
            self.history_.append({"iter": it, "dmu": dmu})

            self.mu_ = mu_new
            self.metric_ = metric_new
            self.n_iter_ = it + 1

            if it > 0 and dmu < self.tol:
                self.converged_ = True
                break

        self.selected_indices_ = self._hard_indices(
            components_per_stim, self.mu_, self.metric_
        )
        return self

    def select_indices(self, components_per_stim: list[np.ndarray]) -> np.ndarray:
        if self.mu_ is None:
            raise RuntimeError("Selector not fit. Call fit() first.")
        return self._hard_indices(components_per_stim, self.mu_, self.metric_)

    def selected_vectors(self, components_per_stim: list[np.ndarray]) -> np.ndarray:
        if self.mu_ is None:
            raise RuntimeError("Selector not fit. Call fit() first.")
        return self._soft_selected_vectors(components_per_stim, self.mu_, self.metric_)

    def summary(self) -> dict:
        return {
            "selector": "FixedCovarianceSelector",
            "metric": "identity" if self.metric is None else "custom",
            "temperature": self.temperature,
            "n_iter": self.n_iter_,
            "converged": self.converged_,
            "tol": self.tol,
            "max_iter": self.max_iter,
            "init": self.init,
            "mu": None if self.mu_ is None else self.mu_.tolist(),
        }

    # ------------------------------------------------------------------
    # Overridable M-step
    # ------------------------------------------------------------------

    def _m_step(
        self,
        soft_selected: np.ndarray,
        responses: np.ndarray,
        mu: np.ndarray,
        metric: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Update mu from the soft-selected vectors.  Returns (mu_new, metric_new).
        Subclasses override to also update the metric.
        ``soft_selected`` is (n_stim, d) — already the weighted-average component
        per stimulus, so the same weighted-mean formula works for both hard and
        soft temperature modes.
        """
        mu_new = _weighted_mean(soft_selected, responses, floor=self.response_weight_floor)
        return mu_new, metric

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _initialize_mu(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> np.ndarray:
        if self.init == "response_weighted_mean":
            stacked, weights = [], []
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

        raise ValueError(f"Unknown init: {self.init!r}")

    def _mahalanobis_dists(
        self, X: np.ndarray, mu: np.ndarray, metric: np.ndarray
    ) -> np.ndarray:
        diff = X - mu[None, :]
        return np.einsum("nd,de,ne->n", diff, metric, diff)

    def _assignment_weights(self, dists: np.ndarray) -> np.ndarray:
        """
        Convert distances to assignment weights.
        temperature=0 → one-hot at argmin (hard).
        temperature>0 → softmax(-dists / temperature) (soft).
        """
        if self.temperature <= 0:
            w = np.zeros(len(dists))
            w[int(np.argmin(dists))] = 1.0
            return w
        log_w = -dists / self.temperature
        log_w -= log_w.max()        # numerical stability
        w = np.exp(log_w)
        return w / w.sum()

    def _soft_selected_vectors(
        self,
        components_per_stim: list[np.ndarray],
        mu: np.ndarray,
        metric: np.ndarray,
    ) -> np.ndarray:
        """Return (n_stim, d) — soft-weighted average component per stimulus."""
        out = np.empty((len(components_per_stim), mu.shape[0]), dtype=np.float64)
        for i, X in enumerate(components_per_stim):
            dists = self._mahalanobis_dists(X, mu, metric)
            w = self._assignment_weights(dists)
            out[i] = w @ X
        return out

    def _hard_indices(
        self,
        components_per_stim: list[np.ndarray],
        mu: np.ndarray,
        metric: np.ndarray,
    ) -> np.ndarray:
        idx = np.empty(len(components_per_stim), dtype=np.int64)
        for i, X in enumerate(components_per_stim):
            dists = self._mahalanobis_dists(X, mu, metric)
            idx[i] = int(np.argmin(dists))
        return idx


class LearnedDiagonalCovarianceSelector(FixedCovarianceSelector):
    """
    Extends FixedCovarianceSelector by also learning a per-feature diagonal
    covariance in the M-step.  The precision matrix becomes diag(1/σ²_k), so
    features where selected components are tightly clustered around mu get
    higher weight in the distance metric — effectively the selector learns
    *which dimensions matter* for identifying the preferred component.

    ``variance_floor`` prevents any dimension from collapsing to zero variance
    (and therefore infinite precision), which would make the distance
    degenerate.  Set it relative to the z-scored scale (default 1e-3 means a
    floor of ~3% of a unit-variance dimension).
    """

    def __init__(
        self,
        max_iter: int = 50,
        tol: float = 0.01,
        init: str = "response_weighted_mean",
        response_weight_floor: float = 0.0,
        temperature: float = 0.0,
        variance_floor: float = 1e-3,
    ):
        # metric is always learned here; don't expose it as a constructor arg
        super().__init__(
            metric=None,
            max_iter=max_iter,
            tol=tol,
            init=init,
            response_weight_floor=response_weight_floor,
            temperature=temperature,
        )
        self.variance_floor = variance_floor
        self.sigma2_: Optional[np.ndarray] = None   # learned per-feature variance

    def _m_step(
        self,
        soft_selected: np.ndarray,
        responses: np.ndarray,
        mu: np.ndarray,
        metric: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        mu_new = _weighted_mean(soft_selected, responses, floor=self.response_weight_floor)

        # Response-weighted variance of soft-selected vectors around the new mu.
        diff = soft_selected - mu_new[None, :]
        w = np.asarray(responses, dtype=np.float64)
        if self.response_weight_floor > 0:
            w = np.clip(w, self.response_weight_floor, None)
        w = np.maximum(w, 0.0)
        total = w.sum()
        if total > 0:
            sigma2 = (w[:, None] * diff ** 2).sum(axis=0) / total
        else:
            sigma2 = np.ones(mu_new.shape[0])

        sigma2 = np.maximum(sigma2, self.variance_floor)
        self.sigma2_ = sigma2
        new_metric = np.diag(1.0 / sigma2)
        return mu_new, new_metric

    def summary(self) -> dict:
        d = super().summary()
        d["selector"] = "LearnedDiagonalCovarianceSelector"
        d["variance_floor"] = self.variance_floor
        d["learned_sigma2"] = None if self.sigma2_ is None else self.sigma2_.tolist()
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _weighted_mean(X: np.ndarray, w: np.ndarray, floor: float = 0.0) -> np.ndarray:
    """
    Response-weighted mean. Falls back to unweighted mean when all weights
    are non-positive (e.g. a channel that never fired) so mu stays valid.
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

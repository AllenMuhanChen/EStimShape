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


def _quick_r2(X: np.ndarray, y: np.ndarray) -> float:
    """Training R² with a fixed-alpha Ridge. Used only for restart comparison."""
    from sklearn.linear_model import Ridge
    from sklearn.metrics import r2_score
    try:
        m = Ridge(alpha=1.0).fit(X, y)
        return float(r2_score(y, m.predict(X)))
    except Exception:
        return float("-inf")


class ClusterModeSelector(FixedCovarianceSelector):
    """
    Avoids the mean-initialization bias of FixedCovarianceSelector by finding
    the dominant density *mode* of the response-weighted component distribution
    rather than its centroid.

    Motivation: a high-response stimulus has M components, only one of which
    actually drives the neuron.  All M share the same response weight, so a
    response-weighted mean of all components is pulled toward the centroid of
    drivers + hitchhikers.  The *mode* (densest cluster) naturally separates
    the tight cluster of true drivers from the diffuse cloud of hitchhikers.

    Two changes from FixedCovarianceSelector:

    1. **Multi-restart mean-shift initialization.**  ``n_random_inits`` starting
       points are drawn from the response-weighted component distribution.  Each
       is run to its local density mode via mean-shift (response-weighted Gaussian
       kernel).  This seed is then handed to the EM loop.  Best restart is kept
       by training R².

    2. **Kernel-weighted M-step.**  Instead of the plain response-weighted mean,
       μ is updated as a Gaussian-kernel-weighted mean of the selected components:
       ``μ ← Σᵢ K(xᵢ, μ, h)·rᵢ·xᵢ / Σᵢ K(xᵢ, μ, h)·rᵢ``
       where ``K(x, μ, h) = exp(-‖x−μ‖²/(2h²))``.  Components far from the
       current μ are down-weighted, so μ converges to the local density peak
       rather than the centroid.

    ``bandwidth=None`` computes h as the median pairwise Euclidean distance
    among all components in the (z-scored) dataset — a data-driven scale that
    adapts to the spread of the component distribution.
    """

    def __init__(
        self,
        bandwidth: Optional[float] = None,
        n_random_inits: int = 10,
        max_iter: int = 50,
        tol: float = 0.01,
        response_weight_floor: float = 0.0,
        temperature: float = 0.0,
    ):
        super().__init__(
            metric=None,
            max_iter=max_iter,
            tol=tol,
            init="response_weighted_mean",  # unused; fit() is fully overridden
            response_weight_floor=response_weight_floor,
            temperature=temperature,
        )
        self.bandwidth = bandwidth
        self.n_random_inits = n_random_inits
        self.bandwidth_: Optional[float] = None
        self.best_train_r2_: Optional[float] = None

    # ------------------------------------------------------------------
    # Override fit() to run multiple restarts
    # ------------------------------------------------------------------

    def fit(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> "ClusterModeSelector":
        if len(components_per_stim) == 0:
            raise ValueError("No stimuli passed to ClusterModeSelector.fit")

        d = components_per_stim[0].shape[1]
        metric = np.eye(d, dtype=np.float64)

        self.bandwidth_ = (
            self.bandwidth if self.bandwidth is not None
            else _median_pairwise_bandwidth(components_per_stim)
        )

        # Stack all components; each inherits its stimulus's response as weight.
        all_comps, all_weights = [], []
        for comps, r in zip(components_per_stim, responses):
            if comps.shape[0] == 0:
                continue
            w = max(float(r), 0.0)
            if self.response_weight_floor > 0:
                w = max(w, float(self.response_weight_floor))
            for _ in range(comps.shape[0]):
                all_weights.append(w)
            all_comps.append(comps)
        X_all = np.vstack(all_comps)
        w_all = np.asarray(all_weights, dtype=np.float64)

        # Draw starting points proportional to response weight.
        w_norm = w_all / (w_all.sum() + 1e-12)
        rng = np.random.default_rng(0)
        start_idx = rng.choice(len(X_all), size=self.n_random_inits, replace=True, p=w_norm)

        best_r2 = float("-inf")
        best_state: Optional[dict] = None

        for idx in start_idx:
            mu_init = _mean_shift(
                X_all, w_all, X_all[idx].copy(), self.bandwidth_
            )
            state = self._run_em(components_per_stim, responses, mu_init, metric)
            selected = self._soft_selected_vectors(
                components_per_stim, state["mu"], state["metric"]
            )
            r2 = _quick_r2(selected, np.asarray(responses))
            if r2 > best_r2:
                best_r2 = r2
                best_state = state

        self.mu_ = best_state["mu"]
        self.metric_ = best_state["metric"]
        self.n_iter_ = best_state["n_iter"]
        self.converged_ = best_state["converged"]
        self.history_ = best_state["history"]
        self.selected_indices_ = self._hard_indices(
            components_per_stim, self.mu_, self.metric_
        )
        self.best_train_r2_ = float(best_r2)
        return self

    # ------------------------------------------------------------------
    # Override M-step: kernel-weighted mean-shift update
    # ------------------------------------------------------------------

    def _m_step(
        self,
        soft_selected: np.ndarray,
        responses: np.ndarray,
        mu: np.ndarray,
        metric: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        h = self.bandwidth_
        if h is None or h < 1e-12:
            return super()._m_step(soft_selected, responses, mu, metric)

        diff = soft_selected - mu[None, :]
        sq_dists = np.sum(diff ** 2, axis=1)
        kernel_w = np.exp(-0.5 * sq_dists / (h ** 2))

        r = np.asarray(responses, dtype=np.float64)
        if self.response_weight_floor > 0:
            r = np.clip(r, self.response_weight_floor, None)
        combined_w = kernel_w * np.maximum(r, 0.0)
        total = combined_w.sum()

        if total < 1e-12 or not np.isfinite(total):
            return super()._m_step(soft_selected, responses, mu, metric)

        mu_new = (combined_w[:, None] * soft_selected).sum(0) / total
        return mu_new, metric

    # ------------------------------------------------------------------
    # EM runner (called once per restart)
    # ------------------------------------------------------------------

    def _run_em(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
        mu_init: np.ndarray,
        metric_init: np.ndarray,
    ) -> dict:
        mu = mu_init.copy()
        metric = metric_init.copy()
        history: list[dict] = []
        converged = False

        for it in range(self.max_iter):
            soft_selected = self._soft_selected_vectors(components_per_stim, mu, metric)
            mu_new, metric_new = self._m_step(soft_selected, responses, mu, metric)
            dmu = float(
                np.linalg.norm(mu_new - mu) / (np.linalg.norm(mu) + 1e-12)
            )
            history.append({"iter": it, "dmu": dmu})
            mu = mu_new
            metric = metric_new
            if it > 0 and dmu < self.tol:
                converged = True
                break

        return {
            "mu": mu,
            "metric": metric,
            "n_iter": len(history),
            "converged": converged,
            "history": history,
        }

    def summary(self) -> dict:
        d = super().summary()
        d["selector"] = "ClusterModeSelector"
        d["bandwidth"] = self.bandwidth
        d["bandwidth_learned"] = self.bandwidth_
        d["n_random_inits"] = self.n_random_inits
        if self.best_train_r2_ is not None:
            d["best_train_r2"] = self.best_train_r2_
        return d


# ---------------------------------------------------------------------------
# Module-level helpers shared by ClusterModeSelector
# ---------------------------------------------------------------------------

def _mean_shift(
    X: np.ndarray,
    weights: np.ndarray,
    mu_init: np.ndarray,
    h: float,
    max_iter: int = 200,
    tol: float = 1e-6,
) -> np.ndarray:
    """
    Run response-weighted mean-shift from mu_init until convergence.
    Used during initialization to find the local density mode.
    """
    mu = mu_init.copy()
    for _ in range(max_iter):
        diff = X - mu[None, :]
        sq_dists = np.sum(diff ** 2, axis=1)
        kernel_w = np.exp(-0.5 * sq_dists / (h ** 2))
        combined_w = kernel_w * weights
        total = combined_w.sum()
        if total < 1e-12:
            break
        mu_new = (combined_w[:, None] * X).sum(0) / total
        if np.linalg.norm(mu_new - mu) < tol:
            break
        mu = mu_new
    return mu


def _median_pairwise_bandwidth(
    components_per_stim: list[np.ndarray],
    max_points: int = 1000,
    random_state: int = 0,
) -> float:
    """
    Median pairwise Euclidean distance among all components (subsampled to
    max_points for efficiency). Gives a data-driven bandwidth scale.
    """
    from sklearn.metrics.pairwise import euclidean_distances
    all_comps = np.vstack([c for c in components_per_stim if c.shape[0] > 0])
    if len(all_comps) > max_points:
        idx = np.random.default_rng(random_state).choice(
            len(all_comps), max_points, replace=False
        )
        all_comps = all_comps[idx]
    dists = euclidean_distances(all_comps)
    iu = np.triu_indices_from(dists, k=1)
    return float(np.median(dists[iu]))

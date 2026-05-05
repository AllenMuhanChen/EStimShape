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


class SoftAttentionAxisSelector(ComponentSelector):
    """
    Joint (μ, w, b) soft-attention model for axis coding.

    Predicts response as
        r_i = Σ_j π_ij · (w · x_ij)  +  b
        π_ij = softmax_j(-||x_ij - μ||² / (2τ²))

    Why this differs from FixedCovarianceSelector with temperature > 0:
      - FixedCovarianceSelector updates μ as the response-weighted mean of the
        soft-pooled vectors — a heuristic that does NOT minimize prediction
        loss with respect to μ.
      - SoftAttentionAxisSelector jointly optimizes (μ, w, b) to minimize the
        squared prediction error.  Because the same w is applied to *every*
        component (weighted by π), the loss "sees" non-selected components
        too: features that vary among non-selected components without
        correlating with response are pushed to lower weight in w.

    What this fixes: with hard selection, "selector quality" (how close the
    nearest component got to μ) and "shape-at-location" (the within-location
    axis) are confounded — both contribute to the variance in x_sel that ridge
    regresses on, so position features can absorb selector-quality variance.
    Joint soft-attention disentangles them: selector quality lives in π,
    shape-at-location lives in w.

    Algorithm — alternating optimization:
      - W-step: with μ fixed, compute X_eff_i = Σ_j π_ij x_ij and fit ridge on
        (X_eff, r) for w, b.
      - M-step: with w, b fixed, optimize μ via L-BFGS-B on the squared loss
        using the analytical gradient
            ∂r̂_i/∂μ = (1/τ²) [<sx>_π_i - <x>_π_i · <s>_π_i]
        where s_j = w · x_ij, <·>_π_i denotes π_i-weighted average over j.

    Convergence: relative change in μ between iterations < tol.

    selected_vectors() returns the attention-pooled X_eff so the downstream
    RidgeRegressionAxisModel sees a coherent design matrix.  Because the model
    is linear in w given μ, the downstream ridge recovers a near-identical w;
    the existing CV-R² / noise-ceiling / orthogonal-axis pipeline runs
    unchanged on top.
    """

    def __init__(
        self,
        tau: float = 1.0,
        alpha: float = 1.0,
        max_iter: int = 30,
        tol: float = 1e-3,
        init: str = "response_weighted_mean",
        response_weight_floor: float = 0.0,
        mu_optimizer_max_iter: int = 50,
    ):
        self.tau = float(tau)
        self.alpha = float(alpha)
        self.max_iter = int(max_iter)
        self.tol = float(tol)
        self.init = init
        self.response_weight_floor = float(response_weight_floor)
        self.mu_optimizer_max_iter = int(mu_optimizer_max_iter)

        self.mu_: Optional[np.ndarray] = None
        self.w_: Optional[np.ndarray] = None
        self.b_: Optional[float] = None
        self.metric_: Optional[np.ndarray] = None
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
    ) -> "SoftAttentionAxisSelector":
        from sklearn.linear_model import Ridge

        if len(components_per_stim) == 0:
            raise ValueError("No stimuli passed to SoftAttentionAxisSelector.fit")

        responses = np.asarray(responses, dtype=np.float64)
        d = components_per_stim[0].shape[1]
        self.metric_ = np.eye(d, dtype=np.float64)

        mu = self._init_mu(components_per_stim, responses)
        prev_mu = mu.copy()

        self.history_.clear()
        self.converged_ = False

        # Initial w from one W-step so the first M-step has something to optimize.
        X_eff = self._pool_all(components_per_stim, mu)
        ridge = Ridge(alpha=self.alpha).fit(X_eff, responses)
        w = ridge.coef_.copy()
        b = float(ridge.intercept_)

        for it in range(self.max_iter):
            # M-step: update μ given current w, b.
            mu = self._optimize_mu(components_per_stim, responses, mu, w, b)

            # W-step: refit w, b with the new μ.
            X_eff = self._pool_all(components_per_stim, mu)
            ridge = Ridge(alpha=self.alpha).fit(X_eff, responses)
            w = ridge.coef_.copy()
            b = float(ridge.intercept_)

            dmu = float(
                np.linalg.norm(mu - prev_mu)
                / (np.linalg.norm(prev_mu) + 1e-12)
            )
            self.history_.append({"iter": it, "dmu": dmu})
            self.n_iter_ = it + 1

            if it > 0 and dmu < self.tol:
                self.converged_ = True
                break
            prev_mu = mu.copy()

        self.mu_ = mu
        self.w_ = w
        self.b_ = b
        self.selected_indices_ = self._hard_indices(components_per_stim, mu)
        return self

    def select_indices(self, components_per_stim: list[np.ndarray]) -> np.ndarray:
        if self.mu_ is None:
            raise RuntimeError("Selector not fit. Call fit() first.")
        return self._hard_indices(components_per_stim, self.mu_)

    def selected_vectors(
        self, components_per_stim: list[np.ndarray]
    ) -> np.ndarray:
        if self.mu_ is None:
            raise RuntimeError("Selector not fit. Call fit() first.")
        return self._pool_all(components_per_stim, self.mu_)

    def summary(self) -> dict:
        return {
            "selector": "SoftAttentionAxisSelector",
            "tau": self.tau,
            "alpha": self.alpha,
            "n_iter": self.n_iter_,
            "converged": self.converged_,
            "tol": self.tol,
            "max_iter": self.max_iter,
            "init": self.init,
            "mu": None if self.mu_ is None else self.mu_.tolist(),
            "w_internal": None if self.w_ is None else self.w_.tolist(),
            "b_internal": self.b_,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_mu(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> np.ndarray:
        if self.init == "response_weighted_mean":
            stacked, weights = [], []
            for comps, r in zip(components_per_stim, responses):
                if comps.shape[0] == 0:
                    continue
                stacked.append(comps)
                weights.append(np.full(comps.shape[0], r, dtype=np.float64))
            X = np.vstack(stacked)
            w = np.concatenate(weights)
            return _weighted_mean(X, w, floor=self.response_weight_floor)
        if self.init == "unweighted_mean":
            X = np.vstack([c for c in components_per_stim if c.shape[0] > 0])
            return X.mean(axis=0)
        raise ValueError(f"Unknown init: {self.init!r}")

    def _attention(self, components: np.ndarray, mu: np.ndarray) -> np.ndarray:
        d2 = ((components - mu) ** 2).sum(axis=1)
        z = -d2 / (2.0 * self.tau ** 2)
        z = z - z.max()
        e = np.exp(z)
        return e / e.sum()

    def _pool(self, components: np.ndarray, mu: np.ndarray) -> np.ndarray:
        if components.shape[0] == 0:
            return np.zeros(mu.shape[0])
        pi = self._attention(components, mu)
        return pi @ components

    def _pool_all(
        self,
        components_per_stim: list[np.ndarray],
        mu: np.ndarray,
    ) -> np.ndarray:
        d = mu.shape[0]
        out = np.empty((len(components_per_stim), d), dtype=np.float64)
        for i, c in enumerate(components_per_stim):
            out[i] = self._pool(c, mu)
        return out

    def _hard_indices(
        self,
        components_per_stim: list[np.ndarray],
        mu: np.ndarray,
    ) -> np.ndarray:
        idx = np.empty(len(components_per_stim), dtype=np.int64)
        for i, X in enumerate(components_per_stim):
            if X.shape[0] == 0:
                idx[i] = 0
                continue
            d2 = ((X - mu) ** 2).sum(axis=1)
            idx[i] = int(np.argmin(d2))
        return idx

    def _optimize_mu(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
        mu_init: np.ndarray,
        w: np.ndarray,
        b: float,
    ) -> np.ndarray:
        """
        L-BFGS-B on μ with analytical gradient.

        For one stimulus with components x_j (m × d) and π = softmax(-d²_j/(2τ²)):
            s_j     = w · x_j
            r̂      = Σ_j π_j s_j + b
            <x>_π  = Σ_j π_j x_j
            <s>_π  = Σ_j π_j s_j  (= r̂ - b)
            ∂r̂/∂μ = (1/τ²) [Σ_j π_j s_j x_j - <x>_π · <s>_π]
        Loss is squared error; gradient sums over stimuli.
        """
        from scipy.optimize import minimize

        tau2 = self.tau ** 2

        def loss_and_grad(mu):
            total_loss = 0.0
            grad = np.zeros_like(mu)
            for comps, r in zip(components_per_stim, responses):
                if comps.shape[0] == 0:
                    continue
                pi = self._attention(comps, mu)
                s = comps @ w                     # (m,)
                spi = float(pi @ s)               # <s>_π
                rhat = spi + b
                resid = float(r) - rhat
                total_loss += resid * resid

                xpi = pi @ comps                  # <x>_π   (d,)
                weighted = (pi * s)[:, None] * comps   # (m, d)
                drhat_dmu = (weighted.sum(axis=0) - xpi * spi) / tau2
                grad += -2.0 * resid * drhat_dmu
            return total_loss, grad

        result = minimize(
            loss_and_grad,
            mu_init,
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": self.mu_optimizer_max_iter, "gtol": 1e-6},
        )
        return result.x


class MultiPrototypeAttentionSelector(ComponentSelector):
    """
    Multi-prototype soft-attention selector that *can* describe a stimulus with
    K prototypes but collapses to fewer when one is enough.

    For stimulus i with components x_ij (m_i × d):
        π_ij^k    = softmax_j(-||x_ij - μ_k||² / (2τ²))           (per-prototype attention)
        x_eff_i^k = Σ_j π_ij^k · x_ij                              (per-prototype pool)
        d_ik      = min_j ||x_ij - μ_k||²                           (closest-component distance)
        g_ik      = α_k exp(-d_ik / (2τ²))  /  Σ_k' α_k' exp(-d_ik' / (2τ²))
        x_combined_i = Σ_k g_ik · x_eff_i^k                         (gated mixture)
        r̂_i       = w · x_combined_i + b

    Loss = ||r - r̂||² + λ_amp · Σ_k α_k     (sparsity prior on prototype amplitudes)
    Constraint: α_k ≥ 0  (enforced by parameterizing α_k = exp(η_k)).

    Why it can collapse:
      - α_k enters g_ik multiplicatively. When α_k → 0, prototype k contributes
        nothing to g_ik (and therefore to x_combined_i) regardless of μ_k.
      - The L1 prior λ_amp · Σ α_k actively pushes amplitudes toward 0; only
        prototypes that earn squared-error reduction larger than λ_amp keep
        nonzero amplitude.
      - In the K=2 case this means: if a single prototype already explains the
        data, α_2 collapses to ~0 and the model is effectively single-prototype.
        ``n_active_prototypes`` in the summary reports how many α_k survived
        above ``amplitude_floor``.

    Algorithm — alternating optimization, mirroring SoftAttentionAxisSelector:
      W-step: with {μ_k, α_k} fixed, fit ridge on (x_combined, r) → (w, b).
      M-step: with (w, b) fixed, jointly optimize {μ_k, η_k} via L-BFGS-B on
              the regularized loss. Numerical gradient is used; the optimization
              is over K·d + K parameters which is small in practice.

    selected_vectors() returns x_combined so the downstream RidgeRegressionAxisModel
    sees a coherent design matrix (same pattern as SoftAttentionAxisSelector).
    ``mu_`` exposes the prototype with the largest amplitude so existing
    visualizers (which expect a single μ) continue to work.
    """

    def __init__(
        self,
        n_prototypes: int = 2,
        tau: float = 1.0,
        alpha: float = 1.0,
        lambda_amp: float = 0.1,
        max_iter: int = 30,
        tol: float = 1e-3,
        init_jitter: float = 0.5,
        amplitude_floor: float = 1e-3,
        mu_optimizer_max_iter: int = 100,
        random_state: int = 0,
    ):
        self.n_prototypes = int(n_prototypes)
        self.tau = float(tau)
        self.alpha = float(alpha)
        self.lambda_amp = float(lambda_amp)
        self.max_iter = int(max_iter)
        self.tol = float(tol)
        self.init_jitter = float(init_jitter)
        self.amplitude_floor = float(amplitude_floor)
        self.mu_optimizer_max_iter = int(mu_optimizer_max_iter)
        self.random_state = int(random_state)

        self.mus_: Optional[np.ndarray] = None        # (K, d)
        self.amplitudes_: Optional[np.ndarray] = None # (K,)
        self.w_: Optional[np.ndarray] = None
        self.b_: Optional[float] = None
        self.metric_: Optional[np.ndarray] = None
        self.mu_: Optional[np.ndarray] = None         # primary prototype (largest α)
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
    ) -> "MultiPrototypeAttentionSelector":
        from sklearn.linear_model import Ridge

        if len(components_per_stim) == 0:
            raise ValueError("No stimuli passed to MultiPrototypeAttentionSelector.fit")

        responses = np.asarray(responses, dtype=np.float64)
        d = components_per_stim[0].shape[1]
        K = self.n_prototypes
        self.metric_ = np.eye(d, dtype=np.float64)

        mus = self._init_mus(components_per_stim, responses)
        etas = np.zeros(K, dtype=np.float64)             # α_k = exp(η_k); α=1 init
        prev_mus = mus.copy()

        self.history_.clear()
        self.converged_ = False

        # First W-step so the M-step has a target.
        x_combined = self._combined_pool(components_per_stim, mus, np.exp(etas))
        ridge = Ridge(alpha=self.alpha).fit(x_combined, responses)
        w = ridge.coef_.copy()
        b = float(ridge.intercept_)

        for it in range(self.max_iter):
            mus, etas = self._optimize_mus_etas(
                components_per_stim, responses, mus, etas, w, b
            )

            x_combined = self._combined_pool(components_per_stim, mus, np.exp(etas))
            ridge = Ridge(alpha=self.alpha).fit(x_combined, responses)
            w = ridge.coef_.copy()
            b = float(ridge.intercept_)

            dmu = float(
                np.linalg.norm(mus - prev_mus)
                / (np.linalg.norm(prev_mus) + 1e-12)
            )
            self.history_.append({
                "iter": it,
                "dmu": dmu,
                "amplitudes": np.exp(etas).tolist(),
            })
            self.n_iter_ = it + 1

            if it > 0 and dmu < self.tol:
                self.converged_ = True
                break
            prev_mus = mus.copy()

        amps = np.exp(etas)

        # Sort prototypes by descending amplitude so μ1 is always the "winner"
        order = np.argsort(-amps)
        mus = mus[order]
        amps = amps[order]

        self.mus_ = mus
        self.amplitudes_ = amps
        self.w_ = w
        self.b_ = b
        self.mu_ = mus[0].copy()  # always μ1 after sorting
        self.selected_indices_ = self._hard_indices(components_per_stim, self.mu_)
        return self

    def select_indices(self, components_per_stim: list[np.ndarray]) -> np.ndarray:
        if self.mus_ is None:
            raise RuntimeError("Selector not fit. Call fit() first.")
        return self._hard_indices(components_per_stim, self.mu_)

    def selected_vectors(
        self, components_per_stim: list[np.ndarray]
    ) -> np.ndarray:
        if self.mus_ is None:
            raise RuntimeError("Selector not fit. Call fit() first.")
        return self._combined_pool(components_per_stim, self.mus_, self.amplitudes_)

    def summary(self, components_per_stim: Optional[list[np.ndarray]] = None) -> dict:
        amps = (
            self.amplitudes_.tolist()
            if self.amplitudes_ is not None
            else None
        )
        n_active = (
            int(np.sum(self.amplitudes_ > self.amplitude_floor))
            if self.amplitudes_ is not None
            else None
        )

        # Normalized amplitudes (only ratios matter for gates; normalize for readability)
        norm_amps = None
        if self.amplitudes_ is not None:
            total = float(self.amplitudes_.sum())
            norm_amps = (self.amplitudes_ / max(total, 1e-30)).tolist()

        # Collapse ratio: α_max / α_second (>1e10 means effective single-prototype)
        collapse_ratio = None
        if self.amplitudes_ is not None and len(self.amplitudes_) >= 2:
            sorted_amps = np.sort(self.amplitudes_)[::-1]
            if sorted_amps[1] > 1e-30:
                collapse_ratio = float(sorted_amps[0] / sorted_amps[1])

        # Mean gate usage per prototype averaged over stimuli
        mean_gate_usage = None
        if (
            self.mus_ is not None
            and self.amplitudes_ is not None
            and components_per_stim is not None
        ):
            K = self.mus_.shape[0]
            tau2 = self.tau ** 2
            gate_sums = np.zeros(K, dtype=np.float64)
            n_valid = 0
            for comps in components_per_stim:
                if comps.shape[0] == 0:
                    continue
                _, min_d2 = self._pool_one(comps, self.mus_)
                log_w = -min_d2 / (2.0 * tau2) + np.log(
                    np.maximum(self.amplitudes_, 1e-30)
                )
                log_w -= log_w.max()
                g = np.exp(log_w)
                g = g / g.sum()
                gate_sums += g
                n_valid += 1
            if n_valid > 0:
                mean_gate_usage = (gate_sums / n_valid).tolist()

        prototype_separation = None
        if self.mus_ is not None and self.mus_.shape[0] >= 2:
            d01 = float(np.linalg.norm(self.mus_[0] - self.mus_[1]))
            prototype_separation = d01
        return {
            "selector": "MultiPrototypeAttentionSelector",
            "n_prototypes": self.n_prototypes,
            "n_active_prototypes": n_active,
            "tau": self.tau,
            "alpha": self.alpha,
            "lambda_amp": self.lambda_amp,
            "amplitude_floor": self.amplitude_floor,
            "amplitudes": amps,
            "amplitudes_normalized": norm_amps,
            "collapse_ratio": collapse_ratio,
            "mean_gate_usage": mean_gate_usage,
            "prototype_separation": prototype_separation,
            "n_iter": self.n_iter_,
            "converged": self.converged_,
            "tol": self.tol,
            "max_iter": self.max_iter,
            "mus": None if self.mus_ is None else self.mus_.tolist(),
            "mu": None if self.mu_ is None else self.mu_.tolist(),
            "w_internal": None if self.w_ is None else self.w_.tolist(),
            "b_internal": self.b_,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_mus(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> np.ndarray:
        """
        Init prototype 1 from the response-weighted mean (matches the K=1 baseline).
        Init prototypes 2..K by perturbing prototype 1 along the dominant
        response-weighted PC direction so they aren't degenerate at start.
        """
        stacked, weights = [], []
        for comps, r in zip(components_per_stim, responses):
            if comps.shape[0] == 0:
                continue
            stacked.append(comps)
            weights.append(np.full(comps.shape[0], r, dtype=np.float64))
        X = np.vstack(stacked)
        w_resp = np.concatenate(weights)
        mu1 = _weighted_mean(X, w_resp, floor=0.0)

        d = mu1.shape[0]
        K = self.n_prototypes
        rng = np.random.default_rng(self.random_state)

        if K == 1:
            return mu1[None, :]

        diff = X - mu1[None, :]
        w_pos = np.maximum(w_resp, 0.0)
        cov = (w_pos[:, None] * diff).T @ diff / max(float(w_pos.sum()), 1e-12)
        try:
            vals, vecs = np.linalg.eigh(cov)
            order = np.argsort(-vals)
            vecs = vecs[:, order]
        except np.linalg.LinAlgError:
            vecs = np.eye(d)

        mus = np.empty((K, d), dtype=np.float64)
        mus[0] = mu1
        for k in range(1, K):
            direction = vecs[:, (k - 1) % d]
            sign = 1.0 if k % 2 == 1 else -1.0
            jitter = 0.05 * rng.standard_normal(d)
            mus[k] = mu1 + sign * self.init_jitter * direction + jitter
        return mus

    def _attention(self, components: np.ndarray, mu: np.ndarray) -> np.ndarray:
        d2 = ((components - mu) ** 2).sum(axis=1)
        z = -d2 / (2.0 * self.tau ** 2)
        z = z - z.max()
        e = np.exp(z)
        return e / e.sum()

    def _pool_one(
        self, components: np.ndarray, mus: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return (per-prototype pools (K, d), per-prototype min-distances (K,))."""
        K = mus.shape[0]
        d = mus.shape[1]
        pools = np.zeros((K, d), dtype=np.float64)
        min_d2 = np.full(K, np.inf, dtype=np.float64)
        if components.shape[0] == 0:
            return pools, np.zeros(K)
        for k in range(K):
            pi = self._attention(components, mus[k])
            pools[k] = pi @ components
            min_d2[k] = float(((components - mus[k]) ** 2).sum(axis=1).min())
        return pools, min_d2

    def _combined_pool(
        self,
        components_per_stim: list[np.ndarray],
        mus: np.ndarray,
        amplitudes: np.ndarray,
    ) -> np.ndarray:
        """Return (n_stim, d) — α-gated mixture across prototypes."""
        K, d = mus.shape
        n = len(components_per_stim)
        out = np.zeros((n, d), dtype=np.float64)
        tau2 = self.tau ** 2
        for i, comps in enumerate(components_per_stim):
            if comps.shape[0] == 0:
                continue
            pools, min_d2 = self._pool_one(comps, mus)
            log_w = -min_d2 / (2.0 * tau2) + np.log(np.maximum(amplitudes, 1e-30))
            log_w -= log_w.max()
            g = np.exp(log_w)
            g = g / g.sum()
            out[i] = g @ pools
        return out

    def _hard_indices(
        self,
        components_per_stim: list[np.ndarray],
        mu: np.ndarray,
    ) -> np.ndarray:
        idx = np.empty(len(components_per_stim), dtype=np.int64)
        for i, X in enumerate(components_per_stim):
            if X.shape[0] == 0:
                idx[i] = 0
                continue
            d2 = ((X - mu) ** 2).sum(axis=1)
            idx[i] = int(np.argmin(d2))
        return idx

    def _optimize_mus_etas(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
        mus_init: np.ndarray,
        etas_init: np.ndarray,
        w: np.ndarray,
        b: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        L-BFGS-B on packed [μ_1, ..., μ_K, η_1, ..., η_K], with α_k = exp(η_k)
        and an L1 sparsity prior on α.  Numerical gradient.
        """
        from scipy.optimize import minimize

        K, d = mus_init.shape

        def _unpack(theta):
            mus = theta[: K * d].reshape(K, d)
            etas = theta[K * d :]
            return mus, etas

        def _loss(theta):
            mus, etas = _unpack(theta)
            amps = np.exp(etas)
            x_combined = self._combined_pool(components_per_stim, mus, amps)
            r_hat = x_combined @ w + b
            resid = responses - r_hat
            sse = float(resid @ resid)
            l1 = self.lambda_amp * float(amps.sum())
            return sse + l1

        theta0 = np.concatenate([mus_init.ravel(), etas_init])
        result = minimize(
            _loss,
            theta0,
            method="L-BFGS-B",
            options={"maxiter": self.mu_optimizer_max_iter, "gtol": 1e-6},
        )
        mus_new, etas_new = _unpack(result.x)
        return mus_new, etas_new


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



# ---------------------------------------------------------------------------
# RWA-peak selector: μ comes from the argmax of an RWA matrix on disk
# ---------------------------------------------------------------------------

import os
import pickle


class RWAPeakSelector(ComponentSelector):
    """
    Pick the component closest to the peak of a precomputed RWA on disk.

    The RWA pkl files written by ``run_rwa.py`` store an ``RWAMatrix`` with
    ``names_for_axes``, ``binners_for_axes``, and a smoothed response density
    over a grid in raw parameter space (e.g. radius, theta, phi, ...). The
    peak (argmax of the matrix) is decoded to a parameter dict, encoded
    through the same ComponentEncoder used by the rest of the pipeline,
    z-scored, and (when PCA is active) projected to PC space — that becomes
    the selector's ``mu_``. Per-stimulus selection is the nearest component
    to ``mu_`` under Euclidean distance, same as FixedCovarianceSelector.

    Path resolution
    ---------------
    Three modes (pick one):
      - ``rwa_path``: explicit path to one pkl. Use this if you only run a
        single component_type per analysis.
      - ``rwa_dir`` + ``experiment_id``: looks up
        ``{rwa_dir}/{experiment_id}_{component_type_lower}_rwa.pkl`` at fit
        time, matching ``run_rwa.py``'s save naming convention.
      - ``path_for_component_type``: explicit ``dict[str, str]`` from
        component_type ("Shaft") to pkl path.

    Wiring
    ------
    The selector needs the encoder + (optional) PCA preprocessor + the
    current component_type to convert the raw-space peak into selector
    space. ``fit_axis_coding`` calls ``set_encoding_context(...)`` before
    ``fit(...)``; other selectors don't have this method and are unaffected.
    """

    def __init__(
        self,
        rwa_path: Optional[str] = None,
        rwa_dir: Optional[str] = None,
        experiment_id: Optional[str] = None,
        path_for_component_type: Optional[dict] = None,
    ):
        if (rwa_path is None
                and (rwa_dir is None or experiment_id is None)
                and not path_for_component_type):
            raise ValueError(
                "RWAPeakSelector: provide rwa_path, "
                "(rwa_dir + experiment_id), or path_for_component_type"
            )
        self.rwa_path = rwa_path
        self.rwa_dir = rwa_dir
        self.experiment_id = experiment_id
        self.path_for_component_type = dict(path_for_component_type or {})

        self.mu_: Optional[np.ndarray] = None
        self.selected_indices_: Optional[np.ndarray] = None
        self.peak_params_: Optional[dict] = None
        self.peak_value_: Optional[float] = None
        self.resolved_path_: Optional[str] = None

        # Set externally by fit_axis_coding before fit().
        self._encoder = None
        self._pca_pre = None
        self._component_type: Optional[str] = None

    # ------------------------------------------------------------------
    # Pipeline integration hook
    # ------------------------------------------------------------------

    def set_encoding_context(self, *, encoder, pca_pre=None, component_type=None):
        self._encoder = encoder
        self._pca_pre = pca_pre
        self._component_type = component_type

    # ------------------------------------------------------------------
    # ComponentSelector API
    # ------------------------------------------------------------------

    def fit(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> "RWAPeakSelector":
        if self._encoder is None:
            raise RuntimeError(
                "RWAPeakSelector requires set_encoding_context() before fit() — "
                "did you call this selector outside fit_axis_coding?"
            )
        path = self._resolve_path()
        with open(path, "rb") as f:
            rwa_obj = pickle.load(f)

        # Find the argmax bin in the (smoothed) RWA matrix.
        flat_idx = int(np.argmax(rwa_obj.matrix))
        idx_tuple = np.unravel_index(flat_idx, rwa_obj.matrix.shape)
        peak_params: dict = {}
        for axis_idx, name in rwa_obj.names_for_axes.items():
            bin_idx = int(idx_tuple[axis_idx])
            peak_params[name] = float(rwa_obj.binners_for_axes[axis_idx].bins[bin_idx].middle)

        # Encode the peak as if it were a single-component stimulus, then
        # apply the same z-score (and PCA) the rest of the pipeline uses.
        peak_encoded = self._encoder.encode_components([peak_params])  # (1, d)
        peak_z = self._encoder.transform_with_scaler(peak_encoded)     # (1, d)
        if self._pca_pre is not None and self._pca_pre.is_fit:
            mu = self._pca_pre._pca.transform(peak_z)[0]
        else:
            mu = peak_z[0]

        self.mu_ = np.asarray(mu, dtype=np.float64)
        self.peak_params_ = peak_params
        self.peak_value_ = float(rwa_obj.matrix[idx_tuple])
        self.resolved_path_ = path
        self.selected_indices_ = self._hard_indices(components_per_stim, self.mu_)
        return self

    def select_indices(self, components_per_stim: list[np.ndarray]) -> np.ndarray:
        if self.mu_ is None:
            raise RuntimeError("RWAPeakSelector not fit.")
        return self._hard_indices(components_per_stim, self.mu_)

    def summary(self) -> dict:
        return {
            "type": "RWAPeakSelector",
            "rwa_path": self.resolved_path_ or self.rwa_path,
            "component_type": self._component_type,
            "peak_params": self.peak_params_,
            "peak_value": self.peak_value_,
            "mu": None if self.mu_ is None else self.mu_.tolist(),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_path(self) -> str:
        if self.rwa_path is not None:
            return self.rwa_path
        ct = self._component_type
        if ct in self.path_for_component_type:
            return self.path_for_component_type[ct]
        if self.rwa_dir is not None and self.experiment_id is not None:
            if ct is None:
                raise RuntimeError(
                    "RWAPeakSelector: component_type unknown — "
                    "set_encoding_context wasn't called with component_type"
                )
            return os.path.join(
                self.rwa_dir,
                f"{self.experiment_id}_{ct.lower()}_rwa.pkl",
            )
        raise RuntimeError(
            f"RWAPeakSelector: cannot resolve RWA path for component_type={ct!r}"
        )

    def _hard_indices(
        self,
        components_per_stim: list[np.ndarray],
        mu: np.ndarray,
    ) -> np.ndarray:
        idx = np.empty(len(components_per_stim), dtype=np.int64)
        for i, X in enumerate(components_per_stim):
            if X.shape[0] == 0:
                idx[i] = 0
                continue
            diff = X - mu[None, :]
            dists = (diff * diff).sum(axis=1)
            idx[i] = int(np.argmin(dists))
        return idx

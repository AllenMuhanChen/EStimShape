# Multi-Prototype Attention Selector — Methods

This document describes how `MultiPrototypeAttentionSelector` infers a
neuron's preferred component template ("μ") from a set of multi-component
stimuli and a per-stimulus response. It is one of several `ComponentSelector`
strategies plugged into the axis-coding pipeline; the others (e.g.
`FixedCovarianceSelector`, `RWAPeakSelector`) follow the same input/output
contract but compute μ differently.

The selector is the upstream half of the pipeline: it produces, per stimulus,
a single feature vector summarizing what that stimulus "looks like" through
the cell's preferred template. The downstream half is a ridge regression
from those vectors to firing rate, from which the preferred axis (`w`) and
all subsequent axis-coding analyses are derived.

The selector is designed to handle the case where a single template is
insufficient — for example, when the cell responds preferentially to two
distinct shape configurations rather than one — while collapsing back to a
single template when one is enough.

## 1. Inputs and outputs

**Inputs**

- `components_per_stim`: a list, one entry per stimulus. Each entry is an
  `(m_i, d)` matrix of `m_i` candidate components for that stimulus,
  encoded by `ComponentEncoder` and z-scored. `d` is the encoded feature
  dimension; if PCA preprocessing is enabled, `d` is the number of retained
  PCs.
- `responses`: per-stimulus mean firing rate, length `n_stim`.

**Outputs**

- `mus_`: `(K, d)` array of fitted prototype centers in the same space as
  the input components. After fitting, prototypes are sorted by descending
  amplitude.
- `amplitudes_`: length-`K` vector of nonnegative prototype amplitudes
  `α_k`. Prototypes whose amplitude falls below `amplitude_floor` are
  reported as inactive.
- `mu_`: the dominant prototype (`mus_[0]`) — exposed so single-prototype
  visualizers continue to work without modification.
- `selected_vectors(...)`: returns one `(n_stim, d)` matrix `x_combined`,
  the soft-pooled, amplitude-gated representation of each stimulus through
  the prototype mixture. This is the design matrix passed to the downstream
  ridge regression.
- `selected_indices_`: per-stimulus index of the component closest to the
  dominant prototype `mus_[0]` (used for hard-selection visualizations).

## 2. Generative model

For stimulus `i` with `m_i` components `x_{ij}` and `K` prototypes
`{μ_k, α_k}`:

**Per-prototype attention** (soft assignment of components to a prototype):

> `π_{ij}^k = softmax_j(−‖x_{ij} − μ_k‖² / (2τ²))`

This is a softmax over the `m_i` components for prototype `k`, with
distances from `μ_k` as the score. `τ` ("tau") is the attention bandwidth:
small `τ` produces near-hard selection, large `τ` produces near-uniform
pooling.

**Per-prototype pooled vector**:

> `x_eff_i^k = Σ_j π_{ij}^k · x_{ij}`

i.e., the attention-weighted average component for prototype `k` on
stimulus `i`. This collapses the variable-length component list to a single
`d`-dimensional vector per prototype.

**Inter-prototype gate** (which prototype best describes this stimulus):

> `g_ik = α_k · exp(−d_{ik} / (2τ²)) / Σ_{k'} α_{k'} · exp(−d_{ik'} / (2τ²))`

where `d_{ik} = min_j ‖x_{ij} − μ_k‖²` is the closest-component distance to
prototype `k`. The gate is also a softmax — over prototypes this time —
weighted by amplitude. A prototype with `α_k = 0` is effectively excluded.

**Stimulus representation**:

> `x_combined_i = Σ_k g_ik · x_eff_i^k`

The amplitude-gated mixture across prototypes; this is the per-stimulus
vector handed to ridge regression.

**Predicted response**:

> `r̂_i = w · x_combined_i + b`

with `w ∈ ℝ^d`, `b ∈ ℝ` learned by the W-step (Section 4).

## 3. Loss and amplitude prior

Loss is squared error on responses plus an L1 prior on amplitudes:

> `L = Σ_i (r_i − r̂_i)² + λ_amp · Σ_k α_k`

with the constraint `α_k ≥ 0`, enforced by the parameterization
`α_k = exp(η_k)` (any real `η_k` produces a positive `α_k`).

The L1 prior actively pushes amplitudes toward zero; only prototypes that
reduce squared error by more than `λ_amp` retain nonzero amplitude. With
`K = 2`, this is the model-selection mechanism that lets a one-prototype
fit emerge automatically whenever a second prototype isn't earning its
keep. The summary reports `n_active_prototypes` (count above
`amplitude_floor`) and `collapse_ratio` (`α_max / α_second`); a high
collapse ratio means the model is effectively single-prototype.

## 4. Optimization (alternating)

Initialization, then alternate W-step and M-step until either prototype
movement falls below `tol` or `max_iter` is reached.

**Initialization.** Prototype 1 is the response-weighted mean of all
components from all stimuli — the same starting point used by
`FixedCovarianceSelector`, so the K=1 case reproduces that selector's
initial guess. Prototypes 2..K are seeded by perturbing prototype 1
along the dominant directions of the response-weighted covariance of
`(x − μ_1)`, with alternating sign and a small Gaussian jitter. This keeps
prototypes from being degenerate at start without imposing strong priors on
where they land.

**Initial W-step.** With `{μ_k, α_k = 1}` at their initial values, compute
`x_combined` via Section 2 and fit ridge regression with the configured
`alpha`:

> `(w, b) = argmin_{w, b} Σ_i (r_i − w · x_combined_i − b)² + α · ‖w‖²`

producing the first weight vector and intercept.

**M-step.** With `(w, b)` fixed, jointly optimize `{μ_k, η_k}` (i.e.,
prototype centers and log-amplitudes) by L-BFGS-B on the packed parameter
vector `[μ_1, ..., μ_K, η_1, ..., η_K]`. Gradients are computed numerically
inside L-BFGS-B; the parameter count is `K · d + K`, small enough that
finite-differencing is acceptable. The objective is the loss in Section 3
evaluated by recomputing `x_combined` and `r̂` from the candidate
parameters.

**W-step.** With the updated `{μ_k, α_k}`, recompute `x_combined` and
refit `(w, b)` by ridge regression. This decouples the linear readout
from the prototype geometry: `(w, b)` optimally fit the current
representation, and the next M-step reshapes the representation given the
current readout.

**Convergence.** After each iteration, compute the relative change in
prototypes:

> `Δμ = ‖μ_new − μ_prev‖_F / ‖μ_prev‖_F`

If `Δμ < tol` (after the first iteration), declare converged. Otherwise
continue until `max_iter`. Convergence and final iteration count are
recorded.

**Final cleanup.** After the loop, prototypes are sorted in descending
amplitude order so `mus_[0]` is always the dominant one, exposed as `mu_`.

## 5. Selection and pooling at inference

For a new (or training) stimulus, `selected_vectors` recomputes
`x_combined` by Section 2 using the fitted prototypes and amplitudes. This
becomes the design matrix `X` for the downstream ridge regression in
`fit_axis_coding`, which produces:

- `w` — the preferred axis in selector space.
- Orthogonal basis on the residual subspace (variance-sorted PCA on
  `X − (X·ŵ)ŵ`).
- All downstream axis-coding analyses (predicted-vs-actual scatter,
  preferred-axis tuning curve, orthogonal-axis tuning, signed Spearman ρ
  per axis, Tsao-style orthogonal modulation depth, etc.).

Because `selected_vectors` returns a *combined* mixture (not a per-
prototype slice), the cell is described to the downstream regression as
"the soft-pooled mixture of all active prototypes." If one prototype
collapses, its contribution is effectively zero and the mixture reduces to
a single-prototype representation automatically.

## 6. Interpretation and reporting

The selector summary (`summary(...)`) reports:

- `n_prototypes`, `n_active_prototypes` — configured `K` vs. number of
  prototypes with `α_k > amplitude_floor`.
- `amplitudes` and `amplitudes_normalized` — raw and sum-to-1 normalized
  amplitudes per prototype.
- `collapse_ratio` — `α_max / α_second`. >1e10 indicates effective
  single-prototype fit.
- `mean_gate_usage` — average `g_ik` across stimuli, per prototype. A
  proxy for "what fraction of stimuli does prototype `k` dominate?"
- `prototype_separation` — Euclidean distance between the top two
  prototypes in selector space; large separation indicates a meaningful
  multi-prototype solution.
- `n_iter`, `converged`, `tol`, `max_iter` — alternation diagnostics.
- `mus`, `mu` — all prototype centers and the dominant one.

Downstream μ-decoding (in `fit_axis_coding`) inverse-scales each prototype
back to raw parameter units and decodes circular and spherical components
to interpretable angles, yielding a per-prototype dictionary of parameter
values shown in the consolidated axis-coding figure's μ panels.

## 7. Hyperparameters

| name | role | typical value |
| --- | --- | --- |
| `n_prototypes` (K) | upper bound on number of prototypes | 2 |
| `tau` | attention bandwidth in selector-space units | 1.0 |
| `alpha` | ridge L2 strength on the W-step | 1.0 (downstream RidgeCV picks the final α) |
| `lambda_amp` | L1 strength on prototype amplitudes | 0.1 |
| `max_iter` | max alternations | 30 |
| `tol` | relative ‖Δμ‖ for convergence | 1e-3 |
| `init_jitter` | scale of prototype 2..K perturbation at init | 0.5 |
| `amplitude_floor` | threshold below which a prototype is reported inactive | 1e-3 |
| `mu_optimizer_max_iter` | per-M-step L-BFGS-B iterations | 100 |
| `random_state` | seed for init jitter | 0 |

`tau` and `lambda_amp` are the two hyperparameters with the largest effect
on solution character. Higher `tau` produces more uniform pooling and
weaker per-prototype specialization; raising `lambda_amp` makes collapse to
fewer prototypes more aggressive.

## 8. Relationship to other selectors in the pipeline

- `FixedCovarianceSelector`: K=1 EM with hard or soft attention (no
  amplitude prior, no joint optimization with `w`). The
  multi-prototype selector reduces to a similar fit when K=1 and
  `lambda_amp=0`, except that `(w, b)` are optimized jointly here whereas
  `FixedCovarianceSelector` doesn't see `w`.
- `SoftAttentionAxisSelector`: same alternating W/M-step structure but
  with K=1 and no amplitudes; the multi-prototype selector is its
  K-prototype generalization with sparsity.
- `RWAPeakSelector`: μ comes from a precomputed RWA grid on disk rather
  than being fit. No iteration; a fixed `μ` is used to hard-pick one
  component per stimulus.

All selectors implement the same `fit / select_indices / selected_vectors /
summary` contract, so the rest of the pipeline (`fit_axis_coding`,
ridge regression, axis-coding plots, orthogonal-tuning summary) is
identical regardless of which selector produced the design matrix.

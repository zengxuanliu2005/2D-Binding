---
type: derivation
status: under-review (criteria 1+3 ✓ in 03_result.md; criterion 2 partial, see 05_open_questions Q1)
date: 2026-06-01
summary: 00_intent — Why we need P(R; lp, Lc) (01_wlc_endpoint_distribution)
derivation_folder: 01_wlc_endpoint_distribution
step: intent
inputs: stage_essay.md §4.4, §5.3; reconcile_methods.py; LP_PHD in xi_rl_candidates.py
outputs: motivation + acceptance criterion for the WLC end-to-end distribution
agent_read_when:
  - working on 01_wlc_endpoint_distribution or its successor
  - need to know the intent of this derivation step
---

# 00_intent — Why we need P(R; lp, Lc)

## The gap we are closing

The senior's `xi_rl_candidates.py` shows that **Xu 2015's formula**

  ξ_RL² = k_B T / k_RL + (k_B T · L₀ / (2 k_a))²

predicts the wrong ξ_RL for all three of our systems (mean error > 80%; see
stage_essay.md §4.4 table). The reason is straightforward (essay §5.3):
the anchor angle stiffness `k_a ≈ 255 ε/rad²` we measure is **identical
across K100/K10/K01**. Xu's formula has no other parameter that varies
with flexibility, so it cannot capture the 35× spread we observe.

What varies with flexibility is the **chain persistence length lp**
(84.6 / 8.18 / 1.14 nm for rigid / semi / flex). We need a theory whose
ξ_RL prediction is parameterised by lp, not k_a.

The natural lp-parametrised theory is the **worm-like chain (WLC) end-to-end
distribution** P(R; lp, Lc). Reduce it to the z-marginal P_z(z; lp, Lc),
convolve two of them with the binding kernel, and you get K2D(l; lp).
σ_K2D(l) then gives ξ_RL directly — see derivation/03 and 04.

## The model

A semiflexible chain of contour length Lc with bending stiffness lp. In
3D, the bond direction at arc length s diffuses according to

  ⟨t̂(s) · t̂(s')⟩ = exp(-|s - s'| / lp)

with t̂(s) = dR/ds the unit tangent vector. R is the end-to-end vector,
R = ∫₀^{Lc} t̂(s) ds.

Two well-known limits frame the problem:

| regime | Lc / lp | qualitative shape of P(R) |
|---|---|---|
| rigid    | « 1 | δ(R - Lc): chain is straight |
| flexible | » 1 | Gaussian with ⟨R²⟩ = 2 lp Lc (random walk limit) |

Our three systems all fall in the intermediate regime where neither
limit is sharp:

| system | lp (nm) | Lc (nm) | Lc/lp | regime |
|---|---:|---:|---:|---|
| rigid (K100) | 84.6  | 12 | 0.14 | "rigid" — but not δ-sharp |
| semi  (K10)  |  8.18 | 12 | 1.47 | intermediate |
| flex  (K01)  |  1.14 | 12 | 10.5 | "Gaussian" — but with stiffness corrections |

So a single closed-form approximation is unlikely to be accurate across
all three. We therefore use **Monte Carlo sampling of a discrete WLC** as
the ground-truth P(R), and benchmark against the Becker–Rosa–Everaers
2010 closed-form interpolation as a literature cross-check.

## Acceptance criterion

The WLC implementation in `scripts/k2d_l_wlc_theory.py` is accepted when:

1. **Reduces correctly in both limits**
   - rigid (Lc/lp = 0.1): MC P(R) peaked at R ≈ Lc with FWHM consistent with thermal bending
   - flex  (Lc/lp = 100): MC P(R) within 5% RMSE of analytical Gaussian over R/Lc ∈ [0.05, 0.5]
2. **Self-consistent** with measured Re from chain_coords.npz
   - ⟨R²⟩^{1/2} from MC at our three lp values matches Re measured in `system_inputs.py`
     (the senior's PPT-slide values 14.76 / 11.65 / 5.66 nm) within 15%.
3. **Numerical convergence**
   - Doubling MC chain count changes the P(R) histogram bin probabilities
     by less than 3% in bins with > 0.5% population.

If 1–3 all pass, the result feeds derivation/02 (z-marginal) and derivation/03
(K2D(l) convolution) — see those READMEs for their own acceptance criteria.

## What this step does NOT do

- It does NOT compute K2D(l) or ξ_RL. Those are downstream (03, 04).
- It does NOT yet include the **anchoring geometry** (chain is rooted at a
  membrane with a known angular cone). That's derivation/02's job.
- It does NOT account for excluded volume (self-avoidance). Our chains are
  12 nm long with bond length 1 nm — short enough that SAW corrections
  are < 5% and we ignore them. (Documented in 05_open_questions.md.)

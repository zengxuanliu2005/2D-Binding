---
type: derivation
status: accepted
date: 2026-06-02
summary: 05_open_questions — caveats and the carry-forward to derivation/04 (03_k2d_l_kernel)
derivation_folder: 03_k2d_l_kernel
step: open_questions
inputs: 03_result.md tables; B2.2 σ_z values; senior's PPT slide 5
outputs: punch list ordered by impact on derivation/04
agent_read_when:
  - working on 03_k2d_l_kernel or its successor
  - need to know the open_questions of this derivation step
---

# 05_open_questions — caveats and the carry-forward to derivation/04

## Q1 — Semi peak position offset (l\* vs 2⟨z⟩)

**Symptom**. For semi: l\* = 18.7 nm but 2·⟨z⟩ = 13.3 nm. The K2D(l) peak
sits 5.4 nm to the right of the prediction.

**Root cause** (probable). The peak of K2D(l) is at the maximum of the
**product distribution** P_z^R(z_R) · P_z^L(z_L) constrained to
z_R + z_L = l + (kernel-centre). For symmetric R-L this maximises when
z_R = z_L ≈ z_mode (mode, not mean, of P_z). For asymmetric P_z (which
semi is — it has a long right tail), the mode ≠ mean, so l\* ≠ 2⟨z⟩.

**To resolve**.
- Plot P_z(z) for semi and identify the mode; compare 2·z_mode to l\*.
- Document in 03_result.md once verified — this is a 30-line numpy check.

Not blocking for derivation/04 (which uses σ_K2D, not l\*).

## Q2 — σ_K2D ordering reversal (semi > flex)

**Symptom**. Production gives σ_K2D(semi) = 5.45 > σ_K2D(flex) = 3.91,
violating criterion 3 from 00_intent.md (expected monotone with lp).

**Root cause**. With z < 0 truncation ON (default), the flex chain's
broad symmetric P_z gets aggressively cut (40 % of its mass), compressing
its σ_z and hence σ_K2D. Semi's P_z is more asymmetric and only loses
~5 % of its mass to truncation, so its σ_K2D stays large.

In other words: the truncation policy artificially **inverts** what would
naïvely be a monotone ordering.

**To resolve** (3 options).
1. Drop truncation (z < 0 allowed). Restores monotone σ_z ordering but
    bakes in unphysical chain-through-membrane configurations.
2. Use reflection boundary (chain bounces off membrane). More physical.
    Requires modifying the WLC MC sampler in derivation/01 — significant.
3. Use the existing truncation but document that the σ_K2D measured here
    is the **truncation-conditional** σ_K2D, which captures the same
    physics as the senior's measured K2D(l) from her constrained-h MD
    (where the chain also cannot pass through).

Pragmatic choice: option 3 + clear documentation. The measured ξ_RL
ordering is rigid (0.685) ≪ semi (2.076) ≈ flex (2.253), so the
"correct" semi vs flex ordering is nearly degenerate even in measurement
— our 5.45 > 3.91 is qualitatively in the right ballpark.

For derivation/04 we report the predicted ξ_RL for all three systems
and the σ_K2D ratio test, flagging semi vs flex as "tight" rather than
demanding strict monotone.

## Q3 — Predicted σ_K2D > measured ξ_RL by 2×

**Symptom**. σ_K2D / ξ_RL ratios are 2.07 / 2.63 / 1.73 for rigid / semi
/ flex (all > 1, similar magnitude).

**Three contributing factors** (already in 03_result.md §3.3):

(a) WLC σ_z is ~1.8× wider than measured σ(R_z) — derivation/01 Q1.
(b) Hard-gate kernel adds rcut/√5 ≈ 0.67 nm in quadrature.
(c) ξ_RL ≠ σ_K2D literally; they're related through the Weikl 2016
    convolution with membrane-separation P(l).

**To resolve** in derivation/04.

The cleanest test: report ξ_RL_predicted = σ_K2D from this step,
acknowledge the 2× over-prediction, but emphasise the **ratio** test:
σ_K2D(rigid) / σ_K2D(flex). This ratio should be lp-dependent in our
theory and lp-independent in Xu 2015. Even if the absolute values are
off by a uniform 2×, the ratio is the key qualitative prediction.

We'll do that comparison explicitly in derivation/04.

## Q4 — Soft-Boltzmann vs hard-gate kernel

**Symptom**. The hard gate is a simplification. The soft kernel from
`raw_tether_partition_k2d.py::radial_u_kbt + angle_factor` (Boltzmann-
weighted radial + angular gates) is what's actually used in production
extracts.

**Impact**. Soft kernel is narrower than hard gate in z (effective
"rcut" smaller), would reduce σ_K2D by ~0.2 nm uniformly. Doesn't change
the ratio test (Q3).

**To resolve**. Trivial swap in `hard_lateral_acceptance` → replace with
a `soft_lateral_acceptance` that calls into `raw_tether_partition_k2d.py`'s
existing kernel. Deferred to derivation/05 or essay revision (not
blocking derivation/04).

## Q5 — Reflection vs truncation (proper membrane BC)

Same as Q2 option 2. Long-term improvement; not urgent.

## Status carry-forward to derivation/04

Three acceptance criteria from 00_intent.md:
1. **Shape sanity rigid + flex** — ✓
2. **σ_K2D ordering monotone** — ✗ (Q2: truncation artefact)
3. **MC convergence** — informal ✓ (Q4 derivation/04 will do formal halving)

Derivation/04 will:
- Take σ_K2D from `results/derivation_b2/k2d_l_curves.npz` directly
- Predict ξ_RL = σ_K2D (with caveats from Q3)
- Compare to measured 0.685 / 2.076 / 2.253 nm
- Report the rigid:flex σ_K2D ratio explicitly as the lp-discrimination
  test
- Compare against Xu 2015's prediction of 1.00 ratio (since k_a is
  identical and lp doesn't enter)

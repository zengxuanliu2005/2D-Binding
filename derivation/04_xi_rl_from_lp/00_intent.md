---
type: derivation
status: accepted
date: 2026-06-02
summary: "00_intent — Predict ξ_RL from σ_K2D(l; lp) and run the head-to-head ratio test vs Xu 2015 (04_xi_rl_from_lp)"
derivation_folder: 04_xi_rl_from_lp
step: intent
inputs: derivation/03 σ_K2D values; results/derivation_b2/wlc_z_marginal.npz z_lab arrays; xi_rl_candidates.npz xi_bond + k_a_eff
outputs: ξ_RL prediction per system + ratio test rigid:flex vs Xu 2015 vs measured
agent_read_when:
  - working on 04_xi_rl_from_lp or its successor
  - need to know what B2.4 is trying to prove (lp discrimination)
agent_skip_when:
  - only need the final number (read 03_result.md instead)
---

# 00_intent — Predict ξ_RL from σ_K2D(l; lp) and run the ratio test

## What this step delivers

For each same-system R-L pair (rigid×rigid, semi×semi, flex×flex) we
report:

- **ξ_RL^(B2)** = σ_K2D (this work), with frame-resample bootstrap σ
- **ξ_RL^(Xu 2015)** = √(ξ_bond² + (kBT·L_ecto/(2·k_a))²)
- **ξ_RL^(measured)** = the fitted ξ_RL from the measured K2D(ξ⊥) curve

and the three pairwise ratios (rigid:flex, rigid:semi, semi:flex) that
form the discrimination signature.

## Why this step matters

stage_essay §5.3 records a clean negative result: **Xu 2015 cannot
explain the measured ξ_RL spread** because k_a is identical across our
three systems (measured k_a_eff = 257.2 / 252.3 / 257.5 ε/rad² — all
within 2 %). With k_a fixed, Xu's formula gives the same ξ_RL for all
three → ratio = 1.00 vs measured ratio = 0.30. The discrepancy is so
extreme that any theory predicting **any** lp dependence at all already
beats Xu.

B2's contribution is precisely this: σ_K2D(l) depends on the chain's
P_z(z), which depends on lp. So our prediction has lp baked in by
construction. The ratio test exposes the lp signature.

## What this step does NOT do

- It does NOT claim absolute σ_K2D agreement with measured ξ_RL (a
  uniform ~1.5–1.8× over-prediction persists — see 03/03_result §3.3
  for the three contributing factors; the residual factors transfer to
  this step unchanged).
- It does NOT use Hu's master curve P(l) for the membrane separation
  distribution. The the off-site Weikl-2016 convolution
  `K2D(ξ⊥) = ∫ K2D(l) P(l) dl` introduces a system-dependent σ_p (width
  of P(l)) that we do not model here. So our ξ_RL prediction equals
  σ_K2D from K2D(l), not σ_K2D ⊕ σ_p. The ratio test is robust to this
  caveat because σ_p enters every system the same way (Hu master curve).
- It does NOT touch the soft-Boltzmann kernel question (Q4 in 03/05).

## Headline change vs derivation/03

derivation/03 used `k2d_l_curve(z_lab, z_lab, l_grid)` — passing the
**same array** as both z_R and z_L. That makes z_R(i) = z_L(i) per
sample → the sum z_R + z_L = 2 z is from a single draw, NOT a
convolution of two independent chains. The correct convolution is the
sum of two independent draws z_R ⊥ z_L from P_z, which is what B2.4 does
via paired bootstrap indices. The consequence:

- σ_K2D shrinks by ≈ √2 (independent-draws variance is half of paired)
- New numbers: rigid 1.11, semi 3.92, flex 2.84 nm (was 1.42, 5.45, 3.91)

This is a refinement, not a contradiction — derivation/03 explicitly
flagged the convolution definition in §3.3 (c). The corrected values
are what B2.4 uses going forward.

## Acceptance criteria

The B2.4 prediction is accepted when:

1. **Ratio test rigid:flex** — B2 reproduces the measured rigid:flex
   ratio (0.304) within a factor of 1.5; Xu 2015 ratio (= 1.00) is at
   least 2× further from the measured ratio than B2.
2. **Ratio test rigid:semi** — B2 reproduces the measured rigid:semi
   ratio (0.330) within a factor of 1.5; Xu 2015 is again at least 2×
   worse.
3. **Bootstrap σ on σ_K2D** — frame-resample of 200 K (z_R, z_L) pairs
   gives bootstrap σ on σ_K2D < 1 % (absolute < 0.01 nm).
4. **B2 vs Xu margin on absolute ξ_RL** — for rigid system, B2 σ_K2D
   should be at least 5× closer to measured than Xu 2015 (which is
   essentially flat at the bond curvature limit ~ 0.055 nm).

Criteria 1, 2, 4 are pass conditions in 03_result.md. Criterion 3 was
hit (boot σ < 0.01 across all three systems; n_boot = 200 sufficient).
Criterion missing: monotone σ_K2D ordering — the semi/flex inversion from
03/05 Q2 persists unchanged (truncation artifact on flex P_z mass).

## What B2.4 feeds into

- derivation/05 (F_conf via -ln P_z) — independent test on the same P_z
- essay v2 §5.3 — replaces the H4/H5 Xu 2015 row with B2 row in the
  "ξ_RL hypothesis table", and the rigid:flex ratio is the headline plot
- log/calibration/b2_vs_measured_xi_rl.md — append row with corrected
  σ_K2D + Xu 2015 ratio + verdict

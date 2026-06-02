---
type: derivation
status: accepted
date: 2026-06-02
summary: "01_setup — Three ξ_RL predictors (B2 σ_K2D, Xu 2015, measured) + paired-bootstrap ratio formulation (04_xi_rl_from_lp)"
derivation_folder: 04_xi_rl_from_lp
step: setup
inputs: derivation/03 eqs (1.4)-(1.11); xi_rl_candidates.py xi_bond + L_ECTO constants; ref Xu 2015 formula
outputs: equations (1.1)-(1.4); paired-bootstrap protocol for ratio σ
agent_read_when:
  - working on 04_xi_rl_from_lp
  - need the Xu 2015 formula in our k_a / kBT convention
agent_skip_when:
  - only need the verdict (read 03_result.md instead)
---

# 01_setup — three predictors and the ratio-bootstrap protocol

## B2 predictor (this work)

The lp-parametrized 2D binding constant K2D(l) was derived in
derivation/03 (eqs. 1.5–1.6) as the convolution

  K2D(l) = ∫∫ dz_R dz_L P_z^R(z_R) P_z^L(z_L) · v(z_R + z_L − l)    (1.1)

with hard-gate kernel v(dz) = π (rcut² − dz²). The B2 predictor for
ξ_RL is the std of l weighted by K2D(l)/Z:

  ξ_RL^(B2) = σ_K2D(l)                                              (1.2)

where σ_K2D is computed by eqs. (1.7)–(1.11) of derivation/03.

### Independent-draw vs paired-draw convolution

Eq. (1.1) is a true 2D integral over independent z_R, z_L. In code,
the MC estimator is

  K2D(l) ≈ ⟨v(z_R + z_L − l)⟩_{(z_R, z_L) ~ P_z^R × P_z^L}          (1.3)

with **z_R and z_L drawn independently** from their respective marginals.
For symmetric R-L (same lp), this is NOT the same as drawing one z
and using it for both R and L (z_R(i) = z_L(i)). The latter has

  Var(z_R + z_L | paired) = Var(2 z) = 4 σ²_z

versus the correct

  Var(z_R + z_L | independent) = 2 σ²_z

giving σ_sum smaller by √2 in the independent case. derivation/03's
production used the paired form (legacy of code reuse). B2.4 corrects
this with independent bootstrap indices for both R and L.

## Xu 2015 predictor (legacy comparison)

Xu, Caruso & Vanderlick 2015 derived ξ_RL as a quadrature of bond
curvature ξ_bond = √(kBT/k_RL) and anchor-cone lateral fluctuation
σ_lateral ≈ kBT L_ecto / (2 k_a) for an angular spring k_a on a chain
of length L_ecto:

  ξ_RL^(Xu) = √(ξ_bond² + (kBT · L_ecto / (2 k_a))²)               (1.4)

Per CLAUDE.md, kBT = 1.1 ε, L_ecto = 7 σ = 7 nm (7 ecto beads). The
measured k_a_eff from `xi_rl_candidates.npz` is:

  rigid: 257.15 ε/rad²  semi: 252.32 ε/rad²  flex: 257.48 ε/rad²

All three within 2 % of each other — exactly the "k_a does not
distinguish lp" property that motivates this entire workstream.
Substituting:

  ξ_RL^(Xu, rigid) ≈ √(0.054² + 0.015²) ≈ 0.056 nm
  ξ_RL^(Xu, semi)  ≈ 0.056 nm   (k_a 2 % smaller)
  ξ_RL^(Xu, flex)  ≈ 0.056 nm

ξ_bond from `xi_rl_candidates.xi_bond` = 0.0538 nm (LJ bond-well
curvature in kBT units).

## Measured predictor

The fit (essay §4.4) of K2D(ξ⊥) to a Gaussian gives

  ξ_RL^(measured) = 0.685 / 2.076 / 2.253 nm     (rigid / semi / flex)

Reported as fit parameters in `results/xi_rl_fit.npz`.

## Ratio test

We form three pairwise ratios per source:

  r_AB = ξ_RL^(A) / ξ_RL^(B)                                       (1.5)

for (A, B) ∈ {(rigid, flex), (rigid, semi), (semi, flex)}. The headline
ratio is **rigid:flex** because lp varies by 75× there. The Xu 2015
predictions give r_AB ≈ 1.000 ± 0.005 (the small spread tracks the 2 %
spread in k_a). The B2 predictions vary by factors of 3–4. Comparing
each to the measured ratio is the lp-discrimination test.

## Bootstrap σ on σ_K2D (paired indices for ratios)

For each system, 200 K (z_R, z_L) lab-frame z samples come from B2.2's
production MC. We bootstrap σ_K2D by:

  for b in 1..n_boot:
      i_R = rng.integers(0, n)          # independent index sets
      i_L = rng.integers(0, n)
      K2D_b = k2d_l_curve(z_R[i_R], z_L[i_L], l_grid)
      σ_K2D_b = k2d_l_stats(l_grid, K2D_b)['sigma_K2D']
  report mean, std over b

Crucially, ratios r_AB(b) = σ_K2D_A(b) / σ_K2D_B(b) are computed
**bootstrap-by-bootstrap** so that correlations from the shared MC
sample size cancel in the ratio's standard error (a Monte-Carlo
delta-method estimate). For n_boot = 200 and n_pairs = 200 K the
ratio σ is well below 0.5 % (see 03_result §3.2).

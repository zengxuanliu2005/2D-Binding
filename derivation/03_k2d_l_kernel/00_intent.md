---
type: derivation
status: under-review (criteria 1 + 4 ✓; criterion 2 partial; criterion 3 fails — see 05)
date: 2026-06-02
summary: 00_intent — Why we need K2D(l; lp_R, lp_L) (03_k2d_l_kernel)
derivation_folder: 03_k2d_l_kernel
step: intent
inputs: derivation/02 z_lab arrays; raw_tether_partition_k2d.py binding kernel; stage_essay §4.3
outputs: motivation + acceptance criteria for K2D(l) per system pair
agent_read_when:
  - working on 03_k2d_l_kernel or its successor
  - need to know the intent of this derivation step
---

# 00_intent — Why we need K2D(l; lp_R, lp_L)

## What this step delivers

For each pair of receptor and ligand flexibility classes (R, L), produce
the **2D binding constant K2D(l)** as a function of membrane separation l.

For derivation 04 (ξ_RL) and derivation 05 (F_conf) we need:

- **K2D,max** = max over l of K2D(l) — sets the absolute binding strength.
- **l\*** = arg-max l — sets the optimal membrane separation.
- **σ_K2D(l)** = std of l weighted by K2D(l)/Z — this is **the predicted ξ_RL**.

For our 3 systems (R == L symmetric by construction), we focus on the 3
same-system pairs (rigid/rigid, semi/semi, flex/flex). Off-diagonal pairs
are also computed for completeness but the actual MD experiments only
study symmetric R-L (essay §4.4).

## Why this matters

stage_essay §5.3 documents that the Hu/Xu master curve K2D(l) shape is
the determinant of ξ_RL. If we can predict K2D(l) from lp alone (no fitting
to MD data), we have an analytic ξ_RL(lp) function — which is what
derivation 04 needs to test against measured ξ_RL = 0.685/2.076/2.253 nm.

The senior's Hu/Xu formula explicitly assumed K2D(l) is Gaussian in l.
stage_essay §4.3 already showed this assumption breaks for semi/flex
(K10/K01 systems). Our explicit MC-based K2D(l) makes no Gaussian
assumption — it reads the actual shape from B2.2's P_z(z) histograms.

## Combining R and L chain endpoints into the bond

The R chain anchored at z=0 has its binding bead at lab z = z_R, sampled
from B2.2 P_z^R(z).
The L chain anchored at z=l (the other membrane) has its binding bead at
lab z = l − z_L, with z_L sampled from B2.2 P_z^L(z) by the same model
(L extends "downward" from its membrane into the gap).

The bond-vector z-component is

  dz = z_R − (l − z_L) = z_R + z_L − l                              (00.1)

A bond forms iff the 3D bond vector r = (r_xy, dz) falls inside the
binding kernel — a small disk of radius rcut ≈ 1.5 σ ("hard gate") or
2.9 σ ("soft Boltzmann gate"). The lateral position (r_xy) is uniform
over the gap, so we integrate it analytically into a per-(z_R, z_L)
acceptance area v(dz):

  v(dz) = ∫ K_bond(|(r_xy, dz)|) · 2π r_xy dr_xy                   (00.2)

The K2D(l) is then the average of v over the R, L chain endpoint pairs:

  K2D(l) = ∫∫ dz_R dz_L P_z^R(z_R) P_z^L(z_L) · v(z_R + z_L − l)   (00.3)

This is the convolution Weikl-2016 wrote down. We evaluate it numerically
using the 200 000 z_R, z_L samples from B2.2 (Monte Carlo over chain
endpoint pairs, analytic v on dz).

## What this step does NOT do

- It does not predict ξ_RL — that's derivation 04 (using σ_K2D).
- It does not predict F_conf — that's derivation 05.
- It uses the **hard-gate kernel** as the first cut (radial < 1.5 σ, no
  angular factor). 05_open_questions discusses extending to the
  soft-Boltzmann kernel from raw_tether_partition_k2d.py — for now we
  trade absolute accuracy for clarity and pin everything to the
  shape-sensitive σ_K2D(l), which is robust to kernel details.

## Acceptance criteria

K2D(l) per system pair is accepted when:

1. **Shape sanity** (rigid×rigid): K2D(l) peaked near l\* ≈ ⟨z_R⟩ + ⟨z_L⟩
   ≈ 22.4 nm with σ_K2D narrow (≤ 1 nm). Reflects the small fluctuation
   of a stiff chain endpoint.
2. **Shape sanity** (flex×flex): K2D(l) broad, σ_K2D ≈ √(2) · σ_z_flex ≈
   3.9 nm, peaked near l\* ≈ 2·⟨z_flex⟩ ≈ 3.4 nm.
3. **Monotone σ_K2D ordering**: σ_K2D(rigid) < σ_K2D(semi) < σ_K2D(flex).
   This is what enables the ξ_RL prediction in derivation 04.
4. **MC convergence**: halving the number of (z_R, z_L) sample pairs
   changes σ_K2D by < 1 %.

If 1-4 hold the result feeds derivation/04 directly.

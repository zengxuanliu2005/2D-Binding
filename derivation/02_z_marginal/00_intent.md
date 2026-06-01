# 00_intent — Why we need P_z(z; lp, Lc, k_a)

> **Status**: accepted (all 3 criteria ✓ in 03_result.md; Q1-5 noted in 05)
> **Date**: 2026-06-01
> **Author**: Claude (Opus 4.7)
> **Inputs**: derivation/01 P(R; lp, Lc); stage_essay.md §4.4 (k_a_eff = 255 ε/rad²)
> **Outputs**: motivation + acceptance criterion for the membrane-anchored z-marginal

## The piece B2.2 must add to B2.1

Derivation 01 gave us P_R(R) — a fully isotropic 3-D distribution of the
chain end-to-end vector. The actual receptor in our problem is **anchored
in a membrane**:

1. The anchor bead lives at z = 0 (membrane surface).
2. The first chain bond is constrained to point roughly along +z by an
   anchor angle potential of effective stiffness k_a_eff ≈ 255 ε/rad²
   (stage_essay §4.4 — same across all three flexibility classes; this is
   the reason Xu 2015 cannot capture the K2D ordering).
3. K2D(l) only sees the z-projection of the binding-bead position, because
   the membrane separation l is the only relevant 1-D coordinate; the
   lateral position integrates over a uniform disk and falls out.

So what derivation/03 actually needs is **P_z(z; lp, Lc, k_a)** —
the probability density of the binding-bead's z-coordinate given the
chain + anchor model.

## Inputs we'll combine

| name | source | comment |
|---|---|---|
| `endpoints` (R vectors, 3D) | derivation/01 result `wlc_endpoint_distribution.npz` | 200 K samples per system |
| `k_a` (anchor stiffness)    | stage_essay §4.4 (255 ε/rad²)                       | identical for K100/K10/K01 |
| `kBT` (energy unit)         | CLAUDE.md (1.1 ε)                                   | convert k_a to kBT/rad² |
| anchor frame convention     | first bond was sampled along +z in 01               | implies the chain's tip direction is +z in the "chain frame" |

The anchor cone applies one Boltzmann-weighted rotation to each MC chain
end-to-end vector: choose a tilt angle θ_anchor from the cone density,
rotate R into the lab frame, take the lab-z component.

## Anchor cone density

For a harmonic anchor angle potential U(θ) = (k_a / 2) θ² (small angle),
the 3-D phase-space density of the tilt angle is

  p(θ) dθ ∝ exp(-k_a θ² / (2 k_B T)) sin θ dθ                       (intent.1)

With k_a / k_B T = 255 / 1.1 = 232 rad⁻²,

  σ_θ = √(k_B T / k_a) ≈ √(1 / 232) = 0.066 rad ≈ 3.8°               (intent.2)

This is the half-width predicted in the plan ("~4°").

## Acceptance criterion

`P_z(z; lp, Lc, k_a)` is accepted when:

1. **Rigid limit (lp ≫ Lc, k_a fixed)**: P_z(z) → distribution of
   Lc · cos(θ_anchor), which is peaked at z ≈ Lc(1 - σ_θ²/2) = 11.95 nm
   with σ_z ≈ Lc · σ_θ ≈ 0.79 nm. MC should reproduce both numbers within
   5 % (well below the chain bending noise).
2. **Flexible limit (lp ≪ Lc)**: in the random-walk regime the chain
   distribution is isotropic, so P_z(z) → P_R(R) · (1/R)² · (... )
   integrated over the unit hemisphere. Concretely, σ_z² ≈ ⟨R²⟩ / 3
   independent of k_a (anchor adds only a small further tilt). MC σ_z²
   should be within 10 % of ⟨R²⟩_MC / 3.
3. **Internal cross-check**: the same z-marginal computed two ways must
   agree to < 2 %:
   - Method A: sample θ_anchor + rotate full R into lab, take z.
   - Method B: in the chain frame, use isotropy to write z_lab in
     terms of R_z_chain + R_perp_chain components and analytically
     marginalise the cone.

If criteria 1–3 hold, the result feeds derivation/03 directly — no further
constants need to be measured.

## What this step does NOT do

- It does NOT convolve two P_z's into K2D(l). That's derivation/03.
- It does NOT yet handle the receptor + ligand asymmetry (different
  flexibility classes meeting at a complex). Derivation/03 will join them
  via two independent P_z draws.
- It does NOT make any small-angle approximation on the anchor cone — the
  cone density is sampled exactly from (intent.1) including the sin θ
  Jacobian.

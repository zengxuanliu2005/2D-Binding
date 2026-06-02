---
type: derivation
status: accepted
date: 2026-06-01
summary: 01_setup — Geometry and the anchor-cone sampler (02_z_marginal)
derivation_folder: 02_z_marginal
step: setup
inputs: derivation/01 endpoints + bond convention; CLAUDE.md kBT = 1.1 ε
outputs: equations (1.1)–(1.7); ready for code mapping in 04_numerics.md
agent_read_when:
  - working on 02_z_marginal or its successor
  - need to know the setup of this derivation step
---

# 01_setup — Geometry and the anchor-cone sampler

## Coordinate system

- Lab z-axis points away from the membrane into the inter-membrane gap.
- The anchor (chain head bead) sits at z = 0.
- The chain extends into the gap, ending at the binding bead at the lab
  position R_lab = (x_lab, y_lab, z_lab).

In derivation/01, we sampled chain end-to-end vectors with the first bond
along +z (call this the **chain frame**). Let R_chain = (x_c, y_c, z_c)
denote the resulting end-to-end vector in that frame.

By construction, the chain-frame distribution of R is rotationally
invariant about the z_c axis (we sampled the per-bond azimuth φ_i
uniformly in derivation/01).

## What "anchor cone" means physically

The first bond in MD is not perfectly aligned with the lab z-axis; it
fluctuates by a small angle θ_anchor due to the membrane anchor's
harmonic restoring potential. We measured the effective stiffness
k_a = 255 ε/rad² in stage_essay §4.4. Converting to kBT units:

  κ_anchor ≡ k_a / k_B T = 255 / 1.1 = 231.8 rad⁻²                  (1.1)

(stage_essay §4.4 confirms this is the same for K100/K10/K01 — flexibility
varies along the chain, not at the anchor.)

The Boltzmann tilt distribution including the 3-D sin θ Jacobian is

  p(θ) dθ ∝ exp(-κ_anchor θ² / 2) sin θ dθ      θ ∈ [0, π]           (1.2)

This is sharply peaked at small θ (κ_anchor σ_θ² ≈ 1):

  σ_θ ≈ √(1 / κ_anchor) = 0.0657 rad ≈ 3.76°                        (1.3)

The azimuth φ_anchor is uniform on [0, 2π).

## Sampler — direct from (1.2)

The standard small-angle approximation says θ_anchor² is approximately
χ²-distributed with 2 d.o.f. (1 angle, scaled), but exact sampling is just
as cheap. Since κ_anchor σ_θ² ≪ 1 we have:

- p(θ²) ∝ exp(-κ_anchor θ² / 2) · θ for θ small,
- → θ² is Exponential(λ = κ_anchor / 2),
- → θ = √(−(2/κ_anchor) ln u), u ∼ Uniform(0, 1)                    (1.4)

For our κ_anchor = 232, θ_max sampled is typically ≤ 5 σ_θ ≈ 0.3 rad ≈ 17°
— well within the small-angle regime. We sample (1.4) directly. (No
rejection needed; no numerical issues.)

## Rotating R_chain → R_lab

Given a sampled anchor direction t̂_anchor with polar (θ_anchor, φ_anchor)
in the lab frame, the chain frame z-axis was supposed to be +z (lab) but
is actually t̂_anchor. So we rotate R_chain by the rotation R̂ that takes
ẑ_lab → t̂_anchor.

Equivalently: R_lab = R̂ R_chain. For the **z-component only**, the lab
z is

  z_lab = R_chain · t̂_anchor                                        (1.5)

because in the chain frame the chain z-axis IS t̂_anchor in lab; so the
projection of R_chain onto t̂_anchor in the chain frame equals the lab z.

Writing t̂_anchor in lab as (sin θ_a cos φ_a, sin θ_a sin φ_a, cos θ_a):

  z_lab = x_c · sin θ_a cos φ_a + y_c · sin θ_a sin φ_a + z_c · cos θ_a
                                                                    (1.6)

Define R_perp,chain = √(x_c² + y_c²) and the chain-frame azimuth of the
in-plane component, φ_c = atan2(y_c, x_c). Then (1.6) simplifies:

  z_lab = R_perp,chain · sin θ_a · cos(φ_c − φ_a) + z_c · cos θ_a   (1.7)

This form is what `scripts/k2d_l_wlc_theory.py::apply_anchor_cone` uses —
it samples (θ_a, φ_a) independently per MC chain, then applies (1.7).

## Limiting cases of (1.7)

| limit | z_lab |
|---|---|
| Rigid (R_chain ≈ Lc ẑ_chain, so z_c ≈ Lc, R_perp ≈ 0) | z_lab ≈ Lc cos θ_a |
| Flex  (R_chain isotropic) | (z_c, R_perp) joint sets the variance, anchor adds a small extra tilt |
| k_a → ∞ (no anchor wobble) | θ_a ≡ 0 → z_lab ≡ z_c (chain-frame z) |

## What we output

For each system (rigid/semi/flex) we attach to the existing 200 K
endpoints a parallel array `z_lab` of length 200 K and build the histogram

  P_z(z) = histogram of z_lab on a chosen grid                      (1.8)

Stored as `<label>__z_lab` and `<label>__Pz_centres` / `<label>__Pz_pdf`
in `results/derivation_b2/wlc_z_marginal.npz`.

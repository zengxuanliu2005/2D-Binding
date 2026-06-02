---
type: derivation
status: accepted
date: 2026-06-02
summary: 01_setup — Binding kernel and the convolution (03_k2d_l_kernel)
derivation_folder: 03_k2d_l_kernel
step: setup
inputs: derivation/02 z_lab; raw_tether_partition_k2d.py constants
outputs: equations (1.1)–(1.6); ready for code mapping in 04_numerics.md
agent_read_when:
  - working on 03_k2d_l_kernel or its successor
  - need to know the setup of this derivation step
---

# 01_setup — Binding kernel and the convolution

## Geometry recap

- R membrane at z = 0, R anchor in it. R chain extends into z > 0.
- L membrane at z = l (above the R membrane). L anchor at the same lab z.
- L chain extends into z < l.

The R binding bead z (lab) is `z_R` (sampled from P_z^R via B2.2).
The L binding bead z (lab) is `l − z_L` (because L extends "downward"
from its membrane). By construction both z_R and z_L are non-negative
(small Q1 caveat from 02/05; we truncate negative tail in the pilot).

## Bond-vector z component

The bond is between the R binding bead and the L binding bead. Its
z component is

  dz_bond = z_R_lab − z_L_lab = z_R − (l − z_L) = z_R + z_L − l    (1.1)

A bond CAN form iff the full 3D bond vector (r_xy, dz_bond) is within the
binding kernel acceptance volume.

## Lateral integration → acceptance area v(dz)

The R and L lateral positions x, y are unconstrained (uniform on the
membrane area A_box). So for a given (z_R, z_L, l) only the relative
lateral vector r_xy enters the binding kernel:

  K_bond(r_xy, dz_bond)                                             (1.2)

We integrate over r_xy to get the per-(z_R, z_L) acceptance area:

  v(dz) = ∫₀^∞ K_bond(√(r_xy² + dz²)) · 2π r_xy dr_xy              (1.3)

For the **hard-gate kernel** (radius < rcut, no angular factors):

  K_bond = 1 if |r| < rcut, else 0
  v(dz) = π (rcut² − dz²) for |dz| < rcut, else 0                  (1.4)

This is the analytic form we use in B2.3. The soft-Boltzmann kernel
(from `raw_tether_partition_k2d.py::radial_u_kbt + angle_factor`) gives a
smoother v(dz) but the same qualitative shape; we document the upgrade
path in 05_open_questions.md.

Default rcut (hard gate): **rcut = 1.5 σ = 1.5 nm**, taken from
`raw_tether_partition_k2d.py::HARD_R`.

## Convolution → K2D(l)

The binding constant at membrane separation l is

  K2D(l) = ∫∫ dz_R dz_L P_z^R(z_R) P_z^L(z_L) · v(z_R + z_L − l)   (1.5)

equivalent to a Monte Carlo average

  K2D(l) = ⟨v(z_R + z_L − l)⟩_{(z_R, z_L) ~ P_z^R × P_z^L}         (1.6)

In code we evaluate (1.6) using 200 000 pairs of samples drawn from
B2.2's z_lab arrays (one z_R from system_R, one z_L from system_L).

## Lateral pair density and physical units of K2D

K2D as defined by (1.5) has units of nm² — it is the equilibrium 2D
binding constant in the dimensionless form K2D = ρ_RL / (ρ_R · ρ_L)
where ρ is areal number density. Our v(dz) carries units of nm² because
of the 2π r_xy dr_xy integration; the P_z integrals are dimensionless
(each P_z is 1/nm and dz is nm, giving dimensionless).

So K2D(l) numerically equals the per-pair lateral acceptance area
averaged over chain endpoint configurations at membrane gap l. The
absolute scale connects to the senior's measured K2D,max via a
prefactor we don't try to compute analytically — the SHAPE of K2D(l)
is what matters for σ_K2D and hence ξ_RL.

## Quantities derivation 04 will need

From the K2D(l) curve we compute:

  K2D,max = max_l K2D(l)                                           (1.7)
  l*      = arg-max l                                              (1.8)
  Z       = ∫ K2D(l) dl                                            (1.9)
  ⟨l⟩     = (1/Z) ∫ l K2D(l) dl                                    (1.10)
  σ_K2D²  = (1/Z) ∫ (l − ⟨l⟩)² K2D(l) dl                          (1.11)

(1.11) is what derivation/04 calls ξ_RL_predicted.

## l-grid choice

K2D(l) is non-zero only when at least one (z_R, z_L) pair has
|z_R + z_L − l| < rcut. The mass of P_z is on z ∈ [0, ~Lc] for each
chain, so K2D(l) is non-zero for l ∈ [−rcut, 2·Lc + rcut] = [−1.5, 25.5]
nm. We use a uniform grid l ∈ [0, 26] nm with Δl = 0.1 nm (260 grid
points) — fine enough to resolve the rigid system's σ_K2D ≈ 0.7 nm peak
while covering the flex tail comfortably.

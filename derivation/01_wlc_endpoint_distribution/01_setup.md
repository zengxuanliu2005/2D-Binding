---
type: derivation
status: accepted
date: 2026-06-01
summary: 01_setup — Discrete WLC model and units (01_wlc_endpoint_distribution)
derivation_folder: 01_wlc_endpoint_distribution
step: setup
inputs: ref/nvt-md.py (force-field reference); CLAUDE.md unit conventions
outputs: discrete bending Hamiltonian and parameter conversions (1.1)–(1.4)
agent_read_when:
  - working on 01_wlc_endpoint_distribution or its successor
  - need to know the setup of this derivation step
---

# 01_setup — Discrete WLC model and units

## Coordinate system + units

- All lengths in **nm = σ** (project convention: σ = 1 nm).
- Energies in **kBT**. The simulation uses kBT = 1.1 ε; we divide all
  ε-quantities by 1.1 when converting.
- Cartesian (x, y, z) with z = chain growth direction. The chain starts at
  the origin with the first bond along +z (this matches the membrane-anchor
  geometry handled in derivation/02; here we keep things isotropic in 3D).

## Discrete chain

We discretise the chain into N segments of bond length b:

  Lc = N · b                                                       (1.1)

Default for our system: b = 1.0 σ (HARM r₀ = 1.0 σ for protein bonds per
CLAUDE.md unit table) and Lc = 12 σ → N = 12.

Each segment is represented by a unit tangent vector t̂_i for i = 1, …, N.
The end-to-end vector is

  R = b · Σᵢ t̂_i                                                  (1.2)

## Bending Hamiltonian

The cost of bending between consecutive segments is the standard discrete
WLC form (Doi–Edwards Eq. 8.5 with our notation):

  U_bend(θ_i) / kBT = κ · (1 - cos θ_i)                            (1.3)

where θ_i is the angle between t̂_i and t̂_{i+1}, and κ is the dimensionless
bending stiffness in units of kBT.

The continuous persistence length lp relates to κ through the well-known
discrete WLC mapping (Flory chain statistics):

  ⟨cos θ⟩ = coth(κ) - 1/κ          ← Langevin function L(κ)        (1.4a)
  lp / b = -1 / ln⟨cos θ⟩                                          (1.4b)

For κ ≫ 1 (rigid): L(κ) ≈ 1 - 1/κ ⇒ ⟨cos θ⟩ ≈ 1 - 1/κ ⇒ lp/b ≈ κ.
For κ ≪ 1 (flexible): L(κ) ≈ κ/3 ⇒ lp/b ≈ -1/ln(κ/3) → 0.

Inverting (1.4) gives the κ corresponding to each system's lp:

| system | lp (nm) | lp/b | κ (numerical solve of 1.4) |
|---|---:|---:|---:|
| rigid (K100) | 84.6  | 84.6 | ≈ 85.1 |
| semi  (K10)  |  8.18 |  8.18 | ≈ 8.69 |
| flex  (K01)  |  1.14 |  1.14 | ≈ 1.81 |

(The numerical κ comes from `scripts/k2d_l_wlc_theory.py::kappa_from_lp`.)

## Boltzmann weight on the bond-angle distribution

For each new bond direction we sample θ_i (relative to previous bond) and
φ_i (azimuth). With the Hamiltonian (1.3), the joint distribution is

  p(θ, φ) sin θ dθ dφ ∝ exp(-κ (1 - cos θ)) sin θ dθ dφ            (1.5)

Marginalising φ (uniform on [0, 2π)) and substituting u = cos θ ∈ [-1, 1]:

  p(u) du = (κ / [exp(κ) - exp(-κ)]) · exp(κ u) du                 (1.6)

This is the (truncated) exponential we sample from. Code: see
`scripts/k2d_l_wlc_theory.py::sample_cos_theta`.

## Rotating frame: how t̂_{i+1} is built from t̂_i + (θ, φ)

We need a rotation matrix that takes t̂_i to t̂_{i+1} given local polar
angles (θ, φ).

1. In a local frame where t̂_i = ẑ_local, the next tangent has Cartesian
   coordinates (sin θ cos φ, sin θ sin φ, cos θ).
2. Build an orthonormal triad (ê₁, ê₂, t̂_i) in the lab frame. ê₁ and ê₂
   span the plane perpendicular to t̂_i; their azimuthal orientation is
   arbitrary (we choose ê₁ via Gram-Schmidt against the lab ẑ when
   |t̂_i × ẑ| > 1e-8, otherwise against lab x̂).
3. The lab-frame next tangent is

   t̂_{i+1} = sin θ cos φ · ê₁ + sin θ sin φ · ê₂ + cos θ · t̂_i   (1.7)

Code: `scripts/k2d_l_wlc_theory.py::rotate_tangent`.

## What "P(R)" means

Two related distributions:

- **Radial probability density**: P_R(R) dR = probability that |R| ∈ [R, R+dR],
  4π R² weight already absorbed. Used in derivation/02 for the z-marginal.
- **Cartesian density**: G(R⃗) d³R = probability of the end-to-end vector.
  Spherically symmetric (in absence of external field), so P_R(R) = 4π R² G(R).

This file derives the WLC Hamiltonian; the resulting P_R(R) is computed
numerically from MC samples in `scripts/k2d_l_wlc_theory.py` and analysed
in `03_result.md`.

## Limiting cases this discrete model captures

| limit | what the discrete WLC does |
|---|---|
| κ → ∞ (rigid) | every θ_i ≈ 0; chain is straight; R ≈ N · b · ẑ |
| κ → 0 (flexible) | each θ_i uniform on sphere; freely-jointed chain; ⟨R²⟩ = N b² |
| intermediate | smooth interpolation; matches WLC continuum at lp/b ≫ 1 limit |

The intermediate WLC continuum has ⟨R²⟩ = 2 lp Lc (1 - (lp/Lc)(1 - e^{-Lc/lp})).
For our discrete chain with b = 1 σ, the discrete ⟨R²⟩ differs from the
continuum result by O(b/lp); for our three systems b/lp = 1/84.6, 1/8.18, 1/1.14,
so the rigid case is exact to 1% and flex is exact to ~12% — acceptable for
B2 where we ultimately measure against MD data with similar resolution.

(`04_numerics.md` reports the exact ⟨R²⟩ from MC for each system vs the
continuum formula and vs measured Re.)

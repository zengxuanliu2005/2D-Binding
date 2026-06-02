---
type: decision
status: accepted
adr_id: 003
date: 2026-06-02
summary: B2.3 K2D(l) uses a hard-cutoff binding kernel (radius < rcut, no angular factor) instead of the soft Boltzmann kernel
agent_read_when:
  - modifying derivation/03 or scripts/k2d_l_wlc_theory.py::hard_lateral_acceptance
  - asking why B2.3 absolute K2D scale is off from raw_tether_partition
  - considering swapping in the soft Boltzmann kernel
alternatives_considered:
  - "hard cutoff π (rcut² − dz²) with rcut = 1.5 nm (HARD_R)"
  - "soft Boltzmann from raw_tether_partition_k2d.py::radial_u_kbt + angle_factor"
  - "delta-function kernel (in z) + lateral integration analytic"
expected_revision_trigger: cluster slab K2D(l) shape disagrees with B2.3 shape → likely culprit is kernel softness
related_sessions: [session5_b2_1_2_3]
related_calibration: [b2_vs_measured_xi_rl]
---

# ADR 003 — Hard-gate kernel for B2.3 first cut

## Context

B2.3 needs a binding-kernel acceptance function v(dz) for the convolution
K2D(l) = ⟨v(z_R + z_L − l)⟩. Two natural choices:

(A) **Hard gate** (HARD_R = 1.5 nm in `raw_tether_partition_k2d.py`):
    v(dz) = π (rcut² − dz²) for |dz| < rcut, else 0.

(B) **Soft Boltzmann** (RL_SIGMA, RL_EPSILON, ANGLE_K, ANGLE0_DEG):
    v(dz) involves an integral of exp(−U_bind/kBT) − 1 over the lateral
    disk, with U_bind including radial LJ and two angle factors.

## Decision

Use **(A) hard gate** for B2.3.

## Rationale

- Closed-form v(dz) — no inner integration loop.
- Computational cost is ~1000× lower than the soft kernel (no angle
  factor lookups, no Boltzmann sum).
- B2.3 is about the **shape** of K2D(l), not the absolute K2D scale.
  The shape is dominated by the chain distribution P_z(z); kernel softness
  contributes O(rcut/√5 ≈ 0.67 nm) to σ_K2D in quadrature — same order
  as the kernel-conditional contribution itself.
- Upgrade path is straightforward: replace `hard_lateral_acceptance` with
  a `soft_lateral_acceptance` that calls existing kernel functions. ≤ 1 hour.

## Consequences

- σ_K2D over-prediction in B2.3 has 3 components (derivation/03 §3.3):
  (a) chain σ_z too wide, (b) kernel adds 0.67 nm in quadrature,
  (c) ξ_RL ≠ σ_K2D literally.
- (b) is the kernel-attributable piece (~30 % of the 2× over-prediction).
- We document this in `derivation/03_k2d_l_kernel/05_open_questions.md`
  Q4 as a planned future improvement.

## Revision plan

Trigger: if cluster slab K2D(l) curves return and the shape disagreement
exceeds 10 % RMSE after normalising K2D,max:
1. Add `soft_lateral_acceptance(dz, rcut, eps, angle_K, angle0)` that
   imports kernel functions from `raw_tether_partition_k2d.py`.
2. Rerun derivation/03 with `kernel="soft"` flag.
3. Compare hard vs soft σ_K2D for all 3 systems.
4. If soft brings σ_K2D within 10 % of measured ξ_RL, supersede this ADR
   with 003b and mark this `superseded-by-003b`.

## Files affected

- `scripts/k2d_l_wlc_theory.py::hard_lateral_acceptance` (line ~432)
- `derivation/03_k2d_l_kernel/01_setup.md` (1.4 equation)
- `derivation/03_k2d_l_kernel/03_result.md` (rcut = 1.5 nm choice)

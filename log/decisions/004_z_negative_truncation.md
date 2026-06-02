---
type: decision
status: accepted
adr_id: 004
date: 2026-06-02
summary: Drop WLC samples with z < 0 in B2.3 K2D(l) convolution (unphysical chain-through-membrane configurations)
agent_read_when:
  - working on B2.3 K2D(l) convolution
  - investigating the σ_K2D ordering reversal (semi > flex)
  - implementing reflection BC as an alternative
alternatives_considered:
  - "truncate: drop samples with z < 0 and renormalise (simplest)"
  - "reflect: chains that would dip below z=0 bounce back (most physical)"
  - "keep: allow z < 0 in the convolution (most permissive, lets K2D extend into negative l)"
expected_revision_trigger: cluster slab K2D(l) shape diverges from B2.3 shape for flex (most impacted by truncation)
related_sessions: [session5_b2_1_2_3]
related_calibration: [b2_vs_measured_xi_rl]
---

# ADR 004 — Truncate z < 0 in B2.3 K2D(l) convolution

## Context

The WLC MC in B2.1 + B2.2 produces lab-frame z_lab values for the chain
endpoint. For rigid (κ_chain = 85) virtually all samples have z > 0. For
flex (κ_chain = 1.4), ~40 % of samples have z < 0 — chain configurations
where the binding bead has folded back below the anchor plane (membrane).

These z < 0 configurations are **unphysical** in the actual membrane
geometry: the chain cannot pass through the membrane to which it's
anchored.

If we include z < 0 samples in K2D(l) convolution, K2D extends to
negative l (membranes overlap), which is also unphysical.

## Decision

**Drop z < 0 samples** before B2.3 convolution. Implemented via
`truncate_negative=True` default in `k2d_l_curve()`.

## Rationale

- Simplest membrane-impermeable boundary condition.
- Implementation is a 1-line filter (`z_R_lab[z_R_lab >= 0]`).
- The senior's S17-S21 "end-volume" framework also implicitly assumes
  chain stays in the gap, so we match her physical assumption.

## Consequences

- B2.3 σ_K2D ordering becomes rigid (1.42) < flex (3.91) < semi (5.45)
  — NOT the naïvely expected rigid < semi < flex monotone.
- Reason: flex P_z is symmetric and broad; truncation aggressively
  compresses its variance. Semi is asymmetric (peaked above z=0) and
  loses only ~5 % of mass to truncation.
- This is a real concern documented in
  `derivation/03_k2d_l_kernel/05_open_questions.md` Q2.
- Measured ξ_RL has semi ≈ flex (2.08 vs 2.25 nm), so the ordering
  reversal is borderline even in experiment.

## Revision plan

If cluster slab K2D(l) for flex disagrees with B2.3 by > 15 % in the
left tail (l near 0):
1. Implement reflection BC: chains that step below z = 0 in the MC are
   reflected back. Modifies `WLCChain.sample_endpoints` to project each
   bond's tip back to z ≥ 0 if negative. Adds ~10 lines, ~2x compute.
2. Compare truncation vs reflection vs un-truncated for flex.
3. If reflection brings flex σ_K2D into agreement, supersede this ADR.

## Files affected

- `scripts/k2d_l_wlc_theory.py::k2d_l_curve` (truncate_negative parameter)
- `derivation/03_k2d_l_kernel/04_numerics.md` ("Why truncate z < 0" section)
- `derivation/03_k2d_l_kernel/05_open_questions.md` (Q2, Q5)

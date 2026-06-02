---
type: derivation
status: accepted
date: 2026-06-02
summary: 05_open_questions — caveats and next-round actions (02_z_marginal)
derivation_folder: 02_z_marginal
step: open_questions
inputs: 03_result.md sanity tables; 04_numerics.md
outputs: short punch list for derivation/03 and the off-site collaborator-conversation queue
agent_read_when:
  - working on 02_z_marginal or its successor
  - need to know the open_questions of this derivation step
---

> **Loop 2 revision protocol**: see `log/decisions/007_loop2_b_revision_playbook.md` for the explicit decision tree mapping off-site data observations → which Q here gets closed / refined and which calibration row to flip.

# 05_open_questions — caveats and next-round actions

## Q1 — z < 0 contributions (chain pointing into the membrane)

**Symptom**. For the flex system, ⟨z⟩ = 1.71 nm and σ_z = 2.79 nm. So a
non-negligible tail of z_lab is negative, meaning the binding bead has
hooked back below the anchor plane. These configurations are unphysical
in the actual system (the bead can't penetrate the membrane).

**Why it matters**. Derivation/03 will convolve two P_z's to get K2D(l).
If we use the raw P_z including z < 0 we'll spuriously contribute to
K2D for very short separations.

**Resolution plan (derivation/03)**.
- Either (a) truncate z_lab > 0 and renormalise, or (b) keep the full
  distribution but only evaluate K2D(l) for l > 0 where the binding kernel
  is physically nonzero.
- (a) is simpler and matches the the off-site S17-S21 "end-volume" framework
  which implicitly assumes the chain stays in the gap. Plan to use (a).

## Q2 — Lc convention (inherited from derivation/01)

Same Q1 from `derivation/01/05_open_questions.md` applies here: if the
off-site collaborator tells us her Re comes from the full chain (Lc ≈ 24 nm) not ecto
only (Lc = 12 nm), the rigid + semi MC numbers shift, but the formalism
is unchanged (just rerun with the new Lc).

## Q3 — Anchor cone azimuth correlation with chain frame

In `apply_anchor_cone`, the chain-frame azimuth φ_c (of R_perp) and the
anchor-frame azimuth φ_a are sampled independently. This is correct if
the chain bend direction and the membrane anchor wobble direction are
physically uncorrelated — which is true to leading order (the chain
bend φ is set by thermal fluctuations of bond angles long after the
first bond was placed). But strictly: for an MD trajectory, there could
be small correlations if the wobble of bond 1 couples to bond 2's bend
direction.

**Resolution**. Measure this from `chain_coords.npz` in a future round:
extract the first-bond direction angle φ₁ and the chain-tip azimuth φ_tip,
compute ⟨cos(φ_tip − φ₁)⟩. If < 0.1 we ignore the correlation.

Not blocking for derivation/03.

## Q4 — k_a effective vs harmonic approximation

We treat the anchor potential as exactly U = (k_a / 2) θ² (small angle
quadratic). For our σ_θ = 3.8° the quadratic approximation is good to
better than 0.5 %. But if for some other system the effective k_a is
much smaller (σ_θ > 15°), the small-angle sampler in (1.4) breaks.

**Resolution**. Add a switch in `sample_anchor_theta` that falls back to
rejection sampling for κ_a < 50. Not needed for our current 3 systems.

## Q5 — Higher-moment validation

We verified ⟨z⟩ and σ_z. The full P_z(z) shape (skewness, kurtosis) is
not explicitly checked. In principle K2D(l) is sensitive to the full
shape, not just two moments.

**Resolution**. Derivation/03 will produce K2D(l) using the full P_z
histogram, so the shape is implicitly carried through. If derivation/04
ξ_RL predictions miss measured ξ_RL by > 15 %, the first thing to check
is whether the P_z shape near the peak is consistent — add a higher-
moment table at that point.

## Status carry-forward

Three acceptance criteria from 00_intent.md:
1. **Rigid limit reproduces analytic Lc·cos θ_a** — ✓ (Sanity A, 3.1)
2. **Flex limit σ_z² ≈ ⟨R²⟩/3 within 10 %** — ✓ (flex σ_z = 2.79 vs 2.87 = 3 %)
3. **Two independent methods agree to < 2 %** — ✓ (Sanity B + production
    table 3.3 ⟨z⟩ vs ⟨z_c⟩·⟨cos θ_a⟩)

All three green. Move on to derivation/03.

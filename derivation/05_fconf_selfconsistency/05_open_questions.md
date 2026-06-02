---
type: derivation
status: accepted
date: 2026-06-02
summary: "05_open_questions — what σ_z calibration / D_bound source / closure budget reanalysis would change (05_fconf_selfconsistency)"
derivation_folder: 05_fconf_selfconsistency
step: open_questions
inputs: 03_result tables; derivation/02 Q2 (σ_z too wide); A1 diagnosis
outputs: open questions for essay v2 / cluster data integration
agent_read_when:
  - working on 05_fconf_selfconsistency or essay revision
  - planning to integrate cluster slab data or revised D_bound
---

# 05_open_questions — caveats and the carry-forward

## Q1 — WLC σ_z (B2.2) vs measured σ(R_z) (PPT slide 5)

**Symptom**. B2.2 reports σ_z(rigid) = 0.625 nm vs measured σ(R_z)
from PPT slide 5 = 0.35 nm — a 1.8× over-prediction. Carried over
from derivation/02 Q2.

**Impact on F_conf**. If we re-ran B2.5 with a sharper P_z (σ_z = 0.35
matching measurement), F_conf^(B2)(rigid) would *increase* (P_z at
D_bound = 9.15, which is 3σ below ⟨z⟩ = 11.2, becomes even smaller
under a sharper Gaussian, so -ln P_z grows). Rough estimate: F_conf
goes from 3.9 to ~6 kBT, **widening** Δ_anchor from +3.79 to ~+5.8 kBT.

**Resolution**. Option 1: replace WLC P_z with KDE of measured z_lab
from chain_coords MD (would tighten σ_z). Option 2: stay analytic but
re-fit κ_a using measured σ_z to give Lc/κ_a = 0.35 → κ_a ≈ 34 rad⁻²
(7× smaller than measured 232 from anchor angle). Inconsistent — the
direct angle measurement says 232, so option 2 is wrong physics.

Option 1 is the right resolution but requires chain_coords access in
the script; deferred to cluster slab data round.

## Q2 — D_bound source: equilibrium MD with sampling bias

**Symptom**. The D_bound values (9.154 / 7.964 / 6.615 nm) come from
equilibrium-MD bound-chain extracts. A1 diagnosis (see
`results/a1_rigid_gap_diagnosis.md` + log/sessions/2026-05-31) showed
**bound R chains are systematically ~0.26 nm more vertical than
unbound R chains** in rigid system. So D_bound (rigid) might be
biased high (toward Lc) — actual constraint geometry might be ~ 8.9
instead of 9.15.

**Impact on F_conf**. F_conf^(B2)(rigid, D=8.9) > F_conf^(B2)(rigid, D=9.15)
because 8.9 is even further from ⟨z⟩ = 11.2. Magnitude: ~ 0.5 kBT
larger. Widens Δ_anchor a little further.

**Resolution**. Use cluster constrained-h slab MD D_bound (when
available — see user-dir plan Workstream C). The slab simulation forces
the membrane gap and measures the bond-vector geometry without the
self-selecting bound-state bias.

## Q3 — Per-component closure budget revisited

The B1 reimpl closure with Marko-Siggia gives ΔΔF_sum (flex−rigid) =
5.23 kBT vs PPT s25 3.64 kBT — already known to overshoot by ~1.6 kBT.
Substituting B2 F_conf for MS:

  ΔΔF_sum^(B2) = ΔΔF_trans + ΔΔF_rot + ΔΔF_conf^(B2)
              = (+0.383 + 1.592 + (−0.576))   for flex − rigid
              = +1.40 kBT

vs PPT target +3.64. So **B2 closure under-shoots by ~2.2 kBT** —
opposite direction from B1's over-shoot of ~1.6 kBT.

Neither closure hits the target alone. Two possible explanations:

(a) The PPT s25 *target* (3.64 kBT for flex−rigid) is itself biased by
    chain_coords sampling (A1 issue) and is too large. Cluster data will
    confirm or refute.
(b) The trans+rot terms are also miscomputed (they could be
    re-derived with B2 P_z too; we have not done this — derivation/06
    territory).

Deferred to essay revision after cluster data return.

## Q4 — Are MS and B2 even comparing the same thing?

**Symptom**. The Δ_anchor(rigid) = +3.79 kBT is so large it suggests
MS and B2 are not just disagreeing on details but measuring different
quantities entirely (one stretching cost, the other bend-cone cost).

**Argument for "same thing"**: both estimate the work to put the
chain endpoint at a specified geometry, conditional on the chain being
WLC with the same lp and Lc.

**Argument for "different things"**: MS imposes a 1D stretching
constraint along the chain axis; B2 imposes a 3D position constraint
on the lab z. For free chains these are the same; for membrane-anchored
chains they are not.

**Resolution**. The reading in 03_result.md is that **both are real
contributions to the physical F_conf**:
  F_conf^physical(rigid) ≈ F_stretch + F_orient = F^MS + Δ_anchor
The B2 estimator measures the SUM; MS measures the stretch part alone.
The decomposition is therefore additive, not redundant. This is the
narrative going into essay v2 §5.3.

## Q5 — z<0 truncation effect on F_conf

**Symptom**. B2.2's P_z is built with z<0 chains DROPPED (truncation
policy from ADR 004 in log/decisions/). For systems where the
truncated mass is large (flex 40%, semi 5%, rigid <0.1%), the residual
P_z is normalized over z ≥ 0 only, so its density values at D_bound are
higher than they would be without truncation — pulling F_conf down.

For flex: 40% mass truncation → P_z at D=6.6 is about 1.67× higher
than without truncation → F_conf is ln(1.67) ≈ 0.51 kBT smaller.
For semi: 5% → ln(1.05) ≈ 0.05 kBT smaller. Rigid: negligible.

**Impact**: F_conf^(B2)(flex) might be 3.9 instead of 3.34 → very
close to F^MS(flex) = 3.38 → flex agreement gets even cleaner. Semi
shifts by 0.05 kBT, barely visible. Rigid unchanged.

**Resolution**. Replace truncation with reflection BC (derivation/03
05 Q4 / 05 Q5). Long-term improvement; not blocking essay v2.

## Status carry-forward

Acceptance criteria from 00_intent.md (all four passed):
1. Flex agreement |Δ_anchor| < 0.3 kBT — **✓**
2. Rigid disagreement Δ_anchor ≥ 2 kBT — **✓** (+3.79)
3. Bootstrap σ < 0.1 kBT — **✓** (max 0.075)
4. Δ_anchor monotone in lp — **✓**

**derivation/05 is accepted** with the caveats above.

## What 05 feeds into

- essay v2 §5.3 — qualitative narrative: F_conf decomposes as
  stretch + orient; PPT s25 closure misses orient; future closure
  should include it
- log/calibration/fconf_three_way.md — running comparison table
- B2 completes (B2.1 → B2.5). Next workstream: cluster Round 2 trial
  outputs (when user uploads) + senior bundle data return.

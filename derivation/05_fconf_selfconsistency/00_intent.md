---
type: derivation
status: accepted
date: 2026-06-02
summary: "00_intent — Evaluate F_conf via -ln P_z(D_bound) and compare to Marko-Siggia (B1) + PPT s25, isolating the anchor-cone surcharge (05_fconf_selfconsistency)"
derivation_folder: 05_fconf_selfconsistency
step: intent
inputs: derivation/02 P_z(z; lp, Lc, k_a); results/closure_wlc_three_term.md (D_bound + B1 MS F_conf); PPT s25 totals
outputs: ΔΔF_conf^(B2) per pair + cross-method table + anchor-cone surcharge per system
agent_read_when:
  - working on 05_fconf_selfconsistency
  - need to understand why MS and B2 disagree on rigid F_conf
agent_skip_when:
  - only need the headline number (read 03_result.md)
---

# 00_intent — F_conf via -ln P_z(D_bound) self-consistency

## What this step delivers

For each same-system R-L pair we compute

  F_conf^(B2)(D) = −ln P_z(D; lp, Lc, k_a)                          (00.1)

at the measured bound-chain vertical reach D_bound (from
`results/closure_wlc_three_term.md`, taken straight out of the off-site
chain_coords MD extracts). Then we form the cross-system pair table

  ΔΔF_conf^(B2)(A − B) = F^(B2)_A(D_A) − F^(B2)_B(D_B)              (00.2)

and compare against three reference values for each of the three pairs:

- ΔΔF_conf^(MS, B1) — Marko-Siggia (chain stretching only), from B1
- ΔΔF_sum^(PPT s25) — the off-site 3-term closure total (trans + rot + MS)

The headline output is the **anchor-cone surcharge** per system:

  Δ_anchor^(label) = F_conf^(B2)(label) − F_conf^(MS)(label)        (00.3)

which isolates what Marko-Siggia misses — namely, the entropic cost of
forcing the chain endpoint to land at a specific z-coordinate when the
chain's other end is anchored to a membrane via a stiff angular cone
(κ_a ≈ 232 rad⁻²).

## Why this step matters

The B1 reimplementation of PPT s25 (commit `3dee6f0`) used Marko-Siggia
integrated WLC for F_conf, with D_bound from our own MD extracts and
Lc = 12 nm from CLAUDE.md. The resulting ΔΔF_sum gave 5.23 / 2.05 /
-3.18 kBT, versus the PPT's reported 3.64 / 2.47 / -1.18 kBT — a 1.5
-2 kBT shift per pair attributed to "system-specific implicit L_c"
the off-site collaborator may have used (essay §4.6 / B1 commit message).

B2.5 tests an independent angle on the same F_conf: use B2's WLC z-marginal P_z directly. If the two estimators agree, the PPT
discrepancy is explained by L_c / data-set differences alone. If they
disagree, the difference reveals which physics MS captures and which
it does not (specifically, the anchor cone).

Spoiler: MS and B2.5 agree on flex (Δ = -0.04 kBT) but disagree on
rigid (Δ = +3.79 kBT). The pattern is unambiguous and mechanistic.

## What this step does NOT do

- It does NOT predict the binding ΔΔF (= K2D ratio target). It only
  predicts the conformational component F_conf.
- It does NOT modify B2.2's P_z arrays — it consumes them via histogram +
  linear interpolation.
- It does NOT propose a "winner" between MS and B2 for the absolute
  F_conf. Both have known biases — MS misses the anchor cone, B2 has
  σ_z too wide (derivation/02 Q2). The point is to QUANTIFY the
  disagreement and locate it physically.
- It does NOT touch the L_c question (whether off-site collaborator used Lc=12 or
  Lc=25). That investigation lives in log/sessions/2026-06-02_session5_b2_1_2_3.md
  and is awaiting the collaborator's reply on PPT s25 conventions.

## Acceptance criteria

1. **Flex agreement** — for the system where the anchor cone is a
   small perturbation (flex, lp ≪ L_chain, chain orientation freely
   sampling the cone), B2 and MS should agree to within 0.3 kBT.
2. **Rigid disagreement** — for the system where the anchor cone
   dominates (rigid, σ_z ≈ Lc/κ_a small), B2 should exceed MS by
   ≥ 2 kBT (because MS treats chain as 3D-free).
3. **Bootstrap σ** — frame-resample on 200 K z_lab samples gives σ
   on F_conf < 0.1 kBT per system.
4. **Sign monotone with lp** — the anchor-cone surcharge
   Δ_anchor(lp) = F_conf^(B2) − F_conf^(MS) should be a monotone
   decreasing function of lp (largest for rigid, smallest for flex).

Criterion 1, 2, 4 are pass conditions in 03_result.md.

## What B2.5 feeds into

- essay v2 §5.3 — qualitative narrative "F_conf has two contributions
  (chain stretch + anchor cone); MS captures only the former; the
  decomposition explains why PPT s25 closure misses ~ 2 kBT on
  semi-rigid pair specifically"
- log/calibration/fconf_three_way.md (new) — running table comparing
  MS / B2 / PPT s25 across future revisions (Lc=25, soft kernel, etc.)
- Conflict Map S5/S6 in user-dir plan — if cluster slab K2D(l) data
  arrives, the F_conf comparison can be re-anchored to slab-measured
  D_bound, decoupling from equilibrium-MD sample bias (Workstream A1)

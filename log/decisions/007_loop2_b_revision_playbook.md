---
type: decision
status: accepted
adr_id: 007
date: 2026-06-02
summary: "Loop 2 protocol: for each off-site data observation, the playbook specifies which derivation step / open_question / calibration row to update — explicit decision tree, no ambiguity"
agent_read_when:
  - cluster/outputs/<date>_round<N>/ just received the off-site distilled tarball
  - writing cluster/results/<date>_round<N>_analysis.md and need to know the B-revision impact
  - cluster slab MD K2D(l) data lands and we need to map it to B2 revisions
  - calibration table action_trigger fires and asks "which scenario is this?"
alternatives_considered:
  - "leave the mapping implicit (Conflict Map S1-S8 in user-dir plan + scattered 'what would resolve' notes in each calibration table) — rejected because requires reading 3+ files to decide one action"
  - "encode as a runnable Python script — rejected because the decision tree has too much human judgment (e.g., 'are these numbers close enough to count as S1?')"
  - "fold into each derivation/0X/05_open_questions.md — rejected because then the mapping is scattered, not centralised"
expected_revision_trigger: "if a 9th Conflict Map scenario emerges OR if the actions per scenario are found insufficient (e.g., S3 resolution turns out to require multiple downstream updates we didn't list)"
related_sessions: [session7]  # the session that creates this ADR
related_calibration: [b2_vs_measured_xi_rl, fconf_three_way, closure_methods_consensus, b2_chain_completeness]
---

# ADR 007 — Loop 2 → B-revision playbook

## Context

Loop 2 of the cluster double-loop (ADR 005) goes: the off-site collaborator runs the bundle on
her full data → distilled outputs return → we land them in
`cluster/outputs/<date>_round<N>/` → we write
`cluster/results/<date>_round<N>_analysis.md`.

The previous Session 6c established a clean analysis template (vs s001 diff,
"§0 hypothesis CONFIRMED/REJECTED") but did NOT crystallize the connection to
**B-derivation revision**. The Conflict Map S1-S8 (in the user-dir plan) and
the "what would resolve" sections of `log/calibration/*.md` together define
the mapping, but reading 3+ files to decide one action is friction.

ADR 007 consolidates the mapping. For each off-site data observation, ONE
table row + a short detail block specifies:
- Which derivation step's open_question gets closed (or opened anew)
- Which calibration table row to flip and to what value
- Which session log slug to write
- Any downstream re-runs needed (e.g., rerun B2.4 with new σ_z)

## Decision

Adopt the playbook below as the canonical Loop 2 protocol. Every
`cluster/results/<date>_round<N>_analysis.md` MUST include a "B-revision
impact" section structured as the playbook table (see template in
`cluster/results/README.md`, updated as part of this ADR's adoption).

## Quick-reference table (which scenario, which actions)

| Conflict-Map scenario | Trigger field (off-site full-data results) | Primary derivation update | Calibration row to flip | Open-question to close | Re-run? |
|---|---|---|---|---|---|
| **S1** Off-site full-data results ≈ PPT s25 (3.64/2.47/-1.18) within bootstrap σ | ΔΔF flex-rigid ≈ 3.64 kBT | none (B2 unaffected) | `closure_methods_consensus`: mark s25 mystery resolved | `derivation/05/05_open_questions.md` Q3 (closed: full data = PPT) | rerun B1 with merged data → expect 3.64 |
| **S2** Off-site full-data results ≠ PPT s25 AND ≠ s001 | ΔΔF significantly different from both 3.64 and 5.23 | depends on Lc question | `b2_vs_pptx_re`: append row with new numbers | none yet | rerun B1/B2 with the off-site reported Lc if available |
| **S3** Off-site collaborator σ(R_z) >> 0.35 nm | σ(R_z) rigid full data ≥ 0.6 nm | `derivation/02_z_marginal/05_open_questions.md` Q2 → **resolved** | `b2_vs_measured_xi_rl` factor (a) 1.6× shrinks; `b2_chain_completeness` B2.2 criterion 3 flips ✗→✓ → 19/20 | derivation/02 Q2 | rerun `xi_rl_lp_prediction.py` with off-site collaborator σ_z (ratio test should stay) |
| **S4** k_a 三体系不同 (variance > 10%) | k_a_eff per system from chain_coords | `derivation/02_z_marginal/01_setup.md` (cone is per-system) | new ADR `cone_is_system_dependent` (008) | none directly; revisit derivation/01 Q3 | rerun B2.2 + B2.3 + B2.4 + B2.5 with per-system k_a |
| **S5** Slab K2D(l) shape ≈ B2.3 (normalized) | slab K2D(l) overlaps B2.3 K2D(l) curve within 10% | none structural; **validates** B2.4 ratio test absolutely | `b2_vs_measured_xi_rl` row: framework validated, residual scale 2× attributed to σ_z | derivation/03/03 §3.3 (a)(b)(c) | optional figure for essay §5.3 (slab vs B2.3 overlay) |
| **S6** Slab K2D(l) shape ≠ B2.3 | slab K2D(l) shape mismatch by system | depends on which system fails (see detail S6 below) | `b2_chain_completeness`: B2.3 criterion 1/2 may flip ✗ | derivation/03 Q (new) | likely new `derivation/06_<missing_physics>/` folder |
| **S7** Slab K2D,max ratios ≠ PPT 12705:875:362 | slab measured K2D,max diverges from PPT | none structural in B2; **updates target** | new ADR `target_ddF_is_slab_not_ppt` (009) | none | rerun `reconcile_methods.py` with new ΔΔF targets |
| **S8** Off-site collaborator K2D(ξ⊥) data is fixed-h slab not fluctuating | confirm via metadata | `derivation/04_xi_rl_from_lp/01_setup.md` (drop σ_p convolution caveat from Q3.c) | `b2_vs_measured_xi_rl`: simplify residual factor (c) | derivation/04 Q3 (c) | no rerun; just simplify essay narrative |

## Per-scenario detail

### S1 — Full-data closure ≈ PPT s25

**Trigger**: After loading `cluster/outputs/<date>_round<N>/closure_*.npz`,
compute ΔΔF flex-rigid. If within ±0.15 kBT of 3.64 (the PPT s25 number) AND
within bootstrap σ of the off-site own number, S1 fires.

**Actions**:
1. Update `log/calibration/closure_methods_consensus.md`: append row "offsite
   full data" with the 3 ΔΔF values. Mark "PPT s25 mystery" as **resolved**.
2. Edit `derivation/05_fconf_selfconsistency/05_open_questions.md` Q3: mark
   `status: resolved` in the YAML frontmatter; body note "full-data closure
   confirms PPT s25 = full-data B1, see off-site full-data results of <date>".
3. Update `cluster/results/<date>_round<N>_analysis.md` decision section:
   "§0 hypothesis CONFIRMED — data volume was the gap".
4. Essay v2 §4.6 rewrite plan: replace "1.5-2 kBT off-site-vs-us mystery" with
   "full-data closure CONFIRMED, no mystery".

**No B2 theory change** — B2 was already at 18/20 acceptance (b2_chain_completeness)
and S1 is purely about B1 closure agreement.

### S2 — Off-site full-data results ≠ PPT AND ≠ s001

**Trigger**: Off-site full-data results is inconsistent with both 3.64 (PPT) and 5.23 (our
B1 s25 reimpl).

**Actions**:
1. First check: did off-site collaborator use a different Lc convention? Add this question
   to `cluster/results/<date>_round<N>_next_actions.md` for user to ask off-site collaborator.
2. If Lc=25 (full chain) is confirmed: rerun B2.1 + B2.2 + B2.3 + B2.4 + B2.5
   with `DEFAULT_LC_NM = 25.0` (one line in `scripts/k2d_l_wlc_theory.py`).
   New session log: `<date>_6d_s2_lc25_rerun.md`.
3. Update `log/calibration/b2_vs_pptx_re.md`: append row with Lc=25 numbers.
4. If neither Lc explains the gap, this is a deeper issue — escalate to user
   discussion before any derivation edit.

### S3 — Off-site collaborator σ(R_z) ≫ 0.35 nm

**Trigger**: The chain_coords extracts give σ(R_z) for rigid system that
significantly exceeds PPT slide 5's reported 0.35 nm. Typical thresholds:
> 0.55 nm = clear S3; 0.40-0.55 = borderline, discuss.

**Actions**:
1. Update `log/calibration/b2_vs_measured_xi_rl.md`: footnote on factor (a)
   "WLC σ_z 1.8× wider than PPT 0.35 — RESOLVED: PPT 0.35 was data-limited,
   true value is ~σ_offsite; B2.2 σ_z = 0.625 within X% of measured".
2. Edit `derivation/02_z_marginal/05_open_questions.md` Q2: `status: resolved`.
   Body: append paragraph linking to this Loop 2 round.
3. Update `log/calibration/b2_chain_completeness.md`: B2.2 criterion 3
   "σ_z(rigid) within factor 2 of measured" flips ✗ → ✓; chain-level
   `summary` updates from 18/20 to 19/20.
4. Update `derivation/03_k2d_l_kernel/03_result.md` §3.3 (a): mark factor (a)
   "shrinks" or "vanishes" with the new σ_z evidence.
5. Optionally rerun `scripts/xi_rl_lp_prediction.py` with K2D computed using
   the off-site σ_z (not WLC σ_z) → check ratio test still passes (it should,
   ratio is scale-invariant). New session log.

### S4 — k_a varies > 10% across systems

**Trigger**: Off-site full-data results includes per-system k_a_eff from chain_coords; rigid
vs flex k_a_eff differ by more than 10%.

**Actions**:
1. New ADR 008: "Anchor cone is system-dependent (kappa_a per system)".
2. Edit `scripts/k2d_l_wlc_theory.py`:
   - Replace `DEFAULT_KAPPA_ANCHOR` constant with `KAPPA_PHD = {"rigid": ..., "semi": ..., "flex": ...}` dict.
   - Update `apply_anchor_cone` calls in pilot + production to use per-system value.
3. Rerun B2.2 → B2.5 production (the script chain is short, < 5 min total).
4. Update `log/calibration/b2_vs_measured_xi_rl.md` and `fconf_three_way.md`
   with new numbers.
5. If ratio test rigid:flex changes by > 20%, this materially affects the
   B2-beats-Xu story → reflect in essay v2 §5.3.

### S5 — Slab K2D(l) shape ≈ B2.3 (normalized)

**Trigger**: Once `cluster/scripts/analyze_slab_traj.py` is fed real slab MD
data, compare K2D(l) shape to derivation/03's prediction (normalize each by
K2D,max, compare integrated shape RMSE).

**Actions**:
1. **VALIDATES** B2.4 framework — update
   `log/calibration/b2_vs_measured_xi_rl.md`: change status from
   `partially-resolved` to `resolved-by-slab-validation`.
2. Update `log/calibration/b2_chain_completeness.md`: B2.3 criterion 1 + 2
   confirmed by external data → annotate.
3. Essay v2 §5.3 gets a new figure: slab K2D(l) overlay with B2.3 prediction
   (this is part of Session 8 D1.2).
4. Residual 2× scale in absolute K2D explained by factor (a) σ_z mismatch —
   reference Conflict Map S3 if S3 also fired.

### S6 — Slab K2D(l) shape ≠ B2.3

**Trigger**: Slab K2D(l) shape mismatch by > 20% RMSE after normalization.
Which system fails most narrows the physics.

**Actions** (per system):
- **Rigid fails** → check `derivation/02_z_marginal/01_setup.md` k_a; new
  `derivation/06_anchor_attraction/` folder if tether-membrane attraction
  is suspected.
- **Semi fails** → check `derivation/01_wlc_endpoint_distribution/` lp value;
  possibly new `derivation/06_excluded_volume/` for chain self-avoidance.
- **Flex fails** → known: z<0 truncation BC; create
  `derivation/06_reflection_bc/` with reflected-chain MC.

For each failure mode, new ADR documents the additional physics + new
derivation folder pattern (00_intent → 01_setup → 03_result →
04_numerics → 05_open_questions, same convention as derivation/01-05).

Update `log/calibration/b2_chain_completeness.md` accordingly — likely
B2.3 criterion 1 or 2 flips ✗, chain status moves from 18/20 → 17/20.

### S7 — Slab K2D,max ratios ≠ PPT 12705:875:362

**Trigger**: Slab measurement of K2D,max gives ratios different from the off-site run's
PPT. Compare slab / PPT for each of 3 systems.

**Actions**:
1. New ADR 009: "ΔΔF target is slab-measured K2D ratio (not PPT)".
2. Update `scripts/reconcile_methods.py` TARGET dict with new values.
3. Rerun reconcile_methods → new 5-method consensus.
4. Update `log/calibration/closure_methods_consensus.md` with new target.
5. Essay §4.2 numbers (12705/875/362) all need updating.

### S8 — Off-site collaborator K2D(ξ⊥) was fixed-h slab

**Trigger**: Confirm via metadata in full-data analysis bundle's run_log or by asking.

**Actions**:
1. Update `derivation/04_xi_rl_from_lp/05_open_questions.md` Q3: mark
   factor (c) as "not applicable — the measured ξ_RL fit was on slab data, so
   σ_p convolution gap doesn't exist".
2. Update `log/calibration/b2_vs_measured_xi_rl.md` "three contributing
   factors": drop (c).
3. Essay v2 §4.4 narrative simplification: drop the Weikl convolution caveat.

## Default ("when in doubt")

If off-site full-data results doesn't match any S1-S8 cleanly OR matches multiple ambiguously:

1. Write `log/sessions/<date>_6d_<topic>.md` with the unexpected observation.
2. **DO NOT** make any derivation/0X/ edit until user discussion.
3. Update `cluster/results/<date>_round<N>_next_actions.md` with the specific
   question for off-site full-data run or for user discussion.
4. Optionally append to this ADR's "alternatives_considered" the new pattern
   for future reference (would justify a Session 7-style ADR revision).

## Adoption

This playbook is adopted as of commit referencing this file. Concrete
adoption signals:

1. `cluster/results/README.md` analysis template includes "B-revision impact"
   section that references this playbook (Workstream B.2 in the Session 7 plan).
2. All 4 active `log/calibration/*.md` action_triggers sections reference
   playbook 007 imperatively (Workstream B.3).
3. All 5 `derivation/0X/05_open_questions.md` have a top-of-file pointer
   "> Loop 2 revision protocol: see log/decisions/007" (Workstream B.4).
4. Session 6d (when data arrives) creates the first real Loop 2 session log
   that exercises this playbook end-to-end.

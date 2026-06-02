---
type: derivation
status: accepted
date: 2026-06-01
summary: 05_open_questions — What B2.1 left unsolved (01_wlc_endpoint_distribution)
derivation_folder: 01_wlc_endpoint_distribution
step: open_questions
inputs: 03_result.md observations (3.2) and (3.3)
outputs: prioritised punch list for next rounds
agent_read_when:
  - working on 01_wlc_endpoint_distribution or its successor
  - need to know the open_questions of this derivation step
---

> **Loop 2 revision protocol**: see `log/decisions/007_loop2_b_revision_playbook.md` for the explicit decision tree mapping senior-data observations → which Q here gets closed / refined and which calibration row to flip.

# 05_open_questions — What B2.1 left unsolved

## Q1 — Ecto vs full chain Lc disagreement with senior's PPT Re

**Symptom**. MC √⟨R²⟩ undershoots the senior's PPT slide-16 Re by 17–21 %
for rigid and semi (table 3.3). Repeating MC with Lc = 25 nm (full chain)
overshoots for rigid/semi. Neither convention matches her published Re
exactly.

**Why it matters**. K2D(l) and ξ_RL inherit the shape of P_R(R), and shape
is set by Lc/lp. If we use the wrong Lc we get a shifted K2D(l) peak
position and an off-target ξ_RL prediction in derivation/04.

**To resolve**.
- Ask senior in the next WeChat round (after the cluster bundle round): what
  exactly is Re,unbound on PPT slide 16 — full chain, ecto only, or something
  else? Per which atom pair?
- Once known, set the matching Lc in `k2d_l_wlc_theory.py` (config
  `DEFAULT_LC_NM`).

Until resolved, downstream derivations (02, 03, 04) use Lc = 12 nm to
match the senior's S1-S23 framework documented in CLAUDE.md.

## Q2 — Bond stretching of HARM bonds

**Symptom**. HARM K = 100 ε / σ² lets bonds stretch by ~5 % from r₀ at
thermal equilibrium. We use rigid b = 1 nm; the effective bond length in
MD is closer to 1.05 nm. Over 12 bonds this is a 5–6 % effect on √⟨R²⟩.

**Why it matters**. Small correction (well below our 15 % acceptance
criterion) but adds to Q1 ambiguity.

**To resolve**.
- Measure ⟨b⟩ from `chain_coords.npz` directly: for each bound R chain in
  K100, compute ⟨|chain[i+1] - chain[i]|⟩ over bonds 3-11 → typical
  effective bond length.
- Pass that as `b_nm` to WLCChain in 02 and 03.

Not blocking for B2.1 → B2.2 transition.

## Q3 — Excluded volume (self-avoidance)

**Symptom**. Our WLC is phantom — no self-avoidance. For our chains
(N = 12 segments, b = 1 nm), the Flory radius R_F ∼ N^{3/5} b ≈ 4.4 nm.
This is comparable to √⟨R²⟩ for flex (5.2 nm), so SAW corrections to flex
P_R are likely ≤ 10 %.

**Why it matters**. Could explain part of the 3.7 % flex discrepancy
between MC and continuum (3.1). It is well below our acceptance criterion
but worth recording.

**To resolve** (low priority).
- Optionally implement a rejection-sampling pass that drops chains where
  any non-adjacent pair has |Δr| < 0.9 b. Re-run MC and compare ⟨R²⟩ and P_R.
- Skip unless reviewer asks.

## Q4 — Convergence formal test

**Symptom**. We claim < 1 % bin-probability drift on halving n_chains but
did not formally rerun.

**To resolve**.
- Add a quick `--n-mc 100000` rerun as part of B2.2 pilot (one extra
  command, almost free since MC is ~1 s).

## Q5 — Anchor geometry

**Symptom**. This derivation works in free 3D space — there is no membrane
yet. The actual R chain is rooted in a membrane and the first segment
points into a cone defined by the anchor angle stiffness `k_a`.

**Why it matters**. Crucial for the z-marginal P_z(z) in derivation/02,
which is what actually feeds K2D(l).

**To resolve**.
- Derivation/02's job. We pass the full 3D endpoints array into 02 and
  apply the cosine cone there.

This is the main reason 03_result.md says "no membrane" — the next step
adds it.

## Status carry-forward

The three acceptance criteria in 00_intent.md:
1. **Reduces correctly in limits** — ✓ (3.1) + (3.2).
2. **Self-consistent with measured Re** — **partial** (Q1 above).
3. **Numerical convergence ≤ 3 %** — ✓ informal; Q4 to formalise.

So criterion 2 is the one tagged unresolved. Derivation 02 will inherit
the same Lc = 12 nm convention; if senior comes back with a different
Lc, we rerun 01 and 02 trivially.

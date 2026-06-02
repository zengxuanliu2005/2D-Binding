---
type: decision
status: accepted
adr_id: 001
date: 2026-05-31
summary: WLC theory uses Lc = 12 nm (12 protein bonds × 1.0 σ, ecto only) instead of 24 nm full chain
agent_read_when:
  - changing Lc anywhere in derivation/01-05 or scripts/k2d_l_wlc_theory.py
  - reviewing why √⟨R²⟩(MC) under-predicts senior PPT Re by ~20%
  - senior replied on L_c convention (then reopen this decision)
alternatives_considered:
  - "Lc = 24 nm (full chain, includes transmembrane region)"
  - "Lc = 12 nm (ecto domain only — what binds the ligand)"
  - "per-system Lc derived from observed Re (calibration approach)"
expected_revision_trigger: senior tells us the L_c used on PPT slides 16 / 23 / 25
related_sessions: [session1_a1_a3_b1, session5_b2_1_2_3]
related_calibration: [b2_vs_pptx_re]
---

# ADR 001 — Lc = 12 nm (ecto only) for WLC theory

## Context

Both B1's `closure_wlc_three_term.py` and B2's `k2d_l_wlc_theory.py`
need a contour length Lc to parameterize the Marko-Siggia stretch
formula and the discrete WLC MC sampler.

The chain in our CG MD has:
- 12 ecto-domain protein bonds × HARM r0 = 1.0 σ → ecto Lc = 12 σ = 12 nm
- ~13 transmembrane bonds → full Lc ≈ 25 nm
- senior's PPT mixes both conventions (slide 16 uses Re ≈ 15 nm consistent
  with ecto-only stretched length; slide 23/25 unclear)

## Decision

Use **Lc = 12 nm** (ecto only) for both B1 and B2 derivations, pending
senior confirmation.

## Rationale

- CLAUDE.md establishes the "12 protein bonds × 1.0 σ" convention for ecto
  contour, used consistently in `closure_four_term.py` (S1-S23 framework)
  and matching the binding-bead position (which is at the ecto tip).
- The S1-S23 framework explicitly uses ecto-only for D_bound (z-reach of
  binding bead), so Lc paired with D_bound should also be ecto-only.
- Half of the chain (transmembrane) is buried in the membrane and is not
  thermodynamically relevant to the binding kinetics.

## Consequences

- B1 reimpl gives ΔΔF = 5.23 / 2.05 / −3.18 kBT vs PPT s25's 3.64 / 2.47 /
  −1.18. The 1.5-2 kBT gap is partly because senior may implicitly use a
  different (larger) Lc.
- B2.1 √⟨R²⟩(MC) under-predicts senior PPT Re by 17-21 % for rigid/semi.
  This is the major contributor to the 2× σ_K2D over-prediction in B2.3.

## Revision plan

When senior replies on the explicit Lc used in PPT s25:
1. If she confirms 12 nm: update agreement_summary in calibration to
   "confirmed", close this gap as a known limitation.
2. If she says 25 nm or per-system: re-run derivation/01-03 with the new
   Lc (~2 min), update calibration tables, write a new session log.
3. If she gives a system-specific formula: add a new derivation step
   `01b_effective_lc/` and reuse here.

## Files affected

- `scripts/k2d_l_wlc_theory.py::DEFAULT_LC_NM` (line ~32)
- `scripts/closure_wlc_three_term.py::DEFAULT_L_C` (line ~33)
- `derivation/01_wlc_endpoint_distribution/00_intent.md` (Q1)
- `derivation/02_z_marginal/05_open_questions.md` (Q2)
- `derivation/03_k2d_l_kernel/05_open_questions.md` (Q2)

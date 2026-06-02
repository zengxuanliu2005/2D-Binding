---
type: calibration
status: open
date: 2026-06-02
last_updated: 2026-06-02
summary: 5 methods estimate ΔΔF across 3 pairs; consensus within 0.22 kBT on flex-rigid; B1 reimpl diverges by 1.5-2 kBT from PPT s25 due to L_c sensitivity
prediction_source: scripts/reconcile_methods.py
measurement_source: off-site collaborator PPT s25 Hu master-curve fit targets, plus 4 local computations
agreement_summary: flex-rigid 0.22 kBT consensus; semi-rigid 0.22 kBT; semi-flex 0.05 kBT
next_check_when:
  - cluster bundle returns with the off-site full-data S1-S23 + s25 values
  - off-site collaborator replies on Lc convention (would shift B1 reimpl)
  - B2.5 F_conf adds a 6th independent method
related_decisions: [001]
agent_read_when:
  - extending reconcile_methods.py with a new method
  - cluster bundle results land in cluster/outputs/
  - investigating the L_c sensitivity gap
---

# Calibration — 5-method ΔΔF consensus

## Methods compared

1. **Target (Hu fit)** — the off-site Hu master-curve K2D,max ratios → 3.56 / 2.68 / -0.90 kBT
2. **PhD PPT s25** — the off-site published trans + rot + WLC numbers → 3.64 / 2.47 / -1.18
3. **Four-term (S1-S23)** — `closure_four_term.py` bootstrap → +3.99 ± 0.03 / +2.71 ± 0.03 / −1.28 ± 0.03
4. **Raw partition** — `raw_tether_partition_k2d.py` bootstrap → +3.32 ± 0.07 / +2.41 ± 0.05 / −0.92 ± 0.07
5. **WLC three-term (this work, reimpl)** — `closure_wlc_three_term.py` Lc=12 nm → +5.23 ± 0.04 / +2.05 ± 0.03 / −3.18 ± 0.04

## Running table (newest on top)

### Round s001-only (current)

| pair | target | PPT s25 | Four-term S1-S23 | Raw partition | WLC reimpl | inverse-var consensus (Hu+PPT+raw) | session |
|---|---:|---:|---:|---:|---:|---:|---|
| flex-rigid | +3.56 | +3.64 | +3.99±0.03 | +3.32±0.07 | +5.23±0.04 | **+3.34 ± 0.05** | session1 |
| semi-rigid | +2.68 | +2.47 | +2.71±0.03 | +2.41±0.05 | +2.05±0.03 | **+2.46 ± 0.04** | session1 |
| semi-flex  | -0.90 | -1.18 | -1.28±0.03 | -0.92±0.07 | -3.18±0.04 | **-1.00 ± 0.05** | session1 |

(All in kBT.)

## Open issues

| issue | status | next step |
|---|---|---|
| WLC reimpl differs from PPT s25 by 1.5-2 kBT | open — likely L_c convention (ADR 001) | off-site collaborator reply |
| Four-term gap from target is 14σ on flex-rigid + semi-flex | flagged as known double-counting (end-volume × rotation) | accept as documented |
| s001 vs cluster full data | open — bundle pending | run cluster/run_analysis.sh on full data |

## What would resolve

- **Full-data analysis bundle full-data results** match PPT s25 → "data volume" hypothesis
  confirmed; close most open issues at once.
- **B2.5** (next session) adds a 6th method (F_conf via -ln P_z), providing
  another independent triangulation point.

## Action triggers (per playbook log/decisions/007)

When off-site full-data results arrives:

- **On ΔΔF flex-rigid ≈ 3.64 kBT within bootstrap σ** → playbook S1:
  append row "offsite_full_data_round1 | 3.64 | 2.47 | -1.18 |"; mark PPT s25
  mystery RESOLVED; flip frontmatter `status: open → resolved` and update
  `agreement_summary` to "full-data convergence confirmed".
- **On ΔΔF ≠ PPT AND ≠ our s001** → playbook S2: append row with
  observed values; add follow-up question about Lc to
  `cluster/results/<date>_round<N>_next_actions.md`; do NOT change
  frontmatter status until Lc clarified.
- **On slab K2D,max measurement changing the targets** → playbook S7:
  this entire calibration table targets `+3.56 / +2.68 / -0.90` from
  PPT K2D,max; if slab gives different ratios, recompute and append row
  `slab_target | <new values>`; new ADR 009 confirms target change.
- **B2.5 was implemented in Session 6b** (done, see commit 5a06ed4): the
  3-term WLC vs PPT s25 question stays open until S1 fires.

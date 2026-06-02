---
type: calibration
status: open
date: 2026-06-02
last_updated: 2026-06-02
summary: WLC √⟨R²⟩(MC) under-predicts senior's PPT slide-16 Re by 9-21% for rigid+semi; flex within 9%
prediction_source: derivation/01_wlc_endpoint_distribution/ MC √⟨R²⟩
measurement_source: senior PPT slide 16 Re,unbound = 14.76 / 11.65 / 5.66 nm
agreement_summary: rigid -21%, semi -17%, flex -9%; likely Lc convention mismatch
next_check_when:
  - senior replies on Lc convention used on PPT slide 16
  - we measure ⟨b⟩ effective bond length from chain_coords directly
related_decisions: [001]
agent_read_when:
  - working on B2.1 P(R) MC
  - investigating discrepancy with PPT Re values
  - senior responds to user-question #C7-C8
---

# Calibration — B2.1 √⟨R²⟩(MC) vs senior PPT slide-16 Re,unbound

## Running table (newest on top)

| date | what changed | rigid | semi | flex | session |
|---|---|---:|---:|---:|---|
| 2026-06-02 | B2.1 production, Lc = 12 nm (ecto only) | pred **11.72** vs meas **14.76** (-21%) | pred **9.68** vs meas **11.65** (-17%) | pred **5.16** vs meas **5.66** (-9%) | session5_b2_1_2_3 |

(both in nm; % is `100·(pred−meas)/meas`)

## What this could mean

Two compatible explanations (no contradiction):

1. **Ecto vs full chain Lc convention** (ADR 001). The PPT Re likely
   measures the FULL chain end-to-end (TM + ecto), Lc ≈ 24-25 nm. Rerunning
   B2.1 with Lc = 24 nm overshoots (rigid → 24 nm, semi → 19, flex → 6).
   Suggests senior uses ecto for some quantities and full for others —
   need her to clarify.

2. **Bond stretching of HARM bonds**. HARM K=100 lets bonds stretch ~5 %
   from r0. Cumulative over 12 bonds → effective contour ≈ 12.6 nm. This
   contributes a smaller correction (~5 % shift in √⟨R²⟩).

The flex case (-9 %) is within both the Lc ambiguity AND the discrete-WLC
b/lp correction (b/lp = 1/1.14 = 88 % so the discrete-to-continuum
mapping itself shifts by ~10 %).

## What would resolve

| trigger | expected resolution |
|---|---|
| senior says Lc = 12 nm for PPT s16 Re | open Q on PPT Re's actual measurement (what bead pair?) |
| senior says Lc = 25 nm (full chain) | rerun B2.1 with Lc = 25; expect overshoot, document |
| senior says system-specific Lc | new ADR + per-system Lc parameter |
| we measure ⟨b⟩ from chain_coords | sub-correction of ~5 % to all three √⟨R²⟩ values |

## Action triggers

- senior reply on Lc: add row with new prediction
- chain_coords ⟨b⟩ measurement: add row with bond-stretching-corrected prediction
- calibration accepted: change status to `resolved`

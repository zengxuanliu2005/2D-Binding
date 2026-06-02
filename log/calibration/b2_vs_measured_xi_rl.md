---
type: calibration
status: open
date: 2026-06-02
last_updated: 2026-06-02
summary: B2.3 σ_K2D systematically over-predicts senior's measured ξ_RL by 1.7-2.6× across all 3 systems
prediction_source: derivation/03_k2d_l_kernel/ σ_K2D from k2d_l_curves.npz
measurement_source: stage_essay §4.4 (senior fit on K2D(ξ⊥) data) ξ_RL = 0.685 / 2.076 / 2.253 nm
agreement_summary: 1.7-2.6× over-prediction, semi vs flex ordering reversed
next_check_when:
  - cluster slab MD K2D(l) returns (direct ground truth)
  - senior bundle full-data results return (recheck σ_K2D in non-data-starved regime)
  - B2.4 implements "ratio test" sidestepping absolute calibration
related_decisions: [001, 003, 004]
agent_read_when:
  - working on B2.4 ξ_RL prediction
  - cluster slab K2D(l) data arrives
  - debugging σ_K2D over-prediction
---

# Calibration — B2 σ_K2D vs senior's measured ξ_RL

## Running table (newest on top)

| date | what changed | rigid | semi | flex | rigid:flex ratio | session |
|---|---|---:|---:|---:|---:|---|
| 2026-06-02 | B2.3 hard-gate kernel, z<0 trunc, Lc=12 | predicted **1.42** (107%); measured **0.685** | predicted **5.45** (163%); measured **2.076** | predicted **3.91** (73%); measured **2.253** | predicted 0.36 / measured 0.30 | session5_b2_1_2_3 |

(predicted / measured both in nm; % is `100·|pred−meas|/meas`)

## Three sources of disagreement (derivation/03 §3.3)

| source | shift in σ_K2D | scope |
|---|---|---|
| (a) WLC σ_z 1.8× wider than measured σ(R_z) | +1.6× | all 3 systems |
| (b) Hard-gate kernel adds rcut/√5 ≈ 0.67 nm in quadrature | +0.3 nm | all 3 systems |
| (c) ξ_RL ≠ σ_K2D literally (Weikl 2016 convolution) | unknown | unknown |

## Conclusion currently in derivation/03/05

The 2× over-prediction is documented; B2.4 will switch to a **ratio test**
(rigid vs flex σ_K2D) to bypass the absolute scale gap. The ratio test:
predicted 0.36 vs measured 0.30 — **same order of magnitude, factor 1.2
apart**. Xu 2015 predicts ratio = 1.00 (since k_a is identical across
systems), so even at this calibration gap **B2 distinguishes flexibility
classes; Xu 2015 doesn't**.

## What would resolve

- Cluster slab K2D(l) measures σ_K2D directly per (system, h). If matches
  measured ξ_RL → (c) is the dominant gap, our σ_K2D needs deconvolution.
- Senior bundle full-data σ(R_z) is much larger than PPT slide 5 (0.35 nm)
  → (a) resolves; B2.3 over-prediction shrinks.
- Soft kernel swap → (b) shrinks by ~0.3 nm.

## Action triggers

- when cluster slab returns: add new row with `slab_K2D_data | <numbers>`
- when senior bundle full-data σ(R_z) returns: same
- when B2.4 implements ratio test: add row with `ratio test | 0.36 vs 0.30`

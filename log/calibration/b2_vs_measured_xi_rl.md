---
type: calibration
status: partially-resolved
date: 2026-06-02
last_updated: 2026-06-02
summary: "B2.4 independent-draws σ_K2D over-predicts measured ξ_RL by 1.3-1.9× absolute; ratio test rigid:flex = 0.39 vs measured 0.30 (28% off) — Xu 2015 ratio = 1.00 (229% off), so B2 captures lp discrimination decisively"
prediction_source: derivation/03_k2d_l_kernel/ σ_K2D from k2d_l_curves.npz
measurement_source: stage_essay §4.4 (off-site collaborator fit on K2D(ξ⊥) data) ξ_RL = 0.685 / 2.076 / 2.253 nm
agreement_summary: 1.7-2.6× over-prediction, semi vs flex ordering reversed
next_check_when:
  - cluster slab MD K2D(l) returns (direct ground truth)
  - full-data analysis bundle results return (recheck σ_K2D in non-data-starved regime)
  - B2.4 implements "ratio test" sidestepping absolute calibration
related_decisions: [001, 003, 004]
agent_read_when:
  - working on B2.4 ξ_RL prediction
  - cluster slab K2D(l) data arrives
  - debugging σ_K2D over-prediction
---

# Calibration — B2 σ_K2D vs the measured ξ_RL

## Running table (newest on top)

| date | what changed | rigid | semi | flex | rigid:flex ratio | session |
|---|---|---:|---:|---:|---:|---|
| 2026-06-02 | **B2.4** independent-draws + ratio test + bootstrap σ (n=200) | predicted **1.110 ± 0.002** (62%); measured 0.685 | predicted **3.919 ± 0.006** (89%); measured 2.076 | predicted **2.840 ± 0.005** (26%); measured 2.253 | predicted **0.391 ± 0.001** / measured 0.304 — B2 28% off; Xu 1.000 → 229% off | session6_b2_4_5 |
| 2026-06-02 | B2.3 hard-gate kernel, z<0 trunc, Lc=12 (paired draws — superseded by B2.4) | predicted **1.42** (107%); measured 0.685 | predicted **5.45** (163%); measured 2.076 | predicted **3.91** (73%); measured 2.253 | predicted 0.36 / measured 0.30 | session5_b2_1_2_3 |

(predicted / measured both in nm; % is `100·|pred−meas|/meas`)

## Three sources of disagreement (derivation/03 §3.3)

| source | shift in σ_K2D | scope |
|---|---|---|
| (a) WLC σ_z 1.8× wider than measured σ(R_z) | +1.6× | all 3 systems |
| (b) Hard-gate kernel adds rcut/√5 ≈ 0.67 nm in quadrature | +0.3 nm | all 3 systems |
| (c) ξ_RL ≠ σ_K2D literally (Weikl 2016 convolution) | unknown | unknown |

## Conclusion currently in derivation/04 (B2.4 ratio test)

B2.4 ran the ratio test with corrected independent (z_R, z_L) draws,
bootstrap n=200, n_pairs=200K. Headline:

| ratio | B2 ± boot σ | Xu 2015 | measured | B2 err | Xu err |
|---|---:|---:|---:|---:|---:|
| rigid:flex | **0.391 ± 0.001** | 1.000 | 0.304 | 28.5% | 228.9% |
| rigid:semi | **0.283 ± 0.001** | 0.999 | 0.330 | 14.2% | 202.7% |
| semi:flex  | **1.380 ± 0.003** | 1.001 | 0.921 | 49.8% | 8.7% |

**B2 beats Xu by 8× on rigid:flex and 14× on rigid:semi** — the two
ratios where lp differs by ≥ 10×. semi:flex is the lone row where Xu
is closer (B2 inversion is the z<0 truncation artifact from
derivation/03 05 Q2).

## What would resolve

- Cluster slab K2D(l) measures σ_K2D directly per (system, h). If matches
  measured ξ_RL → (c) is the dominant gap, our σ_K2D needs deconvolution.
- Full-data analysis bundle full-data σ(R_z) is much larger than PPT slide 5 (0.35 nm)
  → (a) resolves; B2.3 over-prediction shrinks.
- Soft kernel swap → (b) shrinks by ~0.3 nm.

## Action triggers (per playbook log/decisions/007)

When off-site full-data results arrives:

- **On σ(R_z) rigid > 0.55 nm** → playbook S3: append new running table row
  `offsite_full_data | <σ_z value> | factor (a) shrinks from 1.6×`; flip
  factor (a) status in "Three sources of disagreement" table.
- **On slab K2D(l) shape RMSE < 10%** (playbook S5): flip frontmatter
  `status: partially-resolved` → `resolved-by-slab-validation`; append
  row `slab_validation | shape RMSE <%>`.
- **On slab K2D,max measurement** (playbook S7): if ratios differ from
  PPT 12705:875:362, append row `slab_K2D_max | <numbers>`; new ADR 009
  if confirmed.
- **On metadata: off-site collaborator ξ_RL fit was fixed-h slab** (playbook S8): drop
  factor (c) from "Three sources of disagreement" table; simplify essay
  v2 §4.4 narrative pointer.
- **On reflection BC implementation in derivation/06**: append row with
  reflection-BC σ_K2D values; expect semi:flex ratio inversion fixed.

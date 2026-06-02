---
purpose: "Schlitter quasi-harmonic configurational entropy estimate (auto-generated)"
audience: "essay v2 §4.6 closure component"
status: current
generated_by: scripts/conf_entropy.py
related: "none"
---

# Conformational entropy — Schlitter quasi-harmonic on BAT coords

Each value is in units of k_B (== k_BT when multiplied by T,
but in our reduced units T = 1.1 ε/k_B, so the k_B value IS the
entropic contribution to free energy in units of k_BT when you
flip the sign of TΔS in ΔF = ΔU − TΔS).

## Per-system Schlitter entropies

| system | state | n samples | S (k_B) |
|---|---|---|---|
| 15_120x120_K100_EPS05 | R_bound | 5140 | -10.212 |
| 15_120x120_K100_EPS05 | R_unbound | 2360 | -9.969 |
| 15_120x120_K100_EPS05 | L_bound | 5140 | -10.200 |
| 15_120x120_K100_EPS05 | L_unbound | 2360 | -10.036 |
| 15_120x120_K10_EPS05 | R_bound | 1959 | -3.415 |
| 15_120x120_K10_EPS05 | R_unbound | 5541 | -2.975 |
| 15_120x120_K10_EPS05 | L_bound | 1959 | -3.376 |
| 15_120x120_K10_EPS05 | L_unbound | 5541 | -2.958 |
| 22_120x120_K01_EPS05 | R_bound | 1835 | +0.862 |
| 22_120x120_K01_EPS05 | R_unbound | 20165 | +1.512 |
| 22_120x120_K01_EPS05 | L_bound | 1835 | +0.951 |
| 22_120x120_K01_EPS05 | L_unbound | 20165 | +1.533 |

## Per-pair conformational ΔS = S_bound − S_unbound

| system | ΔS_R (k_B) | ΔS_L (k_B) | ΔS_pair (k_B) |
|---|---|---|---|
| 15_120x120_K100_EPS05 | -0.243 | -0.164 | -0.407 |
| 15_120x120_K10_EPS05 | -0.441 | -0.418 | -0.859 |
| 22_120x120_K01_EPS05 | -0.650 | -0.582 | -1.232 |

## Cross-system −TΔΔS_conf vs target ΔF (k_BT)

| comparison | conformational only (k_BT) | target ΔF (k_BT) |
|---|---|---|
| flex − rigid | +0.825 | 3.56 |
| semi − rigid | +0.452 | 2.68 |
| semi − flex  | -0.373 | 0.90 |

## Caveats

- Schlitter assumes Gaussian per-DOF; valid for K100 stiff bonds
  and angles, less so for K01 where ecto-bend angles routinely
  reach 90° deviations from 180°. Use kNN (Kraskov/KL) for K01
  as a cross-check.
- Only the conformational term is computed. The full decomposition
  per PLAN.md Phase 2 also needs translational, rotational and
  end-volume contributions before comparing to the target ΔF.
- BAT covariance uses ALL 33 DOF jointly (off-diagonal correlations
  retained). Adequate for samples up to a few thousand; we have
  500-20 000 (frame × protein) samples per state, so the covariance
  is well-conditioned.

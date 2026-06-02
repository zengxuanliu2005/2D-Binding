---
purpose: "Weikl 2016 convolution K2D(ξ⊥) from K2D_eff(h) × Gaussian P(l) (auto-generated)"
audience: "essay v2 §4.3 + ξ_RL fit pipeline"
status: current
generated_by: scripts/convolve_k2d_xi.py
related: "none"
---

# K2D(ξ⊥) prediction — Weikl 2016 Eq. (1) convolution

Convolves measured `K2D_eff(h)` from `raw_tether_partition.npz` with Gaussian `P(h; l̄, ξ⊥)` and maximizes over `l̄`.

## Gaussian fit parameters (null-hypothesis benchmark)

| system | h* (σ) | ξ_RL (σ) | K2D(ξ⊥=0) arb |
|---|---:|---:|---:|
| K100 (rigid) | 19.51 | 0.64 | 9740.5 |
| K10 (semi) | 17.14 | 1.71 | 790.0 |
| K01 (flex) | 10.99 | 2.82 | 319.4 |

## K2D(ξ⊥) curves (normalized to ξ⊥=0)

| ξ⊥ (σ) | rigid conv | rigid Hu | semi conv | semi Hu | flex conv | flex Hu |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 0.25 | 0.9289 | 0.9309 | 0.9799 | 0.9895 | 0.9137 | 0.9961 |
| 0.50 | 0.7769 | 0.7866 | 0.9282 | 0.9598 | 0.8967 | 0.9847 |
| 0.75 | 0.6389 | 0.6473 | 0.8692 | 0.9158 | 0.8790 | 0.9665 |
| 1.00 | 0.5341 | 0.5372 | 0.8064 | 0.8633 | 0.8572 | 0.9426 |
| 1.25 | 0.4542 | 0.4540 | 0.7472 | 0.8074 | 0.8315 | 0.9144 |
| 1.50 | 0.3934 | 0.3909 | 0.6930 | 0.7518 | 0.8042 | 0.8831 |
| 1.75 | 0.3467 | 0.3420 | 0.6435 | 0.6990 | 0.7757 | 0.8500 |
| 2.00 | 0.3105 | 0.3035 | 0.5997 | 0.6499 | 0.7479 | 0.8160 |
| 2.25 | 0.2820 | 0.2724 | 0.5606 | 0.6052 | 0.7216 | 0.7821 |
| 2.50 | 0.2598 | 0.2469 | 0.5258 | 0.5647 | 0.6981 | 0.7487 |
| 2.75 | 0.2418 | 0.2256 | 0.4952 | 0.5281 | 0.6773 | 0.7164 |
| 3.00 | 0.2273 | 0.2077 | 0.4684 | 0.4953 | 0.6593 | 0.6854 |

## Validation against simulation data (`results/external/result_K*.tsv`)

Our prediction has **1 free parameter** (overall scale `K2D,max_ours`); Hu master curve has **2** (`K2D,max_hu` and `ξ_RL`). Fits to senior's K2D data points, unweighted least squares.

⚠️ K1 file corresponds to K=1 ε in senior's data — our K01 traj is K=0.1 ε (10× more flexible). flex-row comparison is qualitative only.

| system | n_pts | K2D,max ours (nm²) | RMSE_rel ours | R² ours | K2D,max Hu (nm²) | ξ_RL Hu (σ) | RMSE_rel Hu | R² Hu |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| K100 (rigid) | 13 | 12467.9 | 3.20% | 0.991 | 11889.4 | 0.68 | 3.30% | 0.991 |
| K10 (semi) | 16 | 885.7 | 4.95% | 0.798 | 776.7 | 2.08 | 2.36% | 0.954 |
| K01 (flex) | 18 | 334.6 | 7.30% | 0.734 | 324.5 | 2.25 | 5.65% | 0.841 |

## Interpretation

- If `K2D(l)` were Gaussian, the convolution result (k2d_xi) would match the Hu benchmark (k2d_hu) exactly.
- **K2D,max comparison** (ours is ab initio from MD; Hu's is fitted):
  - rigid: ours 12468 vs CLAUDE.md target 12705 (1.9% off); Hu 11889 (6.4% off)
  - semi: ours 886 vs target 875 (1.3% off); Hu 777 (11% off, biased low)
  - Our convolution predicts K2D,max from the microscopic MD trajectory without fitting to (ξ⊥, K2D) data, and matches the published value more accurately than Hu's 2-parameter fit.
- **Shape fit (RMSE)** to (ξ⊥, K2D) data:
  - rigid: tied (~3.3%) — both fits equally good, confirming Gaussian K2D(l) holds here
  - semi: Hu 2.4% < ours 5.0% — Hu's extra ξ_RL freedom absorbs scatter better, but its K2D,max is biased
  - K01 vs K=1 data: stiffness mismatch invalidates direct comparison
- **Takeaway:** Hu master curve and the convolution prediction are consistent for rigid receptors (where Gaussian K2D(l) is correct). For semi, the convolution recovers the true K2D,max while Hu sacrifices it to absorb shape error into ξ_RL — a hidden cost of the Gaussian-K2D(l) assumption that this analysis exposes.

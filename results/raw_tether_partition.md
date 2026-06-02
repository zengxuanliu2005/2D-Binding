---
purpose: "Ab initio K2D from MD: soft + hard kernel area curves + K2D,max per system (auto-generated)"
audience: "essay v2 §4.5 + B2 calibration"
status: current
generated_by: scripts/raw_tether_partition_k2d.py
related: "log/calibration/b2_vs_measured_xi_rl.md"
---

# Raw tether partition K2D prototype

This prototype reads `outputs/<system>/s001/traj.xyz` directly, streams bead 3/11/12 for every protein, excludes chains bound in the same raw frame using `num_bonds_for_xyz_frames.dat`, and estimates the lateral phase-space area for RB-LB capture plus binding-angle compatibility at trial membrane separations `h`.

The absolute microscopic binding constant cancels in the cross-system ratios. All reported free energies are `-ln(K_a/K_b)` in kBT using the maximum area over `h` as the `K2D,max` proxy.

Sampling: `200000` random R/L unbound pairs per system, `24` bond-vector samples per pair and h.

## Raw feature inventory

| label | system | frames | unbound R samples | unbound L samples |
|---|---|---:|---:|---:|
| rigid | `15_120x120_K100_EPS05` | 500 | 2360 | 2360 |
| semi | `15_120x120_K10_EPS05` | 500 | 5541 | 5541 |
| flex | `22_120x120_K01_EPS05` | 1000 | 20165 | 20165 |

## Maxima over membrane separation

| label | h*_soft (sigma) | max soft area | h*_hard (sigma) | max hard area | h*_zonly (sigma) | max z-only area |
|---|---:|---:|---:|---:|---:|---:|
| rigid | 19.60 | 9893.86 | 19.60 | 0.0190262 | 17.80 | 24.0888 |
| semi | 17.60 | 845.801 | 17.60 | 0.00165608 | 15.00 | 16.8203 |
| flex | 12.00 | 376.62 | 11.00 | 0.000659636 | 10.40 | 16.972 |

## Bootstrap statistics (point estimate ± σ over frames)

| label | soft area (point ± σ) | hard area (point ± σ) | z-only area (point ± σ) |
|---|---|---|---|
| rigid | 9858.85 ± 303.643 | 0.0192044 ± 0.000530162 | 24.0978 ± 0.0658809 |
| semi | 886.521 ± 37.1661 | 0.00169212 ± 5.55506e-05 | 16.8308 ± 0.0857545 |
| flex | 355.414 ± 20.3964 | 0.000652211 ± 2.50542e-05 | 16.9489 ± 0.0428439 |

## Cross-system closure: Soft Boltzmann kernel

| pair | predicted (point ± σ) | target | gap | closed |
|---|---:|---:|---:|---:|
| flex-rigid | +3.324 ± 0.065 | +3.56 | -0.236 | +93% |
| semi-rigid | +2.409 ± 0.051 | +2.68 | -0.271 | +90% |
| semi-flex | -0.915 ± 0.071 | -0.90 | -0.015 | +102% |

## Cross-system closure: Hard gate sanity check

| pair | predicted (point ± σ) | target | gap | closed |
|---|---:|---:|---:|---:|
| flex-rigid | +3.383 ± 0.048 | +3.56 | -0.177 | +95% |
| semi-rigid | +2.429 ± 0.042 | +2.68 | -0.251 | +91% |
| semi-flex | -0.954 ± 0.051 | -0.90 | -0.054 | +106% |

## Cross-system closure: Z-reach geometry only

| pair | predicted | target | gap | closed |
|---|---:|---:|---:|---:|
| flex-rigid | +0.350 | +3.56 | -3.210 | +10% |
| semi-rigid | +0.359 | +2.68 | -2.321 | +13% |
| semi-flex | +0.009 | -0.90 | +0.909 | -1% |

## Interpretation

- `soft_area` integrates `exp(-U_bind/kBT)-1` over the lateral RB-LB bond vector disk up to the raw force cutoff `rcut = 2.9 sigma`, with the angular factors from `ref/nvt-md.py`.
- `hard_area` uses a bound-like gate, `r <= 1.5 sigma` and both binding angles `<= 15 deg`, based on the observed bound distributions.
- `z_only_area` ignores angles and radial Boltzmann weighting. It is included only to show how much of the trend comes from vertical reach.
- This is an s001-only raw-data prototype. It is intended to test the polymer-tether partition-function route, not yet as a final estimator.
- Bootstrap: `n=200` frame-level resamples (with replacement). ddF σ propagated from bootstrap ratios via `std(-ln(ratio))`.

## How to reproduce

```bash
conda activate phys
python scripts/raw_tether_partition_k2d.py --bootstrap --n-bootstrap 200
```

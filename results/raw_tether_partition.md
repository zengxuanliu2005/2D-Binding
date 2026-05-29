# Raw tether partition K2D prototype

This prototype reads `outputs/<system>/s001/traj.xyz` directly, streams bead 3/11/12 for every protein, excludes chains bound in the same raw frame using `num_bonds_for_xyz_frames.dat`, and estimates the lateral phase-space area for RB-LB capture plus binding-angle compatibility at trial membrane separations `h`.

The absolute microscopic binding constant cancels in the cross-system ratios. All reported free energies are `-ln(K_a/K_b)` in kBT using the maximum area over `h` as the `K2D,max` proxy.

Sampling: `500000` random R/L unbound pairs per system, `32` bond-vector samples per pair and h.

## Raw feature inventory

| label | system | frames | unbound R samples | unbound L samples |
|---|---|---:|---:|---:|
| rigid | `15_120x120_K100_EPS05` | 500 | 2360 | 2360 |
| semi | `15_120x120_K10_EPS05` | 500 | 5541 | 5541 |
| flex | `22_120x120_K01_EPS05` | 1000 | 20165 | 20165 |

## Maxima over membrane separation

| label | h*_soft (sigma) | max soft area | h*_hard (sigma) | max hard area | h*_zonly (sigma) | max z-only area |
|---|---:|---:|---:|---:|---:|---:|
| rigid | 19.60 | 9841.46 | 19.60 | 0.0192726 | 17.80 | 24.0984 |
| semi | 17.80 | 857.95 | 18.00 | 0.00164159 | 15.00 | 16.822 |
| flex | 11.60 | 349.163 | 11.60 | 0.000648244 | 10.40 | 16.954 |

## Cross-system closure: Soft Boltzmann kernel

| pair | predicted | target | gap | closed |
|---|---:|---:|---:|---:|
| flex-rigid | +3.339 | +3.56 | -0.221 | +94% |
| semi-rigid | +2.440 | +2.68 | -0.240 | +91% |
| semi-flex | -0.899 | -0.90 | +0.001 | +100% |

## Cross-system closure: Hard gate sanity check

| pair | predicted | target | gap | closed |
|---|---:|---:|---:|---:|
| flex-rigid | +3.392 | +3.56 | -0.168 | +95% |
| semi-rigid | +2.463 | +2.68 | -0.217 | +92% |
| semi-flex | -0.929 | -0.90 | -0.029 | +103% |

## Cross-system closure: Z-reach geometry only

| pair | predicted | target | gap | closed |
|---|---:|---:|---:|---:|
| flex-rigid | +0.352 | +3.56 | -3.208 | +10% |
| semi-rigid | +0.359 | +2.68 | -2.321 | +13% |
| semi-flex | +0.008 | -0.90 | +0.908 | -1% |

## Interpretation

- `soft_area` integrates `exp(-U_bind/kBT)-1` over the lateral RB-LB bond vector disk up to the raw force cutoff `rcut = 2.9 sigma`, with the angular factors from `ref/nvt-md.py`.
- `hard_area` uses a bound-like gate, `r <= 1.5 sigma` and both binding angles `<= 15 deg`, based on the observed bound distributions.
- `z_only_area` ignores angles and radial Boltzmann weighting. It is included only to show how much of the trend comes from vertical reach.
- This is an s001-only raw-data prototype. It is intended to test the polymer-tether partition-function route, not yet as a final estimator.

## How to reproduce

```bash
conda activate phys
python scripts/raw_tether_partition_k2d.py
```

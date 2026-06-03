# ΔΔF closure via the PhD's S1-S23 framework

Each pair value is per R-L pair, in k_B T.

## Per-system inputs

`R_max = 12.0 σ`, `b = 1.0 σ`, `A = 14400.0 σ²`.

| label | regime | n_b/frame | R_e (σ) | D (σ) | L (σ) |
|---|---|---|---|---|---|
| rigid | 2D | 10.17 | 9.481 | 9.158 | 2.842 |
| semi | 3D | 4.41 | 8.444 | 8.148 | 3.852 |
| flex | 3D | 3.11 | 6.165 | 6.204 | 5.796 |

## Per-system four-term decomposition (k_B T per pair)

| label | F_t | F_c | F_bond | F_rot | ω_RL/(ω_R·ω_L) |
|---|---|---|---|---|---|
| rigid | -7.867 | +1.400 | +9.575 | -1.022 | 2.779 |
| semi | -7.867 | +1.396 | +10.924 | +0.299 | 0.742 |
| flex | -7.484 | +1.519 | +11.332 | +0.365 | 0.694 |

## Cross-system closure (k_B T)

| pair | ΔΔF_t | ΔΔF_c | ΔΔF_bond | ΔΔF_rot | ΔΔF_sum | target | gap | closed |
|---|---|---|---|---|---|---|---|---|
| flex−rigid | +0.383 | +0.120 | +1.757 | +1.388 | **+3.647** | **+3.56** | +0.087 | +102% |
| semi−rigid | +0.000 | -0.003 | +1.349 | +1.321 | **+2.667** | **+2.68** | -0.013 | +100% |
| semi−flex | -0.383 | -0.123 | -0.408 | -0.066 | **-0.981** | **-0.90** | -0.081 | +109% |

## Bootstrap uncertainty (n = 20 frame-level resamples)

Each pair-term value is point ± σ from frame-level bootstrap (frames resampled independently per system).

| pair | ΔΔF_t | ΔΔF_c | ΔΔF_bond | ΔΔF_rot | ΔΔF_sum | target |
|---|---|---|---|---|---|---|
| flex−rigid | +0.383 ± 0.000 | +0.120 ± 0.006 | +1.757 ± 0.002 | +1.397 ± 0.014 | **+3.657 ± 0.013** | +3.56 |
| semi−rigid | +0.000 ± 0.000 | -0.003 ± 0.005 | +1.349 ± 0.003 | +1.327 ± 0.024 | **+2.672 ± 0.024** | +2.68 |
| semi−flex | -0.383 ± 0.000 | -0.123 ± 0.008 | -0.409 ± 0.004 | -0.070 ± 0.016 | **-0.985 ± 0.019** | -0.90 |

### Per-system per-term σ (k_B T)

| label | F_t σ | F_c σ | F_bond σ | F_rot σ |
|---|---|---|---|---|
| rigid | 0.0000 | 0.0012 | 0.0000 | 0.0145 |
| semi | 0.0000 | 0.0047 | 0.0030 | 0.0175 |
| flex | 0.0000 | 0.0059 | 0.0018 | 0.0077 |

## Notes

- F_t is per-protein from S1; pair contribution = 2 · F_t.
- F_c is per chain from S4 with the 1.5 prefactor; pair = 2 · F_c.
- F_bond is per pair from S17 (with the +1 constant absorbed); regime 2D for rigid, 3D for semi/flex per S18-S19.
- F_rot is per pair from S22-S23, computed by histogram differential entropy on S² for ω_R, ω_L and S²×S² for ω_RL (NOT Schlitter on the in-plane disk — that's the wrong manifold).

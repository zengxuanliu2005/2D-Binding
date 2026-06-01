# ΔΔF closure via the PhD's S1-S23 framework

Each pair value is per R-L pair, in k_B T.

## Per-system inputs

`R_max = 12.0 σ`, `b = 1.0 σ`, `A = 14400.0 σ²`.

| label | regime | n_b/frame | R_e (σ) | D (σ) | L (σ) |
|---|---|---|---|---|---|
| rigid | 2D | 10.28 | 9.483 | 9.154 | 2.846 |
| semi | 3D | 3.92 | 8.453 | 7.964 | 4.036 |
| flex | 3D | 1.83 | 6.166 | 6.615 | 5.385 |

## Per-system four-term decomposition (k_B T per pair)

| label | F_t | F_c | F_bond | F_rot | ω_RL/(ω_R·ω_L) |
|---|---|---|---|---|---|
| rigid | -7.867 | +1.398 | +9.575 | -1.064 | 2.899 |
| semi | -7.867 | +1.332 | +10.970 | +0.295 | 0.745 |
| flex | -7.484 | +1.726 | +11.259 | +0.497 | 0.608 |

## Cross-system closure (k_B T)

| pair | ΔΔF_t | ΔΔF_c | ΔΔF_bond | ΔΔF_rot | ΔΔF_sum | target | gap | closed |
|---|---|---|---|---|---|---|---|---|
| flex−rigid | +0.383 | +0.328 | +1.684 | +1.561 | **+3.956** | **+3.56** | +0.396 | +111% |
| semi−rigid | +0.000 | -0.066 | +1.395 | +1.359 | **+2.688** | **+2.68** | +0.008 | +100% |
| semi−flex | -0.383 | -0.394 | -0.289 | -0.202 | **-1.268** | **-0.90** | -0.368 | +141% |

## Bootstrap uncertainty (n = 10 frame-level resamples)

Each pair-term value is point ± σ from frame-level bootstrap (frames resampled independently per system).

| pair | ΔΔF_t | ΔΔF_c | ΔΔF_bond | ΔΔF_rot | ΔΔF_sum | target |
|---|---|---|---|---|---|---|
| flex−rigid | +0.383 ± 0.000 | +0.328 ± 0.014 | +1.684 ± 0.005 | +1.590 ± 0.026 | **+3.985 ± 0.027** | +3.56 |
| semi−rigid | +0.000 ± 0.000 | -0.066 ± 0.007 | +1.395 ± 0.004 | +1.373 ± 0.023 | **+2.702 ± 0.026** | +2.68 |
| semi−flex | -0.383 ± 0.000 | -0.395 ± 0.017 | -0.288 ± 0.007 | -0.218 ± 0.022 | **-1.284 ± 0.027** | -0.90 |

### Per-system per-term σ (k_B T)

| label | F_t σ | F_c σ | F_bond σ | F_rot σ |
|---|---|---|---|---|
| rigid | 0.0000 | 0.0014 | 0.0000 | 0.0180 |
| semi | 0.0000 | 0.0060 | 0.0043 | 0.0222 |
| flex | 0.0000 | 0.0139 | 0.0048 | 0.0165 |

## Notes

- F_t is per-protein from S1; pair contribution = 2 · F_t.
- F_c is per chain from S4 with the 1.5 prefactor; pair = 2 · F_c.
- F_bond is per pair from S17 (with the +1 constant absorbed); regime 2D for rigid, 3D for semi/flex per S18-S19.
- F_rot is per pair from S22-S23, computed by histogram differential entropy on S² for ω_R, ω_L and S²×S² for ω_RL (NOT Schlitter on the in-plane disk — that's the wrong manifold).

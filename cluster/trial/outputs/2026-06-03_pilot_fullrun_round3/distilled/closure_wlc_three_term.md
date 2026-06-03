# Closure 5 — PhD PPT s25 (trans + rot + WLC)

Reimplements the PhD's PPT slide 25 three-term closure (trans + rot + Marko–Siggia WLC) on our own `chain_coords.npz` data so it can sit beside the four other methods in `reconcile_methods.py`. End-volume (S17) is dropped; conformational is upgraded from Gaussian S4 to the integrated Marko–Siggia force.

Parameters: `L_c = 12.0 nm` (12 protein bonds × 1.0 σ); `l_p` from `xi_rl_candidates.LP_PHD` (rigid 84.6, semi 8.18, flex 1.14 nm).

## Per-system terms (k_B T per pair)

| label | l_p (nm) | D_bound (nm) | L_c (nm) | F_t | F_rot | F_conf (WLC) |
|---|---|---|---|---|---|---|
| rigid | 84.60 | 9.158 | 12.00 | -7.867 | -1.022 | +0.129 |
| semi | 8.18 | 8.148 | 12.00 | -7.867 | +0.299 | +0.865 |
| flex | 1.14 | 6.204 | 12.00 | -7.484 | +0.365 | +2.863 |

## Cross-system closure (k_B T)

| pair | ΔΔF_t | ΔΔF_rot | ΔΔF_conf | ΔΔF_sum | target | gap | closed |
|---|---|---|---|---|---|---|---|
| flex−rigid | +0.383 | +1.388 | +2.735 | **+4.506** | **+3.56** | +0.946 | +127% |
| semi−rigid | +0.000 | +1.321 | +0.736 | **+2.057** | **+2.68** | -0.623 | +77% |
| semi−flex | -0.383 | -0.066 | -1.999 | **-2.448** | **-0.90** | -1.548 | +272% |

## Bootstrap uncertainty (n = 20 frame-level resamples)

| pair | ΔΔF_t | ΔΔF_rot | ΔΔF_conf | ΔΔF_sum | target |
|---|---|---|---|---|---|
| flex−rigid | +0.383 ± 0.000 | +1.397 ± 0.014 | +2.735 ± 0.012 | **+4.516 ± 0.015** | +3.56 |
| semi−rigid | +0.000 ± 0.000 | +1.327 ± 0.024 | +0.737 ± 0.004 | **+2.064 ± 0.024** | +2.68 |
| semi−flex | -0.383 ± 0.000 | -0.070 ± 0.016 | -1.999 ± 0.013 | **-2.452 ± 0.025** | -0.90 |

## Notes on the formula

Marko–Siggia interpolation force `f l_p / k_BT = 1 / (4(1-x)²) − 1/4 + x`, integrated to give the stretching free energy

```
F_conf(D, l_p, L_c) / k_BT = (L_c / l_p) · [1/(4(1-x)) − 1/4 − x/4 + x²/2],  x = D/L_c
```

Valid for 0 ≤ x < 1. F diverges as x → 1 (chain fully extended). For rigid chains D_bound can approach L_c and the formula returns inf — see Discussion in `stage_essay.md` for what this means physically.

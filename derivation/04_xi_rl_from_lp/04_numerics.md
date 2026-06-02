---
type: derivation
status: accepted
date: 2026-06-02
summary: "04_numerics — paired-bootstrap implementation, parallelisation choices, and the σ_K2D correction (04_xi_rl_from_lp)"
derivation_folder: 04_xi_rl_from_lp
step: numerics
inputs: derivation/03 k2d_l_curve + k2d_l_stats; B2.2 z_lab arrays
outputs: code map + bootstrap protocol + footgun documentation
agent_read_when:
  - working on 04_xi_rl_from_lp or its successor
  - need to know why σ_K2D differs from derivation/03's numbers by √2
---

# 04_numerics — implementation choices

## Code anchor

`scripts/xi_rl_lp_prediction.py` is a standalone script (does NOT
extend `k2d_l_wlc_theory.py` because the bootstrap loop is independent
of the WLC MC). It imports `k2d_l_curve` + `k2d_l_stats` from
`k2d_l_wlc_theory` as the inner kernel.

| function | implements |
|---|---|
| `predict_xu_2015(k_a)`               | eq. (1.4) — ξ_RL = √(ξ_bond² + (kBT·L_ecto/(2 k_a))²) |
| `_bootstrap_worker(args)`            | one bootstrap iteration: independent (i_R, i_L) indices → σ_K2D_b |
| `bootstrap_sigma_k2d(z_R, z_L, ...)` | n_boot iterations + ProcessPoolExecutor parallelism |
| `run_production(n_boot, n_jobs)`     | full 3-system loop + ratio table + markdown writer |

## Bootstrap protocol (4.1)

| choice | value | why |
|---|---|---|
| n_boot                         | 200             | enough for σ on σ_K2D < 0.5 %, matches A3 / B1 conventions |
| sample size per boot           | n = 200 000     | full z_lab array; each boot reads the same 200 K but resampled |
| R and L indices                | independent     | correct convolution; derivation/03 used paired (R index = L index) |
| OPENBLAS / MKL threads         | 1 (set in env)  | prevent oversubscription with ProcessPoolExecutor |
| parallel axis                  | bootstrap iter  | embarrassingly parallel; n_jobs = 8 → ~40 s wall for 600 boots total |
| seeds                          | base + 31·i     | reproducible per system, distinct per boot |

## Why we changed from paired to independent draws

derivation/03 called `k2d_l_curve(z_lab, z_lab, l_grid)` passing the
**same array** twice. Inside `k2d_l_curve`:

```python
z_R = z_R_lab[:n]; z_L = z_L_lab[:n]
for i, l in enumerate(l_grid):
    dz = z_R + z_L - l        # ← if z_R = z_L (paired), dz = 2 z[i] - l
```

For paired draws the sum 2 z[i] has variance 4·Var(z); for independent
draws Var(z_R + z_L) = 2·Var(z) — a factor of 2 difference, propagating
into σ_K2D as √2. derivation/03's recorded σ_K2D = 1.42 / 5.45 / 3.91 nm
matches 1.110·√2 / 3.919·√2 (×0.71 doesn't apply uniformly because the
hard-gate kernel deforms the distribution; the empirical factors are
1.28 / 1.39 / 1.38, close to √2 = 1.41 modulo kernel curvature).

B2.4 fixes this by drawing two independent index sets per bootstrap:

```python
i_R = rng.integers(0, n, size=n)
i_L = rng.integers(0, n, size=n)
K2D_b = k2d_l_curve(z_lab[i_R], z_lab[i_L], l_grid)
```

The "primary" B2.4 numbers in 03_result.md are these independent-draw
values. derivation/03's paired numbers stay archived (and 03/05_OQ Q1
is now resolved: "the rigid 22.9 nm vs 22.4 nm peak mismatch was an
independent issue from kernel curvature, not from paired draws").

## Footgun documentation

If you call `k2d_l_curve(arr, arr, l_grid)` and `arr` has length n,
you get paired draws (z_R(i) = z_L(i)) silently. **For a true
convolution you must pass two independent arrays or two independent
slices**. The function does not warn; it simply does what you ask.

## Xu 2015 numerics (4.2)

Inputs from `results/xi_rl_candidates.npz`:

```
xi_bond              = 0.05377 nm        (LJ bond-well curvature)
rigid__k_a_eff       = 257.15 ε/rad²
semi__k_a_eff        = 252.32 ε/rad²
flex__k_a_eff        = 257.48 ε/rad²
```

Other constants (CLAUDE.md):

```
L_ecto = 7.0 nm     (7 ecto beads × 1.0 σ)
kBT    = 1.1 ε
```

Per-system Xu 2015 predictor:

| system | (kBT·L_ecto)/(2·k_a) | angular term (nm) | √(ξ_bond² + angular²) | ξ_RL^(Xu) (nm) |
|---|---:|---:|---:|---:|
| rigid | 1.1·7/(2·257.15) | 0.01497 | √(0.05377² + 0.01497²) | 0.0558 |
| semi  | 1.1·7/(2·252.32) | 0.01526 | √(0.05377² + 0.01526²) | 0.0559 |
| flex  | 1.1·7/(2·257.48) | 0.01495 | √(0.05377² + 0.01495²) | 0.0558 |

The angular term is **tiny** vs the bond term — Xu 2015 is dominated by
ξ_bond, which is the same across systems → identical predictions
modulo the 2% spread in k_a → ratio ≈ 1.

## Wall time

Pilot (rigid only × 20 boot × n_jobs=1): 2.5 s.
Production (3 systems × 200 boot × n_jobs=8): 40 s.
Per-boot cost ≈ 0.07 s (with parallelism amortised).

## Files produced

| path | content |
|---|---|
| `results/derivation_b2/xi_rl_lp_prediction.npz` | full boot trace + summary numbers + ratios |
| `results/derivation_b2/xi_rl_lp_prediction.md`  | rendered table for human readers |
| `results/scratch/pilot_xi_rl_lp/pilot_rigid_boot.npz` | pilot bootstrap dump (gitignored) |

## How to reproduce

```bash
conda activate phys
python scripts/xi_rl_lp_prediction.py --pilot                  # ~3 s; rigid only
python scripts/xi_rl_lp_prediction.py --n-boot 200 --n-jobs 8  # ~40 s; full
```

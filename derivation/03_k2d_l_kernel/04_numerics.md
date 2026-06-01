# 04_numerics — implementation choices for K2D(l) convolution

> **Status**: accepted
> **Date**: 2026-06-02
> **Author**: Claude (Opus 4.7)
> **Inputs**: scripts/k2d_l_wlc_theory.py; derivation/03 eqs. (1.4)–(1.11)
> **Outputs**: code map + grid choices + tail-truncation policy

## Code anchor

`scripts/k2d_l_wlc_theory.py` (already has B2.1 and B2.2) extends to B2.3:

| function | implements |
|---|---|
| `hard_lateral_acceptance(dz, rcut)`  | (1.4) v(dz) = π(rcut² − dz²) |
| `k2d_l_curve(z_R, z_L, l_grid)`      | (1.6) MC avg of v(z_R + z_L − l) over endpoint pairs |
| `k2d_l_stats(l_grid, K2D)`           | (1.7)–(1.11) K2D,max, l\*, ⟨l⟩, σ_K2D |

## Implementation choices (4.1)

| choice | what we use | why |
|---|---|---|
| Kernel form                  | hard gate (eq. 1.4)             | simplest analytic; quantitative absolute K2D not the goal here |
| rcut                         | 1.5 nm                          | matches `raw_tether_partition_k2d.py::HARD_R` |
| l-grid                       | 0 → 26 nm, Δl = 0.1 nm          | resolves rigid σ_K2D ≈ 1 nm; covers flex tail; 260 points |
| (z_R, z_L) sample size      | 200 000 each (= B2.2)           | reuses B2.2 z_lab; no extra MC |
| Truncation z < 0             | ON                              | chains that fold below the membrane are unphysical; convolving with the unphysical tail biases K2D toward negative l |
| Trapz integrator             | `np.trapezoid` (numpy ≥ 2.0)    | replaces deprecated `np.trapz` |

## Pilot (4.2)

The pilot uses 14 l-grid points × 2 nm spacing (Δl = 2 nm). Coarse — the
"σ_K2D" reported in pilot is dominated by grid resolution (~ 0.6 nm Δl
contribution to σ_K2D in quadrature → 1 nm floor). The pilot ONLY checks:
- K2D,max > 0
- l\* in plausible range [15, 25] nm for rigid

Production uses Δl = 0.1 nm and reports the true σ_K2D.

## Why truncate z < 0

In the absence of truncation, K2D(l) extends into negative l because the
chain endpoint can sample z < 0 (the WLC random walk fully samples both
half-spaces, with no membrane to enforce z > 0). These configurations
are unphysical — the chain cannot pass through the membrane to which it's
anchored.

Empirically, dropping z < 0 samples affects:
- **flex** the most (40 % of MC samples have z < 0)
- **semi** a little (5 % of samples)
- **rigid** negligibly (< 0.1 %)

Truncation is the simplest "membrane-impermeable" boundary condition. A
more physical alternative would be reflection (chains that would dip
below the membrane bounce back); deferred to 05_open_questions Q4.

## Files produced

| path | content |
|---|---|
| `results/derivation_b2/k2d_l_curves.npz` | K2D(l) + stats for 3 same-system pairs |
| `results/scratch/pilot_k2d_l_wlc/pilot_k2d_rigid.npz` | pilot's rigid×rigid K2D curve (gitignored) |

## How to reproduce

```bash
conda activate phys
python scripts/k2d_l_wlc_theory.py --pilot                  # ~1 s; all 3 steps pilot
python scripts/k2d_l_wlc_theory.py --n-mc 200000 --n-jobs 8 # 1.6 s; produces all 3 npz
```

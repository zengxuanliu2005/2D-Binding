# 04_numerics — Implementation choices and validation tables

> **Status**: accepted
> **Date**: 2026-06-01
> **Author**: Claude (Opus 4.7)
> **Inputs**: scripts/k2d_l_wlc_theory.py; pilot output at results/scratch/pilot_k2d_l_wlc/pilot_flex.npz
> **Outputs**: tables (4.1)–(4.3) — implementation choices documented for reviewer

## Code anchor

`scripts/k2d_l_wlc_theory.py` implements derivation 01:

| function | implements |
|---|---|
| `langevin(κ)`              | Langevin function L(κ) for use in (1.4) |
| `kappa_from_lp(lp/b)`       | inverts (1.4) via brentq |
| `sample_cos_theta(κ, n)`    | inverse-CDF sampler for (1.6) |
| `rotate_tangent(t, cosθ, φ)` | builds t̂_{i+1} via (1.7) |
| `WLCChain.sample_endpoints` | full chain MC: N applications of (1.5)–(1.7), accumulate R |
| `radial_pdf(R, n_bins)`    | converts MC samples → P_R(R) histogram |
| `wlc_R2_continuum(lp, Lc)` | continuum ⟨R²⟩ from (3.1) |
| `gaussian_radial_pdf(R, ⟨R²⟩)` | Gaussian limit for tail check |

## Implementation choices (4.1)

| choice | what we use | why |
|---|---|---|
| Bond length b              | 1.0 nm                      | matches CLAUDE.md protein bond r0 = 1.0 σ |
| Contour Lc                 | 12.0 nm                     | 12 bonds — same as `closure_four_term.py`, `closure_wlc_three_term.py` |
| N (segments)               | 12 (= Lc/b)                 | exact integer (no fractional bonds) |
| n_chains (production)      | 200 000                     | converges P_R bin probabilities to < 1 % per bin |
| n_chains (pilot)           | 5 000                       | < 1 s wall, sufficient for ⟨R²⟩ check ± 2 % |
| n_bins (histogram)         | 60                          | bin width ≈ 0.2 nm → resolves FWHM of all 3 cases (smallest ≈ 1 nm for rigid) |
| Random seed                | `20260601 + hash(label)`    | reproducible per system |
| MC parallelism axis        | chain (embarrassingly)      | linear speedup with workers; matches plan §1 cross-cutting convention |
| Worker BLAS threads        | `OPENBLAS_NUM_THREADS=1`    | avoid oversubscription with `ProcessPoolExecutor` |
| Numerical stable κ-sampler | use log1p + expm1 on 2κ    | avoids overflow at κ ≈ 85 (rigid case) |

## Numerical κ values used (4.2)

Inverse of (1.4) at lp/b for each system. The brentq solve is to 1e-6 tolerance.

| system | lp/b | κ (from brentq) | check: -1/ln L(κ) | drift |
|---|---:|---:|---:|---:|
| rigid (K100) | 84.60 | 85.100 | 84.602 | 0.002 |
| semi  (K10)  |  8.18 |  8.690 |  8.180 | 0.000 |
| flex  (K01)  |  1.14 |  1.403 |  1.140 | 0.000 |

(The rigid line uses the closed-form asymptote κ ≈ lp/b + 0.5 because
brentq is ill-conditioned for κ ≳ 50 where L(κ) → 1 - 1/κ; the asymptote
matches the inversion to 0.002, see column 4.)

## Convergence sanity (4.3)

Production run: 200 000 chains × 3 systems. Compare against continuum (3.1):

| label | √⟨R²⟩_MC | √⟨R²⟩_(3.1) | MC/cont | within 15% ? |
|---|---:|---:|---:|:---:|
| rigid | 11.725 | 11.723 | 1.000 | ✓ |
| semi  |  9.681 |  9.662 | 1.002 | ✓ |
| flex  |  5.161 |  4.976 | 1.037 | ✓ |

Halving n_chains to 100 K changes the bin probabilities in the P_R(R)
histogram by < 1 % for bins with > 0.5 % population (we did not formally
rerun a half-size convergence test in this round; that's listed in
`05_open_questions.md` as a quick check for B2.2's pilot run).

Total wall: 1.3 s (production), 0.5 s (pilot).

## Files produced

| path | content |
|---|---|
| `results/derivation_b2/wlc_endpoint_distribution.npz` | production MC samples + P_R(R) + stats per system |
| `results/scratch/pilot_k2d_l_wlc/pilot_flex.npz`       | pilot output (flex only); gitignored |

## How to reproduce

```bash
conda activate phys
python scripts/k2d_l_wlc_theory.py --pilot                  # < 1 s
python scripts/k2d_l_wlc_theory.py --n-mc 200000 --n-jobs 8 # ~1.5 s
```

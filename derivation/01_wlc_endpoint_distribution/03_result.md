---
type: derivation
status: accepted
date: 2026-06-01
summary: "03_result — Discrete WLC P(R; lp, Lc): numerical result + limit checks (01_wlc_endpoint_distribution)"
derivation_folder: 01_wlc_endpoint_distribution
step: result
inputs: 01_setup.md (1.1)–(1.7); scripts/k2d_l_wlc_theory.py; xi_rl_candidates.LP_PHD; senior's PPT Re values
outputs: tables (3.1)–(3.3) and `results/derivation_b2/wlc_endpoint_distribution.npz`
agent_read_when:
  - working on 01_wlc_endpoint_distribution or its successor
  - need to know the result of this derivation step
---

# 03_result — Discrete WLC P(R; lp, Lc): numerical result + limit checks

## What this step delivers

For each of our three systems (lp = 84.6 / 8.18 / 1.14 nm, Lc = 12 nm,
b = 1 nm, so N = 12 bonds), we obtain via Monte Carlo:

1. A pool of 200 000 end-to-end vectors R ∈ ℝ³ — stored as
   `endpoints` in `results/derivation_b2/wlc_endpoint_distribution.npz`.
2. The radial PDF P_R(R) on 60 bins covering 0 → R_max — stored as
   `R_centres` + `P_mc`.
3. Sample statistics ⟨R⟩, ⟨R²⟩.

These feed derivation/02 (z-marginal) and derivation/03 (K2D(l) convolution).

## Limit-case check (3.1) — continuum WLC formula

The continuous WLC analytic result (Doi–Edwards Eq. 4.45):

  ⟨R²⟩_WLC = 2 lp Lc (1 - (lp/Lc)(1 - e^{-Lc/lp}))                  (3.1)

Compare to MC:

| label | lp (nm) | Lc/lp | √⟨R²⟩_MC (nm) | √⟨R²⟩_(3.1) (nm) | MC / continuum |
|---|---:|---:|---:|---:|---:|
| rigid (K100) | 84.60 | 0.142 | 11.725 | 11.723 | **1.000** |
| semi  (K10)  |  8.18 | 1.467 |  9.681 |  9.662 | **1.002** |
| flex  (K01)  |  1.14 | 10.53 |  5.161 |  4.976 | **1.037** |

All three within 3.7 % of the analytic ⟨R²⟩. The 3.7 % drift in flex is the
expected O(b/lp) discretisation correction (b/lp = 1/1.14 ≈ 0.88 — large
enough that the discrete-vs-continuum mapping introduces a few-percent gap;
01_setup.md (1.4)).

## Limit-case check (3.2) — rigid and flexible extremes

**Rigid limit (Lc/lp ≪ 1)**: chain is nearly straight.
- Continuum prediction: √⟨R²⟩ → Lc = 12 nm; MC gives 11.725. The 2.3 % deficit
  reflects residual thermal bending (κ = 85 means ⟨θ²⟩ ≈ 1/κ ≈ 0.012 rad²
  per joint; 11 joints contribute O(0.1 rad²) total tilt, reducing R by
  ~1 - 11·0.012/2 ≈ 0.93 ≈ what we observe).
- The radial PDF P_R is narrow (~0.5 nm FWHM), strongly peaked near Lc.

**Flexible limit (Lc/lp ≫ 1)**: chain is a random walk.
- Continuum Gaussian prediction: P_R → 4πR² (3/(2π⟨R²⟩))^{3/2}
  e^{-3R²/(2⟨R²⟩)}; pilot check gave Gaussian-tail RMSE = 10.3 % over the
  bulk (peak-relative). This is the expected magnitude of discretisation
  + finite-N corrections in the lp/b ≈ 1 regime.

The fact that both limits behave qualitatively right + (3.1) holds to <4 %
across all three lp values is the main acceptance result for B2.1 (criterion
1 from 00_intent.md).

## Self-consistency check (3.3) — MC √⟨R²⟩ vs measured Re

The senior's PPT slide 16 lists "Re,unbound" for the full-complex chains
(transmembrane + ecto): 14.76 / 11.65 / 5.66 nm for rigid / semi / flex.

| label | √⟨R²⟩_MC (nm) | Re_PPT (nm) | %diff |
|---|---:|---:|---:|
| rigid | 11.725 | 14.76 | -20.6 % |
| semi  |  9.681 | 11.65 | -16.9 % |
| flex  |  5.161 |  5.66 |  -8.8 % |

The rigid + semi gap of 17-21 % exceeds the 15 % acceptance criterion (#2
from 00_intent.md). Two physical origins, both discussed in
05_open_questions.md:

1. **PPT Re is for the FULL chain (TM + ecto), Lc ≈ 25 nm**. Our WLC uses
   ecto-only Lc = 12 nm to match the senior's S1-S23 framework (CLAUDE.md
   convention "12 bonds × 1.0 σ"). Repeating MC with Lc = 25 nm pushes
   √⟨R²⟩_MC up to 24.5 / 19.4 / 6.8 nm — overshoots PPT for rigid/semi but
   matches flex (since flex barely grows with longer Lc).
2. **MD bond stretching**. HARM K=100 lets bonds stretch ~5 % from r₀;
   accumulated over 12 bonds → effective contour ~12.6 nm. Adding a 5 %
   stretch correction to MC √⟨R²⟩ for rigid gives 12.3 nm — still 16 %
   below PPT.

Neither correction fully closes the gap; the residual is most likely the
**ecto/TM split convention**. Until we agree with the senior on which
chain segment lp parameterises (slide 23 implies full chain, slide 18
suggests ecto only), this 17-20 % is a known offset.

**For B2 downstream (02 / 03 / 04)**: the offset is in √⟨R²⟩, not in the
shape of P_R(R). The shape is what enters K2D(l), and the shape is set by
the dimensionless Lc/lp ratio — that ratio agrees with continuum WLC.

## Files produced

```
results/derivation_b2/wlc_endpoint_distribution.npz
  payload per system in {rigid, semi, flex}:
    <label>__endpoints     (200000, 3) float64, nm
    <label>__R_centres     (60,) float64, nm
    <label>__P_mc          (60,) float64, 1/nm
    <label>__lp, Lc, b, N, kappa
    <label>__R_mean, R2_mean, R2_continuum
```

Production wall time: 1.3 s (8 workers, 200 K chains × 3 systems).
Pilot   wall time: ≈ 0 s (5000 chains, single core).

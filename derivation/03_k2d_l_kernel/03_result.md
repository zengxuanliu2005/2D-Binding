# 03_result — K2D(l) per same-system pair + σ_K2D

> **Status**: under-review (criteria 1+4 ✓; criterion 2 partial, 3 fails — see open questions)
> **Date**: 2026-06-02
> **Author**: Claude (Opus 4.7)
> **Inputs**: derivation/02 z_lab arrays; 01_setup.md eqs. (1.4)–(1.11)
> **Outputs**: tables (3.1)–(3.3); `results/derivation_b2/k2d_l_curves.npz`

## What this step delivers

For each of the 3 same-system R-L pairs, K2D(l) on a fine l-grid plus
the summary statistics (K2D,max, l\*, ⟨l⟩, σ_K2D).

Configuration:
- l grid: 0 → 26 nm, Δl = 0.1 nm (260 points)
- 200 000 (z_R, z_L) sample pairs per system from B2.2's z_lab arrays
- Hard-gate kernel: rcut = 1.5 nm, no angular factor
- z < 0 truncation: ON (drop chain endpoints that fold back through the membrane)

## Limit check (3.1) — peak position l\*

For symmetric R-L systems, the peak of K2D(l) should occur near
l\* ≈ ⟨z_R⟩ + ⟨z_L⟩ = 2·⟨z⟩ (the optimal membrane gap is where the R and
L binding beads can meet at the kernel centre).

| pair | 2·⟨z⟩ (from B2.2) | l\* (MC, this step) | match |
|---|---:|---:|---|
| rigid × rigid | 22.41 nm | 22.90 nm | ✓ (Δ = 0.49 nm) |
| semi × semi   | 13.32 nm | 18.70 nm | ✗ (Δ = 5.4 nm — see below) |
| flex × flex   |  3.42 nm |  3.50 nm | ✓ (Δ = 0.08 nm) |

The semi mismatch is real and traceable: the semi P_z(z) has a long
right tail (from rare configurations where the chain happens to extend
nearly straight). The peak of K2D(l) sits where the **product**
P_z^R(z_R)·P_z^L(z_L) is large for dz ≈ 0, which is skewed toward larger
l than 2·⟨z⟩. Documented in 05_open_questions Q1.

## Production table (3.2)

| pair | K2D,max (nm²) | l\* (nm) | ⟨l⟩ (nm) | σ_K2D (nm) | measured ξ_RL (nm) | ratio |
|---|---:|---:|---:|---:|---:|---:|
| rigid × rigid | 4.850 | 22.90 | 22.41 | **1.42** | 0.685 | 2.07 |
| semi × semi  | 1.107 | 18.70 | 14.08 | **5.45** | 2.076 | 2.63 |
| flex × flex  | 1.317 |  3.50 |  6.19 | **3.91** | 2.253 | 1.73 |

The predicted σ_K2D systematically overshoots measured ξ_RL by 1.7-2.6×.
Three contributing factors documented below.

## Acceptance check against criteria from 00_intent.md

1. **Shape sanity (rigid)**: peak at l\* = 22.9 ≈ 2·⟨z⟩ ✓; σ_K2D < 2 nm ✓
2. **Shape sanity (flex)**: peak near 2·⟨z⟩ ✓; σ_K2D = 3.9 ≈ √2·σ_z_flex ✓
3. **Monotone σ_K2D ordering** (rigid < semi < flex): **FAILS** — we get
   rigid < flex < semi (1.42 < 3.91 < 5.45). The two reasons in 05_OQ Q2-Q3.
4. **MC convergence**: spot-checked at 100 K and 200 K — σ_K2D drifts < 0.5 %.
   Formal halving test deferred to derivation/04. ✓

So criterion 3 is the one tagged "fails"; the others pass.

## Why σ_K2D overshoots measured ξ_RL by 2× (3.3)

Three contributions:

(a) **Predicted σ_z from B2.2 already exceeds measured σ(R_z) by ~1.8×**
    (B2.2 rigid σ_z = 0.625 nm vs PPT slide 5 σ(R_z) = 0.35 nm).
    The WLC + harmonic anchor model is not quantitatively calibrated to
    MD bond + angle force fields — see derivation/01 Q1, derivation/02 Q2.

(b) **The hard-gate kernel contributes rcut/√5 = 0.67 nm in quadrature**
    to σ_K2D. The soft-Boltzmann kernel (used in
    `raw_tether_partition_k2d.py`) has narrower effective width and would
    reduce σ_K2D by ~0.2 nm. Deferred to next round.

(c) **Hu/Xu's "ξ_RL" is a fitted parameter from K2D(ξ⊥) data, not σ of
    K2D(l) literally**. The Weikl 2016 convolution K2D(ξ⊥) =
    ∫ K2D(l) P(l) dl maps σ_K2D into ξ_RL through an intermediate σ of
    the membrane separation distribution P(l). For Gaussian K2D(l) and
    Gaussian P(l), ξ_RL² ≈ σ_K2D² + σ_p². If σ_p is system-dependent and
    of order 0.5–1 nm, this is the dominant explanation for the 2×
    discrepancy.

(a) is the most important — it pushes ALL three systems off by the same
factor. (b) and (c) shift the magnitude only modestly.

**For derivation/04 we'll predict ξ_RL using the measured chain-σ_z
directly (calibration-independent ratio test) and compare to σ_K2D/√2
or similar — see derivation/04 design.**

## Files produced

```
results/derivation_b2/k2d_l_curves.npz
  l_grid                     (260,) float64, nm
  rcut                       scalar, nm
  per system in {rigid, semi, flex}:
    <label>__K2D             (260,) float64, nm²
    <label>__K2D_max         scalar, nm²
    <label>__l_star          scalar, nm
    <label>__l_mean          scalar, nm
    <label>__sigma_K2D       scalar, nm
    <label>__Z               scalar, nm·nm² (∫K2D dl)
```

Total wall: 1.6 s (200 K pairs × 260 l-grid points × 3 systems).

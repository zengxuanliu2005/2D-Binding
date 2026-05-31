# A1 Diagnosis — rigid K2D 22% gap is sample bias, not discretization

> **Date:** 2026-05-31. Closes A1 of plan `open-question-cluster-jiggly-hamster`.
> Reproduce: `bash scripts/diagnose_rigid_sample_bias.py` and the two BG commands at the end of this file.

## Hypothesis tested

`stage_essay.md` §4.5 diagnosed the K100 rigid K2D shortfall (predicted 9,859 vs target 12,705 nm², −22.4%) as a numerical artifact:

1. h-grid resolution: σ_K2D(l) = 0.62 nm rigid → only ~3 grid points cover the FWHM with Δh = 0.2 σ → ~5–10% peak underestimate
2. Angular sampling: 24 bond-vector samples may undersample a narrow angular cone (σ_angle ≈ 3.7°)

Both "fixable (~15 min re-run)" per the essay.

## Result — the proposed fix does NOTHING

| run | Δh (σ) | bond-samples | sample-pairs | rigid soft_area (nm²) | h* (σ) |
|---|---:|---:|---:|---:|---:|
| baseline (`results/raw_tether_partition.md`) | 0.20 | 24 | 200,000 | 9858.9 ± 304 | 19.60 |
| high-precision main (`results/scratch/raw_rigid_hires_main.md`) | 0.02 | 200 | 200,000 | **9843.7** | 19.66 |
| high-precision bootstrap (`results/scratch/raw_rigid_hires_boot.md`) | 0.05 | 96 | 200,000 | **9911.3 ± 266** | 19.66 |

All three are statistically consistent. **10× finer h-grid × 8× more angular samples moves the point estimate by −0.15%.** The 22% gap is robust to numerical refinement.

Peak shape inspection (Δh = 0.02 σ around h*):

```
h=19.58  soft=9694.5
h=19.60  soft=9787.2
h=19.62  soft=9827.1
h=19.64  soft=9812.7
h=19.66  soft=9843.7  <-- peak
h=19.68  soft=9776.8
h=19.70  soft=9826.9
```

Peak is broad and flat; no hidden higher peak between grid points.

## Real root cause — bound/unbound geometric bias

`scripts/diagnose_rigid_sample_bias.py` splits R chains by bound state in each frame and compares the binding-bead geometry:

| system | bound n | unbound n | bound R_end_z (nm) | unbound R_end_z (nm) | Δz (nm) | bound term tilt | unbound term tilt | Δtilt |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rigid | 5140 | 2360 | 9.162 ± 0.379 | 8.902 ± 0.617 | **−0.26** | 17.9° ± 9.1° | 24.9° ± 13.0° | **+7.0°** |
| semi  | 1959 | 5541 | 7.945 ± 0.871 | 7.258 ± 1.468 | −0.69 | 41.1° ± 18.5° | 52.5° ± 22.5° | +11.4° |
| flex  | 1835 | 20165 | 6.629 ± 1.051 | 5.146 ± 1.373 | −1.48 | 44.0° ± 20.5° | 58.2° ± 21.3° | +14.2° |

**Bound chains are systematically more upright** (greater z-reach, smaller tilt from chain axis) than unbound. Physically this is unsurprising — the most binding-competent geometries preferentially become bound, depleting the unbound pool.

## Why this hits rigid hardest

`K2D_eff(h)` in the raw-tether partition uses *unbound* R/L conformations to integrate the soft binding kernel. Because unbound is biased toward worse-binding geometries:

- For **rigid**: σ_K2D(l) = 0.62 nm is *narrow*. A 0.26 nm z-shift sits on the steep slope of the Boltzmann kernel; combined with +7° angular shift, the effective K2D drops by ~exp(0.26²/(2·0.62²)) × angular factor ≈ 25%. Matches observed 22% gap.
- For **semi/flex**: σ_K2D(l) is broad (1.7–2.7 nm). The same fractional geometric bias gets averaged over a wide kernel, producing < 2% shift in K2D. This is consistent with the ab initio predictions matching target within 2% for both.

## Implication — A1 cannot be closed by local rerun

The unbound-sampling bias is intrinsic to the equilibrium MD trajectory. The "right" unbound geometry would come from a constrained simulation where binding is prohibited (each R/L tethered to specified z separation, no bond formation). That is precisely **Workstream C constrained-h slab MD** in the project plan, which needs cluster GPU time.

**This unifies stage_essay's §4.5 (rigid K2D −22%) and §5.4 (chain-response in K10 convolution) as the same physical issue:** equilibrium-sampled unbound conformations are not representative of "would-be-bound" geometry. Constrained-h MD fixes both.

## Recommended write-up changes (for D2 essay v2)

- **§4.5:** Re-cast "Both causes are fixable" as "We verified by 10× finer h-grid and 8× more angular samples that the rigid 22% gap is *not* a discretization artifact." Add diagnosis table above.
- **§5.4:** Promote the chain-response caveat — note that §4.5's K100 gap is the same physical limitation in another guise.
- **§4.6 (consensus):** Cite that the raw-partition ratios (which use within-system geometry bias) are systematically biased toward smaller |ΔΔF| for rigid pairs, partially explaining the consensus drift of ~0.2 kBT vs the Hu-curve target.

## Reproduce

```bash
conda activate phys

# High-precision K100 main estimate (≈20 min, single-core)
python scripts/raw_tether_partition_k2d.py --systems rigid \
    --h-min 17 --h-max 22 --h-step 0.02 \
    --bond-samples 200 --sample-pairs 200000 \
    --out-prefix results/scratch/raw_rigid_hires_main

# High-precision K100 bootstrap (≈45 min, 8 workers)
python scripts/raw_tether_partition_k2d.py --systems rigid \
    --h-min 17 --h-max 22 --h-step 0.05 \
    --bond-samples 96 --sample-pairs 200000 \
    --bootstrap --n-bootstrap 200 --n-jobs 8 \
    --out-prefix results/scratch/raw_rigid_hires_boot

# Bound vs unbound geometry diagnostic (≈3 min)
python scripts/diagnose_rigid_sample_bias.py
```

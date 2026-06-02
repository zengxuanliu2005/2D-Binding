---
type: derivation
status: accepted
date: 2026-06-02
summary: "03_result — Anchor-cone surcharge is +3.8 kBT for rigid, +1.2 kBT semi, -0.04 kBT flex — MS undercounts F_conf for stiff chains (05_fconf_selfconsistency)"
derivation_folder: 05_fconf_selfconsistency
step: result
inputs: results/derivation_b2/wlc_z_marginal.npz; results/closure_wlc_three_term.md
outputs: tables (3.1)-(3.4); results/derivation_b2/fconf_b2_selfconsistency.{npz,md}
agent_read_when:
  - working on 05_fconf_selfconsistency
  - need the headline F_conf comparison numbers
---

# 03_result — F_conf via -ln P_z(D_bound) vs Marko-Siggia

## What this step delivers

Per-system F_conf at the measured bound vertical reach D_bound, from
B2's z-marginal P_z, alongside Marko-Siggia (B1) and PPT s25.

Configuration:
- z_lab samples: 200 000 per system from B2.2's `wlc_z_marginal.npz`
- D_bound (nm): rigid 9.154 / semi 7.964 / flex 6.615 (from B1's chain_coords extracts)
- P_z(z=D) estimator: 200-bin histogram + linear interpolation
- Bootstrap: 200 frame-resamples × 8 workers

## Per-system table (3.1)

| system | D_bound (nm) | F_conf^(B2) ± boot σ | F_conf^(MS, B1) | Δ_anchor = B2 − MS |
|---|---:|---:|---:|---:|
| rigid | 9.154 | **+3.913 ± 0.075** kBT | +0.128 kBT | **+3.785** kBT |
| semi  | 7.964 | **+2.015 ± 0.015** kBT | +0.803 kBT | **+1.212** kBT |
| flex  | 6.615 | **+3.337 ± 0.034** kBT | +3.381 kBT | **−0.044** kBT |

Reading:
- **flex** — B2 and MS agree to within 50 mkBT. The anchor cone is
  invisible for a chain whose internal entropy already spans the full
  cone width. MS is an accurate F_conf for floppy chains.
- **semi** — B2 exceeds MS by 1.2 kBT. Partial anchor-cone visibility.
- **rigid** — B2 exceeds MS by **+3.8 kBT**, a factor-of-30 ratio.
  Marko-Siggia (which assumes a 3D-free chain) undercounts F_conf by
  this amount because it ignores the cone that holds chain orientation
  near +ẑ.

## Cross-pair ΔΔF_conf (3.2)

| pair | ΔΔF^(B2) ± boot σ | ΔΔF^(MS, B1) | ΔΔF_sum^(PPT s25) |
|---|---:|---:|---:|
| flex − rigid | **−0.576 ± 0.084** | +3.253 | +3.640 |
| semi − rigid | **−1.898 ± 0.076** | +0.675 | +2.470 |
| semi − flex  | **−1.322 ± 0.040** | −2.577 | −1.180 |

Note: ΔΔF_sum^(PPT s25) is the **3-term closure total** (trans + rot +
MS conformational), not F_conf alone — we display it for context only.

Reading:
- **B2 flips sign** on flex−rigid and semi−rigid pairs vs MS, because
  the anchor-cone surcharge is much larger for the rigid endpoint of
  each pair, dominating the chain-stretch cost MS captures.
- The B2 ΔΔF_conf for **semi−flex** keeps the same sign as MS (both
  negative) and is closer to PPT s25 total (B2 −1.32 vs PPT total −1.18)
  — coincidentally consistent within 0.14 kBT, but only because the
  PPT total here is dominated by ΔΔF_conf (rot and trans are small for
  this pair, see B1 table).

## Acceptance check against 00_intent.md criteria

1. **Flex agreement (B2 ≈ MS within 0.3 kBT)** — **✓** (|Δ_anchor| = 0.044)
2. **Rigid disagreement (B2 ≥ MS + 2 kBT)** — **✓** (Δ_anchor = +3.785)
3. **Bootstrap σ on F_conf < 0.1 kBT per system** — **✓** (max 0.075)
4. **Δ_anchor monotone in lp (rigid > semi > flex)** — **✓**
   (+3.785 > +1.212 > −0.044, range 3.83 kBT)

All four criteria pass. derivation/05 is **accepted**.

## What this means physically (3.3)

The Marko-Siggia formula `F = (Lc/lp)·g(D/Lc)` measures the free
energy required to **stretch** a worm-like chain from its natural end-to-end
distance to D, treating the chain as a 3D-free object. For lp ≫ Lc
(rigid), the natural state is already nearly fully extended, so even
stretching by 24% (Lc → D = 0.76·Lc) costs only 0.13 kBT.

In our system the chain is NOT 3D-free — it is **anchored to a membrane
via a stiff angular spring**. The lab z-coordinate of the binding bead
is set jointly by chain internal entropy AND anchor orientation. For
rigid chains, σ_z is dominated by Lc/κ_a ≈ 12/232 ≈ 0.05 nm in pure
limit (B2.2 gives 0.625 nm because anchor cone interacts with chain
end excursion). Either way, the natural state has z ≈ ⟨z⟩ ≈ 11.2 nm,
and asking the binding bead to land at z = 9.15 (i.e., 2 nm below
natural) is a 3-σ_z fluctuation — costing ≈ 3.9 kBT to maintain.

The decomposition is exact:

  F_conf^(B2) ≈ F^(MS)(stretch) + Δ_anchor(orientation cost)        (3.1)

with Δ_anchor(rigid) ≫ Δ_anchor(flex). MS captures only the first
term; PPT s25's 3-term closure (trans + rot + F^MS) inherits this
omission. **Adding the anchor-cone surcharge to PPT s25 would
ANTI-match the closure target** (Δ_anchor flips the sign of
ΔΔF_conf), so PPT s25's accidental partial agreement with measured
ΔΔF is *not* because it has the right F_conf — it's because errors in
F_conf cancel against the other terms in the trans-rot-conf budget.

## Files produced

```
results/derivation_b2/fconf_b2_selfconsistency.npz
  n_boot, n_bins, rms_b2_minus_ms, verdict
  per system in {rigid, semi, flex}:
    <label>__D_bound, F_conf_B2_mean, F_conf_B2_std,
    <label>__F_conf_B2_boot   (200,) float64 — bootstrap trace
    <label>__F_conf_MS        scalar — B1 reference
  per pair in {flex-rigid, semi-rigid, semi-flex}:
    ddF__<pair>__{B2, B2_se, MS, PPT_sum}

results/derivation_b2/fconf_b2_selfconsistency.md  (rendered table)
```

## How to reproduce

```bash
conda activate phys
python scripts/fconf_b2_selfconsistency.py --pilot                # ~0.1 s
python scripts/fconf_b2_selfconsistency.py --n-boot 200 --n-jobs 8 # ~1 s
```

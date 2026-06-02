---
type: derivation
status: accepted
date: 2026-06-02
summary: "04_numerics — histogram + linear interp P_z(D); bootstrap protocol; D_bound provenance (05_fconf_selfconsistency)"
derivation_folder: 05_fconf_selfconsistency
step: numerics
inputs: derivation/02 z_lab arrays; results/closure_wlc_three_term.md D_bound
outputs: code map + binning choice + D_bound table + footguns
agent_read_when:
  - working on 05_fconf_selfconsistency or its successor
  - changing the histogram bin count or the D_bound source
---

# 04_numerics — implementation choices for F_conf via P_z

## Code anchor

`scripts/fconf_b2_selfconsistency.py` is a standalone script. It
imports nothing from `k2d_l_wlc_theory.py`; the only inputs are the
B2.2 npz and three hardcoded D_bound numbers.

| function | implements |
|---|---|
| `estimate_p_z_at(z_samples, D, n_bins)`   | hist(z) + linear interp at D |
| `F_conf_from_p_z(z_samples, D, n_bins)`   | -log of above |
| `cross_pair_table_b25(F_per_system)`      | 3 pair differences |
| `bootstrap_F_conf(z_lab, D, n_boot, ...)` | frame-resample × n_boot |
| `run_production(n_boot, n_jobs, n_bins)`  | 3-system loop + cross-method table |

## Bootstrap protocol (4.1)

| choice | value | why |
|---|---|---|
| n_boot                  | 200            | matches B2.4 / A3 / B1 (σ on F_conf < 0.1 kBT achieved) |
| sample size per boot    | 200 000        | full z_lab array; resampled with replacement |
| index draw              | rng.integers(0, n, n) | iid resample within system |
| seeds                   | base + 31·i    | per-system base = 20260604 + hash(label) |
| parallel axis           | bootstrap iter | n_jobs = 8 → 1.1 s wall total |
| OPENBLAS / MKL threads  | 1 (env)        | prevent oversubscription |

## P_z estimator (4.2)

| choice | value | rationale |
|---|---|---|
| binning            | 200 uniform bins over observed z range | enough to resolve narrow rigid peak; not so fine as to over-fit noise on flex tail |
| density flag       | `density=True`                       | counts → 1/nm |
| interp at D        | `np.interp(D, centres, counts)`      | linear; bin centres on each side bracket D in all 3 systems |
| zero-bin fallback  | replace with min non-zero density    | guards against `ln 0 → -∞` in tail samples; never triggered in production |

Alternative considered: scipy.stats.gaussian_kde. Rejected because:
- KDE bandwidth choice (Silverman / Scott) is arbitrary for non-Gaussian
  shapes (semi P_z has long right tail).
- 200-bin histogram on 200 K samples has bin counts of order 1000;
  Poisson noise on F_conf is ~1/√1000 ≈ 0.03 kBT, well below bootstrap σ.
- KDE on 200 K samples is ~100× slower per bootstrap iteration with no
  clear precision win.

## D_bound provenance (4.3)

The three D_bound values come straight from
`results/closure_wlc_three_term.md` (B1 reimplementation, commit
`3dee6f0`), which extracts them from `chain_coords.npz`:

```python
ext_z_R = R_chain[12, 'z'] - R_chain[3, 'z']        # bind bead minus anchor
ext_z_L = -L_chain[12, 'z'] + L_chain[3, 'z']       # ligand z flipped
bound = bR_mask | bL_mask
D_bound = mean(concat([ext_z_R[bound_R], ext_z_L[bound_L]]))
```

System | D_bound (nm) | notes
---|---:|---
rigid | 9.154 | mean over ~ 14 K bound frames
semi  | 7.964 | mean over ~ 12 K bound frames
flex  | 6.615 | mean over ~ 8 K bound frames

Hardcoded into `fconf_b2_selfconsistency.D_BOUND_NM`. If chain_coords
extracts are updated (e.g., from cluster full-data rerun in Conflict
Map S1 / S2), update the constants in the script and rerun.

## Footgun documentation

1. **Density vs probability** — `np.histogram(..., density=True)`
   gives values in 1/nm. So `-ln P_z(D)` has an implicit `-ln(1 nm)`
   offset, which cancels in ΔΔF as long as you use the same definition
   for both systems. Not a footgun if used consistently; would be if
   we tried to compare F_conf^(B2) to a literal Boltzmann free energy
   from MD.

2. **D_bound vs ⟨z_chain⟩** — D_bound is the *vertical reach of the
   bound chain*, NOT ⟨z⟩ of unbound chains. The B2.2 P_z is over
   *unbound* z_lab (chains free to fluctuate in the cone). Evaluating
   P_z at D_bound asks "how often does a free chain accidentally land
   at the bound z?", which is the correct probability to feed -ln for
   F_conf in the dilute-binding limit.

3. **Sign convention** — F_conf > 0 means costly. The Marko-Siggia
   function in `closure_wlc_three_term.F_conf_wlc` also returns
   F > 0 for finite stretch. So both estimators have the same sign
   convention; Δ_anchor = F^(B2) − F^(MS) > 0 means B2 says it's
   harder (anchor cone penalty), which matches intuition for stiff
   chains.

## Wall time

- Pilot (rigid only × 20 boot × n_jobs=1): 0.1 s
- Production (3 systems × 200 boot × n_jobs=8): 1.1 s

The histogram + interp is fast; bottleneck is the bootstrap index
draw. n_boot ≥ 1000 still under 5 s if higher precision needed.

## Files produced

| path | content |
|---|---|
| `results/derivation_b2/fconf_b2_selfconsistency.npz` | full boot trace + summary + ratios |
| `results/derivation_b2/fconf_b2_selfconsistency.md`  | rendered table |

## How to reproduce

```bash
conda activate phys
python scripts/fconf_b2_selfconsistency.py --pilot                  # ~0.1 s
python scripts/fconf_b2_selfconsistency.py --n-boot 200 --n-jobs 8  # ~1 s
```

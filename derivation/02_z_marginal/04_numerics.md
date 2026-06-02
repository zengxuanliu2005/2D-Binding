---
type: derivation
status: accepted
date: 2026-06-02
summary: 04_numerics — implementation choices for the z-marginal (02_z_marginal)
derivation_folder: 02_z_marginal
step: numerics
inputs: scripts/k2d_l_wlc_theory.py; derivation/02 eqs. (1.1)–(1.8)
outputs: tables (4.1)–(4.2); code → derivation mapping
agent_read_when:
  - working on 02_z_marginal or its successor
  - need to know the numerics of this derivation step
---

# 04_numerics — implementation choices for the z-marginal

## Code anchor

`scripts/k2d_l_wlc_theory.py` (already implements derivation/01) extends to 02:

| function | implements |
|---|---|
| `sample_anchor_theta(κ_a, n)`     | (1.4) inverse-CDF: θ = √(−2 ln U / κ_a) |
| `apply_anchor_cone(R, κ_a)`        | (1.7) per-chain rotation z_lab = R_perp sin θ_a cos(φ_c − φ_a) + z_c cos θ_a |
| `z_marginal_pdf(z, n_bins)`       | (1.8) histogram → P_z(z) PDF normalised |
| `rigid_limit_z_stats(Lc, κ_a)`    | analytic prediction for synthetic straight chain |

## Implementation choices (4.1)

| choice | what we use | why |
|---|---|---|
| κ_anchor (rad⁻²)               | 255 / 1.1 = 231.8                  | k_a = 255 ε/rad² (essay §4.4), kBT = 1.1 ε (CLAUDE.md) |
| θ_anchor sampler              | inverse-CDF via Exp(κ/2) on θ²    | exact for small-angle Rayleigh; no rejection needed |
| φ_anchor sampler              | Uniform[0, 2π)                     | trivial; matches isotropy of the anchor cone |
| Independence of anchor / chain | yes (separate RNG, separate seed) | anchor wobble is uncorrelated with chain shape (different time scales physically) |
| n_chains (production)         | 200 000 (= B2.1)                   | reuses B2.1 endpoints; no extra MC cost |
| n_bins z-histogram            | 100                                | bin width ≈ 0.15 nm for rigid, 0.06 nm for flex |
| z range                       | auto = [min−0.1, max+0.1] nm       | covers full sampled range |

## Two sanity checks in the pilot (4.2)

The pilot runs both checks at every invocation:

**Sanity A**. Apply anchor cone to a synthetic perfectly-straight chain
(R = Lc · ẑ, 20 000 samples). Predict via `rigid_limit_z_stats`:
⟨z⟩ = Lc(1 − 1/κ_a), σ_z = Lc/κ_a. Pass criterion: relative match < 0.5 %.

**Sanity B**. Apply anchor cone to a real rigid-MC chain (20 000 samples).
Compare apply_anchor_cone output to the independent-rotation prediction
using ⟨z_c⟩ and ⟨R_perp²⟩ measured from the chain MC and ⟨cos θ_a⟩, ⟨sin² θ_a⟩
measured from a separate anchor sample. Pass criterion: relative match < 10 %.

Both pass exactly (to 4 decimal places) on 20 K samples each — fingerprinted
in `results/scratch/pilot_k2d_l_wlc/pilot_rigid_z.npz`.

## Files produced

| path | content |
|---|---|
| `results/derivation_b2/wlc_z_marginal.npz` | z_lab + P_z(z) per system |
| `results/scratch/pilot_k2d_l_wlc/pilot_rigid_z.npz` | both sanity-check arrays (gitignored) |

## How to reproduce

```bash
conda activate phys
python scripts/k2d_l_wlc_theory.py --pilot                  # < 1 s; passes Sanity A + B
python scripts/k2d_l_wlc_theory.py --n-mc 200000 --n-jobs 8 # 1.4 s; writes both 01 + 02 npz
```

## Why σ_z ∝ 1/κ_a (not 1/√κ_a) — a footgun for future-me

Naïve guess: σ_z = Lc · σ_θ. WRONG. Because the projection is `cos θ_a`,
not `θ_a`. For small angles cos θ ≈ 1 − θ²/2, so cos θ varies as θ²
varies. Var(cos θ) = ¼ Var(θ²) = ¼ · 4/κ_a² = 1/κ_a², hence σ_z = Lc/κ_a.

I (Claude) wrote σ_θ in the first draft of `rigid_limit_z_stats` and the
pilot caught it via Sanity A's 50× discrepancy. The fix is documented in
the docstring of `rigid_limit_z_stats` so the next reader doesn't hit it.

Lesson for derivation/04: when projecting onto a single axis, ALWAYS
compute Var via the projection, not via the angle directly. Same trap
will lurk in K2D(l) where we project the chain endpoint onto z one more time.

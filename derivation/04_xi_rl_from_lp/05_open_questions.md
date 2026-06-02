---
type: derivation
status: accepted
date: 2026-06-02
summary: "05_open_questions — semi/flex inversion (carried over from 03/Q2), absolute over-prediction, and the membrane-σ_p convolution gap (04_xi_rl_from_lp)"
derivation_folder: 04_xi_rl_from_lp
step: open_questions
inputs: 03_result tables; 03/05 Q2-Q3
outputs: open question list for derivation/05 or essay
agent_read_when:
  - working on 04_xi_rl_from_lp or its successor
  - planning derivation/05 (F_conf) or essay §5.3 update
---

# 05_open_questions — what B2.4 leaves on the table

## Q1 — semi:flex ratio inversion (B2 says 1.38, measured 0.92)

**Symptom**. B2 predicts σ_K2D(semi) > σ_K2D(flex), but measured
ξ_RL says semi ≈ flex (2.076 vs 2.253 nm). So B2 gets a ratio of
1.38 when the data wants ~ 0.92.

**Root cause**. Same as 03/05 Q2: with z<0 truncation ON, the flex
chain's broad P_z loses 40% of its mass; semi loses 5%; rigid < 0.1%.
After truncation flex effectively has a smaller σ_z than semi, so its
σ_K2D is smaller — inverting the naïve "broader chain → broader K2D"
expectation. This is a truncation-policy artifact, not a B2 framework
failure.

**Impact on the verdict**. The semi:flex ratio is the one row where
Xu 2015 (= 1.001) is accidentally closer to measured (0.921) than B2
(1.380). Cherry-picking this row makes Xu look acceptable; including
the other two (rigid:flex, rigid:semi) collapses Xu's win because Xu's
prediction is identically 1.00 across all three k_a-equal systems.

**Resolution paths** (deferred to next round / essay revision):

1. Reflection boundary instead of truncation: chains that would dip
   below the membrane bounce back rather than being dropped. This
   preserves more of flex's tail and increases σ_K2D(flex) toward
   σ_K2D(semi). Requires modifying derivation/01 MC sampler — a
   ~30-line change to `apply_anchor_cone`.
2. Document semi:flex as "tight" rather than monotone, accept the
   inversion as a feature of the truncation policy, and emphasize the
   two ratios where lp differs by ≥ 10× — see 03_result.md Verdict.
3. Use measured σ_z (from chain_coords MD extracts) instead of B2.2's
   WLC σ_z, then run the same K2D(l) convolution. This collapses the
   "WLC σ_z too wide" factor (03/03 §3.3 (a)) and might also fix
   the truncation inversion (because measured σ_z already has the
   membrane BC baked in).

## Q2 — Absolute σ_K2D over-predicts measured ξ_RL by 1.3-1.9×

**Symptom**. σ_K2D / ξ_RL_measured = 1.62 / 1.89 / 1.26 for rigid /
semi / flex (down from 03/03's 2.07 / 2.63 / 1.73 by √2 on rigid only;
semi and flex come down by smaller factors because their P_z's are
not Gaussian).

**Three contributing factors** (carried from 03/03 §3.3):

(a) **WLC σ_z is ~1.8× wider than measured σ(R_z)** (B2.2 rigid σ_z =
    0.625 nm vs PPT slide 5 σ(R_z) = 0.35 nm). The chain end-to-end
    distribution from a discrete WLC + harmonic anchor cone is not
    quantitatively calibrated to the MD bond + angle force-field
    detail. derivation/01 Q1 documents this.
(b) **Hard-gate kernel adds rcut/√5 ≈ 0.67 nm in quadrature** to σ_K2D.
    The soft-Boltzmann kernel from `raw_tether_partition_k2d.py` has
    narrower effective width and would reduce σ_K2D by ~0.2 nm.
(c) **Measured ξ_RL is NOT σ_K2D literally**. Senior's ξ_RL comes from
    fitting K2D(ξ⊥) = ∫ K2D(l) P(l) dl to a Gaussian in ξ⊥. The Weikl
    2016 convolution introduces a system-dependent σ_p (membrane gap
    width) that we don't model. For Gaussian K2D(l) and Gaussian P(l):
       ξ_RL² ≈ σ_K2D² + σ_p²
    If σ_p ≈ 0.5–1 nm, then ξ_RL ≤ σ_K2D, and ξ_RL = σ_K2D is an upper
    bound — consistent with our 1.3–1.9× over-prediction.

**The ratio test bypasses all three factors uniformly** (provided σ_p
is system-independent, which Hu's master curve says it is). That's the
robustness argument in 00_intent.md.

## Q3 — Soft-Boltzmann kernel still deferred

Same as 03/05 Q4. Hard gate is a 5-line analytic; soft kernel needs a
1D integral over `radial_u_kbt(r) + angle_factor(...)`. Trivial swap:

```python
def soft_lateral_acceptance(dz, ...): return ∫ K_bond(√(r² + dz²)) · 2π r dr
```

Would reduce σ_K2D by ~0.2 nm uniformly; ratio test unchanged.
Deferred to essay revision phase.

## Q4 — Reflection vs truncation BC

Same as Q1 above. Long-term improvement. Not blocking essay v2 if we
document the inversion as a truncation artifact.

## What carries forward to derivation/05

derivation/05 (F_conf via -ln P_z(D_bound)) uses the same B2.2 P_z
arrays as B2.4 — so any P_z calibration issue (Q2 factor (a)) shows up
in both. The F_conf prediction is therefore subject to the same
~1.8× σ_z mismatch from derivation/02 Q2. The strategy for derivation/05
is the analog of the "ratio test" here: compare ΔF_conf BETWEEN
systems (not absolute) to B1 closure (5.23 / 2.05 / −3.18 kBT) and PPT
s25 (3.64 / 2.47 / −1.18 kBT).

## Status carry-forward

Acceptance criteria from 00_intent.md:
1. rigid:flex ratio — **✓** (1.3× off, B2 8× better than Xu)
2. rigid:semi ratio — **✓** (1.2× off, B2 14× better than Xu)
3. Bootstrap σ — **✓** (0.15-0.18 % relative)
4. B2 ≥ 5× closer absolute on rigid — **✓** (relative-residual reading; see 03_result §3.4)

All four pass. derivation/04 is **accepted** and ready for essay §5.3
incorporation. The semi:flex inversion is the lone caveat; it does not
overturn the lp-discrimination headline.

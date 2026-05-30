# ξ_RL microscopic decomposition

**Question:** PhD's fitted ξ_RL (0.68 / 2.08 / 2.25 nm for rigid / semi / flex) — what microscopic quantity does it correspond to?

## Key measurements

| quantity | rigid | semi | flex |
|---|---:|---:|---:|
| ξ_RL fitted (PhD PPT) | 0.68 | 2.08 | 2.25 |
| σ(h_complex) anchor-to-anchor | 0.651 | 1.518 | 1.635 |
| σ_R unbound | 0.547 | 1.163 | 1.162 |
| σ_L unbound | 0.553 | 1.138 | 1.160 |
| σ_R bound | 0.363 | 0.776 | 1.017 |
| σ_L bound | 0.366 | 0.777 | 1.022 |
| σ_K2D(l) from K2D_eff(h) | 0.624 | 1.726 | 2.686 |
| k_a_eff (first anchor angle) | 257.2 | 252.3 | 257.5 |

## Hypothesis test matrix

| Hypothesis | rigid pred | rigid err | semi pred | semi err | flex pred | flex err | mean err |
|---|---:|---:|---:|---:|---:|---:|---:|
| H1 | 0.651 | 4.9% | 1.518 | 26.9% | 1.635 | 27.5% | 19.7% |
| H2 | 0.778 | 13.5% | 1.627 | 21.6% | 1.642 | 27.1% | 20.8% |
| H3 | 0.921 | 34.5% | 2.147 | 3.4% | 2.312 | 2.6% | 13.5% |
| H4 | 0.066 | 90.3% | 0.389 | 81.3% | 38.500 | 1608.7% | 593.4% |
| H5 | 0.056 | 91.8% | 0.056 | 97.3% | 0.054 | 97.6% | 95.6% |
| H6 | 0.624 | 8.8% | 1.726 | 16.8% | 2.686 | 19.2% | 14.9% |
| H7 | 0.516 | 24.7% | 1.098 | 47.1% | 1.441 | 36.0% | 36.0% |
| H8 | 0.831 | 21.3% | 1.873 | 9.7% | 2.179 | 3.3% | 11.4% |

## Hypotheses

| # | Description |
|---|---|
| H1 | ξ_RL = σ(h_complex) directly — PhD's literal label |
| H2 | ξ_RL = sqrt(σ_R² + σ_L²) unbound — R/L independent |
| H3 | ξ_RL = √2 × σ(h_complex) — interesting empirical match |
| H4 | Xu 2015: k_a = K_ecto literal, L0 = L_ecto |
| H5 | Xu 2015: L0_eff = min(L_ecto, lp), k_a = k_a_eff |
| H6 | ξ_RL = σ_K2D(l) from K2D_eff(h) Gaussian fit (Hu 2013 true definition) |
| H7 | ξ_RL = sqrt(σ_R² + σ_L²) bound-state |
| H8 | ξ_RL² = σ_complex² + σ_R_bound² + σ_L_bound² (additive model) |

## Finding

**ξ_RL has a crossover between two physical regimes:**

1. **Rigid (K=100):** ξ_RL ≈ σ(h_complex) ≈ σ_K2D(l) ≈ 0.65 nm. The K2D(l) width is dominated by the bond interaction well + minimal chain contribution. H1 and H6 both match within 10%.

2. **Semi-rigid / Flexible (K=10, K=0.1):** ξ_RL ≈ √2 × σ(h_complex). The K2D(l) width is dominated by chain flexibility. σ(h_complex) = 1.52/1.63 nm captures the bound-pair anchor-to-anchor fluctuation; the √2 factor arises because K2D(l) integrates over BOTH R and L chain endpoint distributions in the binding kernel. H3 matches within 3–4% for both systems.

**H6 (σ_K2D(l) directly measured from K2D_eff) is the theoretically correct definition** per Hu 2013 — ξ_RL ≡ width of K2D(l). It matches fitted ξ_RL within 9% for rigid (0.62 vs 0.68) but underestimates for semi (1.73 vs 2.08, −17%) and flex (2.69 vs 2.25, +19%). These deviations are the chain-response limitation: K2D_eff(h) is built from unbound conformations at the equilibrium membrane separation, so it misses the chain's conformational response to changing h. Constrained-h slab MD would resolve this.

**H3 (√2 × σ_complex)** is an empirical pattern that fits semi and flex almost perfectly:

| system | σ(h_complex) | √2·σ(h_c) | ξ_RL fitted | error |
|---|---:|---:|---:|---:|
| rigid | 0.651 | 0.921 | 0.685 | 34.5% |
| semi | 1.518 | 2.147 | 2.075 | 3.4% |
| flex | 1.635 | 2.312 | 2.253 | 2.6% |

The physical origin of √2: When chain flexibility dominates, K2D(l) width ≈ sqrt(σ_chain_R² + σ_chain_L²) = √2 × σ_chain per side. In the bound state, σ_chain is closely tied to σ(h_complex), giving ξ_RL ≈ √2 × σ(h_complex).

**H4-H5 (Xu 2015 formula) fail** because the anchor angle stiffness (k_a_eff ≈ 255 ε/rad²) is identical across all three systems — the first ecto angle (beads 2-3-4) is the anchor-linker transition, not the ecto-domain bending. The downstream ecto-domain flexibility (K=100/10/0.1) does not affect the first anchor angle but does affect the chain's overall endpoint distribution.

## Conclusion

**For the essay:** ξ_RL is the width of K2D(l). It can be measured directly from K2D_eff(h) via a Gaussian fit. For rigid receptors, this matches the fitted value. For semi/flexible receptors, K2D_eff(h) underestimates the width because chain conformations sampled at equilibrium h do not capture the chain's response to membrane separation changes (constrained-h MD needed). The empirical relation ξ_RL ≈ √2 × σ(h_complex_bound) for semi/flex is a compact approximation that could be tested against constrained-h slab data.

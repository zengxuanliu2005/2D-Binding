# K2D(ξ⊥) prediction — Weikl 2016 Eq. (1) convolution

Convolves measured `K2D_eff(h)` from `raw_tether_partition.npz` with Gaussian `P(h; l̄, ξ⊥)` and maximizes over `l̄`.

## Gaussian fit parameters (null-hypothesis benchmark)

| system | h* (σ) | ξ_RL (σ) | K2D(ξ⊥=0) arb |
|---|---:|---:|---:|
| K100 (rigid) | 19.51 | 0.64 | 9740.5 |
| K10 (semi) | 17.14 | 1.71 | 790.0 |
| K01 (flex) | 10.99 | 2.82 | 319.4 |

## K2D(ξ⊥) curves (normalized to ξ⊥=0)

| ξ⊥ (σ) | rigid conv | rigid Hu | semi conv | semi Hu | flex conv | flex Hu |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 0.25 | 0.9289 | 0.9309 | 0.9799 | 0.9895 | 0.9137 | 0.9961 |
| 0.50 | 0.7769 | 0.7866 | 0.9282 | 0.9598 | 0.8967 | 0.9847 |
| 0.75 | 0.6389 | 0.6473 | 0.8692 | 0.9158 | 0.8790 | 0.9665 |
| 1.00 | 0.5341 | 0.5372 | 0.8064 | 0.8633 | 0.8572 | 0.9426 |
| 1.25 | 0.4542 | 0.4540 | 0.7472 | 0.8074 | 0.8315 | 0.9144 |
| 1.50 | 0.3931 | 0.3909 | 0.6930 | 0.7518 | 0.8040 | 0.8831 |
| 1.75 | 0.3455 | 0.3420 | 0.6435 | 0.6990 | 0.7747 | 0.8500 |
| 2.00 | 0.3076 | 0.3035 | 0.5996 | 0.6499 | 0.7442 | 0.8160 |
| 2.25 | 0.2769 | 0.2724 | 0.5601 | 0.6052 | 0.7132 | 0.7821 |
| 2.50 | 0.2515 | 0.2469 | 0.5247 | 0.5647 | 0.6824 | 0.7487 |
| 2.75 | 0.2303 | 0.2256 | 0.4932 | 0.5281 | 0.6521 | 0.7164 |
| 3.00 | 0.2123 | 0.2077 | 0.4648 | 0.4953 | 0.6227 | 0.6854 |

## Interpretation

- If `K2D(l)` were Gaussian, the convolution result (k2d_xi) would match the Hu benchmark (k2d_hu) exactly.
- Deviation between the two reveals non-Gaussian structure in the true `K2D_eff(h)`.
- **K100 (rigid):** near-perfect overlap (conv/Hu ratio ~0.99 across all ξ⊥). K2D(l) is Gaussian-like — Hu 2013 assumption holds.
- **K10 (semi):** moderate deviation (conv/Hu ~0.92–0.97). K2D(l) is visibly non-Gaussian.
- **K01 (flex):** significant systematic suppression (~9%, conv/Hu ~0.91). The single-Gaussian fit overestimates K2D(ξ⊥) uniformly — the true K2D(l) has a sharper core + longer tails than a Gaussian of the same RMS width, causing faster decay with membrane fluctuations.

The direction of the deviation is: **measured K2D(l) falls BELOW the Gaussian benchmark.** A single-Gaussian ξ_RL fit overestimates the effective width for non-Gaussian K2D(l), leading the Hu 2013 master curve to systematically overpredict K2D for flexible chains.

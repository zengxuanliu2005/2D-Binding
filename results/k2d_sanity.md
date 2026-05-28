# K2D sanity check

Membrane patch: 120×120 σ² = 14400 nm².

| system | frames | ⟨N_bound⟩ | ⟨R_free⟩ | ⟨L_free⟩ | K2D ⟨per-frame⟩ ± SE (nm²) | K2D ratio-of-avg (nm²) | K2D,max (nm²) | observed/max |
|---|---|---|---|---|---|---|---|---|
| 15_120x120_K100_EPS05 | 500 | 10.28 | 4.72 | 4.72 | 12148.3 ± 514.1 | 6644.6 | 12705 | 95.62% |
| 15_120x120_K10_EPS05 | 500 | 3.92 | 11.08 | 11.08 | 527.6 ± 15.4 | 459.4 | 875 | 60.30% |
| 22_120x120_K01_EPS05 | 877 | 2.09 | 19.91 | 19.91 | 80.8 ± 1.8 | 76.0 | 362 | 22.31% |

## Notes

- Per-frame `K2D = N_bound · A / (N_R_free · N_L_free)`, averaged over frames.
- `K2D ratio-of-avg` uses `⟨N_bound⟩ · A / (⟨R_free⟩·⟨L_free⟩)` — differs from per-frame by O(fluctuation²).
- Free R / L counts use protein-index parity (even = R, odd = L), consistent with cross-pair binding where the simulator's bond record can pair any R with any L.
- Observed K2D < K2D,max is expected — the simulation runs at one fixed mean membrane separation, while K2D,max is the value at the optimal separation. The master curve `K2D = K2D,max · [1 + (ξ⊥/ξ_RL)²]^(-1/2)` connects them.
- **Pass criterion:** ordering rigid > semi > flex preserved, magnitudes within a factor ~5 of K2D,max.

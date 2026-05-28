# Anchor-frame chain coordinates

Per-frame, per-protein 13-bead Cartesian positions for all three flexibility
systems, packaged for the entropy decomposition work in `PLAN.md` Phase 2.

## Files

One `chain_coords.npz` per system, each containing:

| key            | dtype  | shape                       | content                                          |
| -------------- | ------ | --------------------------- | ------------------------------------------------ |
| `positions_R`  | f8     | `(n_frames, n_R, 13, 3)`    | receptor bead Cartesians, σ. Per-chain unwrapped |
| `positions_L`  | f8     | `(n_frames, n_L, 13, 3)`    | ligand   bead Cartesians, σ. Per-chain unwrapped |
| `bound_R`      | bool   | `(n_frames, n_R)`           | True iff R is in any bond that frame             |
| `bound_L`      | bool   | `(n_frames, n_L)`           | True iff L is in any bond that frame             |
| `partner_R`    | i4     | `(n_frames, n_R)`           | L slot R is bound to (-1 if unbound)             |
| `partner_L`    | i4     | `(n_frames, n_L)`           | R slot L is bound to (-1 if unbound)             |
| `box`          | f8     | `(3,)`                      | Lx, Ly, Lz in σ                                  |
| `n_frames`     | i      | scalar                      | number of frames                                 |
| `n_R`, `n_L`   | i      | scalar                      | number of receptors / ligands                    |

Coordinates are **per-chain unwrapped**: each protein's 13 beads are
guaranteed continuous across the periodic boundary (~3 % of chains in
`traj.xyz` straddle a box edge; the extractor detects a ~120-σ "bond"
along the chain and shifts the trailing beads to restore continuity).
Different chains may still live in different periodic images; for
inter-chain distances (e.g. R-to-L vectors) the consumer must apply MIC.

Chain bead order (chain_idx 0..12):

    0,1,2   anchor tail (RT/LT, idx 0 = outermost, membrane-embedded)
    3       anchor head (RH/LH, junction bead)
    4..11   ecto chain (RE/LE × 8)
    12      binding bead (RB/LB)

## How to regenerate

```bash
for s in 15_120x120_K100_EPS05 15_120x120_K10_EPS05 22_120x120_K01_EPS05; do
    python scripts/extract_chain_coords.py outputs/$s/s001
done
python scripts/sanity_chain_coords.py
```

`extract_chain_coords.py` finishes in ~5 s for K100/K10 and ~10 s for K01.

## Sanity checks (`scripts/sanity_chain_coords.py`)

Recomputes Re from the NPZ and compares to the byte-validated
`results/extracted/<sys>/result_Re_complex.dat`. Multisets match at
`atol=1e-4` for all three systems. Per-chain bond lengths peak at
1.067 ± 0.065 σ across all systems (FENE/HARM bonds in the model).
End-to-end distances after unwrap match the expected polymer-physics
regimes (~contour for K=100, Gaussian for K=0.1).

## Physical findings from this data set

End-to-end distance summary (σ, mean ± std over all frames and proteins):

|         | R E2E (bound) | R E2E (unbound) | L E2E (bound) | L E2E (unbound) |
| ------- | ------------- | --------------- | ------------- | --------------- |
| K100    | 12.59 ± 0.25  | 12.54 ± 0.27    | 12.59 ± 0.24  | 12.55 ± 0.26    |
| K10     | 11.71 ± 0.58  | 11.32 ± 0.93    | 11.73 ± 0.57  | 11.32 ± 0.94    |
| K01     | 10.19 ± 0.96  |  8.98 ± 1.22    | 10.16 ± 0.93  |  9.00 ± 1.22    |

- **R and L have the same flexibility within each system** (E2E
  distributions are statistically indistinguishable). `ref/nvt-md.py`'s
  receptor=K100 / ligand=K10 asymmetry does not match the data — the
  actual K10 run used K=10 for both ecto domains.
- **Bound chains are more extended than unbound**, by an amount that grows
  with flexibility: +0.04 σ for K100, +0.40 σ for K10, +1.18 σ for K01.
  This is part of the conformational entropy cost of binding that the
  decomposition needs to account for.

# Harmonized per-pair observables (Re, binding_vector)

Output of `scripts/extract_complex.py` on each system's `s001`. The
extractor streams `traj.xyz`, classifies bonds from
`num_bonds_for_xyz_frames.dat`, and writes legacy-compatible files.

## Validation

`scripts/validate_against_legacy.py` byte-compares against the PhD's
existing files in `outputs/<sys>/s001/`:

- K100 (rigid) — `result_Re_complex.dat`, `binding_vector_final_bound_vectors.tsv`,
  `binding_vector_final_unbound_vectors.tsv`: **IDENTICAL**.
- K10  (semi)  — same three files: **IDENTICAL**.
- K01  (flex)  — legacy files do not exist; these outputs are the harmonized
  replacement, computed by the same code path as K100/K10.

## Definitions (recovered from the legacy K100/K10 outputs)

- **Protein indexing.** A protein's "atom-based index" is `(atom - n_lipid_atoms) / 13`,
  giving 0..2N−1 across the N receptor–ligand pairs. Even indices are
  receptors, odd indices are ligands. Bonds can be **cross-pair** (any R may
  bind any L) — ~25 % of K100 frames have at least one cross-pair bond.

- **Re** (`result_Re_complex.dat`):
  `Re = |pos(R_chain_idx_5) - pos(L_chain_idx_5)|` with periodic-image wrap
  (Lx = Ly = 120 σ, Lz = 50 σ). Chain index 5 is the second RE/LE bead from
  the anchor head, marked `S` in the trajectory's visualization labels.

- **binding_vector** (`binding_vector_final_*_vectors.tsv`):
  for a receptor, `bv = pos(chain_idx_5) - pos(RB)` with periodic-image wrap.
  For a ligand, the z component is then negated, so both proteins'
  binding-vectors point with -z (downward) into the binding gap.

- **bound** classification: ground truth is the simulator's bond record in
  `num_bonds_for_xyz_frames.dat` (one row per frame, each bond logged by the
  two chain_idx_11 atoms — the binding-angle partners of RB/LB). The
  RB-LB threshold (3.0 σ) in `extract_complex.py` is only a sanity check.

## Frame counts

| system  | frames | bound entries | unbound bv entries |
| ------- | -----: | ------------: | -----------------: |
| K100    |    500 |          5140 |               4720 |
| K10     |    500 |          1959 |              11082 |
| K01     |   1000 |          1835 |              40330 |

## Files per system

- `result_Re_complex.dat` — one row per (frame, bond): `frame R_idx L_idx Re Re²`.
- `result_stats_complex.dat` — per-frame mean ⟨Re⟩ and ⟨Re²⟩ over bound pairs.
- `binding_vector_final_bound_vectors.tsv` — per-bond, per-protein
  binding-vector for the proteins involved in any bond that frame.
- `binding_vector_final_unbound_vectors.tsv` — same observable for proteins
  not involved in a bond that frame.
- `bond_state.tsv` — per-frame, per-bond log of `(frame, R_proto, L_proto, RB-LB distance)`.

## How to regenerate

```bash
python scripts/extract_complex.py outputs/15_120x120_K100_EPS05/s001
python scripts/extract_complex.py outputs/15_120x120_K10_EPS05/s001
python scripts/extract_complex.py outputs/22_120x120_K01_EPS05/s001
python scripts/validate_against_legacy.py
```

All three runs finish in well under a minute on a laptop.

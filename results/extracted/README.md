# Harmonized per-pair observables (Re, binding_vector)

Output of `scripts/extract_complex.py` on each system's `s001`. The
extractor streams `traj.xyz`, classifies bonds from
`num_bonds_for_xyz_frames.dat`, and writes legacy-compatible files.

## Validation

`scripts/validate_against_legacy.py` byte-compares against the PhD's
existing files in `outputs/<sys>/s001/`.

Identical (byte-equal) against K100 **and** K10:

- `result_Re_complex.dat`
- `binding_vector_final_bound_vectors.tsv`
- `binding_vector_final_unbound_vectors.tsv`
- `bindsites_rxryrz_distribution.tsv`
- `bindsites_angle_distribution.tsv`
- `EC_angle_distributed_unbind.tsv`

`EC_angle_distributed_bind.tsv`:

- K10: value-set IDENTICAL — every line that appears in legacy also appears in
  ours and vice versa, but row ordering in frames containing cross-pair bonds
  could not be reverse-engineered from K100/K10 alone (the legacy ordering
  rule for the L-chain of a cross-pair bond is opaque). Statistics computed
  from these values are unaffected.
- K100: same as K10, except for a single row where legacy prints `0.000000`
  and ours prints `0.000001` (a 1×10⁻⁶ floating-point rounding difference in
  one of 51 400 angle deviations). Statistically negligible.

K01 legacy files do not exist — our outputs are the harmonized replacement,
computed by the same code path.

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
- `bindsites_rxryrz_distribution.tsv` — per-bond RB-LB vector (rx, ry, rz, |r|),
  one row per bond, raw num_bonds order. Magnitude is the bond length in σ.
- `bindsites_angle_distribution.tsv` — per-bond (θ_atom1, θ_atom2) binding
  angles in degrees. Taken directly from `num_bonds_for_xyz_frames.dat`
  columns 2 and 3 (the simulator's own higher-precision output, not
  recomputed from the lower-precision `traj.xyz`).
- `EC_angle_distributed_{bind,unbind}.tsv` — per-chain, 5 values per chain.
  Each value is (180° − ecto-bend angle) at chain-mid {7, 8, 9, 10, 11}
  (the five ecto angles nearest the binding bead). With min-image PBC wrap
  so unbound chains straddling a box boundary are handled correctly.

## How to regenerate

```bash
for sys in 15_120x120_K100_EPS05 15_120x120_K10_EPS05 22_120x120_K01_EPS05; do
    python scripts/extract_complex.py        outputs/$sys/s001
    python scripts/extract_bindsites_ecangle.py outputs/$sys/s001
done
python scripts/validate_against_legacy.py
```

All six runs finish in ~30 s combined on a laptop.

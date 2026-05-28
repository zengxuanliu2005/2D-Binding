# Observables inventory — s001 of each flexibility class

Generated: 2026-05-28 (Session 0, reconnaissance only).

Systems on disk (local repo, s001 only):

| folder                          | K (ligand ecto) | label  | atoms (mol.psf) |
| ------------------------------- | --------------- | ------ | --------------- |
| `outputs/15_120x120_K100_EPS05` | 100             | rigid  | 144198          |
| `outputs/15_120x120_K10_EPS05`  | 10              | semi   | 144198          |
| `outputs/22_120x120_K01_EPS05`  | 0.1             | flex   | 144380          |

Note: K01 has a different total atom count (144380 vs 144198) — the `15`/`22`
prefix refers to **protein count** (15 vs 22 receptor–ligand pairs, presumably),
so K01 is not just "K=0.1 with same geometry" — its system size differs.
This must be normalised out before any per-pair comparison.

## File-presence matrix

`✓ = present`, `✗ = missing`, **bold** = K01-only legacy file.

| file                                              | K100 (rigid) | K10 (semi) | K01 (flex) | notes                                                  |
| ------------------------------------------------- | :----------: | :--------: | :--------: | ------------------------------------------------------ |
| `traj.xyz`                                        |      ✓       |     ✓      |     ✓      | 2–4 GB; never load whole into memory                   |
| `mol.psf`                                         |      ✓       |     ✓      |     ✓      | atom types all generic `C` — types NOT here            |
| `state.cpt`                                       |      ✓       |     ✓      |     ✓      | XML checkpoint — likely has real bead types            |
| `bond.dat`, `energy_momentum.dat`                 |      ✓       |     ✓      |     ✓      | large MD dumps                                         |
| `mid_planes.xyz`, `num_bonds_for_xyz_frames.dat`  |      ✓       |     ✓      |     ✓      |                                                        |
| `anchor_angle_distributed_{bind,unbind}.tsv`      |      ✓       |     ✓      |     ✓      | one value per sample                                   |
| `theta_angle_distributed_{bind,unbind}.tsv`       |      ✓       |     ✓      |     ✓      |                                                        |
| `complex_distance_bind.tsv`                       |      ✓       |     ✓      |     ✓      |                                                        |
| `complex_distance_to_membrane_distributed_bind`   |      ✓       |     ✓      |     ✓      |                                                        |
| `R_distance_to_membrane_distributed_{b,u}.tsv`    |      ✓       |     ✓      |     ✓      |                                                        |
| `L_distance_to_membrane_distributed_{b,u}.tsv`    |      ✓       |     ✓      |     ✓      |                                                        |
| `roughness.tsv`                                   |      ✓       |     ✓      |     ✓      | **bond-index range differs** (K100: 6-13, K01: 0-5)    |
| `binding_vector_final_{bound,unbound}_vectors`    |      ✓       |     ✓      |     ✗      | new                                                    |
| `bindsites_rxryrz_distribution.tsv`               |      ✓       |     ✓      |     ✗      | new                                                    |
| `bindsites_angle_distribution.tsv`                |      ✓       |     ✓      |     ✗      | new                                                    |
| `EC_angle_distributed_{bind,unbind}.tsv`          |      ✓       |     ✓      |     ✗      | new                                                    |
| `result_Re_complex.dat`                           |      ✓       |     ✓      |     ✗      | per-frame per-pair Re                                  |
| `result_Re.tsv`                                   |      ✓       |     ✓      |     ✗      | 1-line summary                                         |
| `result_stats_complex.dat`                        |      ✓       |     ✓      |     ✗      | per-frame ⟨Re⟩,⟨Re²⟩                                   |
| `roughness_l.tsv`                                 |      ✓       |     ✓      |     ✗      | with sum_lsq column                                    |
| `frame_20.xyz`, `frames_1-3.xyz`, `frame_1.xyz`   |   ✓ / ✓ /   |   / ✓ /✓   |     ✗      | snapshots                                              |
| **`phi_angle_distributed_{bind,unbind}.tsv`**     |      ✗       |     ✗      |   **✓**    | legacy K01-only φ angle                                |
| **`result_Re_distributed_{bind,unbind}.tsv`**     |      ✗       |     ✗      |   **✓**    | legacy K01-only Re storage (one value per line)        |

## Re storage reconciliation

Re is stored differently across systems:

- **K10 / K100 (newer):** `result_Re_complex.dat`, with columns
  `frame  R_idx  L_idx  Re  Re²` — per-frame, per-receptor-ligand pair.
  Bound/unbound is not split in this file; the bound subset must be intersected
  with bond presence from `bond.dat` or `result_stats_complex.dat`.
  `result_Re.tsv` is a 1-line summary: `Bind_Re | Bind_count | Unbind_Re | Unbind_count`.
- **K01 (legacy):** `result_Re_distributed_{bind,unbind}.tsv` — already split
  into bound vs unbound, one Re value per sample, no frame/pair index retained.

Mapping: K01's `result_Re_distributed_bind.tsv` corresponds to the rows of
K10/K100's `result_Re_complex.dat` whose pair is bonded in that frame.
The newer extractor preserves provenance (frame, pair indices) — the legacy
K01 file does not. Re-extracting K01 from `traj.xyz` will recover provenance.

## Column conventions (verified by `head`)

| file                                             | columns                                                         |
| ------------------------------------------------ | --------------------------------------------------------------- |
| `*_angle_distributed_{bind,unbind}.tsv`          | one angle (degrees) per line — raw samples, NOT a histogram     |
| `binding_vector_final_bound_vectors.tsv`         | `frame  protein_index  rx  ry  rz  r` (header line present)     |
| `bindsites_rxryrz_distribution.tsv`              | rx, ry, rz, r (σ); 4 columns, no header                         |
| `bindsites_angle_distribution.tsv`               | 2 angle columns (degrees), no header                            |
| `EC_angle_distributed_*.tsv`                     | header `Angle`; one angle (degrees) per line                    |
| `roughness.tsv`                                  | `#bonds roughness sum_l count`                                  |
| `roughness_l.tsv`                                | `#bonds roughness sum_lsq sum_l count`                          |
| `result_Re_complex.dat`                          | header line `# frame R_idx L_idx Re Re2`; values in σ           |
| `result_stats_complex.dat`                       | `# frame <Re> <Re²>`                                            |

## Roughness bond-index discrepancy

K10 / K100 list bond counts 6–13. K01 lists 0–5. Same column meaning, but the
bond-count axis is offset (or differently defined). Cannot be combined without
reconciling — flag for the PhD when she's reachable.

## Bead-type identification — open question

`mol.psf` contains only generic `C` atom-type labels and `traj.xyz` uses
visualisation labels (`N` for heads, `O` for tails). The real bead-type
identity (`H`, `T`, `T1`, `RH`, `RT`, `RE`, `RB`, `LH`, `LT`, `LE`, `LB`) is
NOT in either file. To map atom-index → bead type the extractor must parse
either (a) `state.cpt` (XML checkpoint, expected to carry real types), or
(b) the system-builder script that produced the initial XML. Resolving this
is a prerequisite for writing any from-`traj.xyz` extractor.

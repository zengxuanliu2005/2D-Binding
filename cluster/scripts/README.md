---
purpose: "Index of cluster/scripts/: 21 Python modules + shell scripts grouped by function"
audience: anyone running the bundle or modifying analysis code
status: current
---

# cluster/scripts/ — analysis modules

These are copies of the analysis scripts that ship inside the cluster bundle.
The development tree at `scripts/` (top-level of the repo) is the source of
truth; these are kept in sync by the maintainer so the bundle is
self-contained when shipped to the off-site full-data run.

## Grouped index

### Extract pipeline (chain_coords from MD traj.xyz)

| script | purpose |
|---|---|
| `extract_chain_coords.py` | core extractor — reads `outputs/<system>/<replica>/traj.xyz` + topology, emits `chain_coords.npz` (per-frame, per-chain bead positions + bound flags + partner ids) |
| `extract_one_replica.py` | thin CLI wrapper around `extract_chain_coords` used by the trial pipeline (Step 4) and `run_analysis.sh` |
| `extract_parallel.py` | reads `(system, replica_dir, out_path)` tuples from stdin and parallel-extracts via `ProcessPoolExecutor`; used by `run_analysis.sh` |
| `extract_complex.py` | extracts bound-complex configurations (used by the rotational closure term) |
| `merge_chain_coords.py` | concatenates per-replica `chain_coords.npz` files along the frame axis, per system |
| `explore_replicas.sh` | one-shot inventory script: count replicas per system, write `inventory.tsv` |

### Closure framework (ΔΔF decomposition)

| script | purpose |
|---|---|
| `closure_four_term.py` | the S1–S23 four-term closure: F_trans + F_conf + F_bond + F_rot per pair, optional `--bootstrap` |
| `closure_wlc_three_term.py` | the three-term Marko–Siggia closure reimpl of the source PPT slide 25 |
| `free_energy_terms.py` | shared physics functions: F_trans, F_conf (S4 Gaussian), F_bond, F_rot (mutual information) |
| `system_inputs.py` | `SystemInputs` dataclass + `system_inputs_from_arrays()` — used by both closure scripts and bootstrap loops |
| `reconcile_methods.py` | 5-method ΔΔF consensus + bootstrap σ + pairwise gaps; writes `results/method_reconciliation.md` |

### Ab initio K2D (raw partition; Mayer f-function)

| script | purpose |
|---|---|
| `raw_tether_partition_k2d.py` | walks raw traj.xyz, applies binding-kernel (soft Boltzmann + angle factor), integrates over R/L pair geometry → K2D,max per system + ΔΔF |
| `xi_rl_candidates.py` | computes microscopic ξ_RL candidates (σ_complex, σ_K2D(l), bond curvature, etc.) from chain_coords |
| `analyze_slab_traj.py` | C.4 — measures K2D(l=h) per (system, h) from constrained-h slab MD traj.xyz; pilot synthesises Gaussian endpoints from B2.2 z-stats when real slab data is absent |

### Diagnostics

| script | purpose |
|---|---|
| `diagnose_bound_vs_unbound.py` | A1 — compares bound vs unbound chain geometry per system (was `phd_diagnose_rigid_sample_bias.py` pre-Session 3 refactor) |

### Molecular dynamics

| script | purpose |
|---|---|
| `nvt-md-constrained-h.py` | NVT MD with z-tether constraint (constrained-h slab MD; Workstream C); skeleton — pygamd API hooks left as TODO until the trial Step 3 confirms the import path |

### Utilities (used by other scripts above)

| script | purpose |
|---|---|
| `topology.py` | parses `mol.psf` → receptor/ligand chain bead indices, lipid count |
| `io_xyz.py` | streaming `traj.xyz` reader (`iter_frames(file, subset_indices=...)`) — never loads the whole file |
| `bonds.py` | parses `num_bonds_for_xyz_frames.dat` → per-frame R-L bond pair lists |
| `features.py` | helper functions for extracting per-chain features (axes, end-vectors, etc.) |
| `bat.py` | bond-angle-torsion utilities (used by closure_wlc_three_term and conf_entropy paths) |

## How they're invoked

The orchestrator `cluster/run_analysis.sh` (or its SBATCH wrapper
`cluster/slurm/full_analysis.slurm`) invokes the scripts in this order:

1. `explore_replicas.sh` → inventory.tsv
2. `extract_parallel.py` → per-replica `chain_coords.npz`
3. `merge_chain_coords.py` → merged per-system `chain_coords.npz`
4. `closure_four_term.py --bootstrap` → `results/closure_four_term_data.{md,npz}`
5. `closure_wlc_three_term.py --bootstrap` → `results/closure_wlc_three_term.{md,npz}`
6. `raw_tether_partition_k2d.py --bootstrap` → `results/raw_tether_partition.{md,npz}`
7. `diagnose_bound_vs_unbound.py` → distilled txt
8. `reconcile_methods.py` → `results/method_reconciliation.md`

Distilled outputs end up under `cluster/outputs/distilled/` ready to tar
and return.

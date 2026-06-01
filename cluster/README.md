# cluster/ — workflow for cluster-side runs

This folder mirrors what runs on the group cluster (`master`, repo path
`/mnt/nfs/ugstu/liuzx/2D-Binding`). Local `scripts/` is for s001 single-replica
analysis; cluster `scripts/` is for multi-replica extract + slab MD pipelines.

## Two pipelines

| § | what | files | scope |
|---|---|---|---|
| **§0** | data-volume test — extract chain_coords from ALL replicas to test the "100× data closes A1/B1 gaps" hypothesis | `scripts/explore_replicas.sh`, `extract_one_replica.py`, `merge_chain_coords.py`; `slurm/array_extract.slurm`; `analysis/run_section0_full.sh` | first, cheapest |
| **C** | constrained-h slab MD — 3 systems × 6 h values, fixed membrane gap, no R-L binding, directly measure K2D(l) | `scripts/nvt-md-constrained-h.py`, `analyze_slab_traj.py`; `slurm/array_slab_md.slurm`, `single_pilot.slurm`; `analysis/run_slab_full.sh` | only if §0 doesn't close the gap |

## Login + first-time setup

```bash
ssh master
cd /mnt/nfs/ugstu/liuzx/2D-Binding
bash cluster/env_setup/check_env.sh
```

Expected: phys env activates, pygamd imports, /mnt/nfs/ugstu/liuzx has disk.
If pygamd missing → `bash cluster/env_setup/install_phys.sh` (TODO: fill in once we know what's there).

## §0 workflow — full

```bash
# 1. Inventory replicas per system (< 1 min)
bash cluster/scripts/explore_replicas.sh
cat cluster/results/section0/inventory.tsv

# 2. Pilot extract (1 system × 2 replicas, < 5 min on 1 GPU node)
SYS=15_120x120_K100_EPS05 sbatch --array=1-2 cluster/slurm/array_extract.slurm

# 3. Verify pilot output then production array
# (edit array range in slurm file to match inventory; one sbatch per system)
SYS=15_120x120_K100_EPS05 sbatch cluster/slurm/array_extract.slurm
SYS=15_120x120_K10_EPS05  sbatch cluster/slurm/array_extract.slurm
SYS=22_120x120_K01_EPS05  sbatch cluster/slurm/array_extract.slurm

# 4. Wait for completion, then merge
python cluster/scripts/merge_chain_coords.py --n-jobs 3

# 5. rsync merged npz back to local laptop
rsync -av master:/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/results/section0/merged_chain_coords/ \
      results/chain_coords_full/

# 6. Locally rerun analysis on full data
python scripts/phd_closure.py --bootstrap --n-bootstrap 200 --n-jobs 8 \
       --inputs-root results/chain_coords_full
# Same for phd_closure_s25.py, raw_tether_partition_k2d.py, diagnose_rigid_sample_bias.py
```

## C workflow — full

```bash
# 1. Pilot one (system, h) job; verify z-tether constraint is enforced and bond count = 0
sbatch cluster/slurm/single_pilot.slurm
# Check log: ⟨z_membrane⟩ ≈ h, bond_count = 0 throughout

# 2. If pilot OK, production array (3 systems × 6 h values = 18 tasks)
sbatch cluster/slurm/array_slab_md.slurm

# 3. Analyze
python cluster/scripts/analyze_slab_traj.py --n-jobs 8
# Writes cluster/results/slab/K2D_l_grid.npz

# 4. Sync back to local
rsync -av master:.../cluster/results/slab/ results/slab/
```

## Pilot discipline

Every script in this folder supports `--pilot` (smaller input, < 60s wall, asserts sanity invariant). Cluster wall time is too expensive to run blind. Always:

1. Run script locally with `--pilot` (if data deps allow)
2. Submit `single_pilot.slurm` on cluster (validates SBATCH template)
3. Then production array

## Sync strategy

- `cluster/outputs/` is gitignored (each MD job is several GB)
- `cluster/results/section0/merged_chain_coords/` is gitignored (~100 MB per system)
- Distilled tables (inventory.tsv, K2D_l_grid.npz) go into git
- Use rsync to pull distilled results back to laptop for `scripts/` analysis

## TODOs (await senior or first cluster login)

- [ ] confirm cluster path to MD output replicas (currently assumed `/mnt/nfs/ugstu/liuzx/2D-Binding-MD/`)
- [ ] confirm conda env `phys` exists with pygamd installed (test with `check_env.sh`)
- [ ] confirm pygamd API for z-tether harmonic constraint (likely `pygamd.force` module — verify on cluster)
- [ ] confirm SLURM wall time for MD jobs (senior said "no need to set" but cluster default may be tight)
- [ ] decide array-task → (system, h) mapping format for `array_slab_md.slurm`

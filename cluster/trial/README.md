---
purpose: 'Trial harness: 4 scripts user runs on cluster-A to validate environment
  + pilot extract'
audience: user (cluster-A); Claude reads outputs/ for diagnosis
status: current
---

# cluster/trial/ — user validation harness for cluster-A

> Run on cluster-A. The output of each round goes into `outputs/`; Claude
> writes diagnosis + script patches in `results/`; iterate until green.

## Why this exists

Local laptop pilots kept hitting macOS / path edge cases that don't
appear on cluster-A. The authoritative environment is cluster-A, so we
do all validation there in one structured pass per round, then iterate
based on Claude's diagnosis.

## Quick start (Round 1)

```bash
# 1. ssh to cluster, clone or sync this repo
ssh master
cd /mnt/nfs/ugstu/liuzx
git clone <your-repo-URL> 2D-Binding
cd 2D-Binding

# 2. Create round dir + run 4 trial scripts in order
ROUND_DIR=cluster/trial/outputs/$(date -I)_round1
mkdir -p "$ROUND_DIR"
bash cluster/trial/01_env_check.sh     > "$ROUND_DIR/01_env_check.out" 2>&1
bash cluster/trial/02_paths_check.sh   > "$ROUND_DIR/02_paths_check.out" 2>&1
bash cluster/trial/03_pygamd_probe.sh  > "$ROUND_DIR/03_pygamd_probe.out" 2>&1
bash cluster/trial/04_extract_pilot.sh > "$ROUND_DIR/04_extract_pilot.out" 2>&1

# 3. Commit and push
git add cluster/trial/outputs/
git commit -m "trial: round 1 outputs from cluster-A"
git push
```

Claude pulls on laptop, writes `cluster/trial/results/<date>_round1_diagnosis.md`
+ commits any patches to `cluster/scripts/*`. Pull on cluster-A and
repeat:

```bash
git pull
ROUND_DIR=cluster/trial/outputs/$(date -I)_round2
mkdir -p "$ROUND_DIR"
# rerun whatever the diagnosis asked you to rerun (usually 03/04 only)
bash cluster/trial/04_extract_pilot.sh > "$ROUND_DIR/04_extract_pilot.out" 2>&1
git add . && git commit -m "trial: round 2 outputs" && git push
```

When trial is green, Claude commits a
`cluster/trial/results/<date>_round<N>_verdict.md` declaring the
validation harness ready.

## What each trial script checks

| # | script | how to run | checks | wall time | required for |
|---|---|---|---|---|---|
| 01 | `01_env_check.sh` | `bash` (login node) | conda + Python pkgs + sbatch on PATH | < 30 s | every downstream step |
| 02 | `02_paths_check.sh` | `bash` (login node) | NFS paths, find K100/K10/K01 dirs + replica counts | < 30 s | extract pipeline |
| 03 | `03_pygamd_probe.sh` | `bash` (login node) | how to import pygamd / cu_gala / gala, find force module | < 1 min | Workstream C only |
| 04 | `04_extract_pilot.sh` | `bash` (login node) | run `extract_one_replica.py --pilot` on K100 s001 | < 2 min | §0 + bundle release |
| 05 | `05_compute_node_check.slurm` | **`sbatch`** (compute node) | identity + NFS + conda + analysis stack + pygamd + extract pilot, all on a SLURM-allocated compute node | ~2-3 min | production array jobs run on compute nodes, so this is required before any production sbatch |

## Step 5 — compute-node validation via SBATCH

Production array jobs (`cluster/slurm/array_extract.slurm`,
`cluster/slurm/array_slab_md.slurm`, `cluster/slurm/full_analysis.slurm`)
all run on **compute nodes**, which on some clusters differ from the login
node in NFS visibility, conda env reachability, and whether GPU-runtime
packages (cu_gala / pygamd) are installed. Steps 01-04 only test the login
node; Step 5 closes that gap by running the same checks inside an
SBATCH-allocated compute-node job.

Submission:

```bash
mkdir -p cluster/trial/outputs/$(date -I)_round<N>/compute
sbatch -o cluster/trial/outputs/$(date -I)_round<N>/compute/%J.out \
       -e cluster/trial/outputs/$(date -I)_round<N>/compute/%J.err \
       cluster/trial/05_compute_node_check.slurm

# wait for it to finish (squeue -u $USER), then commit the .out/.err
git add cluster/trial/outputs/$(date -I)_round<N>/compute/
git commit -m "trial: round<N> compute-node sbatch outputs"
git push
```

Expected tail of `.out`:

```
   ✓✓✓  COMPUTE-NODE CHECKS PASSED on <node>.

   Means:
     • /mnt/nfs/ugstu/liuzx visible from compute node
     • phys env (or equivalent) reachable + analysis stack importable
     • extract_one_replica.py runs end-to-end here

   → Production array jobs will work.
```

If any step fails, Claude writes
`cluster/trial/results/<date>_round<N>_diagnosis.md` with the specific
divergence + a script patch.

## After validation is green (all 5 steps pass)

Run `bash cluster/release_bundle.sh` on the laptop to pack the bundle —
see "Loop 1 closure" section below.

## Loop 1 closure — when trial verdict ✓ ships, run release_bundle.sh

When the round-N diagnosis converges to a `<date>_round<N>_verdict.md`
saying "all green", run **on laptop (NOT on cluster-A)**:

```bash
bash cluster/release_bundle.sh
```

This packs `cluster/` (excluding `trial/`, `outputs/`, `results/`,
the local-dev `release_bundle.sh` itself, and macOS metadata) into
`cluster-bundle-<date>-<sha>.tgz`, logs the release in
`cluster/RELEASES.md`, and prints the next steps for sending to off-site collaborator.
This is the **only protocol-defined Loop 1 → Loop 2 transition** —
don't manually tar things; release_bundle.sh enforces the verdict
check + provenance logging.

Off-site collaborator unpacks the tarball, edits `cluster/run_config.sh` (one file,
~6 lines), runs `sbatch cluster/slurm/full_analysis.slurm` (her cluster
has SLURM — primary path) or `bash cluster/run_analysis.sh` (fallback).
See `cluster/HOWTO_run_full_data_zh.md` for the full-data analysis workflow.

The double-loop continues via `cluster/outputs/` ← the off-site distilled
outputs, and `cluster/results/` ← Claude's analysis (which MUST include
a "B-revision impact" section per
`log/decisions/007_loop2_b_revision_playbook.md`).

## File overview

```
trial/
├── README.md                 # this file
├── 01_env_check.sh                  # bash on login node: conda + Python + sbatch
├── 02_paths_check.sh                # bash on login node: NFS + MD data inventory
├── 03_pygamd_probe.sh               # bash on login node: pygamd import + force-module discovery
├── 04_extract_pilot.sh              # bash on login node: smallest possible extract end-to-end
├── 05_compute_node_check.slurm      # sbatch: same checks on a SLURM compute node
├── outputs/                         # users paste .out here (see outputs/README.md)
│   └── README.md
└── results/                         # Claude writes diagnosis here (see results/README.md)
    └── README.md
```

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

| # | script | checks | wall time | needs to pass before next |
|---|---|---|---|---|
| 01 | `01_env_check.sh` | conda + phys env, basic Python pkgs, sbatch | < 30 s | yes |
| 02 | `02_paths_check.sh` | NFS paths, find K100/K10/K01 dirs + replica counts | < 30 s | yes |
| 03 | `03_pygamd_probe.sh` | how to import pygamd / cu_gala / gala, find their force module | < 1 min | only for Workstream C |
| 04 | `04_extract_pilot.sh` | run `extract_one_replica.py --pilot` on K100 s001 | < 2 min | for §0 / shipping to senior |

## After validation is green

Send `cluster/` (minus `trial/`) to senior:

## Loop 1 closure — when trial verdict ✓ ships, run release_bundle.sh

When the round-N diagnosis converges to a `<date>_round<N>_verdict.md`
saying "all green", run **on laptop (NOT on cluster-A)**:

```bash
bash cluster/release_bundle.sh
```

This packs `cluster/` (excluding `trial/`, `outputs/`, `results/`,
`bundle_for_senior/`, `release_bundle.sh` itself) into
`cluster-bundle-<date>-<sha>.tgz`, logs the release in
`cluster/RELEASES.md`, and prints the next steps for sending to senior.
This is the **only protocol-defined Loop 1 → Loop 2 transition** —
don't manually tar things; release_bundle.sh enforces the verdict
check + provenance logging.

Senior unpacks the tarball, edits `cluster/SENIOR_CONFIG.sh` (one file,
~6 lines), runs `sbatch cluster/slurm/full_analysis.slurm` (her cluster
has SLURM — primary path) or `bash cluster/run_analysis.sh` (fallback).
See `cluster/README_for_senior_zh.md` for senior's full workflow.

The double-loop continues via `cluster/outputs/` ← senior's distilled
outputs, and `cluster/results/` ← Claude's analysis (which MUST include
a "B-revision impact" section per
`log/decisions/007_loop2_b_revision_playbook.md`).

## File overview

```
trial/
├── README.md                 # this file
├── 01_env_check.sh           # conda + Python + sbatch verification
├── 02_paths_check.sh         # NFS + MD data inventory
├── 03_pygamd_probe.sh        # pygamd import + force-module discovery
├── 04_extract_pilot.sh       # smallest possible extract end-to-end
├── outputs/                  # user paste .out (see outputs/README.md)
│   └── README.md
└── results/                  # Claude writes diagnosis (see results/README.md)
    └── README.md
```

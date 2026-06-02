---
type: session
status: accepted
date: 2026-06-02
session_type: debugging
duration_hours: 2
summary: User ran cluster/trial/01-04 on cluster-A; diagnosis found gpu-partition regex bug + ~/miniconda3 hardcoded path. Patched both. Also stripped phys env requirement (cluster uses base) and added compute-node SBATCH validation script.
agent_read_when:
  - checking whether trial scripts are passing on cluster-A
  - asking about the gpu* partition naming quirk
  - need to know which conda is on cluster-A
  - working on a compute-node SBATCH and looking for the template
related_decisions: [002]
key_outputs:
  commits: [2845d02, 1a4fcff]
  artifacts:
    - cluster/trial/outputs/2026-06-01_round1/
    - cluster/trial/results/2026-06-01_round1_diagnosis.md
    - cluster/trial/results/2026-06-01_round1_next_actions.md
    - cluster/trial/slurm/compute_node_check.slurm
followups:
  blockers: ["awaiting user Round 2 outputs (login + compute-node SBATCH)", "awaiting senior reply on cu_gala install"]
  tasks: []
---

# Session 4 — Trial Round 1 diagnosis + patches

## What the user reported

User ran `cluster/trial/01_env_check.sh` through `04_extract_pilot.sh` on
cluster-A (host `master`, user `ugstu`, repo path
`/mnt/nfs/ugstu/liuzx/2D-Binding-main`).

Results:
- 01 env_check  : ⚠ partial (gpu* regex false alarm + phys env missing)
- 02 paths_check: ✓ pass (7 replicas total — K100×2, K10×2, K01×3 — bonus!)
- 03 pygamd     : ✗ fail (no pygamd / cu_gala in base)
- 04 extract    : bailed (phys not active, Step 0 exit)

## What I found

| ✓ already correct | ⚠ needs patch |
|---|---|
| conda at `/opt/miniconda3` (already in fallback chain) | gpu partition is `gpu*` (the * marks default); regex was `^gpu$` exact match |
| NFS workspace mounted, all 3 system dirs found | `phys` env doesn't exist on cluster |
| 7 own replicas discovered (bonus opportunity!) | All SLURM templates hardcode `~/miniconda3`, but cluster has `/opt/miniconda3` |
| sbatch present, gpu partition has 8 idle nodes | pygamd/cu_gala/poetry all missing from cluster base env |

## Patches in commit 2845d02

1. `cluster/trial/01_env_check.sh`: `grep -qx 'gpu'` → `grep -qE '^gpu\*?$'`
2. `cluster/slurm/{_base,single_pilot,array_extract,array_slab_md}.slurm`:
   hard-coded `source ~/miniconda3/etc/profile.d/conda.sh` →
   auto-discovery loop trying `/opt/miniconda3` first

## Then user clarified: phys is LOCAL only

User said "conda phys env是我自己local的环境" — the cluster doesn't need
the phys env; we use whatever python is on PATH (cluster base = Python
3.11.11 at `/opt/miniconda3/bin/python`).

→ ADR 002 documents this.

## Patches in commit 1a4fcff

1. Removed `cluster/env_setup/install_phys.sh` entirely (not needed)
2. All cluster scripts now use auto-discovered conda + current env, no
   `conda activate phys` attempts
3. **NEW**: `cluster/trial/slurm/compute_node_check.slurm` — SBATCH-based
   trial that validates env + pygamd + extract pilot on a COMPUTE node
   (user-flagged concern that login ≠ compute env). 5-step script.
4. Updated `cluster/trial/results/2026-06-01_round1_next_actions.md` to
   document Round 2 as login-node rerun + compute-node SBATCH

## Round 2 protocol (waiting for user)

```bash
ssh master
cd /mnt/nfs/ugstu/liuzx/2D-Binding-main
git pull

ROUND_DIR=cluster/trial/outputs/$(date -I)_round2
mkdir -p "$ROUND_DIR/compute"

# Login-node rerun (~1 min)
bash cluster/trial/01_env_check.sh     > "$ROUND_DIR/01_env_check.out" 2>&1
bash cluster/trial/04_extract_pilot.sh > "$ROUND_DIR/04_extract_pilot.out" 2>&1

# Compute-node SBATCH (~2-3 min wall)
sbatch -o "$ROUND_DIR/compute/%J.out" \
       -e "$ROUND_DIR/compute/%J.err" \
       cluster/trial/slurm/compute_node_check.slurm

git add cluster/trial/outputs/
git commit -m "trial: round 2 outputs (login + compute)"
git push
```

## Decisions made

- **002** phys env is local-only; cluster uses base python.

## Open blockers

- User hasn't pushed Round 2 outputs yet → session 6c / future will diagnose.
- Senior hasn't replied on cu_gala install → Workstream C constrained-h MD
  blocked.

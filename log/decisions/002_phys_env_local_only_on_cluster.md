---
type: decision
status: accepted
adr_id: 002
date: 2026-06-02
summary: Don't require phys conda env on cluster-A; cluster scripts use whatever python is on PATH (system base)
agent_read_when:
  - writing or modifying a SLURM template
  - extending check_env.sh or trial 01-04 scripts
  - debugging "phys env not found" errors on cluster
alternatives_considered:
  - "install phys env on cluster from requirements.txt"
  - "use the system base env directly with required packages"
  - "create env per-user via miniconda in $HOME"
expected_revision_trigger: cluster admin asks us not to write packages to base, or cluster base lacks required pip install permission
related_sessions: [session4_trial_round1]
related_calibration: []
---

# ADR 002 — phys env is local-only; cluster uses base

## Context

`phys` is the conda env name on the user's laptop (where development
happens). Initial cluster scripts assumed phys also exists on cluster-A
and tried `conda activate phys` at the start of every SLURM job.

Round 1 trial revealed:
- cluster has conda at `/opt/miniconda3` (Python 3.11.11 base, not phys)
- no `phys` env created
- system base env has the analysis stack (numpy/scipy/pandas/matplotlib/
  scikit-learn) sufficient for §0 bundle path
- user clarified: phys is just their local dev env name

## Decision

**Cluster scripts use whatever python is on PATH** (cluster base = system
`/opt/miniconda3/bin/python`). No `phys` activation attempts.

## Rationale

- Required packages are already in cluster base; no install needed.
- Removing `conda activate phys` lines simplifies SLURM templates and
  removes a class of "activation failed" errors.
- pygamd / cu_gala (Workstream C blocker) is independent of phys — that's
  about the MD engine, not the analysis env.
- Matches the principle "make the cluster a thin compute node, do the
  fancy env management on the laptop side".

## Consequences

- `cluster/env_setup/install_phys.sh` removed.
- All 4 SLURM templates (_base, single_pilot, array_extract, array_slab_md)
  source conda profile.d but do NOT activate any specific env.
- `cluster/trial/01_env_check.sh` checks "analysis stack importable in
  current python" instead of "phys env activatable".
- `cluster/trial/04_extract_pilot.sh` likewise.

## Revision plan

If cluster admin says "don't write packages to base":
1. Create a per-user conda env (call it whatever; not `phys` to avoid
   confusion with local), install requirements.txt into it.
2. Add the env name as a CLI argument or env var (`CLUSTER_ENV`) the
   SLURM templates source.

## Files affected

- DELETED: `cluster/env_setup/install_phys.sh`
- `cluster/slurm/{_base,single_pilot,array_extract,array_slab_md}.slurm`
- `cluster/env_setup/check_env.sh`
- `cluster/trial/{01_env_check,04_extract_pilot}.sh`
- `cluster/README.md` (removed install_phys reference)

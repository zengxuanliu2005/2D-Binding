---
purpose: 'Convention: user pastes trial 01-04 .out files into <YYYY-MM-DD>_round<N>/
  subdir'
audience: user + Claude
status: current
---

# cluster/trial/outputs/ — user pastes trial script outputs here

## Purpose

After running `cluster/trial/01_env_check.sh` through `04_extract_pilot.sh`
on cluster-A, paste each script's stdout/stderr here. Claude reads these
to diagnose what needs fixing in `cluster/scripts/*` (paths, conda
activation, pygamd imports, etc.) and writes the diagnosis +
script-patch suggestions to `cluster/trial/results/`.

## Convention

Each round of trial runs gets its own dated subdirectory:

```
cluster/trial/outputs/
└── 2026-06-02_round1/
    ├── 01_env_check.out
    ├── 02_paths_check.out
    ├── 03_pygamd_probe.out
    └── 04_extract_pilot.out
```

If round 1 diagnosis points to script fixes, Claude commits the fixes,
user pulls and reruns trial → creates `2026-06-03_round2/` with the new
outputs. Repeat until trial is all green.

## How to populate

```bash
# On cluster-A
cd /mnt/nfs/ugstu/liuzx/2D-Binding
git pull
mkdir -p cluster/trial/outputs/$(date -I)_round1
bash cluster/trial/01_env_check.sh   > cluster/trial/outputs/$(date -I)_round1/01_env_check.out 2>&1
bash cluster/trial/02_paths_check.sh > cluster/trial/outputs/$(date -I)_round1/02_paths_check.out 2>&1
bash cluster/trial/03_pygamd_probe.sh > cluster/trial/outputs/$(date -I)_round1/03_pygamd_probe.out 2>&1
bash cluster/trial/04_extract_pilot.sh > cluster/trial/outputs/$(date -I)_round1/04_extract_pilot.out 2>&1

# Commit and push
git add cluster/trial/outputs/
git commit -m "trial: round 1 outputs from cluster-A"
git push
```

Claude will then pull on laptop, read the outputs, and respond in
`cluster/trial/results/<date>_round1_diagnosis.md`.

## Round termination

A round is "done" when Claude has produced the corresponding
`cluster/trial/results/<date>_round<N>_diagnosis.md` and either:

- Script patches are committed for round N+1, OR
- A `<date>_round<N>_verdict.md` declares the trial pipeline ready
  (all green, no further fixes needed).

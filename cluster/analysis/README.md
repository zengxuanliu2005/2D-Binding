---
purpose: "Index of cluster/analysis/: 2 pipeline wrappers + the output-layout spec"
audience: anyone running §0 (closure pipeline) or C (slab MD pipeline)
status: current
---

# cluster/analysis/ — full-pipeline wrappers

These are the higher-level pipeline orchestrators that string together
multiple SBATCH submissions for §0 (full-data closure) and Workstream C
(constrained-h slab MD). They are independent of the off-site bundle —
they're for running pipelines on a cluster the user has access to.

| file | purpose |
|---|---|
| `run_section0_full.sh` | §0 pipeline: explore_replicas → array_extract → merge_chain_coords → closure scripts → reconcile. Waits for each SBATCH array to finish before launching the next. |
| `run_slab_full.sh` | Workstream C pipeline: pilot constrained-h MD → array of 18 (system, h) jobs → analyze_slab_traj.py. Currently blocked on pygamd-API confirmation; the pilot path can run when nvt-md-constrained-h.py's TODO lines are filled. |
| `expected_output_layout.md` | spec for what files the off-site full-data run produces — the schema for what comes back in `distilled.tgz`. Used by `cluster/results/` analysis (Loop 2) to know what to look for. |

## When to use each

- **Use the off-site bundle path** (`cluster/run_analysis.sh` /
  `cluster/slurm/full_analysis.slurm`) — when the user does not have
  access to the cluster where the MD data lives, but the data holder does.
- **Use `run_section0_full.sh`** — when the user has access to the
  cluster directly (e.g., cluster-A) and wants to run §0 themselves.
- **Use `run_slab_full.sh`** — Workstream C only, after pygamd
  integration is confirmed.

## Outputs

Both pipelines write to `cluster/outputs/` per the ADR 005 double-loop
convention. Distilled results land in `cluster/outputs/distilled/`
(matches the off-site bundle output schema) or `cluster/outputs/slab/`
(Workstream C).

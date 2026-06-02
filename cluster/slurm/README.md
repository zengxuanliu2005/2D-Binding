---
purpose: "Index of cluster/slurm/: 5 SBATCH templates + the user-facing full_analysis wrapper"
audience: anyone submitting SLURM jobs from the bundle or local cluster
status: current
---

# cluster/slurm/ — SBATCH templates

All 5 files are SLURM batch scripts. The first is a TEMPLATE (do not submit
directly); the other 4 are SUBMITTABLE.

| file | role | when to use |
|---|---|---|
| `_base.slurm` | **template only** | copy as the starting point for new SBATCH jobs. Contains the cluster-A defaults (`-p gpu -N 1 -c 1 -w n01`) confirmed from the reference `analysis/analysis.slurm`. Do NOT submit directly — it exits with an error reminding you to override the command. |
| `single_pilot.slurm` | submittable | single-job pilot to validate a new SBATCH template before launching the array equivalent. Used for trial-style smoke tests. |
| `array_extract.slurm` | submittable | array job that runs `cluster/scripts/extract_one_replica.py` over (system, replica) pairs. Indexed via `$SLURM_ARRAY_TASK_ID`. Sized by the inventory. |
| `array_slab_md.slurm` | submittable | array job that runs `cluster/scripts/nvt-md-constrained-h.py` over 18 (system, h) combinations for Workstream C. Currently has TODO lines pending pygamd-API confirmation. |
| `full_analysis.slurm` | **PRIMARY user entry** | SBATCH wrapper for the full-data analysis. Sources `cluster/run_config.sh`, tries the configured Python env, hands off to `cluster/run_analysis.sh`. This is the file the off-site full-data run submits. |

## Quick reference — `full_analysis.slurm`

Off-site full-data analysis workflow:

```bash
vim cluster/run_config.sh                     # edit MD_PARENT etc.
sbatch cluster/slurm/full_analysis.slurm      # ~1-2 h wall time
tar czf distilled.tgz cluster/outputs/distilled/
```

All knobs (partition, time, memory, parallelism) come from
`cluster/run_config.sh`. If the cluster needs different SBATCH headers,
override the SLURM_* variables in `run_config.sh` — the wrapper sources
them on the way into the job.

See `cluster/HOWTO_run_full_data_zh.md` for the full Chinese-language walkthrough.

## Adjacent SBATCH script (NOT in this directory)

`cluster/trial/05_compute_node_check.slurm` — Step 5 of the trial pipeline.
Lives in `cluster/trial/` because it is part of the validation harness,
not a production job. See `cluster/trial/README.md` for submission.

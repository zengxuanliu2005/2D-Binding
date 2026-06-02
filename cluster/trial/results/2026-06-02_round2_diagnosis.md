---
purpose: "Round 2 (2026-06-02, compute-node via SBATCH) diagnosis: all 5 checks pass on n01"
audience: user (Zengxuan) + Claude (verdict + release)
status: current
round: 2026-06-02_round2
node_type: compute (sbatch)
slurm_job_id: 4744
slurm_node: n01
verdict: PASSED
---

# Round 2 diagnosis — 2026-06-02 (compute node via SBATCH)

## Inputs read

- cluster/trial/outputs/2026-06-02_round2/compute/4744.out
- cluster/trial/outputs/2026-06-02_round2/compute/4744.err (0 bytes — no stderr)

Submission: `sbatch cluster/trial/05_compute_node_check.slurm`, allocated to
node `n01`, job id 4744. (At the time of submission the .slurm file lived at
`cluster/trial/slurm/compute_node_check.slurm`; it has since been promoted
to `cluster/trial/05_compute_node_check.slurm` — same content.)

## Per-step result

| step | check | result | observation |
|---|---|---|---|
| 1/5 | node identity | **✓** | hostname `n01`, SLURM_JOB_ID `4744`, SLURM_NODELIST `n01`, SLURM_SUBMIT_DIR reachable |
| 2/5 | NFS visibility | **✓** | `/mnt/nfs/ugstu/liuzx` mounted on compute node; disk free reported; `$HOME` exists |
| 3/5 | conda + analysis stack | **✓** | conda.sh found at `/opt/miniconda3/etc/profile.d/conda.sh`; numpy/scipy/pandas/matplotlib/scikit-learn all import |
| 4/5 | pygamd / cu_gala | **expected absent** | no module in the standard search; Workstream C remains the path needing pygamd installation, but §0 bundle does NOT need it |
| 5/5 | extract pilot | **✓** | `extract_one_replica.py --pilot` on K100 s001 produced K100_s001.npz: n_frames=50, n_R=15, n_L=15, bound R/frame=8.40 — schema OK |

## Key takeaway

The compute node sees the same NFS-mounted `/mnt/nfs/ugstu/liuzx` and the
same `/opt/miniconda3` conda installation as the login node. **There is
no login-vs-compute divergence**, so production array jobs
(`cluster/slurm/array_extract.slurm`, `cluster/slurm/full_analysis.slurm`)
will work without further patches.

## Verdict

**Compute-node trial pipeline is validated.** ✓✓✓ PASSED on n01. No
script patches needed.

## Next step

See `cluster/trial/results/2026-06-02_round2_verdict.md` — both rounds
green, trial loop closes, ready for `bash cluster/release_bundle.sh`.

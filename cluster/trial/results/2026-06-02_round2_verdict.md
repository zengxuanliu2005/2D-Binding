---
purpose: "Trial loop verdict: login + compute both green; release_bundle.sh authorised"
audience: user (Zengxuan) + Claude (release flow)
status: current
verdict: TRIAL VALIDATED — release authorised
date: 2026-06-02
covers_rounds:
  - 2026-06-02_round1  # login-node, 4 bash scripts
  - 2026-06-02_round2  # compute-node, SBATCH job 4744 on n01
---

# Trial verdict — 2026-06-02

## Summary

Both rounds of the 2026-06-02 trial pass:

| round | node type | how to run | result | log |
|---|---|---|---|---|
| round1 | login | `bash cluster/trial/01..04_*.sh` | ✓✓✓ all 4 PASSED | 2026-06-02_round1_diagnosis.md |
| round2 | compute (SBATCH) | `sbatch cluster/trial/05_compute_node_check.slurm` (job 4744 on n01) | ✓✓✓ COMPUTE-NODE CHECKS PASSED | 2026-06-02_round2_diagnosis.md |

No script patches were needed for either round (the issues that round 1
of 2026-06-01 exposed had already been patched in commits 2845d02 + 1a4fcff).

## Implications

- **Login-node env is correct**: conda, analysis stack, sbatch on PATH, gpu partition exists.
- **Compute-node env matches login**: NFS-mounted `/mnt/nfs/ugstu/liuzx` and `/opt/miniconda3` visible identically on n01.
- **Extract pipeline is end-to-end functional** on both node types: K100 s001 pilot extract produced a valid `chain_coords.npz` (n_frames=50, n_R=15, n_L=15, bound R/frame=8.40).
- **pygamd absence** is expected and only affects Workstream C (constrained-h slab MD); §0 bundle path does NOT depend on it.

## Authorisation

This verdict authorises running:

```bash
bash cluster/release_bundle.sh
```

on the laptop (NOT on cluster-A). That will:

1. Verify this verdict file exists (which it does, you're reading it)
2. Pack `cluster/` → `cluster-bundle-<date>-<sha>.tgz` (excluding trial/, outputs/, results/)
3. Log the release in `cluster/RELEASES.md`
4. Print the next steps for sending the tarball to the off-site full-data run

This is the **only protocol-defined Loop 1 → Loop 2 transition** (per
ADR 005). Do NOT manually tar things; `release_bundle.sh` enforces the
verdict + provenance.

## Next

After `release_bundle.sh`:

- Send `cluster-bundle-<date>-<sha>.tgz` to the off-site collaborator
- Wait for the off-site distilled tarball to return → unpack into
  `cluster/outputs/<date>_round1/`
- Apply Loop 2 protocol (ADR 007) — write
  `cluster/results/<date>_round1_analysis.md` including the B-revision
  impact table (per `log/decisions/007_loop2_b_revision_playbook.md`).

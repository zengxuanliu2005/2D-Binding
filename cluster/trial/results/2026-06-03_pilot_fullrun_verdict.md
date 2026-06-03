---
purpose: "Pilot full-data run verdict (2026-06-03): pipeline validated end-to-end on cluster-A; off-site full-data run authorised"
audience: user + Claude + off-site collaborator (indirectly, via release_bundle.sh)
status: current
verdict: PIPELINE VALIDATED — off-site release authorised
date: 2026-06-03
covers_rounds:
  - 2026-06-03_pilot_fullrun (round 1: 3 path bugs exposed)
  - 2026-06-03_pilot_fullrun_round2 (cyberduck overwrite, 0-edit defaults needed)
  - 2026-06-03_pilot_fullrun_round3 (all green ✓)
---

# Pilot full-data verdict — 2026-06-03

## Summary

Three pilot rounds on cluster-A. The first two exposed latent bugs from the
Session 7 IO refactor and the Session 8 mass-substitution pass; Session 9
patched all of them; round 3 was clean.

| round | what happened | outcome |
|---|---|---|
| 1 | first end-to-end attempt with placeholder config edited | extract + merge ✓; closure_four_term, closure_wlc_three_term, raw_tether_partition ✗ (3 path bugs) |
| 2 | patches applied, cyberduck-overwrite reset MD_PARENT to placeholder | failed at `cd $MD_PARENT` |
| 3 | auto-detect MD_PARENT patch applied | **all 8 pipeline steps ✓; 9 distilled files produced (~256 K)** |

Diagnosis: see `cluster/trial/results/2026-06-03_pilot_fullrun_diagnosis.md`.

## Implications

1. **End-to-end pipeline works on cluster-A** with bash mode (login node, base
   conda env). Auto-detect handles MD_PARENT; per-system symlinks resolve
   the traj.xyz paths; `system_inputs.py` reads chain_coords from the
   convention-correct `outputs/chain_coords/` location.

2. **Cyberduck-overwrite workflow is supported zero-edit**: the user can
   `rm -rf cluster/` on cluster-A and re-upload fresh, without editing any
   file, and the next pilot/production run will work.

3. **By extension, the off-site collaborator will succeed too**: the same
   auto-detect logic will fire on her cluster as long as she follows the
   HOWTO's recommended placement (`<md_root>/2D-Binding-fullrun/cluster/`).
   Or she can fall back to `vim run_config.sh` if her layout differs (one
   line edit).

4. **A1 bound/unbound geometric bias persists with 2 replicas**. Pilot
   rigid Δz = +0.26 nm, Δtilt = +7°, identical to Session 1 A1 finding on
   s001. **Early signal that the bias is NOT a data-volume artifact** —
   if it were, it should have started shrinking with 2× the data.
   Full-replica run remains the definitive test.

5. **Four-term closure tightens** with 2 replicas: flex-rigid gap drops
   from +0.40 (s001) to +0.10 kBT (pilot); semi-flex from −0.37 to −0.085 kBT.
   So the closure-level 14σ systematic gap was partly data-volume noise.
   This is independent from finding 4 (closure narrowing vs A1 bias
   persistence are separate phenomena).

## Authorisation

This verdict authorises:

### A. Production full-data run on cluster-A (anytime)

```bash
ssh master && cd /mnt/nfs/ugstu/liuzx/2D-Binding
source /opt/miniconda3/etc/profile.d/conda.sh && conda activate base
bash cluster/run_analysis.sh                  # full run, all replicas, n_bootstrap=200
```

Wall time estimate: 7 total replicas × ~30 s/extract = 4 min, merge 1 min,
4 analyses × ~5 min = 20 min. **Total: ~25 min.**

Or via SBATCH for resource isolation:

```bash
sbatch cluster/slurm/full_analysis.slurm
```

### B. Off-site release (Loop 1 → Loop 2 transition)

```bash
# On laptop:
bash cluster/release_bundle.sh
```

That will record this verdict's git SHA in `cluster/RELEASES.md` and print
the cyberduck reminder + rsync command + WeChat message template for the
user to send the off-site collaborator.

## Next

1. User runs `bash cluster/release_bundle.sh` on laptop → first RELEASES.md row + WeChat template generated.
2. User cyberduck-uploads the latest committed cluster/ to cluster-A so the off-site collaborator's rsync sees the same SHA.
3. User WeChat-pings the off-site collaborator with the rsync template + path.
4. (Optional, parallel) User runs the full-data version of the pilot on cluster-A herself for an internal check.
5. Wait for off-site distilled cp into `cluster/outputs/<date>_round1/`.
6. Apply Loop 2 protocol per `log/decisions/007_loop2_b_revision_playbook.md`.

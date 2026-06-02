---
purpose: "Round 1 (2026-06-02, login-node) diagnosis: all 4 trial scripts pass"
audience: user (Zengxuan) + Claude (next round)
status: current
round: 2026-06-02_round1
node_type: login
verdict: PASSED
---

# Round 1 diagnosis — 2026-06-02 (login node)

## Inputs read

- cluster/trial/outputs/2026-06-02_round1/01_env_check.out
- cluster/trial/outputs/2026-06-02_round1/02_paths_check.out
- cluster/trial/outputs/2026-06-02_round1/03_pygamd_probe.out
- cluster/trial/outputs/2026-06-02_round1/04_extract_pilot.out

(Compare against 2026-06-01_round1/* — the first attempt, which had
4 issues that were patched in commits 2845d02 + 1a4fcff.)

## Per-step result

| step | script | result | key observation |
|---|---|---|---|
| 01 | env_check | **✓ ALL PASSED** | conda OK, analysis stack imports OK, sbatch on PATH, gpu partition exists |
| 02 | paths_check | **✓ Inventory complete** | found 7 replicas across 3 systems on /mnt/nfs/ugstu/liuzx |
| 03 | pygamd_probe | **expected behaviour** | pygamd / cu_gala not installed in the login env on this host (consistent with the constrained-h MD workstream being a separate path); §0 bundle workflow does not require pygamd, so this is not a blocker |
| 04 | extract_pilot | **✓ pipeline works end-to-end** | extract_one_replica.py --pilot on K100 s001 succeeded; npz schema OK |

## What changed since 2026-06-01_round1

The diff against the first round (cluster/trial/results/2026-06-01_round1_diagnosis.md):

- ✓ 01 no longer requires the `phys` conda env on the cluster — only checks that numpy/scipy/pandas/matplotlib/scikit-learn import in whatever Python is on PATH (commit 1a4fcff)
- ✓ 04 same: no `phys` requirement
- ✓ `cluster/env_setup/install_phys.sh` was removed (not needed; the cluster's base env already has the analysis stack)
- ✓ All 4 steps now print `✓✓✓` PASSED at their tail

## Verdict

**Login-node trial pipeline is validated.** No script patches needed.

## Next round

- Run Step 5 (sbatch compute-node check) — this is already done in
  Round 2 (`cluster/trial/outputs/2026-06-02_round2/compute/4744.out`).
  See `cluster/trial/results/2026-06-02_round2_diagnosis.md`.
- Once Step 5 also green → `bash cluster/release_bundle.sh` to pack the
  full-data analysis bundle.

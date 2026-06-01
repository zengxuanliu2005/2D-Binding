# cluster/trial/ — what you (Zengxuan) run on cluster-A and report back

> One-shot validation pipeline. Run the 4 numbered scripts in order, paste each
> script's output into `REPORT_BACK.md` (or directly to Claude), and we'll
> finalize the path constants + env activation + SLURM templates based on the
> actual cluster reality.

## Why this exists

Local pilot on the laptop kept hitting macOS / path edge cases. The
authoritative environment is cluster-A, so let's just confirm everything
there in one pass. Each script is < 5 min, total < 30 min including the
extract pilot.

## Quick start

```bash
# 1. ssh to cluster, clone or sync this repo
ssh master
cd /mnt/nfs/ugstu/liuzx
git clone <your-repo-URL> 2D-Binding
cd 2D-Binding

# 2. Run the 4 trial scripts in order
bash cluster/trial/01_env_check.sh       > cluster/trial/01_env_check.out 2>&1
bash cluster/trial/02_paths_check.sh     > cluster/trial/02_paths_check.out 2>&1
bash cluster/trial/03_pygamd_probe.sh    > cluster/trial/03_pygamd_probe.out 2>&1
bash cluster/trial/04_extract_pilot.sh   > cluster/trial/04_extract_pilot.out 2>&1

# 3. Send back the 4 .out files (or paste contents into REPORT_BACK.md)
```

## What each script checks

| # | script | checks | wall time | needs to pass before next |
|---|---|---|---|---|
| 01 | `01_env_check.sh` | conda + phys env, basic Python pkgs, sbatch | < 30 s | yes |
| 02 | `02_paths_check.sh` | NFS paths, find K100/K10/K01 dirs + replica counts | < 30 s | yes |
| 03 | `03_pygamd_probe.sh` | how to import pygamd / cu_gala / gala, find their force module | < 1 min | for C only |
| 04 | `04_extract_pilot.sh` | run extract_one_replica.py --pilot on K100 s001 | < 2 min | for §0 / bundle |

After all 4 pass, Claude will:
- Fix any path constants in `cluster/scripts/*` that don't match reality
- Lock the pygamd import statement in `cluster/scripts/nvt-md-constrained-h.py`
- Finalize `cluster/slurm/*.slurm` partition / activation lines
- Update `cluster/bundle_for_senior/` if any of the bundle's assumptions broke

## After validation

If 01-04 all green:

```bash
# §0 bundle test on YOUR replicas (if you have s002, s003, ...) — quick way
# to start collecting "more data" evidence without waiting for senior:
cp -R cluster/bundle_for_senior /mnt/nfs/ugstu/liuzx/
cd /mnt/nfs/ugstu/liuzx/bundle_for_senior
bash run_full_analysis.sh --pilot   # 2 replicas/system

# If you DON'T have extra replicas, just zip the bundle and send to senior:
cd /mnt/nfs/ugstu/liuzx/2D-Binding/cluster
tar czf bundle_for_senior.tgz bundle_for_senior/
# scp bundle_for_senior.tgz to a place you can email/wechat from
```

## Files in this folder

```
trial/
├── README.md                 # this file
├── 01_env_check.sh           # conda + Python + sbatch verification
├── 02_paths_check.sh         # NFS + MD data inventory
├── 03_pygamd_probe.sh        # pygamd import + force-module discovery
├── 04_extract_pilot.sh       # smallest possible extract end-to-end
└── REPORT_BACK.md            # template to paste 4 outputs into
```

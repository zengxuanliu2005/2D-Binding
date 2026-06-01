# Round 1 → Round 2 — what you do next

## TL;DR

Round 2 has **two parts**: rerun the login-node trials with the patches I just
shipped, AND submit a SBATCH job to validate the COMPUTE node env (which
may differ from login).

## Patches in this commit

1. `cluster/trial/01_env_check.sh` — stop requiring `phys` env. Now just checks
   that numpy/scipy/pandas/matplotlib/scikit-learn are importable in whatever
   Python is on PATH (cluster `base` env should already have them). Also fixed
   the `gpu*` partition regex.
2. `cluster/trial/04_extract_pilot.sh` — same: no phys requirement, just
   verifies numpy is importable.
3. `cluster/env_setup/check_env.sh` — rewritten without phys.
4. `cluster/env_setup/install_phys.sh` — **deleted**. Not needed: phys is your
   local dev env, server uses base.
5. `cluster/slurm/{_base,single_pilot,array_extract,array_slab_md}.slurm` —
   removed `conda activate phys` lines. Conda profile.d is still sourced so
   the SLURM jobs run with base + your `/opt/miniconda3/bin/python`.
6. **NEW**: `cluster/trial/slurm/compute_node_check.slurm` — SBATCH script
   that runs the env + pygamd + extract pilot on a compute node, so we can
   compare login vs compute environments.

## Step 1 — pull patches

```bash
ssh master
cd /mnt/nfs/ugstu/liuzx/2D-Binding-main
git pull
```

## Step 2 — Round 2 login-node rerun

This is fast (< 1 min) — just confirms the cleanup didn't break anything on
login.

```bash
ROUND_DIR=cluster/trial/outputs/$(date -I)_round2
mkdir -p "$ROUND_DIR"
bash cluster/trial/01_env_check.sh     > "$ROUND_DIR/01_env_check.out" 2>&1
bash cluster/trial/04_extract_pilot.sh > "$ROUND_DIR/04_extract_pilot.out" 2>&1
```

Expected: both ✓✓✓ PASSED (no `phys` requirement; cluster base env has the
analysis stack).

## Step 3 — Round 2 compute-node validation (KEY for this round)

Submit the SBATCH-based compute-node check. This is what `array_extract.slurm`
will eventually run, so we need it green before proceeding.

```bash
mkdir -p "$ROUND_DIR/compute"
sbatch -o "$ROUND_DIR/compute/%J.out" \
       -e "$ROUND_DIR/compute/%J.err" \
       cluster/trial/slurm/compute_node_check.slurm

# wait for it to finish (should be ~2-3 min)
squeue -u $USER             # watch until it's gone
ls -la "$ROUND_DIR/compute"  # see the .out file by job id
```

The compute-node check does, on a compute node:
1. Identity: hostname / SLURM_NODELIST so we know which node
2. NFS visibility: /mnt/nfs/ugstu/liuzx + $HOME mounted?
3. Conda + analysis stack: same python? numpy/scipy/pandas/matplotlib/sklearn import?
4. pygamd / cu_gala: present on compute? (irrelevant for §0, key for C)
5. End-to-end: `extract_one_replica.py --pilot` on K100 s001

Expected: ✓✓✓ COMPUTE-NODE CHECKS PASSED on `<some node>`.

If compute differs from login (NFS not mounted, base env missing pkgs, etc.):
the compute-side trial output will tell us; I'll patch in Round 3.

## Step 4 — commit + push outputs

```bash
git add cluster/trial/outputs/
git commit -m "trial: round 2 outputs (login + compute node)"
git push
```

## Step 5 (async) — WeChat senior about cu_gala

Login-node trial 03 confirmed `cu_gala` not present in cluster `base`. The
compute-node trial 04 will tell us if it's anywhere else. Independent of
that, please send senior:

> 学姐，cluster master 上 base env 里没有 pygamd 也没有 cu_gala
> （`from poetry import cu_gala` 也 fail）。你 `ref/nvt-md.py` 里用的
> 是 `from poetry import cu_gala as gala` —— 你之前是怎么装的？是装在
> 某个专门的 conda env 里，还是有自定义的 python path？我下一步要在
> cluster 上跑 constrained-h slab MD，没 cu_gala 走不了。

(§0 bundle path doesn't need pygamd; that path keeps moving.)

## After Round 2 passes — bonus opportunity

`02_paths_check` (Round 1) showed **you have 7 replicas of your own**
(K100×2 + K10×2 + K01×3), not just s001. Once Round 2 is green you can run
a mini §0 data-volume test on YOUR data, **without waiting for senior**:

```bash
bash cluster/run_analysis.sh --pilot   # 2 reps/system, ~5 min sanity
bash cluster/run_analysis.sh           # all 7 replicas, ~30 min
git add cluster/outputs/$(date -I)_round1/
git commit -m "outputs: mini §0 on user's own 7 replicas"
git push
```

If just K100/K10 doubling (1 → 2 replicas) already nudges ΔΔF toward PPT
s25 numbers, that's an early signal — saves a week of waiting for senior.

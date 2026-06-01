# Round 1 → Round 2 — what you do next

## TL;DR

1. Pull. Install `phys` env (one-time). Rerun 01 + 04. Push outputs.
2. (Async) WeChat senior for `cu_gala` install recipe — only matters for Workstream C.

## Step 1 — pull patches

I've committed two fixes:

- `cluster/trial/01_env_check.sh` — gpu partition regex now accepts `gpu*`
- `cluster/slurm/*.slurm` (all 4) — conda activation now auto-discovers `/opt/miniconda3` (cluster-A) or `~/miniconda3` (laptop)

```bash
ssh master
cd /mnt/nfs/ugstu/liuzx/2D-Binding-main
git pull
```

## Step 2 — install `phys` env (one-time, ~3-5 min)

The `phys` env doesn't exist on cluster-A. `cluster/env_setup/install_phys.sh`
will create it with `numpy/scipy/pandas/matplotlib/scikit-learn` (everything
the §0 bundle needs).

```bash
bash cluster/env_setup/install_phys.sh
```

If it complains about conda channels or auth, ping me; otherwise it should
just work.

## Step 3 — rerun trial 01 + 04 (Round 2)

```bash
ROUND_DIR=cluster/trial/outputs/$(date -I)_round2
mkdir -p "$ROUND_DIR"
bash cluster/trial/01_env_check.sh     > "$ROUND_DIR/01_env_check.out" 2>&1
bash cluster/trial/04_extract_pilot.sh > "$ROUND_DIR/04_extract_pilot.out" 2>&1
```

Expected: both should print `✓✓✓ PASSED`.

```bash
git add cluster/trial/outputs/
git commit -m "trial: round 2 outputs (after phys install)"
git push
```

## Step 4 (optional, async) — WeChat senior

Quote/paraphrase:

> 学姐，cluster master 上 base env 没有装 pygamd 也没有 cu_gala
> （`from poetry import cu_gala` 也 fail）。我看到你的 `ref/nvt-md.py` 里
> 是 `from poetry import cu_gala as gala` —— 你之前是怎么装的这个包？
> 是有专门的 conda env 还是 pip 装路径？我下一步要在 cluster 上跑
> constrained-h slab MD，没有 cu_gala 走不动。

(This is only needed for Workstream C. The §0 data-volume bundle path
doesn't need pygamd, so we keep moving on that in parallel.)

## After Round 2 passes — bonus opportunity

`02_paths_check` revealed **you have 7 replicas of your own**
(K100×2 + K10×2 + K01×3), not just s001. Once `phys` is installed, you
can run a mini §0 data-volume test on YOUR data, **without waiting for
senior's bundle reply**:

```bash
# Stays on cluster-A, all GPU-free, ~30 min wall
cd /mnt/nfs/ugstu/liuzx/2D-Binding-main
bash cluster/run_analysis.sh --pilot   # 2 reps/system, ~5 min sanity
bash cluster/run_analysis.sh           # all 7 replicas, ~30 min

# distilled output is small (~5 MB)
git add cluster/outputs/$(date -I)_round1/
git commit -m "outputs: mini §0 on user's own 7 replicas"
git push
```

This is a quick preview of whether the "data volume" hypothesis holds.
If just doubling K100/K10 (from 1 → 2 replicas) already nudges ΔΔF
toward PPT s25 numbers, that's a strong early signal — saves a week of
waiting for senior.

If you'd rather wait for senior, that's fine too; just send her the
tarball as planned.

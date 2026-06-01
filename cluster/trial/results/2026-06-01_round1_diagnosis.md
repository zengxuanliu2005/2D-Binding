# Round 1 diagnosis — 2026-06-01

## Inputs read

- `cluster/trial/outputs/2026-06-01_round1/01_env_check.out`
- `cluster/trial/outputs/2026-06-01_round1/02_paths_check.out`
- `cluster/trial/outputs/2026-06-01_round1/03_pygamd_probe.out`
- `cluster/trial/outputs/2026-06-01_round1/04_extract_pilot.out`

Trial host: `master`, user `ugstu`, cwd `/mnt/nfs/ugstu/liuzx/2D-Binding-main`,
2026-06-01 17:37:37 +08:00.

## Summary table

| trial | verdict | takeaway |
|---|---|---|
| 01 env_check     | ⚠ partial | conda OK + sbatch OK + `gpu` partition exists; **phys env missing**; partition regex check false-alarms |
| 02 paths_check   | ✓ pass    | NFS mounted, 3 systems + 7 replicas found (K100×2, K10×2, K01×3), s001 has traj.xyz + mol.psf + num_bonds |
| 03 pygamd_probe  | ✗ fail    | no pygamd / cu_gala / poetry / gala in base env → **Workstream C blocked** until install; §0 path still open |
| 04 extract_pilot | bailed    | exited at Step 0 because phys env not active (cascade from 01) |

## What I found

### ✓ Already correct (no changes needed)

- conda lives at `/opt/miniconda3/` — already in the script's fallback chain (`for prefix in ~/miniconda3 ~/anaconda3 /opt/miniconda3 /opt/anaconda3`). `01_env_check` correctly auto-discovered it. **All SLURM templates that hard-code `~/miniconda3/etc/profile.d/conda.sh` are wrong on this cluster and need patching** — see fix #2 below.
- NFS workspace at `/mnt/nfs/ugstu/liuzx/` — exactly the assumed path. `02_paths_check` resolved all 3 systems with our canonical names (`15_120x120_K100_EPS05` / `15_120x120_K10_EPS05` / `22_120x120_K01_EPS05`).
- Each `s001` has the 3 expected files (`traj.xyz` 3.9 G, `mol.psf` 9.2 M, `num_bonds_for_xyz_frames.dat` 76 K).
- `gpu` partition has **8 idle nodes** — plenty of capacity.
- SLURM 20.11.9.

### ⚠ Issues to fix

**#1. `phys` conda env does not exist.** Only `base` is installed (with Python 3.11.11 but no analysis stack). All downstream scripts (`extract_one_replica.py`, `closure_four_term.py`, ...) need numpy/scipy/pandas/matplotlib. Two options:

  - **(recommended)** Run `bash cluster/env_setup/install_phys.sh` to create the env from `cluster/requirements.txt`. The install script is already written for exactly this.
  - Alternative: install packages directly into `base` (slightly messier).

**#2. `01_env_check.sh` regex false-alarms on `gpu*` partition name.** Line 113-ish: `if sinfo -h -o "%P" 2>/dev/null | grep -qx 'gpu'` requires exact match, but the real partition name printed by sinfo is `gpu*` (the `*` flags it as the default partition). Patch: change `grep -qx 'gpu'` to `grep -qE '^gpu\*?$'` so both names are accepted.

**#3. SLURM templates use `~/miniconda3` but cluster has `/opt/miniconda3`.** Hard-coded in:
  - `cluster/slurm/_base.slurm` (line 35)
  - `cluster/slurm/single_pilot.slurm` (line 35)
  - `cluster/slurm/array_extract.slurm` (line 36)
  - `cluster/slurm/array_slab_md.slurm` (line 36)

  Patch: replace with the same fallback chain used in `check_env.sh` (try `/opt/miniconda3` first, then `~/miniconda3`, etc.).

**#4. `pygamd` / `cu_gala` not installed in `base`.** Confirmed:
  - `import pygamd` → ModuleNotFoundError
  - `from poetry import cu_gala` → ModuleNotFoundError (matches what `ref/nvt-md.py` uses)
  - Same for all other candidates.

  This means **Workstream C (constrained-h slab MD) is blocked** until senior or admin installs the `poetry`+`cu_gala` package — same package she uses to run `ref/nvt-md.py` on this cluster. **The §0 data-volume bundle path does NOT need pygamd**, so we can proceed with that independently.

  **Action**: Ask senior how she installs / activates `cu_gala` on this cluster. She must have a non-default conda env or a custom install path; tell us the recipe.

### Bonus observation

Repo was cloned as `/mnt/nfs/ugstu/liuzx/2D-Binding-main` (GitHub zip default suffix), not `2D-Binding`. Some scripts assume the repo dir is the cwd (relative paths) which is fine — they work regardless of the dir name.

## What needs fixing in `cluster/`

Applied in this round (see commit):

1. `cluster/env_setup/check_env.sh` — fix gpu partition regex (#2)
2. `cluster/slurm/{_base,single_pilot,array_extract,array_slab_md}.slurm` — replace hard-coded `~/miniconda3` with auto-discovery (#3)

User actions for Round 2 (no Claude changes needed):

- Run `bash cluster/env_setup/install_phys.sh` to create `phys` env (#1)
- WeChat senior for `cu_gala` install recipe (#4) — async

## Next round

After fixes are pulled and `phys` is installed, rerun on cluster-A:

```bash
git pull
bash cluster/env_setup/install_phys.sh           # one-time

ROUND_DIR=cluster/trial/outputs/$(date -I)_round2
mkdir -p "$ROUND_DIR"
bash cluster/trial/01_env_check.sh   > "$ROUND_DIR/01_env_check.out" 2>&1
bash cluster/trial/04_extract_pilot.sh > "$ROUND_DIR/04_extract_pilot.out" 2>&1
git add cluster/trial/outputs/ && git commit -m "trial: round 2 outputs" && git push
```

Expected Round 2 verdict:

- 01: ✓✓✓ ALL CHECKS PASSED (gpu regex fix + phys env exists)
- 04: ✓✓✓ TRIAL 04 PASSED (extract reads K100 s001 traj.xyz successfully)

Then we're ready to ship `cluster/` to senior **and** kick off `bash cluster/run_analysis.sh` locally on cluster-A using YOUR 7 replicas (mini §0 — independent of senior).

03 (pygamd) stays red until senior comes back with install recipe; that only matters for Workstream C.

# Running the closure pipeline on the cluster

Hi Dr. H (cc Zengxuan) — this folder contains everything to run the
S1–S23 four-term ΔF closure on **all replicas** of the three K-systems
under your `2d_binding_MD/` tree on the cluster. The single-replica
analysis already runs locally and reproduces all three K2D,max
log-ratios within 1 kBT with correct signs (semi−rigid lands at
exactly 100 %); doing this on the full multi-replica data will tighten
F_rot (the rotational orientation entropy) which currently has bin-
sensitivity on flex−rigid and semi−flex.

## TL;DR — what to run

You can copy this whole `cluster/` directory next to your existing
analysis scripts (e.g. into `2d_binding_MD/analysis/`), or just submit
the slurm files in-place after cloning the repo.

```bash
# 1. clone or sync this repo on the cluster, then:
cd /path/where/you/put/the/repo/cluster

# 2. edit TWO things in extract_all.sh (top of file) if the defaults
#    don't match your layout:
#       TRAJ_ROOT   default /mnt/nfs/ugstu/liuzx/2d_binding_MD
#       OUT_ROOT    default $PWD/chain_coords
#    (you can also export them as env vars before sbatching)

# 3. submit the per-replica extraction job
sbatch extract.slurm

# 4. when extract finishes (check %J.log), submit the closure
sbatch closure.slurm

# 5. send the three merged npz files back to me; I'll update main
```

## SBATCH conventions

Both `.slurm` files follow the cluster's house style from your
`analysis.slurm` template:

```
#SBATCH -J <job name>
#SBATCH -o %J.log
#SBATCH -e %J.err
#SBATCH -p gpu
#SBATCH -w n01
#SBATCH -N 1
#SBATCH -c 1
```

If `n01` is busy, change `-w n01` to any other node you have access to;
nothing else needs changing. **Don't** touch `-N 1` (matching your
template). One CPU core is plenty — extraction is single-threaded NumPy
and closure is sub-second arithmetic.

## What each step actually does (physics → code)

### Background: the four-term decomposition

You measured K2D,max ≈ 12 705 / 875 / 362 nm² for rigid / semi / flex,
so the cross-system log-ratios we need to reproduce are:

    ln(K2D,rigid / K2D,flex) = 3.56 kBT     (flex − rigid)
    ln(K2D,rigid / K2D,semi) = 2.68 kBT     (semi − rigid)
    ln(K2D,semi  / K2D,flex) = 0.89 kBT     (flex − semi)

Your S1–S23 SI gives ΔF_bind as four terms:

| term  | equation | physical meaning |
|---|---|---|
| F_t   | S1, ln(σb²)−1                            | translational; same σ across systems ⇒ cancels |
| F_c   | S4, 1.5·(D/R_e)²                         | Gaussian-chain stretching to span the gap |
| F_bond| S17–S19, −ln(b²/A) or −ln(b³/(A·L))     | end-volume / capture probability (2-D vs 3-D) |
| F_rot | S22–S23, −ln[ω_RL / (ω_R·ω_L)]          | orientational restriction on S² |

Every one of these is a number we extract from the simulated chain
configurations:

* **R_e** — free-chain end-to-end distance ⟨|chain[12] − chain[3]|⟩ over
  unbound R and L
* **D** — bound-chain vertical reach ⟨chain[12].z − chain[3].z⟩, ligand
  z flipped to share sign with R
* **L** = R_max − D, the z range available to the binding bead
* **ω_R, ω_L, ω_RL** — solid-angle phase volumes of the chain axis on S²
  (free R, free L) and S² × S² (bound joint), histogram-estimated

### Step 1 — `extract.slurm` calls `extract_all.sh`

The bash worker loops over the three systems and every `s***/` replica
under each. For each `(system, replica)` tuple it runs

```
python <repo>/scripts/extract_chain_coords.py \
    /mnt/nfs/ugstu/liuzx/2d_binding_MD/<system>/<sNNN> \
    --out chain_coords/<system>/<sNNN>
```

`extract_chain_coords.py` is the only step that touches the
2–4 GB trajectory — it parses `traj.xyz` once and writes a small
`chain_coords.npz` (few MB) containing every R and L chain's 13 bead
positions every frame, plus the per-frame bound mask derived from
`num_bonds_for_xyz_frames.dat`.

**Requirements per replica:** `traj.xyz`, `mol.psf`, and
`num_bonds_for_xyz_frames.dat` must all be present in the replica dir.
If `num_bonds_for_xyz_frames.dat` is missing the replica is skipped
with a `[no bond]` log line (a few of your earlier K01 replicas might
not have it — let me know and I can generate it from `traj.xyz` if it
turns out to matter).

**Already-done replicas are skipped** by checking for the output
`chain_coords.npz` — same pattern as your auto-job idiom of
`if [ ! -f "$s/bindsites_angle_distribution.tsv" ]; then ...`. So you
can re-submit safely if some replicas didn't finish.

**Walltime:** ~30 s per replica per system on 1 CPU. With ~23 replicas
of K01 and ~10 each of K10/K100, total walltime is roughly
20–30 minutes. The default time limit on `gpu` should cover it; if
your queue cuts you off, just resubmit — incremental skip handles it.

### Step 2 — `closure.slurm` calls `closure_all.sh`

Two phases:

1. **Combine.** For each system, concatenate every per-replica
   `chain_coords.npz` along the frames axis into one merged file at
   `results/chain_coords/<system>/chain_coords.npz` (~few MB each).
   Per-system metadata (protein counts, box dimensions) is asserted
   identical across replicas as a sanity check.
2. **Closure.** Runs `scripts/phd_inputs.py` (prints the per-system
   R_e / D / L / n_b / bound counts as a sanity table), then
   `scripts/phd_closure.py` (evaluates F_t, F_c, F_bond, F_rot and
   writes the four-term table to `results/phd_closure.md` +
   `results/phd_closure.npz`), then `scripts/plot_phd_closure.py` (bar
   chart `results/figures/closure_phd.png` with the per-pair
   contributions vs target).

Sub-second walltime; you'll see the closure markdown in your job's
log.

## Configurable knobs

Both `extract_all.sh` and `closure_all.sh` read three env vars before
falling back to defaults. Override any of them by exporting before
sbatching, or by editing the script's top section.

| var | meaning | default |
|---|---|---|
| `TRAJ_ROOT` | parent of the `<system>/<sNNN>/` directories | `/mnt/nfs/ugstu/liuzx/2d_binding_MD` |
| `OUT_ROOT` / `CHAIN_COORDS_IN` | where per-replica npz files live | `$PWD/chain_coords` |
| `REPO_ROOT` | repo root containing `scripts/` | parent of `cluster/` (auto) |

Example, if your data root is somewhere else:

```bash
export TRAJ_ROOT=/your/path/2d_binding_MD
export OUT_ROOT=/scratch/$USER/chain_coords
sbatch extract.slurm
CHAIN_COORDS_IN=$OUT_ROOT sbatch closure.slurm
```

## What to send back

Three files, one per system, a few MB each:

```
results/chain_coords/15_120x120_K100_EPS05/chain_coords.npz
results/chain_coords/15_120x120_K10_EPS05/chain_coords.npz
results/chain_coords/22_120x120_K01_EPS05/chain_coords.npz
```

Drop them in the same paths locally (overwriting the single-replica
versions on `main`), and I'll re-run

```bash
python scripts/phd_closure.py
python scripts/plot_phd_closure.py
```

to refresh `results/phd_closure.{md,npz}` and `closure_phd.png` with
the multi-replica numbers, then push to `main`.

## Acceptance: what we're looking for

The single-replica numbers currently on `main`:

| pair | predicted | target | gap | closed |
|---|---|---|---|---|
| flex − rigid | +3.96 | +3.56 | +0.40 | 111 % |
| semi − rigid | +2.69 | +2.68 | +0.01 | 100 % |
| semi − flex  | −1.27 | −0.90 | −0.37 | 141 % |

For the multi-replica result to be a clean upgrade:

1. **All three signs remain correct** — should be trivially true with
   more data.
2. **Semi − rigid stays at ≥ 95 % closure** — strongest physical
   sanity check on the framework.
3. **flex − rigid and semi − flex tighten toward 100 %** — current
   overshoots are dominated by F_rot's bin sensitivity on a sparse
   4-D `S² × S²` joint histogram. More bound frames → denser
   histogram → tighter F_rot.

## Troubleshooting

* **`extract_all.sh` prints `[no bond] <sys>/<replica>`** —
  that replica's `num_bonds_for_xyz_frames.dat` is missing. Either
  exclude it (just leave it as-is, the closure proceeds with the
  replicas that do have it) or send me a note and I'll write a
  one-off that builds the bond file from `traj.xyz`.
* **`closure_all.sh` says `no per-replica chain_coords.npz under …`** —
  the per-replica extractions either didn't run or wrote somewhere
  other than the default. Pass `CHAIN_COORDS_IN=/the/right/path` to
  match where you set `OUT_ROOT`.
* **Closure numbers are wildly different from the single-replica
  baseline** — first check the inputs table from `phd_inputs.py`. If
  `n_b/frame`, `R_e`, or `D` look very different from the single-
  replica numbers (10.28 / 9.48 / 9.15 for rigid; 3.92 / 8.45 / 7.96
  for semi; 1.83 / 6.17 / 6.62 for flex), one of the replica
  trajectories may be from a slightly different setup. The combine
  step asserts matching protein counts and box dimensions, so if it
  passed but inputs differ, the trajectories themselves have drifted
  parameters.
* **GPU partition refuses CPU job** — if the `gpu` queue has any
  policy against CPU-only jobs (you would know this better than me),
  switch `-p gpu` to whatever your CPU queue is named.

## Files in this directory

```
cluster/
├── README.md          ← this file
├── extract.slurm      ← SBATCH wrapper, calls ./extract_all.sh
├── extract_all.sh     ← bash worker, loops (system, replica) → extract_chain_coords.py
├── closure.slurm      ← SBATCH wrapper, calls ./closure_all.sh
└── closure_all.sh     ← bash worker, combines per-replica npz + runs closure
```

And the analysis modules they call (in the repo's `scripts/` dir):

```
scripts/
├── extract_chain_coords.py    ← traj.xyz → chain_coords.npz per replica (heavy step)
├── combine_chain_coords.py    ← merges per-replica npz along frames axis
├── phd_inputs.py              ← per-system R_e, D, L, n_b, axis pops
├── phd_formula.py             ← F_t (S1), F_c (S4), F_bond (S17-S19), F_rot (S22-S23)
├── phd_closure.py             ← driver: assembles cross-system ΔΔF
└── plot_phd_closure.py        ← closure bar chart
```

Holler with any questions. — Claude (via Zengxuan)

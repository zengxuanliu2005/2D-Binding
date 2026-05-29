# Running the closure pipeline on the cluster

## TL;DR

```bash
# 1. on the cluster, after logging in and pulling this repo:
cd ~/2D-Binding
git switch analysis/cluster-pipeline       # or wherever this branch lands
ls /mnt/nfs/ugstu/liuzx/15_120x120_K100_EPS05/   # confirm replica names
# then edit cluster/extract.sbatch line 5 (#SBATCH --array=1-N) to match

# 2. submit the per-replica extractions (one job per replica, one replica
#    does all 3 systems):
sbatch cluster/extract.sbatch

# 3. once the array job finishes, submit the closure step:
sbatch cluster/closure.sbatch

# 4. the merged chain_coords npz files end up under
#    results/chain_coords/<system>/chain_coords.npz   (one per system,
#    a few MB each); send those three files back to me and I'll
#    re-generate the closure markdown + figure on main.
```

That's it. Total compute is light: extract is ~30 s × n_replicas per
system on 1 CPU; closure is sub-second.

## What these scripts actually do (and why each step exists)

### Background — what we're trying to measure

The simulation already gave us K2D,max values for the three flexibility
classes:

    rigid (K=100):  K2D,max ≈ 12 705 nm²
    semi  (K=10):   K2D,max ≈    875 nm²
    flex  (K=0.1):  K2D,max ≈    362 nm²

so the **target log-ratios** are

    ln(K2D,rigid / K2D,flex) = 3.56 kBT   (flex − rigid)
    ln(K2D,rigid / K2D,semi) = 2.68 kBT   (semi − rigid)
    ln(K2D,semi  / K2D,flex) = 0.89 kBT   (flex − semi, sign convention −0.90)

The PhD's SI write-up (`ref/adhesion protein.pdf`, Eqs. S1–S23)
decomposes ΔF_bind into four terms:

    F_t        translational (S1)        — cancels if σ is the same
    F_c        conformational (S4)       — 1.5·(D/R_e)²        Gaussian stretch
    F_bond     end-volume (S17–S19)      — −ln(b²/A) rigid,    2-D capture
                                          −ln(b³/(A·L)) floppy 3-D capture
    F_rot      rotational (S22–S23)      — −ln(ω_RL / (ω_R·ω_L))  on S²

Each of these is a number we extract from the trajectory:

* `R_e` — free-chain end-to-end distance (per-frame mean)
* `D`   — bound-chain vertical reach (per-frame mean, bound subset)
* `L`   — vertical fluctuation range = R_max − D
* `ω_R, ω_L, ω_RL` — orientational phase volumes of the chain axis
  on S² (free) and S² × S² (bound joint), histogram-estimated

So all four ΔF terms come from the same `chain_coords.npz` per system.
The cluster pipeline just collects more frames into that npz so the
histograms (especially ω_RL on the 4-D `S² × S²` joint) carry tighter
statistics.

### Step 1 — `extract.sbatch` → `scripts/extract_chain_coords.py`

For each (system, replica) tuple, parses one `traj.xyz` (the 2-4 GB
trajectory) once and writes a small npz (~few MB) containing:

* per-bead positions of all R chains and L chains, every frame
* boolean "is bound this frame?" flag per protein per frame
* the partner index (which L is each R bonded to, if any)
* box dimensions and metadata

This is the only heavy step (one pass over the 2-4 GB trajectory),
which is why it's run as a SLURM array — one task per replica,
parallel across the whole array.

Output: `chain_coords/<system>/s<NNN>/chain_coords.npz` per replica.

### Step 2 — `closure.sbatch` → two scripts

**`scripts/combine_chain_coords.py`** — concatenates the per-replica
npz files along the frames axis. Asserts that protein counts and box
dimensions match (sanity check that you didn't mix systems). No
re-extraction needed; this is just `numpy.concatenate`.

Output: `results/chain_coords/<system>/chain_coords.npz` (one merged
file per system).

**`scripts/phd_closure.py`** — evaluates the four formulas above on the
merged data and writes the closure table + numpy archive. Also runs
`scripts/phd_inputs.py` first (which prints the per-system inputs as a
sanity check) and `scripts/plot_phd_closure.py` at the end (the bar
chart).

Outputs:

* `results/phd_closure.md` — human-readable closure table
* `results/phd_closure_data.md` — auto-generated numeric tables
* `results/phd_closure.npz` — all term values for further analysis
* `results/figures/closure_phd.png` — the headline figure

## Configurable knobs

Both SBATCH scripts read a couple of env vars before defaulting:

* `TRAJ_ROOT` (default `/mnt/nfs/ugstu/liuzx`) — where your per-system
  per-replica trajectories live. Each replica should sit under
  `$TRAJ_ROOT/<system>/s<NNN>/` with `traj.xyz`, `mol.psf`, and
  `num_bonds_for_xyz_frames.dat` present.
* `OUT_ROOT` (default `$PWD/chain_coords`) — where per-replica npz
  files go before they're combined. Use a scratch location if the
  job submission directory is on a slow filesystem; just remember to
  pass the same path as `CHAIN_COORDS_IN` to `closure.sbatch`.

To use a different path:

```bash
export TRAJ_ROOT=/path/to/your/trajectories
export OUT_ROOT=/scratch/$USER/chain_coords
sbatch cluster/extract.sbatch
CHAIN_COORDS_IN=$OUT_ROOT sbatch cluster/closure.sbatch
```

## What to send back

Just the three merged npz files:

    results/chain_coords/15_120x120_K100_EPS05/chain_coords.npz
    results/chain_coords/15_120x120_K10_EPS05/chain_coords.npz
    results/chain_coords/22_120x120_K01_EPS05/chain_coords.npz

These are ~few MB each (they're small even after merging many
replicas, because we're storing chain coordinates only — 13 beads ×
3 floats per protein per frame, not the full 144 k atoms).

I'll drop them into the same paths locally, re-run
`python scripts/phd_closure.py && python scripts/plot_phd_closure.py`,
and update `results/phd_closure.md` + `closure_phd.png` on `main`
with the multi-replica numbers.

## Acceptance criteria once we have the multi-replica result

The single-replica closure (current state of `main`) is:

| pair | predicted | target | gap | closed |
|---|---|---|---|---|
| flex − rigid | +3.96 | +3.56 | +0.40 | 111 % |
| semi − rigid | +2.69 | +2.68 | +0.01 | 100 % |
| semi − flex  | −1.27 | −0.90 | −0.37 | 141 % |

For the multi-replica result to be a clean upgrade:

1. **All three signs remain correct.** This was already passing on
   single-replica; more samples shouldn't change it.
2. **Semi − rigid stays at ≥ 95 % closure.** This is the strongest
   physical sanity check that the four-term framework is right
   (semi − rigid is squarely in S4's Gaussian-stretch regime where the
   PhD's analytical approach is exact).
3. **flex − rigid and semi − flex tighten toward 100 %.** The current
   overshoots are dominated by F_rot's bin sensitivity on the
   `S² × S²` joint histogram; more bound frames should make those
   histograms denser and the overshoot smaller.

If we see (1–3), we merge the multi-replica branch to `main` and the
closure result becomes the headline for the write-up.

## Troubleshooting

* **Array task X says "skip" for a replica that exists** — make sure
  `$TRAJ_ROOT/<system>/s<NNN>/` has all three of `traj.xyz`,
  `mol.psf`, and `num_bonds_for_xyz_frames.dat`. If `num_bonds_*` is
  missing for a system that hasn't had the harmonised extractor run
  on it, we'll need to handle that separately — let me know.
* **`closure.sbatch` complains "no chain_coords.npz found"** —
  the per-replica extractions either didn't run or wrote somewhere
  other than the default `$PWD/chain_coords/`. Pass
  `CHAIN_COORDS_IN=/scratch/...` matching wherever you set `OUT_ROOT`.
* **Closure numbers wildly off from `main`** — first check the inputs
  table from `scripts/phd_inputs.py` against the values on `main`'s
  `results/phd_closure.md`. If `n_b/frame`, `R_e`, or `D` look weird,
  one of the replica trajectories may be from a different setup
  (different protein count, different box). The combine step asserts
  matching metadata; if it passes but the inputs look off, the
  trajectories themselves differ.

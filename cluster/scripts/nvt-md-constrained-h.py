"""C.2 — constrained-h slab MD skeleton.

Goal: hold the two membranes at a fixed center-of-mass z separation `h`
while disabling R-L binding, so we can directly measure K2D(l = h) from the
fraction of (R, L) endpoint pairs that fall inside the bond acceptance
volume — independent of the equilibrium-MD sampling bias diagnosed in A1.

Status: SKELETON. The pygamd / cu_gala API for two things is uncertain and
left as TODO until first cluster session:

  1. Z-tether harmonic potential between membrane CoMs.
     Candidates: gala.HarmonicCenterForce, gala.PlanePotential, or a
     custom periodic-z restraint via gala.ForceField.add_external. See
     pygamd-v1.readthedocs.io. To-test: pick the first that works in a
     pilot at h=14 σ.

  2. Disabling R-L binding without breaking the rest of the force field.
     Cleanest: set the LJ epsilon between bind beads (RB / LB) to 0 in
     the NB_Tabs entry. ref/nvt-md.py L~80-100 has the relevant table.

CLI:
    --system K100/K10/K01     pick base xml + force field
    --h <float σ>             target membrane separation
    --n-frames <int>          frames to write (= FREQ_TRAJ × steps)
    --seed <int>              RNG seed
    --out-dir <path>          everything goes here
    --pilot                   short run, < 10 min; writes pilot_summary.json

For pilot, n_frames is forced to 20 and a pilot_summary.json is written
with ⟨z_membrane⟩, max ⟨bond_count⟩ (should be 0), and walltime — used by
single_pilot.slurm's sanity assertions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SYS_ALIAS = {
    "K100": "15_120x120_K100_EPS05",
    "K10":  "15_120x120_K10_EPS05",
    "K01":  "22_120x120_K01_EPS05",
}

# Z-tether stiffness — large enough to keep ⟨δz²⟩ < 0.01 σ²
DEFAULT_K_Z = 100.0  # ε / σ²


def build_constrained_app(system: str, h_target: float, out_dir: Path,
                            n_timesteps: int, freq_traj: int, seed: int):
    """Build the cu_gala application with z-tether + RL-binding disabled.

    This is the part that lives on the cluster — cu_gala only runs on
    GPU nodes. Returns the app object ready to run().

    TODO (Session 3 on cluster):
      - import cu_gala, PerformConfig, AllInfo, ...
      - replicate ref/nvt-md.py force-field setup but set bind LJ ε = 0
      - add Z-tether harmonic on lipid head CoM of each leaflet
        (target zR_membrane = -h/2, zL_membrane = +h/2)
      - dump traj.xyz every freq_traj
    """
    raise NotImplementedError(
        "TODO: implement cu_gala constrained-h setup. See module docstring. "
        f"Args received: system={system}, h={h_target}, out={out_dir}, "
        f"n_steps={n_timesteps}, freq={freq_traj}, seed={seed}"
    )


def pilot_summary_from_log(out_dir: Path, h_target: float,
                            wall_seconds: float) -> dict:
    """Read the run's dump.tsv + traj log and return sanity metrics.

    Pilot expects:
      - bond_count_total == 0 (RL binding disabled, no R-L bond should form)
      - mean_z_membrane within 0.5 σ of h_target (z-tether effective)
      - n_frames_written >= 80% of requested

    TODO: implement once we know the exact log format on cluster.
    For now, write placeholder values that the assert script will catch
    if real values are missing.
    """
    summary = {
        "h_target": float(h_target),
        "wall_seconds": float(wall_seconds),
        "bond_count_total": 0,          # TODO: read from log
        "mean_z_membrane": float(h_target),  # TODO: compute from traj
        "n_frames_written": 0,          # TODO: count
        "note": "PILOT SUMMARY IS PLACEHOLDER until cu_gala wiring done",
    }
    return summary


def _print_purpose() -> None:
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  cluster/scripts/nvt-md-constrained-h.py                          ║
║  Constrained-h slab MD: fixed membrane gap, no R-L binding        ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Runs an MD simulation derived from ref/nvt-md.py with two modifications:

  (a) z-tether: harmonic constraint holds each membrane CoM at ±h/2 σ,
      enforcing a fixed gap during the run.
  (b) R-L binding disabled (RL_EPSILON = 0), so the trajectory samples
      pure-unbound chain statistics at the target gap.

The resulting traj.xyz is post-processed by analyze_slab_traj.py to
measure K2D(l = h) directly — this is the unique signal needed to fix
the §4.5 / §5.4 caveats in stage_essay.

CURRENT STATUS: SKELETON
─────────────────────────
The cu_gala wiring (Step 1) is TODO until cluster/trial/03_pygamd_probe.sh
returns the actual import + class names. Until then this script raises
NotImplementedError; --pilot still emits a placeholder pilot_summary.json
so the SLURM template can be smoke-tested.
""")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--system", required=True, choices=list(SYS_ALIAS),
                   help="K100 / K10 / K01")
    p.add_argument("--h", type=float, required=True,
                   help="target membrane separation in σ")
    p.add_argument("--n-frames", type=int, default=500,
                   help="number of trajectory frames to write")
    p.add_argument("--freq-traj", type=int, default=10_000,
                   help="MD steps per trajectory frame (matches ref/nvt-md.py)")
    p.add_argument("--k-z", type=float, default=DEFAULT_K_Z,
                   help="z-tether harmonic stiffness (ε/σ²)")
    p.add_argument("--seed", type=int, default=20260601)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--pilot", action="store_true",
                   help="Pilot: 20 frames, < 10 min on GPU, writes pilot_summary.json")
    p.add_argument("--quiet", action="store_true",
                   help="Skip the PURPOSE banner")
    args = p.parse_args(argv)

    if not args.quiet:
        _print_purpose()

    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    n_frames = 20 if args.pilot else args.n_frames
    n_timesteps = n_frames * args.freq_traj
    print(f"▶  Step 1/3 — config")
    print(f"   system    : {args.system}")
    print(f"   h target  : {args.h} σ")
    print(f"   n_frames  : {n_frames}{' (PILOT)' if args.pilot else ''}")
    print(f"   k_z       : {args.k_z} ε/σ²")
    print(f"   seed      : {args.seed}")
    print(f"   n_steps   : {n_timesteps}")
    print(f"   out_dir   : {args.out_dir}")
    print(f"\n▶  Step 2/3 — build app + run MD")

    t0 = time.time()
    try:
        app = build_constrained_app(
            args.system, args.h, args.out_dir,
            n_timesteps=n_timesteps, freq_traj=args.freq_traj, seed=args.seed,
        )
        # TODO: app.run(n_timesteps)
        # placeholder until cu_gala is wired in:
        print("WARN: cu_gala wiring is TODO. Returning placeholder so SLURM "
              "template can be smoke-tested. Real run will need cluster GPU.")
    except NotImplementedError as e:
        if not args.pilot:
            raise
        # In pilot we tolerate missing impl: still emit a pilot_summary so
        # the SLURM template logic flows end-to-end.
        print(f"NotImplementedError caught in pilot: {e}")

    wall = time.time() - t0
    print(f"\n▶  Step 3/3 — finalize")

    if args.pilot:
        summary = pilot_summary_from_log(args.out_dir, args.h, wall)
        summary["pilot"] = True
        summary["placeholder"] = "cu_gala impl pending"
        out_json = args.out_dir / "pilot_summary.json"
        out_json.write_text(json.dumps(summary, indent=2))
        print(f"Wrote {out_json}")
    print(f"Done in {wall:.1f} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

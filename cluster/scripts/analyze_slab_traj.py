"""C.4 — analyze constrained-h slab MD trajectories → K2D(l) per (system, h).

Walks cluster/outputs/slab/<SYS>_h<H>/traj.xyz for each (system, h) and
measures the equilibrium fraction of R-L endpoint pairs that fall in the
binding kernel acceptance volume. Because the membrane gap is fixed at h
in slab MD, the result is K2D(l = h) directly — no convolution, no
unbound-sampling-bias correction needed.

Approach:
  1. Read traj.xyz frame by frame (stream, do not load whole file)
  2. For each frame, take the binding-bead z-coordinates of all R and L
     proteins; compute the lateral RxRy and tilt angles
  3. Apply the same soft-Boltzmann radial + angular acceptance as
     scripts/raw_tether_partition_k2d.py:radial_u_kbt + angle_factor
  4. Average over frames and pairs → K2D(l = h) for that (system, h)
  5. Stack across 6 h values → (3 × 6) grid in K2D_l_grid.npz

Pilot: read 20 frames of one (system, h), confirm K2D magnitude. < 30 s.
Production: 18 (system, h) jobs × 500 frames. Parallel across (system, h)
  with --n-jobs 8.
"""
from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
# Reuse the bond kernel + angle factor from raw_tether_partition_k2d
from raw_tether_partition_k2d import (  # noqa: E402
    radial_u_kbt, angle_factor, ANGLE_K, ANGLE0_DEG, RL_RCUT, HARD_R,
    KBT_IN_EPSILON,
)
from io_xyz import iter_frames  # noqa: E402

DEFAULT_SLAB_ROOT = REPO_ROOT / "cluster" / "outputs" / "slab"
DEFAULT_OUT = REPO_ROOT / "cluster" / "results" / "slab" / "K2D_l_grid.npz"

SYSTEMS = ("K100", "K10", "K01")
H_VALUES = (8.0, 10.0, 12.0, 14.0, 16.0, 18.0)


def measure_k2d_for_traj(traj_dir: Path, system: str, h: float,
                          n_frames_limit: int | None = None) -> dict:
    """Compute K2D(l = h) from one slab MD trajectory.

    TODO: actual implementation depends on slab traj.xyz layout. Likely
    same atom ordering as ref/nvt-md.py output; reuse extract_chain_coords
    helpers to identify R/L binding beads.

    For pilot phase this returns a placeholder so the pipeline can be
    smoke-tested without real slab data. The placeholder uses random
    values consistent with rigid K100 ≈ 12000 nm² so downstream
    convolution stays well-behaved.
    """
    if not traj_dir.exists():
        return {"system": system, "h": h, "K2D": float("nan"),
                "K2D_err": float("nan"), "n_frames": 0,
                "note": f"missing {traj_dir}"}

    # TODO: replace this placeholder with real measurement
    # 1. iter_frames(traj_dir / "traj.xyz", subset_indices=binding_atoms)
    # 2. For each frame:
    #      lateral disp r_xy = R_bind_xy - L_bind_xy
    #      z separation         = R_bind_z - L_bind_z
    #      tilt angles from R_term / L_term vectors
    #      U_eff = radial_u_kbt(|r|) * angle_factor(theta_R) * angle_factor(theta_L)
    #      K2D contribution = π · r_max² · ⟨exp(-U_eff) - 1⟩
    # 3. Mean over frames

    placeholder = {
        "K100": 12000.0, "K10": 870.0, "K01": 360.0,
    }.get(system, 1.0)
    return {
        "system": system, "h": h,
        "K2D": placeholder,
        "K2D_err": placeholder * 0.05,
        "n_frames": n_frames_limit or 0,
        "note": "PLACEHOLDER — actual implementation pending real slab traj",
    }


def _one_task(args: tuple) -> dict:
    traj_dir, system, h, n_lim = args
    return measure_k2d_for_traj(traj_dir, system, h, n_lim)


def _print_purpose() -> None:
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  cluster/scripts/analyze_slab_traj.py                             ║
║  Slab MD traj → K2D(l = h) per (system, h)                        ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Reads each <slab-root>/<system>_h<h>/traj.xyz, applies the soft-Boltzmann
radial + angular acceptance kernel from raw_tether_partition_k2d.py, and
measures K2D(l = h) directly — bypassing the unbound-sampling bias that
breaks equilibrium-MD analysis.

CURRENT STATUS: SKELETON
─────────────────────────
The actual measurement is a TODO until real slab MD data is available.
For now this script returns placeholder values consistent with target
K2D,max so downstream convolution code can be smoke-tested. Once real
traj.xyz files land in cluster/outputs/slab/, replace the placeholder
in measure_k2d_for_traj() with the actual frame-loop measurement.

PILOT
=====
With --pilot, only (K10, h=14) is read with 20 frames. Use it to confirm
the SLURM template + I/O paths before launching the 18-task array.
""")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slab-root", type=Path, default=DEFAULT_SLAB_ROOT)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--n-jobs", type=int, default=1)
    p.add_argument("--pilot", action="store_true",
                   help="Pilot: only K10 h=14, 20 frames. < 30 s.")
    p.add_argument("--quiet", action="store_true",
                   help="Skip the PURPOSE banner")
    args = p.parse_args(argv)
    if not args.quiet:
        _print_purpose()
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    if args.pilot:
        tasks = [(args.slab_root / "K10_h14", "K10", 14.0, 20)]
        out_path = REPO_ROOT / "results" / "scratch" / "pilot_slab" / "K2D_l_grid.npz"
    else:
        tasks = []
        for s in SYSTEMS:
            for h in H_VALUES:
                d = args.slab_root / f"{s}_h{int(h)}"
                tasks.append((d, s, h, None))
        out_path = args.out

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[analyze_slab_traj] {len(tasks)} (system, h) tasks "
          f"n_jobs={args.n_jobs} pilot={args.pilot}")
    if args.n_jobs <= 1 or len(tasks) == 1:
        rows = [_one_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=args.n_jobs) as ex:
            rows = list(ex.map(_one_task, tasks))

    # Pack to 3×6 grid (or pilot 1-element grid)
    systems_used = sorted({r["system"] for r in rows})
    hs_used = sorted({r["h"] for r in rows})
    K2D = np.full((len(systems_used), len(hs_used)), np.nan)
    err = np.full_like(K2D, np.nan)
    for r in rows:
        i = systems_used.index(r["system"])
        j = hs_used.index(r["h"])
        K2D[i, j] = r["K2D"]
        err[i, j] = r["K2D_err"]

    np.savez(out_path, systems=systems_used, h=hs_used, K2D=K2D, K2D_err=err)
    print(f"Wrote {out_path}")

    # Pilot sanity
    if args.pilot:
        assert not np.isnan(K2D).all(), "PILOT FAIL: all NaN K2D"
        print(f"PILOT OK: K2D[K10, h=14] = {K2D[0, 0]:.1f} ± {err[0, 0]:.1f} nm²")
    return 0


if __name__ == "__main__":
    sys.exit(main())

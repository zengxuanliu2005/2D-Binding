"""§0.2 — thin wrapper around scripts/extract_chain_coords.py for one replica.

PURPOSE
=======
Resolves short system labels (K100/K10/K01) to full cluster directory names,
points at an arbitrary replica subdir, and writes the chain_coords.npz at a
location chosen by the SLURM array job.

Parallelism: this script processes ONE (system, replica). The SLURM array
parallelizes across (system, replica) — see cluster/slurm/array_extract.slurm.

Wall time (per replica, ~500 frames): ~30 s.
Bundle prod (3 systems × 100 replicas, --n-jobs 8): ~6 min.

PILOT MODE (--pilot)
====================
Limits to 50 frames, < 30 s. Asserts the output npz has the expected schema
(positions_R / positions_L / bound_R / bound_L / n_frames / n_R / n_L / box)
and prints them. Use this when first wiring up a new cluster path.

USAGE
=====
    python cluster/scripts/extract_one_replica.py \\
        --system K100 \\
        --replica s001 \\
        --md-base /mnt/nfs/ugstu/liuzx \\
        --out cluster/outputs/extracted/K100/s001/chain_coords.npz \\
        --pilot

WHAT TO LOOK FOR
================
✓ "PILOT OK: n_frames=50, n_R=15, n_L=15, file_size_MB=X" at the end
✓ No traceback. If you see one, paste it to Claude — most fixes live in
  topology.py / bonds.py and depend on the cluster's traj/psf format.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow importing scripts.extract_chain_coords from cluster/scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import extract_chain_coords as ecc  # noqa: E402

SYS_ALIAS = {
    "K100": "15_120x120_K100_EPS05",
    "K10":  "15_120x120_K10_EPS05",
    "K01":  "22_120x120_K01_EPS05",
}

# TODO: confirm this is the cluster path with the off-site collaborator; ENV var override available
DEFAULT_MD_BASE = os.environ.get("MD_BASE", "/mnt/nfs/ugstu/liuzx/2D-Binding-MD")


def resolve_replica_dir(system: str, replica: str, base: Path) -> Path:
    """Map (K100, s003) → /mnt/.../15_120x120_K100_EPS05/s003."""
    full_sys = SYS_ALIAS.get(system, system)
    return base / full_sys / replica


def _print_purpose() -> None:
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  cluster/scripts/extract_one_replica.py                           ║
║  Extract chain_coords.npz for a single (system, replica)          ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Reads <md-base>/<system_dir>/<replica>/{traj.xyz,mol.psf,num_bonds...}
and writes a chain_coords.npz with positions/bound arrays.
The SLURM array job calls this once per (system, replica). With --pilot
only the first 50 frames are processed (< 30 s) and the npz is asserted
to have the expected schema before returning.
""")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--system", required=True,
                   help="System label: K100/K10/K01 or full directory name")
    p.add_argument("--replica", required=True,
                   help="Replica subdir name (e.g. s001)")
    p.add_argument("--out", required=True,
                   help="Output npz path (will create parent dir)")
    p.add_argument("--md-base", default=DEFAULT_MD_BASE,
                   help=f"Cluster MD root (default: {DEFAULT_MD_BASE})")
    p.add_argument("--pilot", action="store_true",
                   help="Pilot mode: extract only 50 frames, < 30 s")
    p.add_argument("--max-frames", type=int, default=None,
                   help="Limit frames (default: all). Pilot sets this to 50.")
    p.add_argument("--quiet", action="store_true",
                   help="Skip the PURPOSE banner (for parallel batch runs)")
    args = p.parse_args(argv)

    if not args.quiet:
        _print_purpose()

    base = Path(args.md_base)
    replica_dir = resolve_replica_dir(args.system, args.replica, base)
    if not replica_dir.exists():
        print(f"   ✗  replica dir not found: {replica_dir}", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    max_frames = 50 if args.pilot else args.max_frames
    print(f"▶  Step 1/3 — resolved paths")
    print(f"   system  : {args.system}")
    print(f"   replica : {args.replica}")
    print(f"   in dir  : {replica_dir}")
    print(f"   out file: {out_path}")
    print(f"   frames  : {max_frames or 'all'}{' (PILOT)' if args.pilot else ''}")
    print(f"\n▶  Step 2/3 — extracting frames ...")

    # extract_chain_coords.run() writes <out_dir>/chain_coords.npz; we want
    # it to land exactly at args.out, so pass parent dir and rename.
    tmp_out_dir = out_path.parent
    summary = ecc.run(replica_dir, tmp_out_dir, max_frames=max_frames,
                       progress=not args.pilot)
    # ecc.run writes tmp_out_dir / "chain_coords.npz"; rename if user gave a
    # different filename.
    default_path = tmp_out_dir / "chain_coords.npz"
    if default_path.exists() and default_path != out_path:
        default_path.rename(out_path)

    print(f"\n▶  Step 3/3 — verify output")
    print(f"   wrote {out_path}  ({out_path.stat().st_size/1e6:.2f} MB)")

    # Pilot sanity: confirm npz loads and has expected keys
    if args.pilot:
        import numpy as np
        d = np.load(out_path)
        for key in ("positions_R", "positions_L", "bound_R", "bound_L",
                     "n_frames", "n_R", "n_L"):
            assert key in d.files, f"PILOT FAIL: missing key {key}"
        nf = int(d["n_frames"])
        assert 0 < nf <= 50, f"PILOT FAIL: n_frames={nf} not in (0, 50]"
        print(f"\n   ✓  PILOT OK: n_frames={nf}, n_R={int(d['n_R'])}, "
              f"n_L={int(d['n_L'])}, file_size_MB={out_path.stat().st_size/1e6:.1f}")
        print("\n   Report: schema OK, paths resolved correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

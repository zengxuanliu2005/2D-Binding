"""§0.2 — concatenate per-replica chain_coords.npz into a single full-data npz.

PURPOSE
=======
After array_extract.slurm finishes, every (system, replica) has its own
chain_coords.npz at cluster/outputs/extracted/<sys>/<replica>/chain_coords.npz.
This script walks those, concatenates along the frame axis, and writes one
merged npz per system at:

    cluster/results/section0/merged_chain_coords/<sys>/chain_coords.npz

This is the "full data" version of what we have locally at
results/chain_coords/<sys>/chain_coords.npz (which is s001 only).

INVARIANTS
==========
For each system, all replicas must agree on (n_R, n_L, box). Mismatch raises
an AssertionError to surface mixed-system corruption early.

PILOT
=====
With --pilot, only the first 2 replicas per system are merged. Use it to
sanity-check that the schema and frame counts line up before running on
all 100+ replicas.

PARALLELISM
===========
Merge is independent per system. Use --n-jobs 3 to merge all three at once
(typical wall time ~1 min for 100 replicas per system on cluster NFS).

USAGE
=====
    python cluster/scripts/merge_chain_coords.py \\
        --input-root cluster/outputs/extracted \\
        --output-root cluster/results/section0/merged_chain_coords \\
        --n-jobs 3
"""
from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_INPUT_ROOT = REPO_ROOT / "cluster" / "outputs" / "extracted"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "cluster" / "results" / "section0" / "merged_chain_coords"

SYSTEMS = ("15_120x120_K100_EPS05", "15_120x120_K10_EPS05", "22_120x120_K01_EPS05")


def merge_one_system(system: str, input_root: Path, output_root: Path,
                      pilot: bool = False) -> dict:
    """Concatenate all replicas of one system along the frame axis.

    Returns a summary dict; writes the merged npz.
    """
    sys_in = input_root / system
    replicas = sorted(sys_in.glob("s[0-9][0-9][0-9]"))
    if pilot:
        replicas = replicas[:2]
    if not replicas:
        return {"system": system, "n_replicas": 0, "skipped": True,
                "reason": f"no s### subdirs in {sys_in}"}

    print(f"[{system}] merging {len(replicas)} replicas", flush=True)

    pR_chunks, pL_chunks = [], []
    bR_chunks, bL_chunks = [], []
    partR_chunks, partL_chunks = [], []
    n_R, n_L = None, None
    box = None
    total_frames = 0

    for rep in replicas:
        npz = rep / "chain_coords.npz"
        if not npz.exists():
            print(f"  WARN  {rep.name}: chain_coords.npz missing, skip")
            continue
        d = np.load(npz)
        if n_R is None:
            n_R = int(d["n_R"]); n_L = int(d["n_L"])
            box = d["box"].copy()
        else:
            assert int(d["n_R"]) == n_R, f"{rep}: n_R mismatch ({int(d['n_R'])} vs {n_R})"
            assert int(d["n_L"]) == n_L, f"{rep}: n_L mismatch"
            assert np.allclose(d["box"], box, atol=1e-6), f"{rep}: box mismatch"
        pR_chunks.append(d["positions_R"])
        pL_chunks.append(d["positions_L"])
        bR_chunks.append(d["bound_R"])
        bL_chunks.append(d["bound_L"])
        if "partner_R" in d.files:
            partR_chunks.append(d["partner_R"])
            partL_chunks.append(d["partner_L"])
        total_frames += int(d["n_frames"])

    if total_frames == 0:
        return {"system": system, "n_replicas": len(replicas), "skipped": True,
                "reason": "no usable frames"}

    pR = np.concatenate(pR_chunks, axis=0)
    pL = np.concatenate(pL_chunks, axis=0)
    bR = np.concatenate(bR_chunks, axis=0)
    bL = np.concatenate(bL_chunks, axis=0)
    payload = dict(
        positions_R=pR, positions_L=pL,
        bound_R=bR,     bound_L=bL,
        n_frames=np.int64(pR.shape[0]),
        n_R=np.int64(n_R), n_L=np.int64(n_L),
        box=box,
    )
    if partR_chunks:
        payload["partner_R"] = np.concatenate(partR_chunks, axis=0)
        payload["partner_L"] = np.concatenate(partL_chunks, axis=0)

    sys_out = output_root / system
    sys_out.mkdir(parents=True, exist_ok=True)
    out_path = sys_out / "chain_coords.npz"
    np.savez_compressed(out_path, **payload)

    assert pR.shape[0] == total_frames, (
        f"INVARIANT FAIL: merged frames {pR.shape[0]} ≠ sum {total_frames}"
    )
    summary = {
        "system": system,
        "n_replicas": len(replicas),
        "total_frames": int(pR.shape[0]),
        "n_R": n_R, "n_L": n_L,
        "out_size_MB": out_path.stat().st_size / 1e6,
        "out_path": str(out_path),
    }
    print(f"[{system}] OK: {summary['total_frames']} frames, "
          f"{summary['out_size_MB']:.1f} MB → {summary['out_path']}", flush=True)
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    p.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    p.add_argument("--systems", nargs="+", default=list(SYSTEMS))
    p.add_argument("--n-jobs", type=int, default=1,
                   help="Parallel across systems (default 1; max 3 = # systems)")
    p.add_argument("--pilot", action="store_true",
                   help="Pilot: merge only 2 replicas per system, < 5 s")
    args = p.parse_args(argv)

    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")  # avoid oversubscription

    print("""
╔════════════════════════════════════════════════════════════════════╗
║  cluster/scripts/merge_chain_coords.py                            ║
║  Concatenate per-replica npz into one full-data npz per system    ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Walks <input-root>/<system>/<replica>/chain_coords.npz for every system
+ replica, concatenates along the frame axis, and writes one merged npz
per system to <output-root>/<system>/chain_coords.npz.
""")
    print(f"▶  config: n_systems={len(args.systems)}, "
          f"n_jobs={args.n_jobs}, pilot={args.pilot}")
    print(f"   input-root  : {args.input_root}")
    print(f"   output-root : {args.output_root}\n")
    if args.n_jobs <= 1 or len(args.systems) <= 1:
        results = [merge_one_system(s, args.input_root, args.output_root, args.pilot)
                   for s in args.systems]
    else:
        from functools import partial
        worker = partial(merge_one_system, input_root=args.input_root,
                          output_root=args.output_root, pilot=args.pilot)
        with ProcessPoolExecutor(max_workers=args.n_jobs) as ex:
            results = list(ex.map(worker, args.systems))

    print("\n=== summary ===")
    for r in results:
        if r.get("skipped"):
            print(f"  SKIP  {r['system']}: {r['reason']}")
        else:
            print(f"  {r['system']:<32}  n_replicas={r['n_replicas']:>3}  "
                  f"frames={r['total_frames']:>6}  "
                  f"size={r['out_size_MB']:5.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

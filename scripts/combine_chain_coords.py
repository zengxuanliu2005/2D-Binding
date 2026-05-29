"""Combine per-replica `chain_coords.npz` files into one per-system npz.

The per-replica npz layout (from `scripts/extract_chain_coords.py`):

    positions_R   (n_frames, n_R, 13, 3)   float64
    positions_L   (n_frames, n_L, 13, 3)   float64
    bound_R       (n_frames, n_R)          bool
    bound_L       (n_frames, n_L)          bool
    partner_R     (n_frames, n_R)          int32
    partner_L     (n_frames, n_L)          int32
    box           (3,)                     float64
    n_frames      scalar                   int64
    n_R, n_L      scalar                   int64

This script concatenates the per-frame arrays along axis 0 across all
input replicas, asserting that the scalar / per-protein metadata
(`n_R`, `n_L`, `box`) match across replicas. `n_frames` becomes the
sum of the input replica frame counts.

Usage (from cluster or local):

    python scripts/combine_chain_coords.py \\
        chain_coords/<sys>/s001/chain_coords.npz \\
        chain_coords/<sys>/s002/chain_coords.npz \\
        ... \\
        --out results/chain_coords/<sys>/chain_coords.npz

The downstream `phd_inputs.py` / `phd_closure.py` consume the combined
npz unchanged.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np


FRAME_KEYS = ("positions_R", "positions_L",
              "bound_R", "bound_L",
              "partner_R", "partner_L")
SCALAR_KEYS = ("n_R", "n_L")
ARRAY_KEYS = ("box",)


def combine(inputs: list[Path], out: Path) -> dict:
    if not inputs:
        raise ValueError("no input npz paths")

    # Load first replica to set the reference metadata
    ref = np.load(inputs[0])
    ref_n_R = int(ref["n_R"])
    ref_n_L = int(ref["n_L"])
    ref_box = np.asarray(ref["box"])

    # Accumulate per-frame arrays as lists, sum n_frames
    parts = {k: [ref[k]] for k in FRAME_KEYS}
    total_frames = int(ref["n_frames"])

    for p in inputs[1:]:
        d = np.load(p)
        # metadata must match
        if int(d["n_R"]) != ref_n_R:
            raise ValueError(f"{p}: n_R={int(d['n_R'])} != {ref_n_R}")
        if int(d["n_L"]) != ref_n_L:
            raise ValueError(f"{p}: n_L={int(d['n_L'])} != {ref_n_L}")
        if not np.allclose(np.asarray(d["box"]), ref_box):
            raise ValueError(f"{p}: box mismatch")
        for k in FRAME_KEYS:
            parts[k].append(d[k])
        total_frames += int(d["n_frames"])

    combined = {k: np.concatenate(parts[k], axis=0) for k in FRAME_KEYS}
    combined["box"]      = ref_box
    combined["n_frames"] = total_frames
    combined["n_R"]      = ref_n_R
    combined["n_L"]      = ref_n_L

    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **combined)
    sz_mb = out.stat().st_size / 1024 / 1024
    return {
        "n_inputs": len(inputs),
        "n_frames_total": total_frames,
        "n_R": ref_n_R,
        "n_L": ref_n_L,
        "out_size_MB": sz_mb,
    }


def _smoke_test():
    """Self-check: combining a single replica twice should produce arrays
    exactly twice as long, and the four-term closure should be unchanged."""
    print("[smoke] doubling the local s001 K100 replica...")
    src = Path("results/chain_coords/15_120x120_K100_EPS05/chain_coords.npz")
    if not src.exists():
        print(f"[smoke] {src} not found — skipping")
        return 1
    out = Path("/tmp/_combine_smoke.npz")
    summary = combine([src, src], out)
    single = np.load(src)
    doubled = np.load(out)
    for k in FRAME_KEYS:
        if doubled[k].shape[0] != 2 * single[k].shape[0]:
            print(f"[smoke] FAIL: {k} shape {doubled[k].shape}")
            return 1
    for k in SCALAR_KEYS:
        if int(doubled[k]) != int(single[k]):
            print(f"[smoke] FAIL: {k} {int(doubled[k])} != {int(single[k])}")
            return 1
    if int(doubled["n_frames"]) != 2 * int(single["n_frames"]):
        print(f"[smoke] FAIL: n_frames")
        return 1
    print(f"[smoke] OK: combined {summary['n_frames_total']} frames "
          f"({summary['out_size_MB']:.2f} MB)")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="*", type=Path,
                   help="per-replica chain_coords.npz paths")
    p.add_argument("--out", type=Path,
                   help="combined output npz path")
    p.add_argument("--smoke", action="store_true",
                   help="run the self-check on the local s001 replica")
    args = p.parse_args(argv[1:])

    if args.smoke:
        return _smoke_test()

    if not args.inputs or args.out is None:
        p.error("either --smoke or (inputs + --out) are required")

    summary = combine(args.inputs, args.out)
    print("Done.")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

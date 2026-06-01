"""Streaming reader for the project's `traj.xyz` files.

Format (verified on K100):
    line 1: int N (atom count)
    line 2: arbitrary comment ('membrane protein binding')
    next N lines: `element x y z ix iy iz`  (ix/iy/iz are image flags)

Coordinates are unwrapped (the simulator writes continuous coords with image
flags, see nvt-md.py `dcd_dump.unpbc(True)`), so each atom's (x, y, z) value
is the unwrapped position; image flags are written for completeness only.

The protein subset is small (~hundreds of atoms) and almost always all we need,
so the reader supports `subset_indices=` to skip unwanted atoms efficiently.
"""

from __future__ import annotations
from pathlib import Path
from typing import Iterator
import numpy as np


def iter_frames(
    xyz_path: Path,
    subset_indices: list[int] | None = None,
    max_frames: int | None = None,
) -> Iterator[tuple[int, np.ndarray]]:
    """Yield `(frame_idx, coords)` per frame. `coords` is shape (N_sub, 3)
    if `subset_indices` is given, otherwise (N_total, 3).

    Atoms are 0-indexed throughout the project. `subset_indices` may be in any
    order; the returned coords follow the same order.
    """
    if subset_indices is not None:
        # we'll use a boolean mask for fast skipping, then reorder
        sub = np.asarray(subset_indices, dtype=np.int64)
        want = set(int(i) for i in sub)
        # map orig->position in output
        order_map = {int(i): k for k, i in enumerate(sub)}
        n_sub = len(sub)
    else:
        sub = None
        want = None
        order_map = None
        n_sub = -1

    frame_idx = 0
    with open(xyz_path, "r") as f:
        while True:
            head = f.readline()
            if not head:
                return
            n = int(head.strip())
            f.readline()  # comment line
            if subset_indices is None:
                coords = np.empty((n, 3), dtype=np.float64)
                for i in range(n):
                    toks = f.readline().split()
                    coords[i, 0] = float(toks[1])
                    coords[i, 1] = float(toks[2])
                    coords[i, 2] = float(toks[3])
                yield frame_idx, coords
            else:
                coords = np.empty((n_sub, 3), dtype=np.float64)
                got = 0
                for i in range(n):
                    line = f.readline()
                    if i in want:
                        toks = line.split()
                        out = order_map[i]
                        coords[out, 0] = float(toks[1])
                        coords[out, 1] = float(toks[2])
                        coords[out, 2] = float(toks[3])
                        got += 1
                if got != n_sub:
                    raise RuntimeError(
                        f"frame {frame_idx}: requested {n_sub} atoms, found {got}"
                    )
                yield frame_idx, coords

            frame_idx += 1
            if max_frames is not None and frame_idx >= max_frames:
                return

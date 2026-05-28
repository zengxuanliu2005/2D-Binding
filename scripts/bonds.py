"""Parse `num_bonds_for_xyz_frames.dat`.

Format (one line per frame):
    n_bonds  [b_len  x  y  z  R_atom_idx_1indexed  L_atom_idx_1indexed] * n_bonds

Atom indices in the file are 1-indexed (PSF convention).

Returns a list (per frame) of (R_atom_idx_0indexed, L_atom_idx_0indexed) pairs.
"""
from __future__ import annotations
from pathlib import Path


def parse_num_bonds(path: Path) -> list[list[tuple[int, int]]]:
    out: list[list[tuple[int, int]]] = []
    with open(path) as f:
        for line in f:
            toks = line.split()
            n = int(toks[0])
            pairs: list[tuple[int, int]] = []
            for k in range(n):
                base = 1 + 6 * k
                r_atom = int(toks[base + 4]) - 1
                l_atom = int(toks[base + 5]) - 1
                pairs.append((r_atom, l_atom))
            out.append(pairs)
    return out

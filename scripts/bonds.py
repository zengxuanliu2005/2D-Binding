"""Parse `num_bonds_for_xyz_frames.dat`.

Format (one line per frame, repeating per bond):
    n_bonds  [b_len  theta_R  theta_L  z_complex  R_atom_idx_1indexed
              L_atom_idx_1indexed] * n_bonds

* `b_len`: |RB-LB| (σ).
* `theta_R`, `theta_L`: receptor- and ligand-side binding angles (degrees),
  i.e. the values stored verbatim by the legacy
  `bindsites_angle_distribution.tsv`.
* `z_complex`: z of the receptor membrane patch near the bond (σ);
  legacy `*_distance_to_membrane_*` files derive from these.
* Atom indices are 1-indexed (PSF convention). The two atoms recorded are
  the chain_idx_11 beads (RE_8 / LE_8 — the binding-angle partners).
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BondRow:
    b_len: float
    theta_R: float
    theta_L: float
    z_complex: float
    r_atom: int            # 0-indexed
    l_atom: int            # 0-indexed


def parse_num_bonds(path: Path) -> list[list[tuple[int, int]]]:
    """Backward-compatible: returns only the atom-pair list per frame."""
    out: list[list[tuple[int, int]]] = []
    for frame in parse_num_bonds_full(path):
        out.append([(b.r_atom, b.l_atom) for b in frame])
    return out


def parse_num_bonds_full(path: Path) -> list[list[BondRow]]:
    """Returns full per-bond data (lengths, angles, z, atoms) per frame."""
    out: list[list[BondRow]] = []
    with open(path) as f:
        for line in f:
            toks = line.split()
            n = int(toks[0])
            frame: list[BondRow] = []
            for k in range(n):
                base = 1 + 6 * k
                frame.append(BondRow(
                    b_len=float(toks[base + 0]),
                    theta_R=float(toks[base + 1]),
                    theta_L=float(toks[base + 2]),
                    z_complex=float(toks[base + 3]),
                    r_atom=int(toks[base + 4]) - 1,
                    l_atom=int(toks[base + 5]) - 1,
                ))
            out.append(frame)
    return out

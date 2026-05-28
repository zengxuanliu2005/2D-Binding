"""Per-protein feature vectors for the MI chain-rule decomposition.

For each protein in each frame we compute three independent feature blocks:

  * `axis(3)`  — unit vector along the chain axis (R: chain[12] − chain[0],
    flipped to point "up" for both R and L so that bound states cluster
    at the same hemisphere).
  * `bat_inner(30)` — the 30 BAT internal coordinates that describe the
    chain shape EXCLUDING the binding end: 11 bond lengths (RT/LT chain
    only, indices 0..10), 10 bond angles (interior, indices 0..9), and
    9 torsions (chain_idx 0..9). The full BAT has 33 DOF; we hold back
    3 to capture the binding-bead "end" separately.
  * `bat_end(3)`  — the 3 BAT entries that touch the binding bead:
    (last bond length, last bond angle, last torsion). These form the
    "end-volume" degrees of freedom whose distribution captures the
    binding-bead's local wiggle room.

The trans/rot/conf/bond decomposition is then obtained by computing the
Kozachenko-Leonenko entropy on growing nested feature sets and taking
chain-rule differences:

    H(axis, bat_inner, bat_end) = H(axis) + H(bat_inner | axis)
                                          + H(bat_end | axis, bat_inner)
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from bat import bond_lengths, bond_angles, dihedral_angles  # noqa: E402


def chain_axis(chain: np.ndarray, kind: str) -> np.ndarray:
    """In-plane (x, y) components of the chain axis unit vector.

    The axis unit vector v lives on the 2-sphere — using (vx, vy, vz)
    yields a rank-deficient covariance. We use the 2 in-plane components
    (vx, vy) which parameterise the 2-sphere bijectively in the hemisphere
    around (0, 0, 1) (where bound chains live). z is implicitly √(1−x²−y²).

    Ligand z is flipped so that both R and L axes share the same +z hemisphere
    — this makes the joint (axis_R, axis_L) distribution clustered in the same
    region when the pair is bound, instead of axis_R pointing up and axis_L
    pointing down.
    """
    v = chain[..., 12, :] - chain[..., 0, :]
    v = v / np.linalg.norm(v, axis=-1, keepdims=True)
    if kind == "L":
        v = np.stack([v[..., 0], v[..., 1], -v[..., 2]], axis=-1)
    return v[..., :2]   # (x, y) only — 2 DOF


def bat_split(chain: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split BAT into (inner_30, end_3).

    inner_30 = [b[0..10], a[0..9], t[0..8]]   — 11+10+9 = 30 DOF
    end_3    = [b[11], a[10], t[9]]           — last bond, angle, torsion = 3 DOF

    The last bond (b[11] = |chain[12] − chain[11]|) is the bond touching
    the binding bead; the last angle (a[10]) and last torsion (t[9]) are
    the angle and torsion at the binding-bead end.
    """
    b = bond_lengths(chain)
    a = bond_angles(chain)
    t = dihedral_angles(chain)
    inner = np.concatenate([b[..., :-1], a[..., :-1], t[..., :-1]], axis=-1)
    end = np.stack([b[..., -1], a[..., -1], t[..., -1]], axis=-1)
    return inner, end


def per_protein_features(positions: np.ndarray, kind: str
                         ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """positions: (..., 13, 3). Returns (axis(3), bat_inner(30), bat_end(3))."""
    axis = chain_axis(positions, kind)
    inner, end = bat_split(positions)
    return axis, inner, end

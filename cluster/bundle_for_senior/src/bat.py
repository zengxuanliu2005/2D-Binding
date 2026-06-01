"""Bond-angle-torsion (BAT) internal coordinates for a 13-bead chain.

For a chain of N=13 beads (anchored tail → ecto → binding bead) we compute:

    * 12 bond lengths           b[i]    = |r[i+1] - r[i]|,        i = 0..11
    * 11 bond angles            θ[i]    = ∠(r[i-1], r[i], r[i+1]),i = 1..11
    * 10 dihedral torsions      φ[i]    = dihedral(r[i], r[i+1],
                                                   r[i+2], r[i+3]),i = 0..9

Total = 33 internal degrees of freedom, equal to 3N - 6 — consistent with
the 39 Cartesian coordinates minus 3 translation + 3 rotation.

Angles in radians.

These coordinates are intrinsically rotation- and translation-invariant, so
no explicit Cartesian alignment is needed before computing them. Periodic
boundary effects must be handled UPSTREAM (positions should already be
per-chain unwrapped — that's what `extract_chain_coords.py` does).
"""
from __future__ import annotations
import numpy as np


def bond_lengths(chain: np.ndarray) -> np.ndarray:
    """chain: (..., N, 3). Returns (..., N-1) bond lengths."""
    return np.linalg.norm(np.diff(chain, axis=-2), axis=-1)


def bond_angles(chain: np.ndarray) -> np.ndarray:
    """chain: (..., N, 3). Returns (..., N-2) interior angles (radians)."""
    v1 = chain[..., :-2, :] - chain[..., 1:-1, :]       # toward predecessor
    v2 = chain[..., 2:, :]  - chain[..., 1:-1, :]       # toward successor
    cosv = np.einsum("...ij,...ij->...i", v1, v2) / (
        np.linalg.norm(v1, axis=-1) * np.linalg.norm(v2, axis=-1)
    )
    cosv = np.clip(cosv, -1.0, 1.0)
    return np.arccos(cosv)


def dihedral_angles(chain: np.ndarray) -> np.ndarray:
    """chain: (..., N, 3). Returns (..., N-3) dihedrals (radians, [-π, π])."""
    b0 = chain[..., 1:-2, :] - chain[..., :-3, :]
    b1 = chain[..., 2:-1, :] - chain[..., 1:-2, :]
    b2 = chain[..., 3:, :]  - chain[..., 2:-1, :]
    # normalise b1
    b1n = b1 / np.linalg.norm(b1, axis=-1, keepdims=True)
    # project b0 and b2 onto plane perp. to b1
    v = b0 - np.einsum("...i,...i->...", b0, b1n)[..., None] * b1n
    w = b2 - np.einsum("...i,...i->...", b2, b1n)[..., None] * b1n
    x = np.einsum("...i,...i->...", v, w)
    y = np.einsum("...i,...i->...", np.cross(b1n, v), w)
    return np.arctan2(y, x)


def bat_coords(chain: np.ndarray) -> np.ndarray:
    """chain: (..., N, 3). Returns (..., 3N-6) flat BAT array
    [bond_lengths(N-1) | bond_angles(N-2) | torsions(N-3)]."""
    b = bond_lengths(chain)
    a = bond_angles(chain)
    t = dihedral_angles(chain)
    return np.concatenate([b, a, t], axis=-1)

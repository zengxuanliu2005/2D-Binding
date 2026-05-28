"""Per-protein feature blocks for the MI chain-rule decomposition.

Five chain-rule blocks per protein, conditioned in the order listed below.
The Numata chain rule

    H(axis_ecto, ext_z, bonds, angles, torsions)
        = H(axis_ecto)
        + H(ext_z | axis_ecto)
        + H(bonds | axis_ecto, ext_z)
        + H(angles | axis_ecto, ext_z, bonds)
        + H(torsions | axis_ecto, ext_z, bonds, angles)

makes the per-block ΔS contributions sum to ΔS_total by construction.

| block      | dim | content                                                           |
|------------|-----|-------------------------------------------------------------------|
| axis_ecto  | 2   | in-plane (x, y) of the unit vector chain[12] − chain[3] (RH→RB)   |
| ext_z      | 1   | vertical ecto extension |chain[12].z − chain[3].z|                |
| bonds      | 12  | all 12 bond lengths along the chain                               |
| angles     | 11  | all 11 interior bond angles                                       |
| torsions   | 10  | all 10 dihedral torsions in (−π, π]                               |

This is the same total dimensionality (36) as the previous (axis(3) +
bat_inner(30) + bat_end(3)) split, but the changes matter:

  * The rotational feature is now the **ecto-domain orientation**
    (chain[12] − chain[3]) instead of the whole chain (chain[12] −
    chain[0]). The anchor (chain[0..3]) is rigid in all three K
    settings, so the previous axis was system-invariant; the ecto
    axis varies with the K01/K10/K100 stiffness and gives a real
    ΔΔS_rot.
  * Torsions live in their own block, so the cyclic estimator from
    `entropy_cyclic.py` can be applied to them without affecting the
    Gaussian-valid (bonds, angles, axis_ecto, ext_z) sub-blocks where
    Schlitter is exact.

Ligand z is flipped before computing ecto features so both R and L axes
share the same +z hemisphere (matches the convention from session 3 for
binding-vector vectors).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from bat import bond_lengths, bond_angles, dihedral_angles  # noqa: E402


def _flip_ligand_z(chain: np.ndarray, kind: str) -> np.ndarray:
    """Flip z of every bead for a ligand chain so axes share +z hemisphere."""
    if kind == "R":
        return chain
    out = chain.copy()
    out[..., 2] = -out[..., 2]
    return out


def ecto_features(chain: np.ndarray, kind: str
                  ) -> tuple[np.ndarray, np.ndarray]:
    """Return (axis_ecto(2), ext_z(1)).

    axis_ecto : (vx, vy) of the unit ecto vector  v = (chain[12] − chain[3]) / |.|
    ext_z     : chain[12].z − chain[3].z (signed; both R and L have +z anchor side)
    """
    ch = _flip_ligand_z(chain, kind)
    v = ch[..., 12, :] - ch[..., 3, :]
    nrm = np.linalg.norm(v, axis=-1, keepdims=True)
    nrm = np.where(nrm < 1e-12, 1.0, nrm)
    u = v / nrm
    axis = u[..., :2]                                     # (..., 2)
    extz = (ch[..., 12, 2] - ch[..., 3, 2])[..., None]    # (..., 1)
    return axis, extz


def bat_blocks(chain: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (bonds(12), angles(11), torsions(10)) BAT blocks."""
    b = bond_lengths(chain)
    a = bond_angles(chain)
    t = dihedral_angles(chain)
    return b, a, t


def per_protein_blocks(chain: np.ndarray, kind: str
                        ) -> dict[str, np.ndarray]:
    """Returns a dict with keys axis_ecto, ext_z, bonds, angles, torsions
    each of shape (..., d_block). chain has shape (..., 13, 3)."""
    axis_ecto, ext_z = ecto_features(chain, kind)
    bonds, angles, torsions = bat_blocks(chain)
    return {
        "axis_ecto": axis_ecto,
        "ext_z":     ext_z,
        "bonds":     bonds,
        "angles":    angles,
        "torsions":  torsions,
    }

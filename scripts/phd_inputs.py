"""Per-system inputs for the PhD's S1-S23 ΔF decomposition.

For each of the three flexibility classes (K100/K10/K01), bundle:

    R_e        free-chain end-to-end ⟨|chain[12] − chain[3]|⟩, σ
    D          bound-chain vertical reach ⟨chain[12].z − chain[3].z⟩
               (ligand z flipped — same convention as features.py), σ
    L          = R_max − D, σ (vertical range the binding bead can fluctuate)
    n_b        ⟨bound-pair count per frame⟩
    axes_R/L   in-plane (x, y, z) of the chain unit vector for unbound
               and bound R, L populations (used downstream for ω)

Constants (from ref/nvt-md.py and project conventions):

    R_max  = 12 σ (12 protein bonds × HARM r0 = 1.0; line 60)
    b      = 1.0 σ (HARM r0; NOT 0.95 — that's the lipid bond)
    A      = 14400 σ² (120 × 120 box)

All four `chain_coords.npz` quantities are sub-second to load.
"""
from __future__ import annotations
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from features import _flip_ligand_z  # noqa: E402

R_MAX = 12.0
B = 1.0
AREA = 14400.0    # σ² = nm²

SYSTEMS = [
    ("15_120x120_K100_EPS05", "rigid"),
    ("15_120x120_K10_EPS05",  "semi"),
    ("22_120x120_K01_EPS05",  "flex"),
]


@dataclass
class SystemInputs:
    label: str
    sys_name: str
    n_frames: int
    n_R: int
    n_L: int
    n_b_per_frame: float
    R_e_free: float
    D_bound: float
    L: float
    # axis unit vectors for the four populations
    axes_R_unbound: np.ndarray
    axes_L_unbound: np.ndarray
    axes_R_bound: np.ndarray
    axes_L_bound: np.ndarray


def _axis_unit_vector(positions: np.ndarray, kind: str) -> np.ndarray:
    """Chain unit vector chain[12] − chain[3], with ligand z flipped so that
    R and L axes share the same +z hemisphere when bound (matches
    `features.py::_flip_ligand_z` convention)."""
    flipped = _flip_ligand_z(positions, kind)
    v = flipped[..., 12, :] - flipped[..., 3, :]
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    n = np.where(n < 1e-12, 1.0, n)
    return v / n


def load_system(npz_path: Path, label: str, sys_name: str) -> SystemInputs:
    d = np.load(npz_path)
    pR = d["positions_R"]
    pL = d["positions_L"]
    bR = d["bound_R"]
    bL = d["bound_L"]
    n_frames = int(d["n_frames"])
    n_R = int(d["n_R"])
    n_L = int(d["n_L"])

    # End-to-end of free chain (chain[12] - chain[3] is the ecto domain)
    v_R = pR[..., 12, :] - pR[..., 3, :]
    v_L = pL[..., 12, :] - pL[..., 3, :]
    rmag_R = np.linalg.norm(v_R, axis=-1)
    rmag_L = np.linalg.norm(v_L, axis=-1)
    R_e_free = float(np.mean(np.concatenate([rmag_R[~bR], rmag_L[~bL]])))

    # D = vertical reach of bound chain (ligand z flipped to share sign with R)
    flipped_R = _flip_ligand_z(pR, "R")  # no-op for R
    flipped_L = _flip_ligand_z(pL, "L")  # flips z
    ext_z_R = flipped_R[..., 12, 2] - flipped_R[..., 3, 2]
    ext_z_L = flipped_L[..., 12, 2] - flipped_L[..., 3, 2]
    D_bound = float(np.mean(np.concatenate([ext_z_R[bR], ext_z_L[bL]])))

    L = R_MAX - D_bound

    # n_b per frame (number of bound R = number of bound L = number of bonds/frame)
    n_b_per_frame = float(bR.sum(axis=1).mean())

    # axis populations
    aR = _axis_unit_vector(pR, "R")
    aL = _axis_unit_vector(pL, "L")
    return SystemInputs(
        label=label,
        sys_name=sys_name,
        n_frames=n_frames,
        n_R=n_R,
        n_L=n_L,
        n_b_per_frame=n_b_per_frame,
        R_e_free=R_e_free,
        D_bound=D_bound,
        L=L,
        axes_R_unbound=aR[~bR],
        axes_L_unbound=aL[~bL],
        axes_R_bound=aR[bR],
        axes_L_bound=aL[bL],
    )


def load_all() -> dict[str, SystemInputs]:
    root = Path(__file__).resolve().parent.parent
    out = {}
    for sys_name, label in SYSTEMS:
        npz = root / "results" / "chain_coords" / sys_name / "chain_coords.npz"
        out[label] = load_system(npz, label, sys_name)
    return out


def main():
    inputs = load_all()
    print(f"{'label':6s}  {'n_frames':>8s}  {'n_R':>4s}  {'n_L':>4s}  "
          f"{'n_b/frm':>8s}  {'R_e':>6s}  {'D':>6s}  {'L':>6s}")
    for lab in ("rigid", "semi", "flex"):
        i = inputs[lab]
        print(f"{lab:6s}  {i.n_frames:8d}  {i.n_R:4d}  {i.n_L:4d}  "
              f"{i.n_b_per_frame:8.3f}  {i.R_e_free:6.3f}  "
              f"{i.D_bound:6.3f}  {i.L:6.3f}")
    print(f"\nR_max = {R_MAX} σ,  b = {B} σ,  A = {AREA} σ²")


if __name__ == "__main__":
    main()

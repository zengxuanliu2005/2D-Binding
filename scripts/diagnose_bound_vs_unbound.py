"""Diagnose whether unbound rigid (K100) chains are sampled differently
from bound rigid chains — i.e., is the 22% K2D gap a sampling-bias artifact?

For K100, only ~31% of R chains are unbound at any frame; if those are
geometrically biased relative to bound chains, the raw-tether partition will
underestimate K2D,max.

Compares for both bound and unbound R-chains:
- z-coordinate of binding bead relative to head anchor (R_end[:, 2])
- |R_end_xy| lateral excursion of binding bead
- angle of terminal direction (R_term) from +z axis
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from topology import build_topology
from io_xyz import iter_frames
from bonds import parse_num_bonds
from extract_complex import box_from_sysdir, min_image

SYSTEMS = {
    "rigid": "15_120x120_K100_EPS05",
    "semi": "15_120x120_K10_EPS05",
    "flex": "22_120x120_K01_EPS05",
}


def atom_slot_from_bond_atom(atom: int, n_lipid_atoms: int) -> tuple[str, int]:
    chain = (atom - n_lipid_atoms - 1) // 13
    if chain < 15 + 15 + 22 + 22:  # all chains; we don't actually need to discriminate by system
        pass
    return ("R" if chain % 2 == 0 else "L", chain // 2) if False else _slot_from_atom(atom, n_lipid_atoms)


def _slot_from_atom(atom: int, n_lipid_atoms: int) -> tuple[str, int]:
    # Replicate scripts/raw_tether_partition_k2d.py:atom_slot_from_bond_atom
    from raw_tether_partition_k2d import atom_slot_from_bond_atom as f
    return f(atom, n_lipid_atoms)


def extract_split(sys_dir: Path) -> dict[str, np.ndarray]:
    topo = build_topology(sys_dir / "mol.psf")
    box = box_from_sysdir(sys_dir)
    bond_pairs = parse_num_bonds(sys_dir / "num_bonds_for_xyz_frames.dat")
    n_lipid_atoms = topo.n_lipids * 3

    needed: list[int] = []
    R_atoms: list[tuple[int, int, int]] = []
    L_atoms: list[tuple[int, int, int]] = []
    for i in range(topo.n_receptors):
        atoms = (topo.receptor_chain[i][3], topo.receptor_chain[i][11], topo.receptor_chain[i][12])
        R_atoms.append(atoms)
        needed.extend(atoms)
    for i in range(topo.n_ligands):
        atoms = (topo.ligand_chain[i][3], topo.ligand_chain[i][11], topo.ligand_chain[i][12])
        L_atoms.append(atoms)
        needed.extend(atoms)
    idx = {atom: k for k, atom in enumerate(needed)}

    R_end_bound, R_end_unbound = [], []
    R_term_bound, R_term_unbound = [], []

    for frame_idx, coords in iter_frames(sys_dir / "traj.xyz", subset_indices=needed):
        bound_R: set[int] = set()
        if frame_idx < len(bond_pairs):
            for a1, a2 in bond_pairs[frame_idx]:
                for atom in (a1, a2):
                    kind, slot = _slot_from_atom(atom, n_lipid_atoms)
                    if kind == "R":
                        bound_R.add(slot)

        for slot, atoms in enumerate(R_atoms):
            head, terminal_partner, bind = atoms
            p_head = coords[idx[head]]
            p_partner = coords[idx[terminal_partner]]
            p_bind = coords[idx[bind]]
            vec_end = min_image(p_bind - p_head, box)
            vec_term = min_image(p_bind - p_partner, box)
            if slot in bound_R:
                R_end_bound.append(vec_end)
                R_term_bound.append(vec_term)
            else:
                R_end_unbound.append(vec_end)
                R_term_unbound.append(vec_term)

    return {
        "R_end_bound": np.asarray(R_end_bound, dtype=np.float64),
        "R_end_unbound": np.asarray(R_end_unbound, dtype=np.float64),
        "R_term_bound": np.asarray(R_term_bound, dtype=np.float64),
        "R_term_unbound": np.asarray(R_term_unbound, dtype=np.float64),
    }


def term_tilt_deg(R_term: np.ndarray) -> np.ndarray:
    """Angle of R_term from +z axis (or -z; reports min(theta, 180-theta))."""
    if R_term.size == 0:
        return np.array([])
    z = R_term[:, 2]
    n = np.linalg.norm(R_term, axis=1)
    n = np.where(n < 1e-12, 1.0, n)
    c = z / n
    c = np.clip(c, -1.0, 1.0)
    th = np.degrees(np.arccos(np.abs(c)))  # tilt from chain axis
    return th


def summarize(name: str, data: dict[str, np.ndarray]) -> None:
    print(f"\n=== {name} ===")
    for tag in ("bound", "unbound"):
        end = data[f"R_end_{tag}"]
        term = data[f"R_term_{tag}"]
        if end.size == 0:
            print(f"{tag:8s}: (empty)")
            continue
        rxy = np.linalg.norm(end[:, :2], axis=1)
        z = end[:, 2]
        rz = np.abs(z)  # |z| reach
        rmag = np.linalg.norm(end, axis=1)
        tilt = term_tilt_deg(term)
        print(f"{tag:8s} (n={len(end)}):")
        print(f"  |R_end|       mean={rmag.mean():.3f}  std={rmag.std():.3f}")
        print(f"  R_end_z       mean={z.mean():.3f}  std={z.std():.3f}  range=[{z.min():.2f}, {z.max():.2f}]")
        print(f"  |R_end_xy|    mean={rxy.mean():.3f}  std={rxy.std():.3f}")
        print(f"  term tilt deg mean={tilt.mean():.2f}  std={tilt.std():.2f}  (from chain axis +z)")


_BANNER = """
╔════════════════════════════════════════════════════════════════════╗
║  diagnose_bound_vs_unbound.py                                     ║
║  Bound vs unbound R-chain geometry per system                     ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Splits R chains by per-frame bound state and reports mean / std of
binding-bead z-reach and chain-axis tilt for each population. Used to
diagnose whether the equilibrium MD sampling has a geometric bias
between bound and unbound configurations.

Interpretation
  Δz > 0   : bound chains stand more upright than unbound (expected
              for narrow K2D(l) systems; large Δz hints at a sampling
              bias that the raw-tether partition will inherit)
  Δtilt > 0 : bound chains tilt less than unbound

A1 finding (s001 only): rigid Δz=−0.26 nm, Δtilt=+7°; flex Δz=−1.48 nm,
Δtilt=+14°. Re-run with the off-site full-data run should shrink these
toward statistical noise IF the "data volume" hypothesis is right.
"""


def main() -> None:
    print(_BANNER)
    root = Path(__file__).resolve().parent.parent
    for label, sysname in SYSTEMS.items():
        sys_dir = root / "outputs" / sysname / "s001"
        print(f"\n>>> Extracting {label} ({sysname}) ...", flush=True)
        data = extract_split(sys_dir)
        summarize(label, data)


if __name__ == "__main__":
    main()

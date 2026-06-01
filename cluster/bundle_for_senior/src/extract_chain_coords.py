"""Extract per-frame, per-protein chain coordinates for the entropy work.

For each frame of `traj.xyz`, save the 13 bead positions of every receptor
and ligand to a per-system NPZ:

    positions_R  : float64, shape (n_frames, n_R, 13, 3)
    positions_L  : float64, shape (n_frames, n_L, 13, 3)
    bound_R      : bool,    shape (n_frames, n_R)        — True iff R is in any bond
    bound_L      : bool,    shape (n_frames, n_L)        — True iff L is in any bond
    partner_R    : int32,   shape (n_frames, n_R)        — L slot R is bound to (-1 if unbound)
    partner_L    : int32,   shape (n_frames, n_L)        — R slot L is bound to (-1 if unbound)
    n_frames     : int                                   — number of frames
    n_R, n_L     : int                                   — number of receptors / ligands
    box          : float64, shape (3,)                   — Lx, Ly, Lz in σ

Coordinates are unwrapped per chain — for each chain we walk from bead 0
to bead 12, applying a min-image correction to each successive bond. This
fixes the ~3 % of chains in `traj.xyz` whose 13 beads happen to straddle
a periodic boundary (the simulator's `unpbc(True)` is per-DCD-output but
the local xyz can still wrap on chain centres; we detect a 119-σ "bond"
and shift the rest of the chain to restore continuity).

Each chain's 13 beads are in canonical order:
    0,1,2 = anchor tail (RT/LT — chain idx 0 is the outermost, membrane-embedded)
    3     = anchor head (RH/LH, the junction bead)
    4..11 = ecto chain (RE/LE × 8)
    12    = binding bead (RB/LB)

For receptors anchor is below (z < 0), binding bead in the gap (z ≈ 0).
For ligands anchor is above (z > 0), binding bead in the gap (z ≈ 0).
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from topology import build_topology  # noqa: E402
from io_xyz import iter_frames  # noqa: E402
from bonds import parse_num_bonds_full  # noqa: E402
from extract_complex import box_from_sysdir  # noqa: E402


def run(sys_dir: Path, out_dir: Path, max_frames: int | None = None,
        progress: bool = True) -> dict:
    topo = build_topology(sys_dir / "mol.psf")
    box = np.array(box_from_sysdir(sys_dir), dtype=np.float64)
    n_R, n_L = topo.n_receptors, topo.n_ligands

    # bond record: per frame, list of (R_slot, L_slot) pairs
    bond_rows = parse_num_bonds_full(sys_dir / "num_bonds_for_xyz_frames.dat")
    n_lipid_atoms = topo.n_lipids * 3
    def atom_kind_slot(atom: int) -> tuple[str, int]:
        component = (atom - n_lipid_atoms) // 13
        kind = "R" if component % 2 == 0 else "L"
        slot = component // 2 if kind == "R" else (component - 1) // 2
        return kind, slot
    bonds_per_frame: list[list[tuple[int, int]]] = []
    for frame in bond_rows:
        rl: list[tuple[int, int]] = []
        for b in frame:
            k1, s1 = atom_kind_slot(b.r_atom)
            k2, s2 = atom_kind_slot(b.l_atom)
            r_slot = s1 if k1 == "R" else s2
            l_slot = s2 if k2 == "L" else s1
            rl.append((r_slot, l_slot))
        bonds_per_frame.append(rl)

    # atom subset = every protein bead
    needed: list[int] = []
    for ch in topo.receptor_chain:
        needed.extend(ch)
    for ch in topo.ligand_chain:
        needed.extend(ch)
    idx_in_subset = {atom: k for k, atom in enumerate(needed)}

    # count frames first by reading the file once (cheap relative to extraction
    # because frame-count from byte size requires unsanctioned assumptions).
    # We allocate arrays as we go to avoid a separate pass.
    pos_R_chunks: list[np.ndarray] = []
    pos_L_chunks: list[np.ndarray] = []
    bound_R_chunks: list[np.ndarray] = []
    bound_L_chunks: list[np.ndarray] = []
    partner_R_chunks: list[np.ndarray] = []
    partner_L_chunks: list[np.ndarray] = []

    def unwrap_chain(chain_xyz: np.ndarray) -> None:
        """In-place: walk bead 0 → 12 and fix any PBC-wrapped successor bead
        by shifting all subsequent beads by the same lattice vector."""
        for j in range(1, chain_xyz.shape[0]):
            bond = chain_xyz[j] - chain_xyz[j - 1]
            shift = box * np.round(bond / box)
            if np.any(shift != 0):
                chain_xyz[j:] -= shift

    fidx_max = -1
    for fidx, coords in iter_frames(sys_dir / "traj.xyz",
                                     subset_indices=needed,
                                     max_frames=max_frames):
        fidx_max = fidx
        pos_R = np.empty((n_R, 13, 3), dtype=np.float64)
        pos_L = np.empty((n_L, 13, 3), dtype=np.float64)
        for i, ch in enumerate(topo.receptor_chain):
            for j, atom in enumerate(ch):
                pos_R[i, j] = coords[idx_in_subset[atom]]
            unwrap_chain(pos_R[i])
        for i, ch in enumerate(topo.ligand_chain):
            for j, atom in enumerate(ch):
                pos_L[i, j] = coords[idx_in_subset[atom]]
            unwrap_chain(pos_L[i])
        pos_R_chunks.append(pos_R)
        pos_L_chunks.append(pos_L)

        bonds = bonds_per_frame[fidx] if fidx < len(bonds_per_frame) else []
        bR = np.zeros(n_R, dtype=bool)
        bL = np.zeros(n_L, dtype=bool)
        pR = np.full(n_R, -1, dtype=np.int32)
        pL = np.full(n_L, -1, dtype=np.int32)
        for r_slot, l_slot in bonds:
            bR[r_slot] = True
            bL[l_slot] = True
            pR[r_slot] = l_slot
            pL[l_slot] = r_slot
        bound_R_chunks.append(bR)
        bound_L_chunks.append(bL)
        partner_R_chunks.append(pR)
        partner_L_chunks.append(pL)

        if progress and (fidx + 1) % 100 == 0:
            print(f"  frame {fidx + 1}", flush=True)

    n_frames = fidx_max + 1
    positions_R = np.stack(pos_R_chunks, axis=0)        # (n_frames, n_R, 13, 3)
    positions_L = np.stack(pos_L_chunks, axis=0)
    bound_R = np.stack(bound_R_chunks, axis=0)
    bound_L = np.stack(bound_L_chunks, axis=0)
    partner_R = np.stack(partner_R_chunks, axis=0)
    partner_L = np.stack(partner_L_chunks, axis=0)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "chain_coords.npz"
    np.savez_compressed(
        out_path,
        positions_R=positions_R,
        positions_L=positions_L,
        bound_R=bound_R,
        bound_L=bound_L,
        partner_R=partner_R,
        partner_L=partner_L,
        box=box,
        n_frames=n_frames,
        n_R=n_R,
        n_L=n_L,
    )
    sz_mb = out_path.stat().st_size / 1024 / 1024
    return {
        "n_frames": n_frames,
        "n_R": n_R,
        "n_L": n_L,
        "out_size_MB": sz_mb,
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("sys_dir")
    p.add_argument("--out", default=None)
    p.add_argument("--max-frames", type=int, default=None)
    args = p.parse_args(argv[1:])

    sys_dir = Path(args.sys_dir)
    out = Path(args.out) if args.out else Path("results/chain_coords") / sys_dir.parent.name
    summary = run(sys_dir, out, max_frames=args.max_frames)
    print("\nDone.")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

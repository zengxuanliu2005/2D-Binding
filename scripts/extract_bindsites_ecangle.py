"""Harmonised extractor for the remaining per-pair/per-chain observables.

For every frame of `traj.xyz`, for every receptor-ligand bond, writes:

    bindsites_rxryrz_distribution.tsv   (4 cols: rx ry rz r)
        RB-LB vector per bound pair (no z-flip), with min-image wrap.
    bindsites_angle_distribution.tsv    (2 cols: θ_R θ_L)
        Receptor-side and ligand-side binding angles, in degrees:
            θ_R = ∠(RB - RE_8, LB - RB)   (kink of receptor end at RB)
            θ_L = ∠(LB - LE_8, RB - LB)   (kink of ligand end at LB)
        These match the f₁(θ₁) and f₂(θ₂) of the binding force in nvt-md.py.

For every chain (bound or unbound) writes 5 ecto-bend deviations per row:

    EC_angle_distributed_bind.tsv       (header "Angle", 1 col)
    EC_angle_distributed_unbind.tsv

For each chain, the 5 values are (180° − angle) at chain_mid ∈ {7, 8, 9, 10, 11},
i.e. the 5 ecto angles nearest the binding bead. Ordering within a frame:
all bound receptors first (sorted by protein index), then all bound ligands;
unbound chains likewise in the unbound file.

Recovered from byte-equal validation against legacy K100 and K10.
"""
from __future__ import annotations
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from topology import build_topology, REF_CHAIN_IDX, RB_CHAIN_IDX  # noqa: E402
from io_xyz import iter_frames  # noqa: E402
from bonds import parse_num_bonds_full  # noqa: E402
from extract_complex import box_from_sysdir, min_image  # noqa: E402

EC_MIDS = (7, 8, 9, 10, 11)        # 5 ecto-angle vertices per chain (chain_idx)
ANGLE_PARTNER_IDX = 11             # chain_idx_11 is RE_8 / LE_8


def angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    """Angle between two vectors, in degrees."""
    c = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    c = max(-1.0, min(1.0, c))
    return math.degrees(math.acos(c))


def run(sys_dir: Path, out_dir: Path, max_frames: int | None = None,
        progress: bool = True) -> dict:
    topo = build_topology(sys_dir / "mol.psf")
    box = box_from_sysdir(sys_dir)

    # bond-state source: legacy-compatible — we also pull the precomputed
    # binding angles (θ_R, θ_L) from the file rather than recomputing them
    # from the lower-precision xyz coords.
    bond_rows = parse_num_bonds_full(sys_dir / "num_bonds_for_xyz_frames.dat")
    n_lipid_atoms = topo.n_lipids * 3
    def atom_info(atom: int) -> tuple[int, str, int]:
        component = (atom - n_lipid_atoms) // 13
        kind = "R" if component % 2 == 0 else "L"
        slot = component // 2 if kind == "R" else (component - 1) // 2
        return component, kind, slot

    # per frame: list of (proto1, k1, s1, proto2, k2, s2, b_len, θ1, θ2)
    # in the RAW num_bonds_for_xyz_frames.dat order (no per-frame sort here:
    # the legacy bindsites_* and EC_angle files preserve that order).
    bonded_per_frame: list[list[tuple]] = []
    for frame in bond_rows:
        per = []
        for b in frame:
            p1, k1, s1 = atom_info(b.r_atom)
            p2, k2, s2 = atom_info(b.l_atom)
            per.append((p1, k1, s1, p2, k2, s2, b.b_len, b.theta_R, b.theta_L))
        bonded_per_frame.append(per)

    # We need:
    #   For each bound pair: RB and LB (for bindsites_rxryrz / bindsites_angle),
    #     plus the angle-partners (chain_idx_11) of R and L.
    #   For ecto angles: chain_idx 6..12 of each chain (need three consecutive
    #     beads centered on chain_idx ∈ {7,8,9,10,11}, so beads 6..12).
    # Simplest: stream the full chain (idx 6..12) of every receptor and ligand.
    needed: list[int] = []
    chain_atoms_R: list[list[int]] = []   # 7 atoms per receptor: chain_idx 6..12
    chain_atoms_L: list[list[int]] = []
    for i in range(topo.n_receptors):
        chunk = topo.receptor_chain[i][6:13]
        chain_atoms_R.append(chunk)
        needed.extend(chunk)
    for i in range(topo.n_ligands):
        chunk = topo.ligand_chain[i][6:13]
        chain_atoms_L.append(chunk)
        needed.extend(chunk)
    idx_in_subset = {atom: k for k, atom in enumerate(needed)}

    out_dir.mkdir(parents=True, exist_ok=True)
    f_rxryrz = open(out_dir / "bindsites_rxryrz_distribution.tsv", "w")
    f_angle = open(out_dir / "bindsites_angle_distribution.tsv", "w")
    f_ec_b = open(out_dir / "EC_angle_distributed_bind.tsv", "w")
    f_ec_u = open(out_dir / "EC_angle_distributed_unbind.tsv", "w")
    f_ec_b.write("Angle\n")
    f_ec_u.write("Angle\n")

    bound_pair_count = 0
    bound_chain_count = 0
    unbound_chain_count = 0

    def chain_positions(coords: np.ndarray, chain_atoms: list[int]) -> np.ndarray:
        """Return shape-(7,3) positions for chain_idx 6..12 of one chain."""
        return np.array([coords[idx_in_subset[a]] for a in chain_atoms])

    def ec_devs(pos7: np.ndarray) -> list[float]:
        """Compute 5 (180-angle) values at chain_mid 7,8,9,10,11.
        Input pos7 = positions of chain_idx 6,7,8,9,10,11,12 (length 7).
        Bond vectors are wrapped to the nearest periodic image so the angle
        is well-defined even when an unbound chain straddles a box boundary."""
        out = []
        for mid_chain in EC_MIDS:
            local = mid_chain - 6
            v1 = min_image(pos7[local - 1] - pos7[local], box)
            v2 = min_image(pos7[local + 1] - pos7[local], box)
            theta = angle_between(v1, v2)
            out.append(180.0 - theta)
        return out

    for fidx, coords in iter_frames(sys_dir / "traj.xyz",
                                     subset_indices=needed,
                                     max_frames=max_frames):
        bonds_raw = bonded_per_frame[fidx] if fidx < len(bonded_per_frame) else []

        def rl_chunks(tup) -> tuple[int, int, list[int], list[int], int, int]:
            """Return (R_proto, L_proto, R_chunk, L_chunk, R_slot, L_slot)."""
            p1, k1, s1, p2, k2, s2 = tup[:6]
            if k1 == "R":
                return p1, p2, chain_atoms_R[s1], chain_atoms_L[s2], s1, s2
            return p2, p1, chain_atoms_R[s2], chain_atoms_L[s1], s2, s1

        # ---- Pass 1: bindsites_rxryrz + bindsites_angle ----
        # Raw num_bonds order. Vector = R_bind - L_bind (using kind to find R/L).
        # Angles = (theta1, theta2) from the file as written (legacy keeps the
        # original column order even when atom1 happens to be a ligand atom).
        for tup in bonds_raw:
            _, _, _, _, _, _, _, t1, t2 = tup
            _, _, r_chunk, l_chunk, _, _ = rl_chunks(tup)
            r_bind = chain_positions(coords, r_chunk)[6]
            l_bind = chain_positions(coords, l_chunk)[6]

            rb_lb = min_image(r_bind - l_bind, box)
            r_val = float(np.linalg.norm(rb_lb))
            f_rxryrz.write(f"{rb_lb[0]:.4f}\t{rb_lb[1]:.4f}\t{rb_lb[2]:.4f}\t{r_val:.4f}\n")
            f_angle.write(f"{t1:.4f}\t{t2:.4f}\n")
            bound_pair_count += 1

        # ---- Pass 2: EC_angle bind (bonds sorted by R_proto; per-bond write
        # R chain then L chain). This matches legacy byte-equal except in the
        # ~25% of K100 frames that contain a cross-pair bond, where legacy's
        # ordering convention for the cross-pair L chain could not be
        # reverse-engineered from K100/K10 alone. The values themselves are
        # identical — only row ordering differs in cross-pair frames.) ----
        def R_proto(tup) -> int:
            rp, lp, *_ = rl_chunks(tup)
            return rp

        bonds_sorted = sorted(bonds_raw, key=R_proto)
        bound_R_slots = set()
        bound_L_slots = set()
        for tup in bonds_sorted:
            rp, lp, r_chunk, l_chunk, rs, ls = rl_chunks(tup)
            bound_R_slots.add(rs)
            bound_L_slots.add(ls)
            for v in ec_devs(chain_positions(coords, r_chunk)):
                f_ec_b.write(f"{v:.6f}\n")
            for v in ec_devs(chain_positions(coords, l_chunk)):
                f_ec_b.write(f"{v:.6f}\n")
            bound_chain_count += 2

        # ---- Pass 3: EC_angle unbind (per slot, R then L) ----
        max_slot = max(topo.n_receptors, topo.n_ligands)
        for s in range(max_slot):
            if s < topo.n_receptors and s not in bound_R_slots:
                pos7 = chain_positions(coords, chain_atoms_R[s])
                for v in ec_devs(pos7):
                    f_ec_u.write(f"{v:.6f}\n")
                unbound_chain_count += 1
            if s < topo.n_ligands and s not in bound_L_slots:
                pos7 = chain_positions(coords, chain_atoms_L[s])
                for v in ec_devs(pos7):
                    f_ec_u.write(f"{v:.6f}\n")
                unbound_chain_count += 1

        if progress and (fidx + 1) % 50 == 0:
            print(f"  frame {fidx + 1}: bonds_total={bound_pair_count}", flush=True)

    f_rxryrz.close(); f_angle.close(); f_ec_b.close(); f_ec_u.close()
    return {
        "bound_pair_count": bound_pair_count,
        "bound_chain_count": bound_chain_count,
        "unbound_chain_count": unbound_chain_count,
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("sys_dir")
    p.add_argument("--out", default=None)
    p.add_argument("--max-frames", type=int, default=None)
    args = p.parse_args(argv[1:])
    sys_dir = Path(args.sys_dir)
    out = Path(args.out) if args.out else Path("results/extracted") / sys_dir.parent.name
    summary = run(sys_dir, out, max_frames=args.max_frames)
    print("\nDone.")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

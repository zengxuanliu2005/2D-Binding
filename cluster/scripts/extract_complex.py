"""Harmonised per-pair extractor for the three flexibility systems.

For every frame of `traj.xyz`, for every receptor-ligand pair, computes:

    * RB-LB distance (bond length when bound).
    * bound flag: True iff |RB-LB| < BOUND_THRESHOLD (2.0 σ).
    * Re = |pos(R_chain_idx_5) - pos(L_chain_idx_5)|  (matches legacy
      `result_Re_complex.dat`).
    * binding_vector for receptor: pos(R_chain_idx_5) - pos(RB).
    * binding_vector for ligand:   (pos(L_chain_idx_5) - pos(LB)) with z
      negated, to match the legacy `binding_vector_final_bound_vectors.tsv`
      sign convention (chain points "into the binding gap" with -z for both
      proteins, since R and L are anchored on opposing membranes).

Writes legacy-compatible files in `results/extracted/<sys>/`:

    result_Re_complex.dat                       (frame R_idx L_idx Re Re²)
    result_stats_complex.dat                    (frame <Re> <Re²>)
    binding_vector_final_bound_vectors.tsv      (frame proto_idx rx ry rz r)
    binding_vector_final_unbound_vectors.tsv    (same format, unbound pairs)
    bond_state.tsv                              (frame pair_idx bound 0/1, RB-LB dist)

Protein indexing follows the legacy convention: receptor i = even index 2i,
ligand i = odd index 2i+1.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from topology import build_topology, REF_CHAIN_IDX, RB_CHAIN_IDX  # noqa: E402
from io_xyz import iter_frames  # noqa: E402
from bonds import parse_num_bonds  # noqa: E402

# Bound classification uses the simulator's own record in
# `num_bonds_for_xyz_frames.dat`. Atom pairs are recorded using each side's
# chain_idx_11 bead (the binding-angle partner of RB/LB).
BOUND_THRESHOLD = 3.0   # σ — sanity-check threshold

# Periodic-box dimensions (from analysis/vertical_distance_to_membrane_complex.py:
# Lz = 50 σ; Lx = Ly come from the folder name `..._{Lx}x{Ly}_...`).
LZ_DEFAULT = 50.0


def box_from_sysdir(sys_dir: Path) -> tuple[float, float, float]:
    """Extract (Lx, Ly, Lz) from the system folder name."""
    name = sys_dir.parent.name        # e.g. '15_120x120_K100_EPS05'
    m = re.search(r"_(\d+)x(\d+)_", name)
    if not m:
        raise RuntimeError(f"could not parse Lx/Ly from {name}")
    Lx = float(m.group(1))
    Ly = float(m.group(2))
    return Lx, Ly, LZ_DEFAULT


def min_image(v: np.ndarray, box: tuple[float, float, float]) -> np.ndarray:
    Lx, Ly, Lz = box
    out = v.copy()
    out[0] -= Lx * round(out[0] / Lx)
    out[1] -= Ly * round(out[1] / Ly)
    out[2] -= Lz * round(out[2] / Lz)
    return out


def run(sys_dir: Path, out_dir: Path, max_frames: int | None = None,
        progress: bool = True) -> dict:
    topo = build_topology(sys_dir / "mol.psf")
    n_pairs = topo.n_pairs
    box = box_from_sysdir(sys_dir)

    # Bond-state source: simulator record. Each bond is logged using the
    # chain_idx_11 atom (RE_8 / LE_8 — the angle-partner of the binding bead).
    # Bonds can be CROSS-PAIR (any receptor component may bind any ligand
    # component). The atom pair as written in the bond file is preserved as
    # (atom1, atom2) — atom1 may be a ligand atom; the legacy output keeps
    # the original ordering as `R_idx L_idx` regardless of parity.
    # Per frame we store a list of (proto1, proto2, kind1, kind2, slot1, slot2)
    # where proto_i is the legacy protein index (atom component), kind_i is
    # 'R' or 'L', and slot_i is the position into receptor_chain/ligand_chain.
    bond_pairs = parse_num_bonds(sys_dir / "num_bonds_for_xyz_frames.dat")
    n_lipid_atoms = topo.n_lipids * 3
    def atom_info(atom: int) -> tuple[int, str, int]:
        component = (atom - n_lipid_atoms) // 13
        kind = "R" if component % 2 == 0 else "L"
        slot = component // 2 if kind == "R" else (component - 1) // 2
        return component, kind, slot

    bonded_per_frame: list[list[tuple[int, str, int, int, str, int]]] = []
    for pairs in bond_pairs:
        per_frame = []
        for a1, a2 in pairs:
            p1, k1, s1 = atom_info(a1)
            p2, k2, s2 = atom_info(a2)
            # legacy puts the lower component index first in (R_idx, L_idx)
            if p1 > p2:
                p1, k1, s1, p2, k2, s2 = p2, k2, s2, p1, k1, s1
            per_frame.append((p1, k1, s1, p2, k2, s2))
        per_frame.sort(key=lambda t: t[0])
        bonded_per_frame.append(per_frame)

    # Atoms to stream: chain_idx_5 + RB for every receptor and ligand.
    needed: list[int] = []
    for i in range(topo.n_receptors):
        needed.append(topo.receptor_chain[i][REF_CHAIN_IDX])
        needed.append(topo.receptor_chain[i][RB_CHAIN_IDX])
    for i in range(topo.n_ligands):
        needed.append(topo.ligand_chain[i][REF_CHAIN_IDX])
        needed.append(topo.ligand_chain[i][RB_CHAIN_IDX])
    idx_in_subset = {atom: k for k, atom in enumerate(needed)}

    out_dir.mkdir(parents=True, exist_ok=True)
    f_re = open(out_dir / "result_Re_complex.dat", "w")
    f_stats = open(out_dir / "result_stats_complex.dat", "w")
    f_bv_b = open(out_dir / "binding_vector_final_bound_vectors.tsv", "w")
    f_bv_u = open(out_dir / "binding_vector_final_unbound_vectors.tsv", "w")
    f_state = open(out_dir / "bond_state.tsv", "w")

    f_re.write("# frame  R_idx  L_idx   Re    Re2\n")
    f_stats.write("# frame   <Re>    <Re^2>\n")
    f_bv_b.write("# frame\tprotein_index\trx\try\trz\tr\n")
    f_bv_u.write("# frame\tprotein_index\trx\try\trz\tr\n")
    f_state.write("# frame\tR_proto\tL_proto\tRB_LB_dist\n")

    bound_count = 0
    unbound_count = 0
    sum_re = 0.0
    sum_re2 = 0.0

    for fidx, coords in iter_frames(sys_dir / "traj.xyz",
                                     subset_indices=needed,
                                     max_frames=max_frames):
        bonds = bonded_per_frame[fidx] if fidx < len(bonded_per_frame) else []
        bound_re_vals: list[float] = []

        def lookup_atoms(kind: str, slot: int) -> tuple[int, int]:
            """Return (ref_atom, binding_bead_atom) for receptor or ligand."""
            if kind == "R":
                return topo.rref(slot), topo.rb(slot)
            return topo.lref(slot), topo.lb(slot)

        def bv_for(kind: str, ref_pos, bind_pos):
            v = min_image(ref_pos - bind_pos, box)
            if kind == "L":
                # legacy z-flip for ligand-side binding vector
                return np.array([v[0], v[1], -v[2]])
            return v

        # bond_state: one row per bond (R_proto, L_proto written in file order)
        for proto1, k1, s1, proto2, k2, s2 in bonds:
            ra, rb_a = lookup_atoms(k1, s1)
            la, lb_a = lookup_atoms(k2, s2)
            d = float(np.linalg.norm(coords[idx_in_subset[rb_a]] - coords[idx_in_subset[lb_a]]))
            f_state.write(f"{fidx}\t{proto1}\t{proto2}\t{d:.6f}\n")
            if d > BOUND_THRESHOLD + 2.0:
                pass

        # Re_complex and binding_vector for each bond.
        # Legacy bv file groups by kind (all receptors first, then all ligands),
        # each section sorted by protein index — INDEPENDENT of which side of
        # the bond record the protein appears on.
        bound_proto: set[int] = set()
        bv_rows_R: list[tuple[int, str]] = []
        bv_rows_L: list[tuple[int, str]] = []
        for proto1, k1, s1, proto2, k2, s2 in bonds:
            a1_ref, a1_bind = lookup_atoms(k1, s1)
            a2_ref, a2_bind = lookup_atoms(k2, s2)
            p1_ref = coords[idx_in_subset[a1_ref]]
            p1_bnd = coords[idx_in_subset[a1_bind]]
            p2_ref = coords[idx_in_subset[a2_ref]]
            p2_bnd = coords[idx_in_subset[a2_bind]]

            Re = float(np.linalg.norm(min_image(p1_ref - p2_ref, box)))
            Re2 = Re * Re

            bv1 = bv_for(k1, p1_ref, p1_bnd)
            bv2 = bv_for(k2, p2_ref, p2_bnd)
            mag1 = float(np.linalg.norm(bv1))
            mag2 = float(np.linalg.norm(bv2))

            f_re.write(f"{fidx} {proto1} {proto2} {Re:.6f} {Re2:.6f}\n")
            row1 = f"{fidx}\t{proto1}\t{bv1[0]:.6f}\t{bv1[1]:.6f}\t{bv1[2]:.6f}\t{mag1:.6f}\n"
            row2 = f"{fidx}\t{proto2}\t{bv2[0]:.6f}\t{bv2[1]:.6f}\t{bv2[2]:.6f}\t{mag2:.6f}\n"
            (bv_rows_R if k1 == "R" else bv_rows_L).append((proto1, row1))
            (bv_rows_R if k2 == "R" else bv_rows_L).append((proto2, row2))

            bound_proto.add(proto1)
            bound_proto.add(proto2)
            bound_re_vals.append(Re)
            sum_re += Re
            sum_re2 += Re2
            bound_count += 1
        bv_rows_R.sort(key=lambda t: t[0])
        bv_rows_L.sort(key=lambda t: t[0])
        for _, row in bv_rows_R: f_bv_b.write(row)
        for _, row in bv_rows_L: f_bv_b.write(row)

        # Unbound binding_vectors: receptors first (in slot order), then ligands.
        ub_R_rows: list[str] = []
        ub_L_rows: list[str] = []
        for i in range(topo.n_receptors):
            proto = topo.protein_index("receptor", i)
            if proto in bound_proto:
                continue
            ref = coords[idx_in_subset[topo.rref(i)]]
            bnd = coords[idx_in_subset[topo.rb(i)]]
            bv = bv_for("R", ref, bnd)
            mag = float(np.linalg.norm(bv))
            ub_R_rows.append(f"{fidx}\t{proto}\t{bv[0]:.6f}\t{bv[1]:.6f}\t{bv[2]:.6f}\t{mag:.6f}\n")
            unbound_count += 1
        for i in range(topo.n_ligands):
            proto = topo.protein_index("ligand", i)
            if proto in bound_proto:
                continue
            ref = coords[idx_in_subset[topo.lref(i)]]
            bnd = coords[idx_in_subset[topo.lb(i)]]
            bv = bv_for("L", ref, bnd)
            mag = float(np.linalg.norm(bv))
            ub_L_rows.append(f"{fidx}\t{proto}\t{bv[0]:.6f}\t{bv[1]:.6f}\t{bv[2]:.6f}\t{mag:.6f}\n")
            unbound_count += 1
        for row in ub_R_rows: f_bv_u.write(row)
        for row in ub_L_rows: f_bv_u.write(row)

        if bound_re_vals:
            mean_re = float(np.mean(bound_re_vals))
            mean_re2 = float(np.mean([v * v for v in bound_re_vals]))
            f_stats.write(f"{fidx} {mean_re:.6f} {mean_re2:.6f}\n")
        # silence frames with no bound pairs (mirrors legacy: stats only when there's data)

        if progress and (fidx + 1) % 50 == 0:
            print(f"  frame {fidx + 1}: bound_total={bound_count}", flush=True)

    f_re.close(); f_stats.close(); f_bv_b.close(); f_bv_u.close(); f_state.close()

    return {
        "n_receptors": topo.n_receptors,
        "n_ligands": topo.n_ligands,
        "bound_entries": bound_count,
        "unbound_entries": unbound_count,
        "sum_re": sum_re,
        "sum_re2": sum_re2,
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("sys_dir", help="path to outputs/<system>/s001")
    p.add_argument("--out", default=None, help="output dir (default: results/extracted/<sys>)")
    p.add_argument("--max-frames", type=int, default=None)
    args = p.parse_args(argv[1:])

    sys_dir = Path(args.sys_dir)
    if args.out is None:
        out = Path("results/extracted") / sys_dir.parent.name
    else:
        out = Path(args.out)
    summary = run(sys_dir, out, max_frames=args.max_frames)
    print("\nDone.")
    print(f"  receptors / ligands: {summary['n_receptors']} / {summary['n_ligands']}")
    print(f"  bound entries:       {summary['bound_entries']}")
    print(f"  unbound entries:    {summary['unbound_entries']}")
    if summary["bound_entries"]:
        print(f"  Σ Re  (bound):      {summary['sum_re']:.4f}")
        print(f"  Σ Re² (bound):      {summary['sum_re2']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

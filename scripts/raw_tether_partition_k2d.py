"""Raw-trajectory tether partition estimate for K2D,max ratios.

This prototype follows the polymer-tether partition-function idea in
`results/potential_framework_review.md`, but reads directly from
`outputs/<system>/s001/traj.xyz` each run instead of using cached
`chain_coords.npz`.

For each system, it streams the raw trajectory, extracts unbound R/L chain
endpoint and terminal-segment vectors, then estimates the lateral phase-space
area over which a randomly paired R/L tether pair can satisfy the RB-LB
distance and binding-angle kernel at a trial membrane separation h.

The absolute microscopic binding constant cancels in cross-flexibility ratios,
so the reported DeltaDeltaF values use the maxima of the per-system area
integrals as K2D,max proxies.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from bonds import parse_num_bonds  # noqa: E402
from extract_complex import box_from_sysdir, min_image  # noqa: E402
from io_xyz import iter_frames  # noqa: E402
from topology import build_topology  # noqa: E402


SYSTEMS = [
    ("15_120x120_K100_EPS05", "rigid"),
    ("15_120x120_K10_EPS05", "semi"),
    ("22_120x120_K01_EPS05", "flex"),
]

TARGETS = {
    "flex-rigid": 3.56,
    "semi-rigid": 2.68,
    "semi-flex": -0.90,
}

KBT_IN_EPSILON = 1.1
RL_EPSILON = 15.0
RL_SIGMA = 0.95
RL_WF = 0.4
RL_RCUT = 2.9
RL_UC = 4.0 * RL_EPSILON * ((1.0 / 2.5) ** 12 - (1.0 / 2.5) ** 6)
ANGLE_K = 15.0
ANGLE0_DEG = 10.0
HARD_R = 1.5
HARD_THETA_DEG = 15.0


@dataclass
class RawFeatures:
    sys_name: str
    label: str
    n_frames: int
    n_R: int
    n_L: int
    R_end: np.ndarray
    R_term: np.ndarray
    L_end: np.ndarray
    L_term: np.ndarray
    # per-frame (list of arrays, one element per frame; empty list for frames with no unbound)
    R_end_per_frame: list = None  # type: ignore
    R_term_per_frame: list = None  # type: ignore
    L_end_per_frame: list = None  # type: ignore
    L_term_per_frame: list = None  # type: ignore


def angle_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    denom = np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1)
    denom = np.where(denom < 1e-12, 1.0, denom)
    c = np.sum(a * b, axis=-1) / denom
    return np.degrees(np.arccos(np.clip(c, -1.0, 1.0)))


def radial_u_kbt(r: np.ndarray) -> np.ndarray:
    """RL binding radial potential in kBT units, following ref/nvt-md.py."""
    r = np.asarray(r)
    r_min = (2.0 ** (1.0 / 6.0)) * RL_SIGMA + RL_WF
    shifted = np.maximum(r - RL_WF, 1e-6)
    lj = 4.0 * RL_EPSILON * ((RL_SIGMA / shifted) ** 12 - (RL_SIGMA / shifted) ** 6) - RL_UC
    well = -RL_EPSILON - RL_UC
    u_eps = np.where(r <= r_min, well, lj)
    u_eps = np.where(r < RL_RCUT, u_eps, 0.0)
    return u_eps / KBT_IN_EPSILON


def angle_factor(theta_deg: np.ndarray) -> np.ndarray:
    excess = np.maximum(theta_deg - ANGLE0_DEG, 0.0)
    return np.exp(-ANGLE_K * np.radians(excess) ** 2)


def atom_slot_from_bond_atom(atom: int, n_lipid_atoms: int) -> tuple[str, int]:
    component = (atom - n_lipid_atoms) // 13
    kind = "R" if component % 2 == 0 else "L"
    slot = component // 2 if kind == "R" else (component - 1) // 2
    return kind, slot


def extract_raw_unbound_features(sys_dir: Path, label: str) -> RawFeatures:
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

    R_end: list[np.ndarray] = []
    R_term: list[np.ndarray] = []
    L_end: list[np.ndarray] = []
    L_term: list[np.ndarray] = []
    R_end_per_frame: list[np.ndarray] = []
    R_term_per_frame: list[np.ndarray] = []
    L_end_per_frame: list[np.ndarray] = []
    L_term_per_frame: list[np.ndarray] = []
    n_frames = 0

    for frame_idx, coords in iter_frames(sys_dir / "traj.xyz", subset_indices=needed):
        bound_R: set[int] = set()
        bound_L: set[int] = set()
        if frame_idx < len(bond_pairs):
            for a1, a2 in bond_pairs[frame_idx]:
                for atom in (a1, a2):
                    kind, slot = atom_slot_from_bond_atom(atom, n_lipid_atoms)
                    if kind == "R":
                        bound_R.add(slot)
                    else:
                        bound_L.add(slot)

        fr_R_end: list[np.ndarray] = []
        fr_R_term: list[np.ndarray] = []
        fr_L_end: list[np.ndarray] = []
        fr_L_term: list[np.ndarray] = []

        for slot, atoms in enumerate(R_atoms):
            if slot in bound_R:
                continue
            head, terminal_partner, bind = atoms
            p_head = coords[idx[head]]
            p_partner = coords[idx[terminal_partner]]
            p_bind = coords[idx[bind]]
            vec_end = min_image(p_bind - p_head, box)
            vec_term = min_image(p_bind - p_partner, box)
            R_end.append(vec_end)
            R_term.append(vec_term)
            fr_R_end.append(vec_end)
            fr_R_term.append(vec_term)

        for slot, atoms in enumerate(L_atoms):
            if slot in bound_L:
                continue
            head, terminal_partner, bind = atoms
            p_head = coords[idx[head]]
            p_partner = coords[idx[terminal_partner]]
            p_bind = coords[idx[bind]]
            vec_end = min_image(p_bind - p_head, box)
            vec_term = min_image(p_bind - p_partner, box)
            L_end.append(vec_end)
            L_term.append(vec_term)
            fr_L_end.append(vec_end)
            fr_L_term.append(vec_term)

        R_end_per_frame.append(np.asarray(fr_R_end, dtype=np.float64))
        R_term_per_frame.append(np.asarray(fr_R_term, dtype=np.float64))
        L_end_per_frame.append(np.asarray(fr_L_end, dtype=np.float64))
        L_term_per_frame.append(np.asarray(fr_L_term, dtype=np.float64))
        n_frames = frame_idx + 1

    return RawFeatures(
        sys_name=sys_dir.parent.name,
        label=label,
        n_frames=n_frames,
        n_R=topo.n_receptors,
        n_L=topo.n_ligands,
        R_end=np.asarray(R_end, dtype=np.float64),
        R_term=np.asarray(R_term, dtype=np.float64),
        L_end=np.asarray(L_end, dtype=np.float64),
        L_term=np.asarray(L_term, dtype=np.float64),
        R_end_per_frame=R_end_per_frame,
        R_term_per_frame=R_term_per_frame,
        L_end_per_frame=L_end_per_frame,
        L_term_per_frame=L_term_per_frame,
    )


def estimate_area_curve(
    feat: RawFeatures,
    h_values: np.ndarray,
    sample_pairs: int,
    bond_samples: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    idx_R = rng.integers(0, feat.R_end.shape[0], size=sample_pairs)
    idx_L = rng.integers(0, feat.L_end.shape[0], size=sample_pairs)

    R_end = feat.R_end[idx_R]
    R_term = feat.R_term[idx_R]
    L_end = feat.L_end[idx_L]
    L_term = feat.L_term[idx_L]

    soft = np.zeros_like(h_values, dtype=np.float64)
    hard = np.zeros_like(h_values, dtype=np.float64)
    z_only = np.zeros_like(h_values, dtype=np.float64)
    valid_frac = np.zeros_like(h_values, dtype=np.float64)

    for ih, h in enumerate(h_values):
        # RB-LB z component after placing R anchor at z=0 and L anchor at z=h.
        dz = R_end[:, 2] - (h + L_end[:, 2])

        valid = np.abs(dz) < RL_RCUT
        valid_frac[ih] = float(np.mean(valid))
        if np.any(valid):
            dz_v = dz[valid]
            rxy_max = np.sqrt(np.maximum(RL_RCUT * RL_RCUT - dz_v * dz_v, 0.0))
            z_only[ih] = float(np.sum(math.pi * rxy_max * rxy_max) / sample_pairs)

            rho = np.sqrt(rng.random((dz_v.size, bond_samples))) * rxy_max[:, None]
            phi = rng.random((dz_v.size, bond_samples)) * (2.0 * math.pi)
            r_vec = np.empty((dz_v.size, bond_samples, 3), dtype=np.float64)
            r_vec[..., 0] = rho * np.cos(phi)
            r_vec[..., 1] = rho * np.sin(phi)
            r_vec[..., 2] = dz_v[:, None]
            r = np.linalg.norm(r_vec, axis=-1)

            theta_R = angle_deg(R_term[valid, None, :], -r_vec)
            theta_L = angle_deg(L_term[valid, None, :], r_vec)
            f_ang = angle_factor(theta_R) * angle_factor(theta_L)
            u_eff = radial_u_kbt(r) * f_ang
            w = np.expm1(-u_eff)
            integrals = math.pi * rxy_max * rxy_max * np.mean(w, axis=1)
            soft[ih] = float(np.sum(integrals) / sample_pairs)

        valid_hard = np.abs(dz) < HARD_R
        if np.any(valid_hard):
            dz_v = dz[valid_hard]
            rxy_max = np.sqrt(np.maximum(HARD_R * HARD_R - dz_v * dz_v, 0.0))
            rho = np.sqrt(rng.random((dz_v.size, bond_samples))) * rxy_max[:, None]
            phi = rng.random((dz_v.size, bond_samples)) * (2.0 * math.pi)
            r_vec = np.empty((dz_v.size, bond_samples, 3), dtype=np.float64)
            r_vec[..., 0] = rho * np.cos(phi)
            r_vec[..., 1] = rho * np.sin(phi)
            r_vec[..., 2] = dz_v[:, None]
            theta_R = angle_deg(R_term[valid_hard, None, :], -r_vec)
            theta_L = angle_deg(L_term[valid_hard, None, :], r_vec)
            gate = (theta_R <= HARD_THETA_DEG) & (theta_L <= HARD_THETA_DEG)
            integrals = math.pi * rxy_max * rxy_max * np.mean(gate, axis=1)
            hard[ih] = float(np.sum(integrals) / sample_pairs)

    return {
        "h": h_values,
        "soft_area": soft,
        "hard_area": hard,
        "z_only_area": z_only,
        "valid_frac": valid_frac,
    }


def _boot_one(args: tuple) -> tuple[float, float, float]:
    """Single bootstrap iteration — top-level for pickling."""
    R_parts, R_term_parts, L_parts, L_term_parts, R_label, L_label, \
        h_vals, sample_pairs, bond_samples, seed, ib = args

    rng_frame = np.random.default_rng(seed + ib)
    n_frames = len(R_parts)
    idx = rng_frame.integers(0, n_frames, size=n_frames)

    def _pool(parts):
        selected = [parts[i] for i in idx if len(parts[i]) > 0]
        return np.concatenate(selected) if selected else np.empty((0, 3))

    boot_feat = RawFeatures(
        sys_name="", label="bootstrap",
        n_frames=n_frames, n_R=R_label, n_L=L_label,
        R_end=_pool(R_parts), R_term=_pool(R_term_parts),
        L_end=_pool(L_parts), L_term=_pool(L_term_parts),
    )
    boot_rng = np.random.default_rng(seed + ib + 1000000)
    curve = estimate_area_curve(boot_feat, h_vals, sample_pairs, bond_samples, boot_rng)
    return (
        float(curve["soft_area"][int(np.argmax(curve["soft_area"]))]),
        float(curve["hard_area"][int(np.argmax(curve["hard_area"]))]),
        float(curve["z_only_area"][int(np.argmax(curve["z_only_area"]))]),
    )


def bootstrap_area_curves(
    feat: RawFeatures,
    h_values: np.ndarray,
    sample_pairs: int,
    bond_samples: int,
    n_bootstrap: int,
    seed: int,
    n_jobs: int = 1,
) -> dict[str, np.ndarray]:
    """Frame-level bootstrap with optional multiprocessing.

    Args:
        n_jobs: Number of parallel workers (1 = sequential).
    """
    # Pre-extract per-frame arrays as lists for pickling.
    R_parts = feat.R_end_per_frame
    R_term_parts = feat.R_term_per_frame
    L_parts = feat.L_end_per_frame
    L_term_parts = feat.L_term_per_frame

    tasks = [
        (R_parts, R_term_parts, L_parts, L_term_parts,
         feat.n_R, feat.n_L, h_values, sample_pairs, bond_samples,
         seed, ib)
        for ib in range(n_bootstrap)
    ]

    max_soft = np.empty(n_bootstrap)
    max_hard = np.empty(n_bootstrap)
    max_zonly = np.empty(n_bootstrap)

    if n_jobs <= 1:
        for ib in range(n_bootstrap):
            if ib % 5 == 0:
                print(f"    bootstrap {ib}/{n_bootstrap}...", flush=True)
            s, h, z = _boot_one(tasks[ib])
            max_soft[ib] = s
            max_hard[ib] = h
            max_zonly[ib] = z
    else:
        import multiprocessing as mp
        mp.set_start_method("fork", force=True)
        with ProcessPoolExecutor(max_workers=n_jobs) as ex:
            for ib, (s, h, z) in enumerate(ex.map(_boot_one, tasks)):
                if ib % 5 == 0:
                    print(f"    bootstrap {ib}/{n_bootstrap}...", flush=True)
                max_soft[ib] = s
                max_hard[ib] = h
                max_zonly[ib] = z

    print(f"    bootstrap {n_bootstrap}/{n_bootstrap} done.", flush=True)
    return {"soft_area": max_soft, "hard_area": max_hard, "z_only_area": max_zonly}


def pair_rows(maxima: dict[str, dict], key: str, only_present: bool = False) -> list[dict]:
    specs = [
        ("flex-rigid", "flex", "rigid"),
        ("semi-rigid", "semi", "rigid"),
        ("semi-flex", "semi", "flex"),
    ]
    rows = []
    for name, a, b in specs:
        if only_present and (a not in maxima or b not in maxima):
            continue
        ka = maxima[a][key]
        kb = maxima[b][key]
        ddF = -math.log(ka / kb)
        target = TARGETS[name]
        rows.append({
            "pair": name,
            "ddF": ddF,
            "target": target,
            "gap": ddF - target,
            "closed": 100.0 * ddF / target if target else float("nan"),
        })
    return rows


def write_report(
    out_md: Path,
    features: dict[str, RawFeatures],
    curves: dict[str, dict[str, np.ndarray]],
    maxima: dict[str, dict],
    sample_pairs: int,
    bond_samples: int,
    bootstrap_max: dict[str, dict[str, np.ndarray]] | None = None,
) -> None:
    with open(out_md, "w") as fp:
        fp.write("# Raw tether partition K2D prototype\n\n")
        fp.write("This prototype reads `outputs/<system>/s001/traj.xyz` directly, "
                 "streams bead 3/11/12 for every protein, excludes chains bound "
                 "in the same raw frame using `num_bonds_for_xyz_frames.dat`, and "
                 "estimates the lateral phase-space area for RB-LB capture plus "
                 "binding-angle compatibility at trial membrane separations `h`.\n\n")
        fp.write("The absolute microscopic binding constant cancels in the cross-system ratios. "
                 "All reported free energies are `-ln(K_a/K_b)` in kBT using the maximum "
                 "area over `h` as the `K2D,max` proxy.\n\n")
        fp.write(f"Sampling: `{sample_pairs}` random R/L unbound pairs per system, "
                 f"`{bond_samples}` bond-vector samples per pair and h.\n\n")

        fp.write("## Raw feature inventory\n\n")
        fp.write("| label | system | frames | unbound R samples | unbound L samples |\n")
        fp.write("|---|---|---:|---:|---:|\n")
        for label in [l for l in ("rigid", "semi", "flex") if l in features]:
            f = features[label]
            fp.write(f"| {label} | `{f.sys_name}` | {f.n_frames} | "
                     f"{len(f.R_end)} | {len(f.L_end)} |\n")

        fp.write("\n## Maxima over membrane separation\n\n")
        if bootstrap_max is not None:
            fp.write("| label | h*_soft (sigma) | max soft area | h*_hard (sigma) | "
                     "max hard area | h*_zonly (sigma) | max z-only area |\n")
            fp.write("|---|---:|---:|---:|---:|---:|---:|\n")
            for label in [l for l in ("rigid", "semi", "flex") if l in features]:
                m = maxima[label]
                fp.write(f"| {label} | {m['soft_h']:.2f} | {m['soft_area']:.6g} | "
                         f"{m['hard_h']:.2f} | {m['hard_area']:.6g} | "
                         f"{m['z_only_h']:.2f} | {m['z_only_area']:.6g} |\n")

            fp.write("\n## Bootstrap statistics (point estimate ± σ over frames)\n\n")
            fp.write("| label | soft area (point ± σ) | hard area (point ± σ) | z-only area (point ± σ) |\n")
            fp.write("|---|---|---|---|\n")
            for label in [l for l in ("rigid", "semi", "flex") if l in features]:
                s_mean = np.mean(bootstrap_max[label]["soft_area"])
                s_std = np.std(bootstrap_max[label]["soft_area"])
                h_mean = np.mean(bootstrap_max[label]["hard_area"])
                h_std = np.std(bootstrap_max[label]["hard_area"])
                z_mean = np.mean(bootstrap_max[label]["z_only_area"])
                z_std = np.std(bootstrap_max[label]["z_only_area"])
                fp.write(f"| {label} | {s_mean:.6g} ± {s_std:.6g} | "
                         f"{h_mean:.6g} ± {h_std:.6g} | "
                         f"{z_mean:.6g} ± {z_std:.6g} |\n")
        else:
            fp.write("| label | h*_soft (sigma) | max soft area | h*_hard (sigma) | "
                     "max hard area | h*_zonly (sigma) | max z-only area |\n")
            fp.write("|---|---:|---:|---:|---:|---:|---:|\n")
            for label in [l for l in ("rigid", "semi", "flex") if l in features]:
                m = maxima[label]
                fp.write(f"| {label} | {m['soft_h']:.2f} | {m['soft_area']:.6g} | "
                         f"{m['hard_h']:.2f} | {m['hard_area']:.6g} | "
                         f"{m['z_only_h']:.2f} | {m['z_only_area']:.6g} |\n")

        for key, title in [("soft_area", "Soft Boltzmann kernel"),
                           ("hard_area", "Hard gate sanity check"),
                           ("z_only_area", "Z-reach geometry only")]:
            fp.write(f"\n## Cross-system closure: {title}\n\n")
            if bootstrap_max is not None and key != "z_only_area":
                fp.write("| pair | predicted (point ± σ) | target | gap | closed |\n")
                fp.write("|---|---:|---:|---:|---:|\n")
                pair_specs = [
                    ("flex-rigid", "flex", "rigid"),
                    ("semi-rigid", "semi", "rigid"),
                    ("semi-flex", "semi", "flex"),
                ]
                for name, a, b in [(n, x, y) for (n, x, y) in pair_specs
                                    if x in bootstrap_max and y in bootstrap_max]:
                    boot_a = bootstrap_max[a][key]
                    boot_b = bootstrap_max[b][key]
                    ratios = boot_a / boot_b
                    ddF_samples = -np.log(ratios)
                    ddF_mean = float(np.mean(ddF_samples))
                    ddF_std = float(np.std(ddF_samples))
                    target = TARGETS[name]
                    gap = ddF_mean - target
                    closed = 100.0 * ddF_mean / target if target else float("nan")
                    fp.write(f"| {name} | {ddF_mean:+.3f} ± {ddF_std:.3f} | "
                             f"{target:+.2f} | {gap:+.3f} | {closed:+.0f}% |\n")
            else:
                fp.write("| pair | predicted | target | gap | closed |\n")
                fp.write("|---|---:|---:|---:|---:|\n")
                for row in pair_rows(maxima, key, only_present=True):
                    fp.write(f"| {row['pair']} | {row['ddF']:+.3f} | "
                             f"{row['target']:+.2f} | {row['gap']:+.3f} | "
                             f"{row['closed']:+.0f}% |\n")

        fp.write("\n## Interpretation\n\n")
        fp.write("- `soft_area` integrates `exp(-U_bind/kBT)-1` over the lateral RB-LB "
                 "bond vector disk up to the raw force cutoff `rcut = 2.9 sigma`, with "
                 "the angular factors from `ref/nvt-md.py`.\n")
        fp.write("- `hard_area` uses a bound-like gate, `r <= 1.5 sigma` and both "
                 "binding angles `<= 15 deg`, based on the observed bound distributions.\n")
        fp.write("- `z_only_area` ignores angles and radial Boltzmann weighting. It is "
                 "included only to show how much of the trend comes from vertical reach.\n")
        fp.write("- This is an s001-only raw-data prototype. It is intended to test the "
                 "polymer-tether partition-function route, not yet as a final estimator.\n")
        if bootstrap_max is not None:
            n_boot = len(next(iter(bootstrap_max.values()))["soft_area"])
            fp.write(f"- Bootstrap: `n={n_boot}` frame-level resamples (with replacement). "
                     "ddF σ propagated from bootstrap ratios via `std(-ln(ratio))`.\n")

        fp.write("\n## How to reproduce\n\n")
        fp.write("```bash\n")
        fp.write("conda activate phys\n")
        fp.write("python scripts/raw_tether_partition_k2d.py")
        if bootstrap_max is not None:
            n_boot = len(next(iter(bootstrap_max.values()))["soft_area"])
            fp.write(f" --bootstrap --n-bootstrap {n_boot}")
        fp.write("\n```\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-pairs", type=int, default=200_000)
    parser.add_argument("--bond-samples", type=int, default=24)
    parser.add_argument("--h-min", type=float, default=6.0)
    parser.add_argument("--h-max", type=float, default=24.0)
    parser.add_argument("--h-step", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--n-bootstrap", type=int, default=200)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--out-prefix", default="results/raw_tether_partition")
    parser.add_argument(
        "--systems",
        default="all",
        help="Comma-separated subset of labels to run (default: all). E.g. 'rigid' or 'rigid,semi'.",
    )
    args = parser.parse_args(argv[1:])

    root = Path(__file__).resolve().parent.parent
    rng = np.random.default_rng(args.seed)
    h_values = np.arange(args.h_min, args.h_max + 0.5 * args.h_step, args.h_step)

    if args.systems.strip().lower() == "all":
        active_systems = list(SYSTEMS)
    else:
        wanted = {s.strip() for s in args.systems.split(",")}
        active_systems = [(s, l) for (s, l) in SYSTEMS if l in wanted]
        if not active_systems:
            raise SystemExit(f"--systems={args.systems} matched none of {[l for _, l in SYSTEMS]}")
    active_labels = [l for _, l in active_systems]

    features: dict[str, RawFeatures] = {}
    curves: dict[str, dict[str, np.ndarray]] = {}
    maxima: dict[str, dict] = {}
    bootstrap_max: dict[str, dict[str, np.ndarray]] | None = {}

    for sys_name, label in active_systems:
        sys_dir = root / "outputs" / sys_name / "s001"
        print(f"[{label}] extracting raw unbound features from {sys_dir.relative_to(root)}", flush=True)
        feat = extract_raw_unbound_features(sys_dir, label)
        features[label] = feat
        print(f"  unbound samples: R={len(feat.R_end)} L={len(feat.L_end)} "
              f"(per-frame avg: R={len(feat.R_end)/feat.n_frames:.1f} L={len(feat.L_end)/feat.n_frames:.1f})", flush=True)
        print(f"  estimating area curve over {len(h_values)} h values", flush=True)
        curve = estimate_area_curve(feat, h_values, args.sample_pairs, args.bond_samples, rng)
        curves[label] = curve
        maxima[label] = {}
        for key in ("soft_area", "hard_area", "z_only_area"):
            i = int(np.argmax(curve[key]))
            maxima[label][key] = float(curve[key][i])
            maxima[label][key.replace("_area", "_h")] = float(curve["h"][i])
        print(
            f"  soft max={maxima[label]['soft_area']:.6g} at h={maxima[label]['soft_h']:.2f}; "
            f"hard max={maxima[label]['hard_area']:.6g} at h={maxima[label]['hard_h']:.2f}",
            flush=True,
        )

        if args.bootstrap:
            print(f"  bootstrap: {args.n_bootstrap} frame-level resamples", flush=True)
            boot = bootstrap_area_curves(
                feat, h_values, args.sample_pairs, args.bond_samples,
                args.n_bootstrap, args.seed, n_jobs=args.n_jobs,
            )
            bootstrap_max[label] = boot
            s = boot["soft_area"]
            print(f"  soft boot: mean={float(np.mean(s)):.6g} sigma={float(np.std(s)):.6g}", flush=True)
            hb = boot["hard_area"]
            print(f"  hard boot: mean={float(np.mean(hb)):.6g} sigma={float(np.std(hb)):.6g}", flush=True)

    if not args.bootstrap:
        bootstrap_max = None

    out_prefix = root / args.out_prefix
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    out_npz = out_prefix.with_suffix(".npz")
    payload = {"h": h_values}
    for label in active_labels:
        for key, arr in curves[label].items():
            payload[f"{label}__{key}"] = arr
        for key, value in maxima[label].items():
            payload[f"{label}__max__{key}"] = value
        payload[f"{label}__n_R_unbound"] = len(features[label].R_end)
        payload[f"{label}__n_L_unbound"] = len(features[label].L_end)
        payload[f"{label}__n_frames"] = features[label].n_frames
        if bootstrap_max is not None:
            for key, arr in bootstrap_max[label].items():
                payload[f"{label}__boot__{key}"] = arr
    np.savez(out_npz, **payload)

    out_md = out_prefix.with_suffix(".md")
    write_report(out_md, features, curves, maxima, args.sample_pairs, args.bond_samples, bootstrap_max)

    print("\n=== Soft-kernel closure ===")
    for row in pair_rows(maxima, "soft_area", only_present=True):
        print(f"{row['pair']:11s} pred={row['ddF']:+.3f} target={row['target']:+.2f} gap={row['gap']:+.3f}")
    if not any(a in maxima and b in maxima for _, a, b in [
        ("flex-rigid", "flex", "rigid"),
        ("semi-rigid", "semi", "rigid"),
        ("semi-flex", "semi", "flex"),
    ]):
        print("(single-system run: no cross-system pair available)")
    if bootstrap_max is not None:
        pair_specs = [
            ("flex-rigid", "flex", "rigid"),
            ("semi-rigid", "semi", "rigid"),
            ("semi-flex", "semi", "flex"),
        ]
        available = [(n, a, b) for (n, a, b) in pair_specs
                     if a in bootstrap_max and b in bootstrap_max]
        if available:
            print("\n=== Bootstrap closure (mean ± σ) ===")
            for name, a, b in available:
                ratios = bootstrap_max[a]["soft_area"] / bootstrap_max[b]["soft_area"]
                ddF_samples = -np.log(ratios)
                print(f"{name:11s} pred={float(np.mean(ddF_samples)):+.3f} ± {float(np.std(ddF_samples)):.3f} "
                      f"target={TARGETS[name]:+.2f}")
        print("\n=== Per-system soft area (bootstrap mean ± σ) ===")
        for label, boot in bootstrap_max.items():
            s = boot["soft_area"]
            print(f"{label:11s} soft_area={float(np.mean(s)):.6g} ± {float(np.std(s)):.6g} "
                  f"(point={maxima[label]['soft_area']:.6g})")
    print(f"\nSaved {out_npz.relative_to(root)} and {out_md.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

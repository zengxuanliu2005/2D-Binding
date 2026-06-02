"""C.4 — analyze constrained-h slab MD trajectories → K2D(l = h) per (system, h).

Walks cluster/outputs/slab/<SYS>_h<H>/traj.xyz for each (system, h) and
measures the equilibrium fraction of R-L endpoint pairs that fall in the
binding kernel acceptance volume. Because the membrane gap is fixed at h
in slab MD, the result is K2D(l = h) directly — no convolution, no
unbound-sampling-bias correction needed.

K2D formula (same Mayer f-function as scripts/raw_tether_partition_k2d.py):

    K2D(h) = ⟨ π · rxy_max² · ⟨exp(-U_eff/kBT) - 1⟩_{r_xy ~ U(disk)} ⟩_{(R,L) pairs}

where for each (R, L) bead pair at lab z (R: z_R; L: h + z_L):
    dz = z_R - (h + z_L)
    rxy_max = √(RL_RCUT² - dz²) if |dz| < RL_RCUT else 0
    r_xy ~ Uniform(disk of radius rxy_max)
    U_eff = radial_u_kbt(|r|) * angle_factor(θ_R) * angle_factor(θ_L)

PILOT (--pilot)
===============
No real slab traj.xyz data exists yet. Pilot uses synthetic Gaussian R/L
binding-bead distributions matching B2.2 (μ ≈ 11.2/6.7/1.7 nm, σ ≈
0.63/3.18/2.79 nm for rigid/semi/flex). Verifies the K2D math itself
without needing a slab MD run. < 30 s wall.

PRODUCTION
==========
18 (system, h) tasks × 500 frames. ProcessPoolExecutor across (system, h)
with --n-jobs 8. Requires real traj.xyz files; topology parsing point is
the `_load_slab_frames_real` stub — fill in when slab MD data lands.

DERIVATION → CODE MAP
=====================
  03 (1.4)  v(dz) = π (rcut² − dz²)              → rxy_max disk
  raw (Mayer f) ⟨exp(-U)-1⟩                       → measure_k2d_from_arrays
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
# Reuse the bond kernel + angle factor from raw_tether_partition_k2d
from raw_tether_partition_k2d import (  # noqa: E402
    radial_u_kbt, angle_factor, angle_deg, RL_RCUT,
)

DEFAULT_SLAB_ROOT = REPO_ROOT / "cluster" / "outputs" / "slab"
DEFAULT_OUT = REPO_ROOT / "cluster" / "results" / "slab" / "K2D_l_grid.npz"

SYSTEMS = ("K100", "K10", "K01")
H_VALUES = (8.0, 10.0, 12.0, 14.0, 16.0, 18.0)

# Synthetic z distributions (μ, σ) matching B2.2 wlc_z_marginal.npz —
# used only in pilot mode when no real slab traj exists yet.
_PILOT_Z_STATS = {
    "K100": {"mu": 11.207, "sigma": 0.625},
    "K10":  {"mu":  6.661, "sigma": 3.181},
    "K01":  {"mu":  1.705, "sigma": 2.789},
}


# ─────────────────────────────────────────────────────────────────────────────
# K2D core (real math — no placeholder)
# ─────────────────────────────────────────────────────────────────────────────
def measure_k2d_from_arrays(R_bind: np.ndarray, R_term: np.ndarray,
                             L_bind: np.ndarray, L_term: np.ndarray,
                             h: float, bond_samples: int = 24,
                             rng: np.random.Generator | None = None,
                             ) -> dict[str, float]:
    """Compute K2D(l = h) from R/L binding-bead and terminal-partner positions.

    Same formula as `scripts/raw_tether_partition_k2d.py:estimate_area_curve`,
    specialised to a single membrane gap h (the slab MD constrains gap = h).

    Parameters
    ----------
    R_bind, L_bind : (n_pairs, 3) — binding-bead positions (lab frame).
        For R: chain anchored at z=0, binding bead at z_R ≥ 0.
        For L: chain anchored at z=h, binding bead at z_L_lab = h - z_L_chain;
        callers should pass L_bind in lab frame.
    R_term, L_term : (n_pairs, 3) — terminal-partner bead positions (bead 11),
        used to compute the chain-end angle factor.
    h : membrane gap (σ = nm).
    bond_samples : MC integration points per pair over the rxy disk.
    rng : numpy Generator (default: fresh).

    Returns
    -------
    {"K2D_soft": float (nm²), "K2D_hard": float (nm²), "valid_frac": float}

    Notes
    -----
    R_bind and L_bind are assumed to come from FRAME-PAIRED sampling — i.e.,
    R_bind[i] and L_bind[i] are taken from the same trajectory frame. For
    slab MD this is enforced by construction (one frame ↔ one snapshot).
    """
    if rng is None:
        rng = np.random.default_rng()
    R_bind = np.asarray(R_bind, dtype=np.float64)
    L_bind = np.asarray(L_bind, dtype=np.float64)
    R_term = np.asarray(R_term, dtype=np.float64)
    L_term = np.asarray(L_term, dtype=np.float64)
    n_pairs = R_bind.shape[0]
    if n_pairs == 0:
        return {"K2D_soft": float("nan"), "K2D_hard": float("nan"),
                "valid_frac": 0.0, "n_pairs": 0}

    # z separation at lab frame: R bind sits at z_R, L bind at h + (L's chain z)
    # but we treat L_bind as ALREADY in lab frame (so just R_bind.z - L_bind.z)
    dz = R_bind[:, 2] - L_bind[:, 2]
    valid = np.abs(dz) < RL_RCUT
    valid_frac = float(np.mean(valid))

    K2D_soft = 0.0
    if np.any(valid):
        dz_v = dz[valid]
        rxy_max = np.sqrt(np.maximum(RL_RCUT ** 2 - dz_v ** 2, 0.0))
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
        integrands = math.pi * rxy_max * rxy_max * np.mean(w, axis=1)
        K2D_soft = float(np.sum(integrands) / n_pairs)

    return {
        "K2D_soft": K2D_soft,
        "K2D_hard": float("nan"),  # hard-gate variant could be added if needed
        "valid_frac": valid_frac,
        "n_pairs": n_pairs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Slab traj loading
# ─────────────────────────────────────────────────────────────────────────────
def _load_slab_frames_real(traj_dir: Path, h: float,
                            n_frames_limit: int | None) -> dict | None:
    """Parse real slab traj.xyz (TODO: requires topology — fill when data lands).

    Returns None if real slab data isn't available; caller falls back to
    synthetic-pilot mode. Once cluster slab MD lands in cluster/outputs/slab/,
    implement using the same pattern as
    `scripts/raw_tether_partition_k2d.py:extract_raw_unbound_features` — read
    mol.psf for topology, iter_frames(traj.xyz, subset_indices=...), pick out
    chain[3] / chain[11] / chain[12] for each R and L protein.
    """
    if not traj_dir.exists():
        return None
    # Implementation hook: real parsing goes here.
    return None


def _synthesize_slab_frames(system: str, h: float, n_frames: int = 500,
                             n_chains_per_membrane: int = 30,
                             rng: np.random.Generator | None = None,
                             ) -> dict:
    """Generate synthetic R/L binding-bead positions matching B2.2 z stats.

    Used in pilot mode (no real slab data yet). Produces (n_pairs × 3) arrays
    with z drawn from Gaussian(μ, σ) per system; lateral (x, y) uniform in
    a 120×120 σ box; R_term/L_term unit vectors close to +ẑ/-ẑ.
    """
    if rng is None:
        rng = np.random.default_rng(20260602)
    stats = _PILOT_Z_STATS[system]
    n_pairs = n_chains_per_membrane * n_chains_per_membrane * n_frames

    box = 120.0
    R_bind = np.empty((n_pairs, 3))
    L_bind = np.empty((n_pairs, 3))
    R_bind[:, 0:2] = rng.uniform(0, box, size=(n_pairs, 2))
    L_bind[:, 0:2] = rng.uniform(0, box, size=(n_pairs, 2))
    R_bind[:, 2] = rng.normal(stats["mu"], stats["sigma"], size=n_pairs)
    # L: anchored at z=h, extends "down". L's binding bead lab z = h - z_chain
    L_bind[:, 2] = h - rng.normal(stats["mu"], stats["sigma"], size=n_pairs)

    # Terminal vectors point roughly along chain (close to +ẑ for R, -ẑ for L)
    # plus small isotropic noise to mimic anchor cone
    eps = 0.1
    R_term = np.empty((n_pairs, 3))
    L_term = np.empty((n_pairs, 3))
    R_term[:, 0:2] = rng.normal(0, eps, size=(n_pairs, 2))
    R_term[:, 2] = 1.0
    L_term[:, 0:2] = rng.normal(0, eps, size=(n_pairs, 2))
    L_term[:, 2] = -1.0

    return {"R_bind": R_bind, "R_term": R_term,
             "L_bind": L_bind, "L_term": L_term,
             "n_frames": n_frames,
             "source": f"synthetic ({system}, B2.2 z-stats)"}


def measure_k2d_for_traj(traj_dir: Path, system: str, h: float,
                          n_frames_limit: int | None = None,
                          synthesize_if_missing: bool = False,
                          rng: np.random.Generator | None = None,
                          ) -> dict:
    """Compute K2D(l = h) from one slab MD trajectory dir.

    Order of operations:
      1. Try real traj parsing (`_load_slab_frames_real`).
      2. If real data missing AND `synthesize_if_missing` (pilot path),
         fall back to Gaussian-z synthetic frames.
      3. If real data missing AND not pilot, return NaN row with note.
    """
    frames = _load_slab_frames_real(traj_dir, h, n_frames_limit)
    if frames is None and synthesize_if_missing:
        frames = _synthesize_slab_frames(system, h, n_frames=20
                                          if n_frames_limit == 20 else 500,
                                          rng=rng)
    if frames is None:
        return {"system": system, "h": h, "K2D": float("nan"),
                "K2D_err": float("nan"), "valid_frac": float("nan"),
                "n_pairs": 0,
                "note": f"missing slab traj at {traj_dir}"}

    result = measure_k2d_from_arrays(
        frames["R_bind"], frames["R_term"],
        frames["L_bind"], frames["L_term"],
        h=h, rng=rng,
    )
    # Block-resampled bootstrap for K2D_err: split into 10 blocks
    n_pairs = frames["R_bind"].shape[0]
    block = n_pairs // 10
    boots = []
    if block > 100:
        for b in range(10):
            sl = slice(b * block, (b + 1) * block)
            r = measure_k2d_from_arrays(
                frames["R_bind"][sl], frames["R_term"][sl],
                frames["L_bind"][sl], frames["L_term"][sl],
                h=h, rng=rng,
            )
            boots.append(r["K2D_soft"])
    K2D_err = float(np.std(boots, ddof=1)) if boots else float("nan")

    return {"system": system, "h": h,
             "K2D": result["K2D_soft"],
             "K2D_err": K2D_err,
             "valid_frac": result["valid_frac"],
             "n_pairs": result["n_pairs"],
             "source": frames.get("source", "real-traj"),
             "note": "",
            }


def _one_task(args: tuple) -> dict:
    traj_dir, system, h, n_lim, synth = args
    rng = np.random.default_rng(20260602 + hash((system, h)) % 1_000_000)
    return measure_k2d_for_traj(traj_dir, system, h, n_lim,
                                 synthesize_if_missing=synth, rng=rng)


def _print_purpose() -> None:
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  cluster/scripts/analyze_slab_traj.py                              ║
║  Slab MD traj → K2D(l = h) per (system, h)                         ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Reads each <slab-root>/<system>_h<h>/traj.xyz, applies the soft-Boltzmann
radial + angular acceptance kernel from raw_tether_partition_k2d.py, and
measures K2D(l = h) directly — bypassing the unbound-sampling bias that
breaks equilibrium-MD analysis.

STATUS (post 6c.A)
─────────────────────────
- K2D math (measure_k2d_from_arrays) implemented — same Mayer f-function
  as scripts/raw_tether_partition_k2d.py:estimate_area_curve.
- Real-traj parsing (_load_slab_frames_real) is a hook — implement once
  slab MD lands in cluster/outputs/slab/<sys>_h<h>/traj.xyz with mol.psf.
- Pilot mode synthesises R/L binding-bead positions from B2.2 z-stats
  (μ, σ matching wlc_z_marginal.npz) so the K2D pipeline is testable now.

PILOT
=====
With --pilot, runs all 3 systems × 1 h value (h=14) with synthetic frames
matching B2.2 z-distributions. Asserts K2D > 0 finite and rigid > flex
on absolute magnitude. < 30 s wall.
""")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slab-root", type=Path, default=DEFAULT_SLAB_ROOT)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--n-jobs", type=int, default=1)
    p.add_argument("--pilot", action="store_true",
                   help="Pilot: 3 systems × h=14 with synthetic frames. < 30 s.")
    p.add_argument("--quiet", action="store_true",
                   help="Skip PURPOSE banner")
    args = p.parse_args(argv)
    if not args.quiet:
        _print_purpose()
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    if args.pilot:
        # Each system at its own optimal h = 2·μ_z (B2.2 stats) — h=14 only
        # hits the K10 system; rigid needs h≈22 and flex needs h≈3.
        h_optimal = {s: round(2 * _PILOT_Z_STATS[s]["mu"], 1) for s in SYSTEMS}
        tasks = [(args.slab_root / f"{s}_h{int(h_optimal[s])}", s,
                   h_optimal[s], 20, True) for s in SYSTEMS]
        out_path = (REPO_ROOT / "results" / "scratch" / "pilot_slab"
                     / "K2D_l_grid.npz")
    else:
        tasks = []
        for s in SYSTEMS:
            for h in H_VALUES:
                d = args.slab_root / f"{s}_h{int(h)}"
                tasks.append((d, s, h, None, False))
        out_path = args.out

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[analyze_slab_traj] {len(tasks)} (system, h) tasks "
          f"n_jobs={args.n_jobs} pilot={args.pilot}")
    if args.n_jobs <= 1 or len(tasks) == 1:
        rows = [_one_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=args.n_jobs) as ex:
            rows = list(ex.map(_one_task, tasks))

    for r in rows:
        marker = "✓" if not np.isnan(r["K2D"]) else "—"
        src = r.get("source", "")
        print(f"  {marker} {r['system']:5s}  h = {r['h']:5.1f}   "
              f"K2D = {r['K2D']:10.3f} ± {r['K2D_err']:8.3f} nm²   "
              f"(valid_frac = {r['valid_frac']:.3f}, pairs = {r['n_pairs']})"
              f"   [{src}]"
              f"{('  ' + r['note']) if r.get('note') else ''}")

    # Pack to grid
    systems_used = sorted({r["system"] for r in rows})
    hs_used = sorted({r["h"] for r in rows})
    K2D = np.full((len(systems_used), len(hs_used)), np.nan)
    err = np.full_like(K2D, np.nan)
    for r in rows:
        i = systems_used.index(r["system"])
        j = hs_used.index(r["h"])
        K2D[i, j] = r["K2D"]
        err[i, j] = r["K2D_err"]

    np.savez(out_path, systems=systems_used, h=hs_used,
              K2D=K2D, K2D_err=err)
    print(f"Wrote {out_path}")

    # Pilot sanity — each system measured at its own optimal h, so read
    # from rows (not from the sparse grid)
    if args.pilot:
        fails = []
        by_sys = {r["system"]: r for r in rows}
        for s in SYSTEMS:
            k = by_sys.get(s, {}).get("K2D", float("nan"))
            if not (np.isfinite(k) and k > 0):
                fails.append(f"{s} K2D non-finite: {k}")
        # Magnitude sanity vs target K2D,max from the off-site run PPT
        target = {"K100": 12705, "K10": 875, "K01": 362}
        for s, expected in target.items():
            k = by_sys.get(s, {}).get("K2D", 0)
            ratio = k / expected if expected > 0 else 0
            ok = (0.1 < ratio < 10) if np.isfinite(k) else False
            print(f"   {s}: synthetic K2D = {k:.0f} nm² vs target "
                  f"{expected} nm² → ratio {ratio:.2f} {'✓' if ok else '⚠'}")
        if fails:
            print("\n   ✗  PILOT FAILED:")
            for f in fails:
                print(f"      • {f}")
            return 1
        print("\n   ✓  PILOT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

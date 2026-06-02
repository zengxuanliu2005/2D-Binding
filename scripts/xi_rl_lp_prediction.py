"""B2.4 — ξ_RL prediction from lp-parametrized K2D(l) + Xu 2015 ratio test.

Reads B2.2's z_lab samples (lab-frame chain endpoint z coordinates) and
B2.3's K2D(l) curves, predicts ξ_RL = σ_K2D for each same-system R-L pair,
and reports the rigid:flex (and rigid:semi, semi:flex) ratios alongside
Xu 2015's identical-k_a prediction (ratio = 1.00) and the measured ratios.

Bootstrap σ on σ_K2D: frame-resample (z_R, z_L) sample-pair indices with
replacement, recompute σ_K2D for each bootstrap, report std.

DERIVATION → CODE MAP
=====================
  04 (1.1)  ξ_RL^(B2) = σ_K2D from derivation/03 (1.11)   → predict_b2()
  04 (1.2)  ξ_RL^(Xu) = √(ξ_bond² + (kBT·L_ecto/(2·k_a))²) → predict_xu_2015()
  04 (1.3)  ratio = σ_K2D(R)/σ_K2D(F)                      → compute_ratios()
  04 (2.x)  bootstrap σ via (z_R, z_L) frame resample      → bootstrap_sigma_k2d()

PILOT (--pilot)
===============
Runs the rigid system × 20 bootstraps. < 5 s wall. Asserts σ_K2D within
[1.0, 2.0] nm and bootstrap σ < 0.15 nm.

PRODUCTION
==========
3 systems × 200 bootstraps × 200 K (z_R, z_L) pairs, ProcessPoolExecutor.
Outputs:
    results/derivation_b2/xi_rl_lp_prediction.npz
    results/derivation_b2/xi_rl_lp_prediction.md

USAGE
=====
    python scripts/xi_rl_lp_prediction.py --pilot
    python scripts/xi_rl_lp_prediction.py --n-boot 200 --n-jobs 8
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from k2d_l_wlc_theory import (  # noqa: E402
    DEFAULT_RCUT_NM,
    k2d_l_curve,
    k2d_l_stats,
)

# Reference numbers
MEASURED_XI_RL = {"rigid": 0.685, "semi": 2.076, "flex": 2.253}
LP_PHD = {"rigid": 84.6, "semi": 8.18, "flex": 1.14}
KBT_IN_EPS = 1.1
L_ECTO_NM = 7.0          # 7 ecto beads × 1.0 σ (CLAUDE.md)
XI_BOND_NM = 0.05377     # from results/xi_rl_candidates.npz (bond curvature only)
K_A_EFF_EPS_PER_RAD2 = {"rigid": 257.15, "semi": 252.32, "flex": 257.48}

L_GRID_DEFAULT = np.arange(0.0, 26.0 + 0.05, 0.1)  # 261 points, Δl = 0.1 nm

_BANNER = """
╔════════════════════════════════════════════════════════════════════╗
║  xi_rl_lp_prediction.py — B2.4 ξ_RL from σ_K2D + Xu 2015 ratio test ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
  Predict ξ_RL = σ_K2D for each same-system R-L pair (using B2.2's
  WLC z_lab samples), bootstrap the prediction, then compare ratios
  rigid:flex / rigid:semi / semi:flex against:
    - Xu 2015 (identical k_a → ratio = 1.00)
    - measured ξ_RL fit (0.685 / 2.076 / 2.253 nm)
  Outputs the head-to-head table to xi_rl_lp_prediction.{npz,md}.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Xu 2015 formula
# ─────────────────────────────────────────────────────────────────────────────
def predict_xu_2015(k_a_eps: float, L_ecto: float = L_ECTO_NM,
                    xi_bond: float = XI_BOND_NM, kbt_eps: float = KBT_IN_EPS,
                    ) -> float:
    """Xu 2015: ξ_RL² = ξ_bond² + (kBT · L_ecto / (2 k_a))².

    Note k_a is in ε/rad² and we work in kBT units, so the kBT/k_a
    Boltzmann ratio becomes kbt_eps/k_a_eps (dimensionless × rad²).
    """
    angle_term = (kbt_eps * L_ecto) / (2.0 * k_a_eps)
    return math.sqrt(xi_bond ** 2 + angle_term ** 2)


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap σ_K2D
# ─────────────────────────────────────────────────────────────────────────────
def _bootstrap_worker(args):
    z_R, z_L, l_grid, rcut, seed = args
    rng = np.random.default_rng(seed)
    n = z_R.size
    idx_R = rng.integers(0, n, size=n)
    idx_L = rng.integers(0, n, size=n)
    K2D = k2d_l_curve(z_R[idx_R], z_L[idx_L], l_grid, rcut=rcut,
                       truncate_negative=True)
    return k2d_l_stats(l_grid, K2D)


def bootstrap_sigma_k2d(z_R: np.ndarray, z_L: np.ndarray,
                         l_grid: np.ndarray, n_boot: int, n_jobs: int,
                         rcut: float = DEFAULT_RCUT_NM, base_seed: int = 0,
                         ) -> dict:
    """Frame-resample (z_R, z_L) pairs with replacement n_boot times.

    Returns a dict of arrays (length n_boot) for K2D_max, l_star, l_mean,
    sigma_K2D, Z plus their bootstrap means/stds.
    """
    seeds = [base_seed + 31 * i for i in range(n_boot)]
    args = [(z_R, z_L, l_grid, rcut, s) for s in seeds]

    if n_jobs <= 1:
        rows = [_bootstrap_worker(a) for a in args]
    else:
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        with ProcessPoolExecutor(max_workers=n_jobs) as pool:
            rows = list(pool.map(_bootstrap_worker, args))

    keys = ("K2D_max", "l_star", "l_mean", "sigma_K2D", "Z")
    out = {k: np.array([r[k] for r in rows]) for k in keys}
    out["sigma_K2D_boot_mean"] = float(out["sigma_K2D"].mean())
    out["sigma_K2D_boot_std"] = float(out["sigma_K2D"].std(ddof=1))
    out["K2D_max_boot_mean"] = float(out["K2D_max"].mean())
    out["K2D_max_boot_std"] = float(out["K2D_max"].std(ddof=1))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Production run
# ─────────────────────────────────────────────────────────────────────────────
def run_production(n_boot: int, n_jobs: int, out_dir: Path) -> int:
    """B2.4 — ξ_RL predictions + bootstrap σ + ratio table."""
    z_path = ROOT / "results" / "derivation_b2" / "wlc_z_marginal.npz"
    if not z_path.exists():
        print(f"   ✗ missing {z_path} — run k2d_l_wlc_theory.py production first")
        return 1
    z_data = np.load(z_path, allow_pickle=True)
    print(f"   loaded z_lab arrays from {z_path.relative_to(ROOT)}")
    print(f"   n_boot = {n_boot}, n_jobs = {n_jobs}, "
          f"l grid = {len(L_GRID_DEFAULT)} points × "
          f"{L_GRID_DEFAULT[1] - L_GRID_DEFAULT[0]:.2f} nm, "
          f"rcut = {DEFAULT_RCUT_NM} nm")

    t0 = time.time()
    boot = {}
    for label in ("rigid", "semi", "flex"):
        z_lab = z_data[f"{label}__z_lab"]
        tic = time.time()
        boot[label] = bootstrap_sigma_k2d(
            z_lab, z_lab, L_GRID_DEFAULT, n_boot=n_boot, n_jobs=n_jobs,
            base_seed=20260603 + hash(label) % 1_000_000,
        )
        print(f"     {label:6s}: σ_K2D = {boot[label]['sigma_K2D_boot_mean']:.4f} "
              f"± {boot[label]['sigma_K2D_boot_std']:.4f} nm   "
              f"({n_boot} boot in {time.time() - tic:.1f} s)")

    # ── ξ_RL predictions per system ──────────────────────────────────────────
    print(f"\n▶  B2.4.1 — ξ_RL prediction per same-system pair")
    print(f"   {'system':6s}  {'σ_K2D (nm)':>18s}  {'Xu 2015 (nm)':>14s}  "
          f"{'measured (nm)':>14s}")
    rows = []
    for label in ("rigid", "semi", "flex"):
        xi_b2 = boot[label]["sigma_K2D_boot_mean"]
        xi_b2_se = boot[label]["sigma_K2D_boot_std"]
        xi_xu = predict_xu_2015(K_A_EFF_EPS_PER_RAD2[label])
        xi_meas = MEASURED_XI_RL[label]
        print(f"   {label:6s}  {xi_b2:8.4f} ± {xi_b2_se:6.4f}  "
              f"{xi_xu:14.4f}  {xi_meas:14.4f}")
        rows.append((label, xi_b2, xi_b2_se, xi_xu, xi_meas))

    # ── ratio test ───────────────────────────────────────────────────────────
    print(f"\n▶  B2.4.2 — ratio test (lp discrimination signature)")
    print(f"   {'ratio':12s}  {'B2 (this work)':>16s}  {'Xu 2015':>10s}  "
          f"{'measured':>10s}")

    def _ratio(num_lbl, den_lbl, source):
        if source == "B2":
            return (boot[num_lbl]["sigma_K2D_boot_mean"]
                    / boot[den_lbl]["sigma_K2D_boot_mean"])
        if source == "Xu":
            return (predict_xu_2015(K_A_EFF_EPS_PER_RAD2[num_lbl])
                    / predict_xu_2015(K_A_EFF_EPS_PER_RAD2[den_lbl]))
        return MEASURED_XI_RL[num_lbl] / MEASURED_XI_RL[den_lbl]

    ratios = {}
    pairs = [("rigid", "flex"), ("rigid", "semi"), ("semi", "flex")]
    for (a, b) in pairs:
        r_b2 = _ratio(a, b, "B2")
        # bootstrap σ via paired resamples (each iteration shares index list)
        r_boot = (boot[a]["sigma_K2D"] / boot[b]["sigma_K2D"])
        r_b2_se = float(r_boot.std(ddof=1))
        r_xu = _ratio(a, b, "Xu")
        r_meas = _ratio(a, b, "MEAS")
        ratios[f"{a}_over_{b}"] = {
            "B2": r_b2, "B2_se": r_b2_se, "Xu": r_xu, "measured": r_meas}
        print(f"   {a + ':' + b:12s}  {r_b2:8.3f} ± {r_b2_se:5.3f}  "
              f"{r_xu:10.3f}  {r_meas:10.3f}")

    # ── interpretation ──────────────────────────────────────────────────────
    rigid_flex_b2 = ratios["rigid_over_flex"]["B2"]
    rigid_flex_meas = ratios["rigid_over_flex"]["measured"]
    rigid_flex_xu = ratios["rigid_over_flex"]["Xu"]
    print(f"\n▶  Verdict")
    err_b2 = 100 * abs(rigid_flex_b2 - rigid_flex_meas) / rigid_flex_meas
    err_xu = 100 * abs(rigid_flex_xu - rigid_flex_meas) / rigid_flex_meas
    print(f"   rigid:flex ratio  →  B2 {rigid_flex_b2:.3f}  vs measured "
          f"{rigid_flex_meas:.3f}   ({err_b2:.1f}% off)")
    print(f"   rigid:flex ratio  →  Xu {rigid_flex_xu:.3f}  vs measured "
          f"{rigid_flex_meas:.3f}   ({err_xu:.1f}% off)")
    verdict = ("B2 captures lp discrimination, Xu cannot"
               if err_b2 < err_xu / 2
               else "Verdicts close — read individual rows")
    print(f"   → {verdict}")

    # ── output ───────────────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"l_grid": L_GRID_DEFAULT, "rcut": DEFAULT_RCUT_NM,
                "n_boot": n_boot, "verdict": verdict}
    for label in ("rigid", "semi", "flex"):
        payload[f"{label}__sigma_K2D_boot"] = boot[label]["sigma_K2D"]
        payload[f"{label}__sigma_K2D_mean"] = boot[label]["sigma_K2D_boot_mean"]
        payload[f"{label}__sigma_K2D_std"] = boot[label]["sigma_K2D_boot_std"]
        payload[f"{label}__K2D_max_boot"] = boot[label]["K2D_max"]
        payload[f"{label}__xi_rl_xu_2015"] = predict_xu_2015(
            K_A_EFF_EPS_PER_RAD2[label])
        payload[f"{label}__xi_rl_measured"] = MEASURED_XI_RL[label]
        payload[f"{label}__lp_nm"] = LP_PHD[label]
        payload[f"{label}__k_a_eps"] = K_A_EFF_EPS_PER_RAD2[label]
    for key, val in ratios.items():
        for src, v in val.items():
            payload[f"ratio__{key}__{src}"] = v
    npz_path = out_dir / "xi_rl_lp_prediction.npz"
    np.savez(npz_path, **payload)
    print(f"\n   saved {npz_path.relative_to(ROOT)}")

    # Markdown summary
    md_path = out_dir / "xi_rl_lp_prediction.md"
    with md_path.open("w") as fp:
        fp.write(f"# B2.4 — ξ_RL prediction + Xu 2015 ratio test\n\n")
        fp.write(f"_Generated by_ `scripts/xi_rl_lp_prediction.py`  "
                  f"_(n_boot = {n_boot}, rcut = {DEFAULT_RCUT_NM} nm)_\n\n")
        fp.write(f"## Per-system ξ_RL (nm)\n\n")
        fp.write("| system | lp (nm) | σ_K2D (B2 ± boot σ) | Xu 2015 | measured |\n")
        fp.write("|---|---:|---:|---:|---:|\n")
        for (lbl, xi_b2, xi_se, xi_xu, xi_meas) in rows:
            fp.write(f"| {lbl} | {LP_PHD[lbl]:.2f} | "
                      f"{xi_b2:.3f} ± {xi_se:.3f} | "
                      f"{xi_xu:.4f} | {xi_meas:.3f} |\n")
        fp.write(f"\n## Ratio test (lp discrimination signature)\n\n")
        fp.write("| ratio | B2 (this work) ± boot σ | Xu 2015 | measured |\n")
        fp.write("|---|---:|---:|---:|\n")
        for (a, b) in pairs:
            r = ratios[f"{a}_over_{b}"]
            fp.write(f"| {a}:{b} | {r['B2']:.3f} ± {r['B2_se']:.3f} | "
                      f"{r['Xu']:.3f} | {r['measured']:.3f} |\n")
        fp.write(f"\n## Verdict\n\n{verdict}\n\n")
        fp.write("**rigid:flex ratio** — measured = "
                  f"{rigid_flex_meas:.3f}, B2 = {rigid_flex_b2:.3f} "
                  f"({err_b2:.1f}% off), Xu 2015 = "
                  f"{rigid_flex_xu:.3f} ({err_xu:.1f}% off).\n")
    print(f"   saved {md_path.relative_to(ROOT)}")
    print(f"\n   total wall: {time.time() - t0:.1f} s")
    return 0


def run_pilot() -> int:
    """Smoke test: rigid system × 20 bootstraps, single core."""
    print("\n▶  Pilot — rigid × 20 bootstraps (single core)")
    z_path = ROOT / "results" / "derivation_b2" / "wlc_z_marginal.npz"
    if not z_path.exists():
        print(f"   ✗ missing {z_path}")
        return 1
    z_data = np.load(z_path, allow_pickle=True)
    z_lab = z_data["rigid__z_lab"]
    t0 = time.time()
    boot = bootstrap_sigma_k2d(
        z_lab, z_lab, L_GRID_DEFAULT, n_boot=20, n_jobs=1,
        base_seed=20260603,
    )
    dt = time.time() - t0
    print(f"   σ_K2D = {boot['sigma_K2D_boot_mean']:.4f} ± "
          f"{boot['sigma_K2D_boot_std']:.4f} nm   ({dt:.1f} s)")
    fails = []
    if not (1.0 < boot["sigma_K2D_boot_mean"] < 2.0):
        fails.append(f"σ_K2D rigid = {boot['sigma_K2D_boot_mean']:.3f} "
                      "outside [1.0, 2.0] nm")
    if boot["sigma_K2D_boot_std"] > 0.15:
        fails.append(f"bootstrap σ on σ_K2D = "
                      f"{boot['sigma_K2D_boot_std']:.3f} > 0.15 nm")

    # Xu 2015 quick check
    xu_rigid = predict_xu_2015(K_A_EFF_EPS_PER_RAD2["rigid"])
    xu_flex = predict_xu_2015(K_A_EFF_EPS_PER_RAD2["flex"])
    print(f"   Xu 2015: rigid = {xu_rigid:.5f}, flex = {xu_flex:.5f} nm "
          f"  (ratio = {xu_rigid/xu_flex:.4f})")
    if abs(xu_rigid / xu_flex - 1.0) > 0.05:
        fails.append(f"Xu 2015 ratio rigid/flex = {xu_rigid/xu_flex:.3f} "
                      "(expected ≈ 1.00 with identical k_a)")

    out_dir = ROOT / "results" / "scratch" / "pilot_xi_rl_lp"
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(out_dir / "pilot_rigid_boot.npz", **boot)
    print(f"   saved {out_dir.relative_to(ROOT)}/pilot_rigid_boot.npz")
    if fails:
        print("\n   ✗  PILOT FAILED:")
        for f in fails:
            print(f"      • {f}")
        return 1
    print("\n   ✓  PILOT PASSED")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pilot", action="store_true",
                   help="Pilot: rigid only × 20 boot, single core, < 5 s")
    p.add_argument("--n-boot", type=int, default=200,
                   help="Bootstrap iterations per system (production)")
    p.add_argument("--n-jobs", type=int, default=1,
                   help="Parallel workers for bootstrap")
    p.add_argument("--out-dir", type=Path,
                   default=ROOT / "results" / "derivation_b2",
                   help="Production output directory")
    p.add_argument("--quiet", action="store_true",
                   help="Skip PURPOSE banner")
    args = p.parse_args(argv)

    if not args.quiet:
        print(_BANNER)

    if args.pilot:
        return run_pilot()
    return run_production(args.n_boot, args.n_jobs, args.out_dir)


if __name__ == "__main__":
    sys.exit(main())

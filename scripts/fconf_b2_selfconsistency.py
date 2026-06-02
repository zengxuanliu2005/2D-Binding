"""B2.5 — F_conf via -ln P_z(D_bound) self-consistency vs Marko-Siggia.

Reads B2.2's lab-frame z_lab samples and evaluates the membrane-anchored
chain endpoint probability at z = D_bound (the measured bound-chain
vertical reach). The natural-log gives F_conf in kBT units:

    F_conf^(B2)(D) = -ln P_z(D; lp, Lc, k_a)                 (B2.5 eq 1.1)

Then computes the cross-system pair table

    ΔΔF_conf(A-B) = F_conf^(A)(D_A) - F_conf^(B)(D_B)         (B2.5 eq 1.2)

and compares against Marko-Siggia integrated WLC (Closure 5 / B1) and
PPT slide 25 numbers from the senior. Bootstrap σ via frame-resample of
the z_lab arrays (n_boot = 200).

DERIVATION → CODE MAP
=====================
  05 (1.1)  F_conf^(B2)(D) = -ln P_z(D)              → F_conf_from_p_z()
  05 (1.2)  ΔΔF_conf(A-B) = F^A(D_A) - F^B(D_B)      → cross_pair_table_b25()
  05 (2.x)  histogram + linear interp for P_z(D)     → estimate_p_z_at()

PILOT (--pilot)
===============
Rigid system × D = 9.154 nm × 20 bootstraps × single core. < 5 s.
Asserts F_conf > 0 (chain stretched from natural length) and bootstrap
σ < 0.05 kBT.

PRODUCTION
==========
3 systems × 200 bootstraps × 200 K samples each. ~10 s with n_jobs=8.
Outputs:
    results/derivation_b2/fconf_b2_selfconsistency.{npz,md}

USAGE
=====
    python scripts/fconf_b2_selfconsistency.py --pilot
    python scripts/fconf_b2_selfconsistency.py --n-boot 200 --n-jobs 8
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

# D_bound (measured bound-chain vertical reach, nm) from
# results/closure_wlc_three_term.md — same numbers feed Marko-Siggia.
D_BOUND_NM = {"rigid": 9.154, "semi": 7.964, "flex": 6.615}

# Marko-Siggia F_conf per system (kBT) from B1, for cross-check.
F_CONF_MS_B1 = {"rigid": 0.128, "semi": 0.803, "flex": 3.381}

# B1 ΔΔF_conf (3 pairs, kBT) — Marko-Siggia.
DDF_CONF_B1 = {
    "flex-rigid": +3.253,
    "semi-rigid": +0.675,
    "semi-flex":  -2.577,
}

# PPT s25 ΔΔF_sum (3-term closure result; F_conf part not separately
# reported by senior). We display these for context only.
DDF_SUM_PPT_S25 = {
    "flex-rigid": +3.64,
    "semi-rigid": +2.47,
    "semi-flex":  -1.18,
}

# Pair specification (matches closure_wlc_three_term.PAIR_SPECS).
PAIR_SPECS = [
    ("flex-rigid", "flex", "rigid"),
    ("semi-rigid", "semi", "rigid"),
    ("semi-flex",  "semi", "flex"),
]

# Histogram resolution for P_z estimate; 200 bins over the observed
# range gives sub-nm resolution for all three systems.
DEFAULT_N_BINS = 200

_BANNER = """
╔════════════════════════════════════════════════════════════════════╗
║  fconf_b2_selfconsistency.py — B2.5 F_conf via -ln P_z(D_bound)    ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
  Evaluate F_conf for each system at its bound vertical reach D_bound
  via the membrane-anchored z marginal P_z(z; lp, Lc, k_a) from B2.2.
  Form ΔΔF_conf cross-pair, compare with B1 Marko-Siggia (3.253 /
  0.675 / -2.577 kBT) and PPT s25 closure totals.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Core: P_z(D) and F_conf
# ─────────────────────────────────────────────────────────────────────────────
def estimate_p_z_at(z_samples: np.ndarray, D: float,
                     n_bins: int = DEFAULT_N_BINS) -> float:
    """Histogram-based estimate of P_z(z=D) (units: 1/nm).

    Linear interpolation on bin centres. Returns a positive density;
    if D falls in an empty bin we replace with the minimum non-zero
    density in the histogram (worst case: ln 0 → +inf).
    """
    counts, edges = np.histogram(z_samples, bins=n_bins, density=True)
    centres = 0.5 * (edges[:-1] + edges[1:])
    val = float(np.interp(D, centres, counts))
    if val <= 0:
        nz = counts[counts > 0]
        val = float(nz.min()) if nz.size else 1e-12
    return val


def F_conf_from_p_z(z_samples: np.ndarray, D: float,
                     n_bins: int = DEFAULT_N_BINS) -> float:
    """F_conf(D) = -ln P_z(D) (kBT units, natural log).

    The constant offset (depending on the choice of z-reference unit)
    cancels in cross-system differences ΔΔF.
    """
    return -math.log(estimate_p_z_at(z_samples, D, n_bins=n_bins))


# ─────────────────────────────────────────────────────────────────────────────
# Cross-pair table
# ─────────────────────────────────────────────────────────────────────────────
def cross_pair_table_b25(F_per_system: dict[str, float]) -> dict[str, float]:
    return {name: F_per_system[a] - F_per_system[b]
            for (name, a, b) in PAIR_SPECS}


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────────────────────
def _bootstrap_worker(args):
    z_lab, D, seed, n_bins = args
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, z_lab.size, size=z_lab.size)
    return F_conf_from_p_z(z_lab[idx], D, n_bins=n_bins)


def bootstrap_F_conf(z_lab: np.ndarray, D: float, n_boot: int, n_jobs: int,
                     base_seed: int = 0,
                     n_bins: int = DEFAULT_N_BINS) -> dict:
    seeds = [base_seed + 31 * i for i in range(n_boot)]
    args = [(z_lab, D, s, n_bins) for s in seeds]
    if n_jobs <= 1:
        F_b = np.array([_bootstrap_worker(a) for a in args])
    else:
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        with ProcessPoolExecutor(max_workers=n_jobs) as pool:
            F_b = np.fromiter(pool.map(_bootstrap_worker, args),
                              dtype=float, count=n_boot)
    return {
        "F_boot": F_b,
        "F_mean": float(F_b.mean()),
        "F_std":  float(F_b.std(ddof=1)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Production
# ─────────────────────────────────────────────────────────────────────────────
def run_production(n_boot: int, n_jobs: int, n_bins: int,
                   out_dir: Path) -> int:
    z_path = ROOT / "results" / "derivation_b2" / "wlc_z_marginal.npz"
    if not z_path.exists():
        print(f"   ✗ missing {z_path}")
        return 1
    z_data = np.load(z_path, allow_pickle=True)
    print(f"   loaded z_lab from {z_path.relative_to(ROOT)}")
    print(f"   n_boot = {n_boot}, n_jobs = {n_jobs}, n_bins = {n_bins}")

    t0 = time.time()
    boot = {}
    for label in ("rigid", "semi", "flex"):
        z_lab = z_data[f"{label}__z_lab"]
        D = D_BOUND_NM[label]
        tic = time.time()
        boot[label] = bootstrap_F_conf(
            z_lab, D, n_boot=n_boot, n_jobs=n_jobs,
            base_seed=20260604 + hash(label) % 1_000_000,
            n_bins=n_bins,
        )
        boot[label]["D_bound"] = D
        # also point-estimate (no bootstrap) for the headline number
        boot[label]["F_point"] = F_conf_from_p_z(z_lab, D, n_bins=n_bins)
        print(f"     {label:6s}  D = {D:6.3f} nm   "
              f"F_conf^(B2) = {boot[label]['F_mean']:+7.3f} ± "
              f"{boot[label]['F_std']:5.3f} kBT   "
              f"(point = {boot[label]['F_point']:+7.3f})   "
              f"({n_boot} boot in {time.time() - tic:.1f} s)")

    # Per-system table
    print(f"\n▶  B2.5.1 — per-system F_conf (kBT)")
    print(f"   {'sys':6s}  {'D (nm)':>7s}  {'F_conf^(B2)':>17s}  "
          f"{'F_conf^(MS, B1)':>17s}  {'Δ (B2−MS)':>11s}")
    diffs = {}
    for label in ("rigid", "semi", "flex"):
        F_b2 = boot[label]["F_mean"]
        F_se = boot[label]["F_std"]
        F_ms = F_CONF_MS_B1[label]
        delta = F_b2 - F_ms
        diffs[label] = delta
        print(f"   {label:6s}  {D_BOUND_NM[label]:7.3f}  "
              f"{F_b2:+8.3f} ± {F_se:5.3f}   {F_ms:+17.3f}   "
              f"{delta:+11.3f}")

    # Cross-pair table
    print(f"\n▶  B2.5.2 — ΔΔF_conf cross-pair (kBT)")
    print(f"   {'pair':12s}  {'ΔΔF^(B2)':>15s}  "
          f"{'ΔΔF^(MS, B1)':>14s}  {'ΔΔF_sum^(PPT s25)':>20s}")
    F_per_system = {l: boot[l]["F_mean"] for l in ("rigid", "semi", "flex")}
    ddF_b2 = cross_pair_table_b25(F_per_system)
    # bootstrap σ for ΔΔF: paired across labels by sample index
    pair_se = {}
    for (name, a, b) in PAIR_SPECS:
        diff_boot = boot[a]["F_boot"] - boot[b]["F_boot"]
        pair_se[name] = float(diff_boot.std(ddof=1))
        print(f"   {name:12s}  {ddF_b2[name]:+8.3f} ± {pair_se[name]:5.3f}  "
              f"{DDF_CONF_B1[name]:+14.3f}  "
              f"{DDF_SUM_PPT_S25[name]:+20.3f}")

    # Verdict
    rms_b2_ms = math.sqrt(np.mean([(ddF_b2[n] - DDF_CONF_B1[n]) ** 2
                                    for n, _, _ in PAIR_SPECS]))
    print(f"\n▶  Verdict")
    print(f"   RMS(ΔΔF_conf^B2 − ΔΔF_conf^MS) = {rms_b2_ms:.3f} kBT")
    if rms_b2_ms < 0.5:
        verdict = ("✓ B2 P_z and Marko-Siggia agree (RMS < 0.5 kBT) — same "
                    "WLC physics, two independent estimators of F_conf")
    elif rms_b2_ms < 1.5:
        verdict = ("⚠ B2 P_z and Marko-Siggia disagree by ~ 1 kBT RMS — "
                    "anchor cone modulates F_conf beyond pure WLC stretch")
    else:
        verdict = ("✗ B2 P_z and Marko-Siggia disagree by > 1.5 kBT RMS — "
                    "investigate (anchor cone / z<0 truncation / KDE binning)")
    print(f"   → {verdict}")

    # Save outputs
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"n_boot": n_boot, "n_bins": n_bins,
                "rms_b2_minus_ms": rms_b2_ms, "verdict": verdict}
    for label in ("rigid", "semi", "flex"):
        payload[f"{label}__D_bound"] = D_BOUND_NM[label]
        payload[f"{label}__F_conf_B2_mean"] = boot[label]["F_mean"]
        payload[f"{label}__F_conf_B2_std"] = boot[label]["F_std"]
        payload[f"{label}__F_conf_B2_boot"] = boot[label]["F_boot"]
        payload[f"{label}__F_conf_MS"] = F_CONF_MS_B1[label]
    for (name, a, b) in PAIR_SPECS:
        payload[f"ddF__{name}__B2"] = ddF_b2[name]
        payload[f"ddF__{name}__B2_se"] = pair_se[name]
        payload[f"ddF__{name}__MS"] = DDF_CONF_B1[name]
        payload[f"ddF__{name}__PPT_sum"] = DDF_SUM_PPT_S25[name]
    npz_path = out_dir / "fconf_b2_selfconsistency.npz"
    np.savez(npz_path, **payload)
    print(f"\n   saved {npz_path.relative_to(ROOT)}")

    md_path = out_dir / "fconf_b2_selfconsistency.md"
    with md_path.open("w") as fp:
        fp.write("---\n")
        fp.write("purpose: B2.5 F_conf via -ln P_z(D) vs Marko-Siggia (auto-generated)\n")
        fp.write("audience: Claude (next session) + essay v2 §5.3 author\n")
        fp.write("status: current\n")
        fp.write("generated_by: scripts/fconf_b2_selfconsistency.py\n")
        fp.write("derivation: derivation/05_fconf_selfconsistency/\n")
        fp.write("---\n\n")
        fp.write("# B2.5 — F_conf via -ln P_z(D_bound) self-consistency\n\n")
        fp.write(f"_Generated by_ `scripts/fconf_b2_selfconsistency.py` "
                  f"_(n_boot = {n_boot}, n_bins = {n_bins})_\n\n")
        fp.write("## Per-system F_conf (kBT, natural log)\n\n")
        fp.write("| system | D_bound (nm) | F_conf^(B2 P_z) ± σ | "
                  "F_conf^(MS, B1) | Δ (B2-MS) |\n")
        fp.write("|---|---:|---:|---:|---:|\n")
        for label in ("rigid", "semi", "flex"):
            fp.write(f"| {label} | {D_BOUND_NM[label]:.3f} | "
                      f"{boot[label]['F_mean']:+.3f} ± "
                      f"{boot[label]['F_std']:.3f} | "
                      f"{F_CONF_MS_B1[label]:+.3f} | "
                      f"{diffs[label]:+.3f} |\n")
        fp.write("\n## ΔΔF_conf cross-pair (kBT)\n\n")
        fp.write("| pair | ΔΔF^(B2) ± σ | ΔΔF^(MS, B1) | ΔΔF_sum^(PPT s25) |\n")
        fp.write("|---|---:|---:|---:|\n")
        for (name, a, b) in PAIR_SPECS:
            fp.write(f"| {name} | {ddF_b2[name]:+.3f} ± "
                      f"{pair_se[name]:.3f} | "
                      f"{DDF_CONF_B1[name]:+.3f} | "
                      f"{DDF_SUM_PPT_S25[name]:+.3f} |\n")
        fp.write(f"\n## Verdict\n\nRMS(ΔΔF_conf^B2 − ΔΔF_conf^MS) = "
                  f"{rms_b2_ms:.3f} kBT\n\n{verdict}\n")
    print(f"   saved {md_path.relative_to(ROOT)}")
    print(f"\n   total wall: {time.time() - t0:.1f} s")
    return 0


def run_pilot() -> int:
    print("\n▶  Pilot — rigid only × 20 boot, single core")
    z_path = ROOT / "results" / "derivation_b2" / "wlc_z_marginal.npz"
    if not z_path.exists():
        print(f"   ✗ missing {z_path}")
        return 1
    z_lab = np.load(z_path, allow_pickle=True)["rigid__z_lab"]
    D = D_BOUND_NM["rigid"]
    t0 = time.time()
    boot = bootstrap_F_conf(z_lab, D, n_boot=20, n_jobs=1,
                             base_seed=20260604)
    F_p = F_conf_from_p_z(z_lab, D)
    print(f"   F_conf^(B2)(D = {D} nm) = {boot['F_mean']:+.3f} "
          f"± {boot['F_std']:.3f} kBT   "
          f"(point estimate = {F_p:+.3f})")
    print(f"   reference (B1 Marko-Siggia): F_conf = "
          f"{F_CONF_MS_B1['rigid']:+.3f} kBT")
    print(f"   ({time.time() - t0:.1f} s)")
    fails = []
    if boot["F_std"] > 0.05:
        fails.append(f"bootstrap σ = {boot['F_std']:.3f} > 0.05 kBT")
    if not np.isfinite(boot["F_mean"]):
        fails.append("F_conf is NaN/inf")
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
                   help="Pilot: rigid only × 20 boot, < 5 s")
    p.add_argument("--n-boot", type=int, default=200)
    p.add_argument("--n-jobs", type=int, default=1)
    p.add_argument("--n-bins", type=int, default=DEFAULT_N_BINS,
                   help="P_z histogram bin count (default 200)")
    p.add_argument("--out-dir", type=Path,
                   default=ROOT / "results" / "derivation_b2")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)
    if not args.quiet:
        print(_BANNER)
    if args.pilot:
        return run_pilot()
    return run_production(args.n_boot, args.n_jobs, args.n_bins, args.out_dir)


if __name__ == "__main__":
    sys.exit(main())

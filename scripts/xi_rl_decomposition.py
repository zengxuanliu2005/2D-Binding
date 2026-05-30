"""Q1 Step 1: replicate PhD's 2-step fit protocol on result_K*.tsv.

Step 1 — Unconstrained Hu master curve fit per system:
    K2D(ξ⊥) = K2D,max · [1 + (ξ⊥/ξ_RL)²]^(-1/2)
    → (K2D,max_unconstrained, ξ_RL_unconstrained)

Step 2 — Fix ξ_RL, refit K2D,max for each #bonds (n→n+1) transition:
    K2D(ξ⊥) = K2D,max · [1 + (ξ⊥/ξ_RL_fixed)²]^(-1/2)
    → K2D,max per transition

Then report the consensus: fix ξ_RL from Step 1, report K2D,max from
the mean (or most-populated transition) of Step 2.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parent.parent

SYSTEMS = [
    ("rigid", "result_K100.tsv", "K100"),
    ("semi",  "result_K10.tsv",  "K10"),
    ("flex",  "result_K1.tsv",   "K1"),
]

# PhD's published values (from PPT slides 5-9)
PHD_VALUES = {
    "rigid": {"xi_rl": 0.68, "k2d_max": 12705},
    "semi":  {"xi_rl": 2.08, "k2d_max": 875},
    "flex":  {"xi_rl": 2.25, "k2d_max": 362},
}


def hu_master(xi, k2d_max, xi_rl):
    """Hu 2013 master curve."""
    return k2d_max / np.sqrt(1.0 + (xi / xi_rl) ** 2)


def load_tsv(path):
    """Load a result_K*.tsv file, return (xi, k2d, bonds_col) arrays."""
    with open(path) as fp:
        header = fp.readline().lstrip("#").strip().split("\t")
    arr = np.genfromtxt(path, skip_header=1, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    cols = {name: i for i, name in enumerate(header)}
    xi = arr[:, cols["roughness"]]
    k2d = arr[:, cols["K2D(n->n+1)"]]
    bonds = arr[:, cols["bonds"]].astype(int)
    return xi, k2d, bonds


def fit_unconstrained(xi, k2d):
    """Unconstrained 2-param Hu fit. Returns (k2d_max, xi_rl, pcov)."""
    k2d_max_guess = k2d.max() * 1.3
    xi_rl_guess = max(np.std(xi), 0.3)
    popt, pcov = curve_fit(
        hu_master, xi, k2d,
        p0=[k2d_max_guess, xi_rl_guess],
        bounds=([0, 0.01], [1e6, 20.0]),
        maxfev=10000,
    )
    return popt[0], popt[1], pcov


def fit_k2d_max_fixed_xi(xi, k2d, xi_rl_fixed):
    """Fit only K2D,max with ξ_RL held fixed. Returns (k2d_max, rmse)."""
    # The model is linear in K2D,max when ξ_RL is fixed:
    # K2D = K2D,max · f(ξ⊥) where f(ξ⊥) = [1 + (ξ⊥/ξ_RL)²]^(-1/2)
    f = 1.0 / np.sqrt(1.0 + (xi / xi_rl_fixed) ** 2)
    k2d_max = float(np.sum(k2d * f) / np.sum(f ** 2))
    pred = k2d_max * f
    rmse = float(np.sqrt(np.mean((k2d - pred) ** 2)))
    return k2d_max, rmse


def main():
    out_npz = ROOT / "results" / "xi_rl_fit.npz"
    out_md = ROOT / "results" / "xi_rl_fit_summary.md"

    fit_results = {}

    print("=" * 70)
    print("Q1 Step 1: Replicate PhD's 2-step K2D,max fit protocol")
    print("=" * 70)

    for label, fname, sys_name in SYSTEMS:
        path = ROOT / "results" / "external" / fname
        xi, k2d, bonds = load_tsv(path)

        # --- Step 1: Unconstrained fit ---
        k2d_max_unc, xi_rl_unc, pcov = fit_unconstrained(xi, k2d)
        xi_rl_se = float(np.sqrt(pcov[1, 1])) if pcov[1, 1] > 0 else 0.0
        k2d_max_se = float(np.sqrt(pcov[0, 0])) if pcov[0, 0] > 0 else 0.0

        # --- Step 2: Per-#bonds refit with ξ_RL fixed ---
        unique_bonds = np.unique(bonds)
        per_bond_results = []
        for b in unique_bonds:
            mask = bonds == b
            k2d_max_b, rmse_b = fit_k2d_max_fixed_xi(
                xi[mask], k2d[mask], xi_rl_unc)
            per_bond_results.append((int(b), k2d_max_b, rmse_b, mask.sum()))

        # Mean across transitions (unweighted)
        per_bond_k2d_max = np.array([r[1] for r in per_bond_results])
        k2d_max_mean = float(np.mean(per_bond_k2d_max))
        k2d_max_std = float(np.std(per_bond_k2d_max, ddof=1))

        # Also the value from the most-populated transition (likely #bonds 5-7)
        best = max(per_bond_results, key=lambda r: r[3])
        k2d_max_best = best[1]

        # PhD published
        phd = PHD_VALUES[label]

        print(f"\n--- {sys_name} ({label}) ---")
        print(f"  n_data = {len(xi)}, n_transitions = {len(unique_bonds)}")
        print(f"  Step 1 unconstrained:")
        print(f"    K2D,max = {k2d_max_unc:.1f} ± {k2d_max_se:.1f} nm²")
        print(f"    ξ_RL    = {xi_rl_unc:.4f} ± {xi_rl_se:.4f} nm")
        print(f"  Step 2 per-#bonds (ξ_RL={xi_rl_unc:.4f} fixed):")
        for b, km, rmse, n in per_bond_results:
            print(f"    #bonds={b}: K2D,max={km:.1f} nm², RMSE={rmse:.1f}, n={n}")
        print(f"  Per-#bonds mean K2D,max = {k2d_max_mean:.1f} ± {k2d_max_std:.1f}")
        print(f"  Best-populated (#bonds={best[0]}): K2D,max = {k2d_max_best:.1f}")
        print(f"  PhD published: ξ_RL={phd['xi_rl']:.2f}, K2D,max={phd['k2d_max']:.0f}")
        print(f"  Match: Δξ_RL/σ={abs(xi_rl_unc - phd['xi_rl']) / max(xi_rl_se, 0.01):.1f}σ, "
              f"ΔK2D,max={abs(k2d_max_mean - phd['k2d_max']) / phd['k2d_max'] * 100:.1f}%")

        fit_results[label] = {
            "k2d_max_unconstrained": k2d_max_unc,
            "k2d_max_se": k2d_max_se,
            "xi_rl_unconstrained": xi_rl_unc,
            "xi_rl_se": xi_rl_se,
            "k2d_max_per_bond_mean": k2d_max_mean,
            "k2d_max_per_bond_std": k2d_max_std,
            "k2d_max_best_transition": k2d_max_best,
            "best_bonds": int(best[0]),
            "per_bond_results": per_bond_results,
            "n_data": len(xi),
            "n_transitions": len(unique_bonds),
        }

    # --- Save ---
    payload = {}
    for label, d in fit_results.items():
        for k, v in d.items():
            if k == "per_bond_results":
                continue
            payload[f"{label}__{k}"] = v
    np.savez(out_npz, **payload)

    with open(out_md, "w") as fp:
        fp.write("# ξ_RL fit replication — PhD's 2-step protocol\n\n")
        fp.write("## Step 1: Unconstrained Hu fit\n\n")
        fp.write("| system | K2D,max (nm²) | ξ_RL (nm) | n_data |\n")
        fp.write("|---|---:|---:|---:|\n")
        for label, name, _ in SYSTEMS:
            d = fit_results[label]
            fp.write(f"| {name} | {d['k2d_max_unconstrained']:.1f} ± {d['k2d_max_se']:.1f} | "
                     f"{d['xi_rl_unconstrained']:.4f} ± {d['xi_rl_se']:.4f} | {d['n_data']} |\n")

        fp.write("\n## Step 2: Per-#bonds K2D,max (ξ_RL fixed from Step 1)\n\n")
        for label, name, _ in SYSTEMS:
            d = fit_results[label]
            xi_rl = d["xi_rl_unconstrained"]
            fp.write(f"\n### {name} (ξ_RL = {xi_rl:.4f} nm fixed)\n\n")
            fp.write("| #bonds | K2D,max (nm²) | RMSE | n_pts |\n")
            fp.write("|---|---:|---:|---:|\n")
            for b, km, rmse, n in d["per_bond_results"]:
                fp.write(f"| {b} | {km:.1f} | {rmse:.1f} | {n} |\n")
            fp.write(f"\n**Mean across transitions:** {d['k2d_max_per_bond_mean']:.1f} ± {d['k2d_max_per_bond_std']:.1f} nm²\n")

        fp.write("\n## Comparison to PhD's published values\n\n")
        fp.write("| system | ξ_RL fit (ours) | ξ_RL PhD | Δ | "
                 "K2D,max fit (ours, mean) | K2D,max PhD | Δ% |\n")
        fp.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for label, name, _ in SYSTEMS:
            d = fit_results[label]
            phd = PHD_VALUES[label]
            fp.write(f"| {name} | {d['xi_rl_unconstrained']:.4f} | {phd['xi_rl']:.2f} | "
                     f"{abs(d['xi_rl_unconstrained'] - phd['xi_rl']):.4f} | "
                     f"{d['k2d_max_per_bond_mean']:.1f} | {phd['k2d_max']:.0f} | "
                     f"{abs(d['k2d_max_per_bond_mean'] - phd['k2d_max']) / phd['k2d_max'] * 100:.1f}% |\n")

    print(f"\nSaved {out_npz.relative_to(ROOT)} and {out_md.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

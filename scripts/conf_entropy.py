"""Conformational entropy of the protein chain via Schlitter quasi-harmonic.

Reads `results/chain_coords/<sys>/chain_coords.npz`, converts each chain to
33 BAT internal coordinates, and computes the classical-limit Schlitter
entropy for bound and unbound subsets:

    S = (1/2) Σ_i ln(2π e σ_i²)  [in units of k_B]

where σ_i² are eigenvalues of the BAT covariance matrix. The bound–unbound
difference ΔS_conf = S_bound − S_unbound is the per-chain conformational
entropy change on binding, in k_B units (== k_B T units with T = 1.1 ε/k_B,
since temperature is absorbed into the kBT energy scale of the project).

This is a PROTOTYPE estimator. Schlitter assumes Gaussian distributions of
internal coordinates and so:
  * is exact for stiff (rigid) regions (K100);
  * over-estimates conformational entropy when coordinates explore a non-
    Gaussian region (K01, where ecto-bend angles can deviate ∼90° from
    180°). For K01 the kNN (Kraskov / Kozachenko-Leonenko) estimator
    elsewhere should be used as the cross-check.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from bat import bat_coords  # noqa: E402


def schlitter_entropy(coords: np.ndarray) -> tuple[float, np.ndarray]:
    """coords: shape (N_samples, d). Returns (S_kB_units, eigenvalues)."""
    if coords.shape[0] < coords.shape[1] + 2:
        return float("nan"), np.array([])
    C = np.cov(coords, rowvar=False, ddof=1)
    eigvals = np.linalg.eigvalsh(C)
    eigvals = np.clip(eigvals, 1e-30, None)   # avoid log(0)
    log2pi_e = float(np.log(2 * np.pi * np.e))
    S = 0.5 * np.sum(np.log(eigvals) + log2pi_e)
    return float(S), eigvals


def collect_chain_coords(positions: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """positions: (n_frames, n_proteins, 13, 3). mask: (n_frames, n_proteins) bool.
    Returns flattened (M, 33) BAT array over selected (frame, protein) pairs."""
    f_idx, p_idx = np.where(mask)
    chains = positions[f_idx, p_idx, :, :]               # (M, 13, 3)
    return bat_coords(chains)


def run_one_system(npz_path: Path) -> dict:
    d = np.load(npz_path)
    positions_R = d["positions_R"]
    positions_L = d["positions_L"]
    bound_R = d["bound_R"]
    bound_L = d["bound_L"]
    n_frames = int(d["n_frames"])

    # Build the BAT array per (R/L) × (bound/unbound).
    res: dict[str, dict] = {}
    for name, positions, mask in [
        ("R_bound",    positions_R, bound_R),
        ("R_unbound",  positions_R, ~bound_R),
        ("L_bound",    positions_L, bound_L),
        ("L_unbound",  positions_L, ~bound_L),
    ]:
        bat = collect_chain_coords(positions, mask)
        S, eigvals = schlitter_entropy(bat)
        res[name] = {
            "n_samples": int(bat.shape[0]),
            "n_dim":     int(bat.shape[1]),
            "S_kB":      S,
            "log_det":   float(np.sum(np.log(np.clip(eigvals, 1e-30, None)))),
        }

    ds_R = res["R_bound"]["S_kB"] - res["R_unbound"]["S_kB"]
    ds_L = res["L_bound"]["S_kB"] - res["L_unbound"]["S_kB"]

    res["delta"] = {
        "DS_R_kB":         ds_R,
        "DS_L_kB":         ds_L,
        "DS_total_kB":     ds_R + ds_L,
        "TDS_total_kBT_at_T1.1": (ds_R + ds_L),   # numerical k_B*T factor = 1 in reduced units
    }
    res["n_frames"] = n_frames
    return res


def main():
    root = Path(__file__).resolve().parent.parent
    systems = [
        ("15_120x120_K100_EPS05", "rigid"),
        ("15_120x120_K10_EPS05",  "semi"),
        ("22_120x120_K01_EPS05",  "flex"),
    ]
    summary: dict[str, dict] = {}
    print("=== per-system Schlitter conformational entropy ===\n")
    for sys_name, label in systems:
        npz = root / "results" / "chain_coords" / sys_name / "chain_coords.npz"
        r = run_one_system(npz)
        summary[label] = r
        print(f"[{label} / {sys_name}]   n_frames={r['n_frames']}")
        for k in ("R_bound", "R_unbound", "L_bound", "L_unbound"):
            row = r[k]
            print(f"  {k:10s}  n={row['n_samples']:6d}  S(k_B) = {row['S_kB']:+9.3f}")
        print(f"  ΔS_R = {r['delta']['DS_R_kB']:+.3f}  k_B")
        print(f"  ΔS_L = {r['delta']['DS_L_kB']:+.3f}  k_B")
        print(f"  ΔS_total per pair = {r['delta']['DS_total_kB']:+.3f}  k_B")
        print()

    # cross-system differences (-TΔS in kBT units; we report ΔS directly)
    print("=== cross-system comparisons (conformational ΔS only) ===\n")
    print("Target ΔF (kBT):  flex−rigid=3.56, semi−rigid=2.68, semi−flex=0.90")
    print("(positive value = HIGHER K2D, i.e. binding more favourable)\n")
    s_rigid = summary["rigid"]["delta"]["DS_total_kB"]
    s_semi  = summary["semi"]["delta"]["DS_total_kB"]
    s_flex  = summary["flex"]["delta"]["DS_total_kB"]
    print(f"  ΔS_conf  rigid pair  = {s_rigid:+.3f} k_B")
    print(f"  ΔS_conf  semi  pair  = {s_semi:+.3f} k_B")
    print(f"  ΔS_conf  flex  pair  = {s_flex:+.3f} k_B")
    print(f"\n  -T*ΔΔS_conf  flex−rigid = {-(s_flex - s_rigid):+.3f} k_BT")
    print(f"  -T*ΔΔS_conf  semi−rigid = {-(s_semi - s_rigid):+.3f} k_BT")
    print(f"  -T*ΔΔS_conf  semi−flex  = {-(s_semi - s_flex):+.3f} k_BT")

    # write a results file
    out = root / "results" / "conf_entropy_schlitter.md"
    with open(out, "w") as fp:
        fp.write("# Conformational entropy — Schlitter quasi-harmonic on BAT coords\n\n")
        fp.write("Each value is in units of k_B (== k_BT when multiplied by T,\n")
        fp.write("but in our reduced units T = 1.1 ε/k_B, so the k_B value IS the\n")
        fp.write("entropic contribution to free energy in units of k_BT when you\n")
        fp.write("flip the sign of TΔS in ΔF = ΔU − TΔS).\n\n")
        fp.write("## Per-system Schlitter entropies\n\n")
        fp.write("| system | state | n samples | S (k_B) |\n|---|---|---|---|\n")
        for sys_name, label in systems:
            r = summary[label]
            for k in ("R_bound", "R_unbound", "L_bound", "L_unbound"):
                row = r[k]
                fp.write(f"| {sys_name} | {k} | {row['n_samples']} | {row['S_kB']:+.3f} |\n")
        fp.write("\n## Per-pair conformational ΔS = S_bound − S_unbound\n\n")
        fp.write("| system | ΔS_R (k_B) | ΔS_L (k_B) | ΔS_pair (k_B) |\n|---|---|---|---|\n")
        for sys_name, label in systems:
            d = summary[label]["delta"]
            fp.write(f"| {sys_name} | {d['DS_R_kB']:+.3f} | {d['DS_L_kB']:+.3f} "
                     f"| {d['DS_total_kB']:+.3f} |\n")
        fp.write("\n## Cross-system −TΔΔS_conf vs target ΔF (k_BT)\n\n")
        fp.write("| comparison | conformational only (k_BT) | target ΔF (k_BT) |\n"
                 "|---|---|---|\n")
        fp.write(f"| flex − rigid | {-(s_flex - s_rigid):+.3f} | 3.56 |\n")
        fp.write(f"| semi − rigid | {-(s_semi - s_rigid):+.3f} | 2.68 |\n")
        fp.write(f"| semi − flex  | {-(s_semi - s_flex):+.3f} | 0.90 |\n")
        fp.write("\n## Caveats\n\n")
        fp.write("- Schlitter assumes Gaussian per-DOF; valid for K100 stiff bonds\n")
        fp.write("  and angles, less so for K01 where ecto-bend angles routinely\n")
        fp.write("  reach 90° deviations from 180°. Use kNN (Kraskov/KL) for K01\n")
        fp.write("  as a cross-check.\n")
        fp.write("- Only the conformational term is computed. The full decomposition\n")
        fp.write("  per PLAN.md Phase 2 also needs translational, rotational and\n")
        fp.write("  end-volume contributions before comparing to the target ΔF.\n")
        fp.write("- BAT covariance uses ALL 33 DOF jointly (off-diagonal correlations\n")
        fp.write("  retained). Adequate for samples up to a few thousand; we have\n")
        fp.write("  500-20 000 (frame × protein) samples per state, so the covariance\n")
        fp.write("  is well-conditioned.\n")
    print(f"\nSaved {out.relative_to(root)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

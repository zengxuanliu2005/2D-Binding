"""K2D sanity check — does the harmonised bond_state.tsv reproduce published
K2D values?

Published K2D,max (from CLAUDE.md / 2D-binding-MD.pptx):
    rigid (K100) ≈ 12 705 nm²
    semi  (K10)  ≈    875 nm²
    flex  (K01)  ≈    362 nm²

These are the MAXIMUM K2D, achieved at the optimal membrane separation. The
single simulation we have is at one fixed separation, so observed
K2D <= K2D,max, with the master curve

    K2D(ξ⊥) = K2D,max · [1 + (ξ⊥/ξ_RL)²]^(−1/2)

A reasonable sanity check is that the observed K2D ordering matches
(rigid > semi > flex) and the magnitudes are within a factor of ~5 of
K2D,max (the master-curve range over plausible ξ⊥).

Per-frame formula (1:1 binding, but cross-pair bonds allowed):

    K2D[f] = N_bound[f] · A / (N_R_unbound[f] · N_L_unbound[f])

where N_R_unbound = n_R - |{proteins serving as R in any bond}|, similarly
for L. "R" / "L" identified by protein-index parity (even / odd), not by the
bond record's column order.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SYSTEMS = [
    ("15_120x120_K100_EPS05", 15, 15, 12705.0),
    ("15_120x120_K10_EPS05",  15, 15,   875.0),
    ("22_120x120_K01_EPS05",  22, 22,   362.0),
]
LX = LY = 120.0   # σ = nm, from folder name
AREA = LX * LY    # nm²


def k2d_from_bond_state(bond_state_path: Path, n_R: int, n_L: int) -> dict:
    df = pd.read_csv(bond_state_path, sep="\t", comment="#",
                     names=["frame", "p1", "p2", "RB_LB_dist"])
    n_frames = df["frame"].nunique() if len(df) else 0

    # For each frame collect distinct bound R / L proteins.
    per_frame_R_bound: dict[int, set] = {}
    per_frame_L_bound: dict[int, set] = {}
    for f, p1, p2 in df[["frame", "p1", "p2"]].itertuples(index=False):
        per_frame_R_bound.setdefault(f, set())
        per_frame_L_bound.setdefault(f, set())
        # even protein index = receptor, odd = ligand
        (per_frame_R_bound if p1 % 2 == 0 else per_frame_L_bound)[f].add(p1)
        (per_frame_R_bound if p2 % 2 == 0 else per_frame_L_bound)[f].add(p2)

    frames = sorted(set(per_frame_R_bound) | set(per_frame_L_bound))
    n_bound = np.array([
        ((df["frame"] == f).sum()) for f in frames
    ], dtype=float)
    n_R_bound = np.array([len(per_frame_R_bound.get(f, set())) for f in frames], dtype=float)
    n_L_bound = np.array([len(per_frame_L_bound.get(f, set())) for f in frames], dtype=float)
    n_R_free = n_R - n_R_bound
    n_L_free = n_L - n_L_bound

    valid = (n_R_free > 0) & (n_L_free > 0)
    k2d_per_frame = np.zeros_like(n_bound)
    k2d_per_frame[valid] = n_bound[valid] * AREA / (n_R_free[valid] * n_L_free[valid])

    # bootstrap a rough error bar
    rng = np.random.default_rng(0)
    n_boot = 200
    boot_means = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(k2d_per_frame), size=len(k2d_per_frame))
        boot_means.append(np.mean(k2d_per_frame[idx]))
    boot_means = np.array(boot_means)

    return {
        "n_frames": len(frames),
        "mean_n_bound": float(n_bound.mean()),
        "mean_R_free": float(n_R_free.mean()),
        "mean_L_free": float(n_L_free.mean()),
        "k2d_mean": float(k2d_per_frame.mean()),
        "k2d_median": float(np.median(k2d_per_frame)),
        "k2d_se": float(boot_means.std()),
        # also the "ratio of averages" form
        "k2d_ratio": float(n_bound.mean() * AREA /
                           (n_R_free.mean() * n_L_free.mean()))
                     if (n_R_free.mean() > 0 and n_L_free.mean() > 0) else float("nan"),
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    rows = []
    for sys_name, n_R, n_L, k2d_max in SYSTEMS:
        bs = root / "results" / "extracted" / sys_name / "bond_state.tsv"
        if not bs.exists():
            print(f"!! missing {bs}")
            continue
        s = k2d_from_bond_state(bs, n_R, n_L)
        s["system"] = sys_name
        s["K2D_max_published"] = k2d_max
        s["fraction_of_max"] = s["k2d_mean"] / k2d_max
        rows.append(s)

    df = pd.DataFrame(rows)
    print("\n=== K2D sanity check ===\n")
    print(df[[
        "system", "n_frames", "mean_n_bound", "mean_R_free", "mean_L_free",
        "k2d_mean", "k2d_se", "k2d_ratio", "K2D_max_published", "fraction_of_max",
    ]].to_string(index=False))

    out = root / "results" / "k2d_sanity.md"
    with open(out, "w") as fp:
        fp.write("---\n")
        fp.write('purpose: "K2D pipeline sanity checks (units, magnitudes, monotone trends) (auto-generated)"\n')
        fp.write('audience: "Claude diagnostics + reviewer"\n')
        fp.write("status: current\n")
        fp.write("generated_by: scripts/k2d_sanity.py\n")
        fp.write('related: "none"\n')
        fp.write("---\n\n")
        fp.write("# K2D sanity check\n\n")
        fp.write(f"Membrane patch: {LX:.0f}×{LY:.0f} σ² = {AREA:.0f} nm².\n\n")
        fp.write("| system | frames | ⟨N_bound⟩ | ⟨R_free⟩ | ⟨L_free⟩ | "
                 "K2D ⟨per-frame⟩ ± SE (nm²) | K2D ratio-of-avg (nm²) | "
                 "K2D,max (nm²) | observed/max |\n")
        fp.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            fp.write(
                f"| {r['system']} | {r['n_frames']} | {r['mean_n_bound']:.2f} | "
                f"{r['mean_R_free']:.2f} | {r['mean_L_free']:.2f} | "
                f"{r['k2d_mean']:.1f} ± {r['k2d_se']:.1f} | "
                f"{r['k2d_ratio']:.1f} | {r['K2D_max_published']:.0f} | "
                f"{r['fraction_of_max']:.2%} |\n"
            )
        fp.write("\n## Notes\n\n")
        fp.write("- Per-frame `K2D = N_bound · A / (N_R_free · N_L_free)`, "
                 "averaged over frames.\n")
        fp.write("- `K2D ratio-of-avg` uses `⟨N_bound⟩ · A / (⟨R_free⟩·⟨L_free⟩)` — "
                 "differs from per-frame by O(fluctuation²).\n")
        fp.write("- Free R / L counts use protein-index parity (even = R, odd = L), "
                 "consistent with cross-pair binding where the simulator's bond "
                 "record can pair any R with any L.\n")
        fp.write("- Observed K2D < K2D,max is expected — the simulation runs at "
                 "one fixed mean membrane separation, while K2D,max is the value at "
                 "the optimal separation. The master curve "
                 "`K2D = K2D,max · [1 + (ξ⊥/ξ_RL)²]^(-1/2)` connects them.\n")
        fp.write("- **Pass criterion:** ordering rigid > semi > flex preserved, "
                 "magnitudes within a factor ~5 of K2D,max.\n")
    print(f"\nSaved {out.relative_to(root)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

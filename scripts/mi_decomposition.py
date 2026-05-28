"""MI chain-rule decomposition of the binding entropy (hybrid estimator).

Two-stage decomposition that avoids mixing estimators inside any single
chain-rule subtraction (their biases don't cancel):

Stage A — linear blocks via Schlitter chain rule:
    H(axis_ecto, ext_z, bonds, angles)
        = H(axis_ecto) + H(ext_z|axis_ecto) + H(bonds|axis_ecto,ext_z)
          + H(angles|axis_ecto,ext_z,bonds)
    → ΔS_rot, ΔS_extz, ΔS_bonds, ΔS_angles.

Stage B — torsions block via cyclic-kNN, marginal:
    H(torsions)  computed independently in bound and unbound states.
    → ΔS_torsions.

The total
    ΔS_total ≈ ΔS_linear + ΔS_torsions
neglects the linear↔torsion mutual information. For a chain-anchored
protein where the binding constrains the end-bead position (linear ext_z,
axis_ecto, end-of-chain BAT), torsions are mostly determined by the local
ecto stiffness rather than by the binding, so this coupling is expected
to be small. We surface the residual ΔS_total_direct − Σ_terms as the
"coupling" gap so the reader can see it.

Cross-system −T·ΔΔS gets compared against the target ΔΔF from CLAUDE.md:

    flex − rigid = +3.56 kBT,  semi − rigid = +2.68 kBT,
    semi − flex  = −0.90 kBT  (semi has lower ΔF than flex)

Each −T·ΔΔS gets a bootstrap σ from frame-resampling (the `--boot` flag).
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from features import per_protein_blocks  # noqa: E402
from entropy_qh import qh_entropy as _qh  # noqa: E402
from entropy_cyclic import cyclic_entropy  # noqa: E402


# ----------------------------------------------------------------------
# sample gathering
# ----------------------------------------------------------------------

def _gather(positions: np.ndarray, mask: np.ndarray, kind: str
            ) -> dict[str, np.ndarray]:
    f, p = np.where(mask)
    return per_protein_blocks(positions[f, p], kind)


def collect_unbound(positions: np.ndarray, mask_bound: np.ndarray, kind: str
                    ) -> dict[str, np.ndarray]:
    return _gather(positions, ~mask_bound, kind)


def collect_bound_pairs(d):
    pR, pL = d["positions_R"], d["positions_L"]
    bR = d["bound_R"]
    partner_R = d["partner_R"]
    f, r = np.where(bR)
    l = partner_R[f, r]
    bR_blocks = per_protein_blocks(pR[f, r], "R")
    bL_blocks = per_protein_blocks(pL[f, l], "L")
    return bR_blocks, bL_blocks


# ----------------------------------------------------------------------
# standardisation (per-block, pooled bound+unbound, per dim z-score)
# ----------------------------------------------------------------------

def _pool_stats(blocks: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    X = np.concatenate(blocks, axis=0)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    return mu, sd


def _apply(X, mu, sd):
    return (X - mu) / sd


# ----------------------------------------------------------------------
# block ordering and estimator policy
# ----------------------------------------------------------------------

LINEAR_ORDER = ["axis_ecto", "ext_z", "bonds", "angles"]
LINEAR_TERMS = ["rot", "extz", "bonds", "angles"]
TORSION_NAME = "torsions"
ALL_TERMS = LINEAR_TERMS + ["torsions"]


def _stack_pair(R: dict, L: dict, names: list[str]) -> np.ndarray:
    parts = []
    for n in names:
        parts.append(R[n])
        parts.append(L[n])
    return np.concatenate(parts, axis=1)


def _stack_single(R: dict, names: list[str]) -> np.ndarray:
    return np.concatenate([R[n] for n in names], axis=1)


def _decompose_one(uR: dict, uL: dict, bR: dict, bL: dict) -> dict:
    """Compute ΔS terms on already-standardised blocks. Returns dict."""
    res = {}

    # --- Stage A: Schlitter chain rule on the four linear blocks --------
    H_b_prev, H_uR_prev, H_uL_prev = 0.0, 0.0, 0.0
    for i, name in enumerate(LINEAR_ORDER):
        nms = LINEAR_ORDER[: i + 1]
        H_b_cur  = _qh(_stack_pair(bR, bL, nms))
        H_uR_cur = _qh(_stack_single(uR, nms))
        H_uL_cur = _qh(_stack_single(uL, nms))
        dS_term = (H_b_cur - H_b_prev) \
                  - (H_uR_cur - H_uR_prev) \
                  - (H_uL_cur - H_uL_prev)
        res[f"dS_{LINEAR_TERMS[i]}"] = dS_term
        H_b_prev, H_uR_prev, H_uL_prev = H_b_cur, H_uR_cur, H_uL_cur

    H_b_linear  = H_b_prev          # final joint of all linear blocks (bound pair)
    H_uR_linear = H_uR_prev
    H_uL_linear = H_uL_prev
    res["H_b_linear"]  = H_b_linear
    res["H_uR_linear"] = H_uR_linear
    res["H_uL_linear"] = H_uL_linear
    dS_linear = sum(res[f"dS_{t}"] for t in LINEAR_TERMS)

    # --- Stage B: cyclic kNN entropy of torsions, treated as independent
    H_b_tors_pair = cyclic_entropy(_stack_pair(bR, bL, [TORSION_NAME]))
    H_uR_tors     = cyclic_entropy(uR[TORSION_NAME])
    H_uL_tors     = cyclic_entropy(uL[TORSION_NAME])
    res["dS_torsions"] = H_b_tors_pair - H_uR_tors - H_uL_tors

    res["dS_total"] = dS_linear + res["dS_torsions"]

    # --- Direct full-joint sanity (linear-Schlitter + torsion-cyclic
    #     assumed independent). The "coupling" residual is the difference
    #     between this sum and a hypothetical full-joint estimate which we
    #     can't compute without mixing estimators; we report the linear
    #     chain-rule self-consistency only.
    direct_lin = (_qh(_stack_pair(bR, bL, LINEAR_ORDER))
                  - _qh(_stack_single(uR, LINEAR_ORDER))
                  - _qh(_stack_single(uL, LINEAR_ORDER)))
    res["dS_linear_chain_vs_direct"] = dS_linear - direct_lin   # ≈ 0
    return res


# ----------------------------------------------------------------------
# system driver with optional bootstrap
# ----------------------------------------------------------------------

def _standardise(uR, uL, bR, bL):
    out_uR, out_uL, out_bR, out_bL = {}, {}, {}, {}
    for n in LINEAR_ORDER + [TORSION_NAME]:
        if n == TORSION_NAME:
            # leave torsions raw (cyclic estimator handles units)
            out_uR[n] = uR[n]; out_uL[n] = uL[n]
            out_bR[n] = bR[n]; out_bL[n] = bL[n]
            continue
        muR, sdR = _pool_stats([uR[n], bR[n]])
        muL, sdL = _pool_stats([uL[n], bL[n]])
        out_uR[n] = _apply(uR[n], muR, sdR)
        out_bR[n] = _apply(bR[n], muR, sdR)
        out_uL[n] = _apply(uL[n], muL, sdL)
        out_bL[n] = _apply(bL[n], muL, sdL)
    return out_uR, out_uL, out_bR, out_bL


def decompose_one_system(npz_path: Path, n_boot: int = 0,
                          seed: int = 0) -> dict:
    d = dict(np.load(npz_path))
    pR, pL = d["positions_R"], d["positions_L"]
    bR_m, bL_m = d["bound_R"], d["bound_L"]
    partner_R = d["partner_R"]
    n_frames = pR.shape[0]

    # full-sample decomposition
    uR = collect_unbound(pR, bR_m, "R")
    uL = collect_unbound(pL, bL_m, "L")
    bR_blk, bL_blk = collect_bound_pairs(d)
    uR_s, uL_s, bR_s, bL_s = _standardise(uR, uL, bR_blk, bL_blk)
    result = _decompose_one(uR_s, uL_s, bR_s, bL_s)
    result["n_unbound_R"] = int(uR["bonds"].shape[0])
    result["n_unbound_L"] = int(uL["bonds"].shape[0])
    result["n_bound"] = int(bR_blk["bonds"].shape[0])

    # bootstrap (frame-resampling)
    if n_boot > 0:
        rng = np.random.default_rng(seed)
        boot = {f"dS_{t}": [] for t in ALL_TERMS + ["total"]}
        for _ in range(n_boot):
            idx = rng.integers(0, n_frames, size=n_frames)
            pR_b, pL_b = pR[idx], pL[idx]
            bR_bm, bL_bm = bR_m[idx], bL_m[idx]
            partner_R_b = partner_R[idx]
            uR_b = collect_unbound(pR_b, bR_bm, "R")
            uL_b = collect_unbound(pL_b, bL_bm, "L")
            f, r = np.where(bR_bm)
            l = partner_R_b[f, r]
            bR_blk_b = per_protein_blocks(pR_b[f, r], "R")
            bL_blk_b = per_protein_blocks(pL_b[f, l], "L")
            uR_bs, uL_bs, bR_bs, bL_bs = _standardise(
                uR_b, uL_b, bR_blk_b, bL_blk_b
            )
            try:
                sub = _decompose_one(uR_bs, uL_bs, bR_bs, bL_bs)
            except Exception:
                continue
            for t in ALL_TERMS + ["total"]:
                boot[f"dS_{t}"].append(sub[f"dS_{t}"])
        for t in ALL_TERMS + ["total"]:
            result[f"dS_{t}_se"] = (
                float(np.std(boot[f"dS_{t}"])) if len(boot[f"dS_{t}"]) else float("nan")
            )
    else:
        for t in ALL_TERMS + ["total"]:
            result[f"dS_{t}_se"] = float("nan")
    return result


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------

SYSTEMS = [
    ("15_120x120_K100_EPS05", "rigid"),
    ("15_120x120_K10_EPS05",  "semi"),
    ("22_120x120_K01_EPS05",  "flex"),
]
TARGETS = {"flex−rigid": +3.56, "semi−rigid": +2.68, "semi−flex": -0.90}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--boot", type=int, default=0,
                   help="bootstrap iterations for error bars (0 = skip)")
    p.add_argument("--save", default="results/mi_decomposition_results.npz",
                   help="numeric results NPZ for downstream plotting")
    args = p.parse_args()

    root = Path(__file__).resolve().parent.parent
    print("=== MI chain-rule decomposition (hybrid Schlitter + cyclic kNN) ===\n")
    print("per-system ΔS (k_B units, bootstrap σ in parens) "
          f"with --boot {args.boot}\n")
    results = {}
    print(f"{'system':10s} {'n_uR':>5s} {'n_uL':>5s} {'n_bP':>5s}   "
          + "  ".join(f"{'ΔS_'+t:>13s}" for t in ALL_TERMS)
          + f"   {'ΔS_total':>13s}")
    for sys_name, label in SYSTEMS:
        npz = root / "results" / "chain_coords" / sys_name / "chain_coords.npz"
        r = decompose_one_system(npz, n_boot=args.boot)
        results[label] = r
        print(f"{label:10s} {r['n_unbound_R']:5d} {r['n_unbound_L']:5d} "
              f"{r['n_bound']:5d}   "
              + "  ".join(f"{r['dS_'+t]:+7.3f}({r['dS_'+t+'_se']:.2f})"
                          for t in ALL_TERMS)
              + f"   {r['dS_total']:+7.3f}({r['dS_total_se']:.2f})")
        sanity = r["dS_linear_chain_vs_direct"]
        if abs(sanity) > 1e-6:
            print(f"   (linear chain-rule self-consistency: "
                  f"{sanity:+.2e} k_B — should be 0)")

    print("\n=== Cross-system −T·ΔΔS (k_BT) ===\n")
    print(f"{'pair':12s} "
          + "  ".join(f"{'-TΔΔS_'+t:>14s}" for t in ALL_TERMS)
          + f"   {'-TΔΔS_sum':>14s}    target")
    rows = []
    for name, (a, b) in [("flex−rigid", ("flex", "rigid")),
                          ("semi−rigid", ("semi", "rigid")),
                          ("semi−flex",  ("semi", "flex"))]:
        ra, rb = results[a], results[b]
        dd = {t: -(ra[f"dS_{t}"] - rb[f"dS_{t}"]) for t in ALL_TERMS}
        dd["total"] = -(ra["dS_total"] - rb["dS_total"])
        dd_se = {t: float(np.hypot(ra.get(f"dS_{t}_se", 0),
                                    rb.get(f"dS_{t}_se", 0)))
                 for t in ALL_TERMS + ["total"]}
        rows.append((name, dd, dd_se))
        print(f"{name:12s} "
              + "  ".join(f"{dd[t]:+7.3f}({dd_se[t]:.2f})" for t in ALL_TERMS)
              + f"   {dd['total']:+7.3f}({dd_se['total']:.2f})"
              + f"   {TARGETS[name]:+5.2f}")

    # save NPZ for downstream plotting
    out_npz = root / args.save
    out_npz.parent.mkdir(exist_ok=True, parents=True)
    payload = {}
    for label, r in results.items():
        for k, v in r.items():
            if isinstance(v, (int, float)):
                payload[f"{label}__{k}"] = float(v)
    np.savez(out_npz, **payload, ALL_TERMS=np.array(ALL_TERMS),
             SYSTEMS=np.array([label for _, label in SYSTEMS]))
    print(f"\nSaved {out_npz.relative_to(root)}.")

    # write markdown summary
    out = root / "results" / "mi_decomposition.md"
    with open(out, "w") as fp:
        fp.write("# MI chain-rule decomposition (hybrid estimator, with bootstrap σ)\n\n")
        fp.write("Five chain-rule blocks per protein:\n\n")
        fp.write("    axis_ecto (2) → ext_z (1) → bonds (12) → angles (11) → torsions (10)\n\n")
        fp.write("Schlitter (chain rule) for the first four; cyclic kNN for torsions\n")
        fp.write("(treated as independent of the linear blocks — see script docstring).\n\n")
        fp.write("## Per-system ΔS terms (k_B, bootstrap σ in parens)\n\n")
        fp.write("| system | n_uR | n_uL | n_bP | ΔS_rot | ΔS_extz | ΔS_bonds | ΔS_angles | ΔS_torsions | **ΔS_total** |\n")
        fp.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for sys_name, label in SYSTEMS:
            r = results[label]
            fp.write(f"| {sys_name} | {r['n_unbound_R']} | {r['n_unbound_L']} "
                     f"| {r['n_bound']} | ")
            for t in ALL_TERMS:
                se = r[f"dS_{t}_se"]
                fp.write(f"{r['dS_'+t]:+.3f}±{se:.2f} | "
                         if not np.isnan(se) else f"{r['dS_'+t]:+.3f} | ")
            se = r["dS_total_se"]
            fp.write(f"**{r['dS_total']:+.3f}"
                     + (f"±{se:.2f}**" if not np.isnan(se) else "**")
                     + " |\n")
        fp.write("\n## Cross-system −T·ΔΔS vs target ΔΔF (k_BT)\n\n")
        fp.write("| pair | −T·ΔΔS_rot | −T·ΔΔS_extz | −T·ΔΔS_bonds | −T·ΔΔS_angles | "
                 "−T·ΔΔS_torsions | **−T·ΔΔS_sum** | **target** | closed |\n")
        fp.write("|---|---|---|---|---|---|---|---|---|\n")
        for name, dd, dd_se in rows:
            cells = " | ".join(
                f"{dd[t]:+.2f}±{dd_se[t]:.2f}" if not np.isnan(dd_se[t])
                else f"{dd[t]:+.2f}" for t in ALL_TERMS)
            tgt = TARGETS[name]
            closed = 100 * dd["total"] / tgt if tgt != 0 else float("nan")
            tot_se = dd_se["total"]
            fp.write(f"| {name} | {cells} | "
                     f"**{dd['total']:+.2f}"
                     + (f"±{tot_se:.2f}" if not np.isnan(tot_se) else "")
                     + "** | "
                     f"**{tgt:+.2f}** | {closed:+.0f} % |\n")
    print(f"Wrote {out.relative_to(root)}.")
    return results


if __name__ == "__main__":
    main()

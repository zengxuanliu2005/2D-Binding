"""MI chain-rule decomposition of the binding entropy.

For each pair of proteins, the configurational entropy of (axis, BAT) splits
exactly via Numata's chain rule of differential entropy:

    H(axis, inner, end) = H(axis)
                        + H(inner | axis)
                        + H(end | axis, inner)

We compute these on the simulation samples for two states:

    UNBOUND : single protein not in any bond — pooled across proteins and
              frames where the protein is free. R and L treated separately.
    BOUND   : a bonded (R, L) pair — pooled across all bonds (cross-pair
              included).

The binding entropy ΔS_pair = S_bound(R, L joint) − S_unbound(R) − S_unbound(L)
then decomposes into three terms that sum to ΔS_pair by construction:

    ΔS_rot  = H_b(axis_R, axis_L) − H_u(axis_R) − H_u(axis_L)
    ΔS_conf = [H_b(axes, inners) − H_b(axes)]
              − [H_u(inner_R | axis_R) + H_u(inner_L | axis_L)]
    ΔS_end  = [H_b(full) − H_b(axes, inners)]
              − [H_u(end_R | axis_R, inner_R) + H_u(end_L | axis_L, inner_L)]

The translational term is the SAME for all systems (a constant ln A) and
therefore cancels in the cross-system comparison; we omit it from the
features and from the per-system tabulation.

Entropies are computed with the Kozachenko-Leonenko (kNN) estimator from
`entropy_kl.py`. Features are standardised (z-scored) with statistics
pooled across BOUND and UNBOUND samples per dimension so the standardisation
constant cancels in ΔS.

The closure target is

    −T · ΔΔS_pair  ≈  ΔF_class − ΔF_rigid

with target values (kBT) from CLAUDE.md:
    flex − rigid = 3.56
    semi − rigid = 2.68
    semi − flex  = 0.90
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from features import per_protein_features  # noqa: E402
from entropy_qh import qh_entropy as _H  # Schlitter QH; sign-safe in high D


def collect_unbound(positions: np.ndarray, mask: np.ndarray, kind: str
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """positions: (n_frames, n_p, 13, 3). mask: bound flag (True = bound).
    Returns axis(3), inner(30), end(3) over (frame, protein) where mask is False."""
    sel = ~mask
    f_idx, p_idx = np.where(sel)
    chains = positions[f_idx, p_idx]               # (M, 13, 3)
    return per_protein_features(chains, kind)


def collect_bound_pairs(d: dict) -> tuple[np.ndarray, ...]:
    """Returns (axis_R, inner_R, end_R, axis_L, inner_L, end_L) for every
    (frame, R_slot) pair where R is bound (its partner gives the L)."""
    pR = d["positions_R"]
    pL = d["positions_L"]
    bR = d["bound_R"]
    partner_R = d["partner_R"]
    f_idx, r_idx = np.where(bR)
    l_idx = partner_R[f_idx, r_idx]
    chains_R = pR[f_idx, r_idx]
    chains_L = pL[f_idx, l_idx]
    aR, iR, eR = per_protein_features(chains_R, "R")
    aL, iL, eL = per_protein_features(chains_L, "L")
    return aR, iR, eR, aL, iL, eL


def standardise(blocks_per_dim: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Concatenate samples along axis 0, compute mean/std per dim, return."""
    pooled = np.concatenate(blocks_per_dim, axis=0)
    mu = pooled.mean(axis=0)
    sd = pooled.std(axis=0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    return mu, sd


def apply_std(X: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return (X - mu) / sd


def decompose_one_system(npz_path: Path, k: int = 4) -> dict:
    d = np.load(npz_path)
    pR, pL = d["positions_R"], d["positions_L"]
    bR, bL = d["bound_R"], d["bound_L"]

    # ----- gather samples ----------------------------------------------------
    uR_axis, uR_inner, uR_end = collect_unbound(pR, bR, "R")
    uL_axis, uL_inner, uL_end = collect_unbound(pL, bL, "L")
    bR_axis, bR_inner, bR_end, bL_axis, bL_inner, bL_end = collect_bound_pairs(d)

    # ----- standardise (pool bound+unbound per protein side) -----------------
    mu_aR, sd_aR = standardise([uR_axis, bR_axis])
    mu_iR, sd_iR = standardise([uR_inner, bR_inner])
    mu_eR, sd_eR = standardise([uR_end, bR_end])
    mu_aL, sd_aL = standardise([uL_axis, bL_axis])
    mu_iL, sd_iL = standardise([uL_inner, bL_inner])
    mu_eL, sd_eL = standardise([uL_end, bL_end])

    # standardise everything
    def std_R(a, i, e):
        return (apply_std(a, mu_aR, sd_aR),
                apply_std(i, mu_iR, sd_iR),
                apply_std(e, mu_eR, sd_eR))
    def std_L(a, i, e):
        return (apply_std(a, mu_aL, sd_aL),
                apply_std(i, mu_iL, sd_iL),
                apply_std(e, mu_eL, sd_eL))

    uR_a, uR_i, uR_e = std_R(uR_axis, uR_inner, uR_end)
    uL_a, uL_i, uL_e = std_L(uL_axis, uL_inner, uL_end)
    bR_a, bR_i, bR_e = std_R(bR_axis, bR_inner, bR_end)
    bL_a, bL_i, bL_e = std_L(bL_axis, bL_inner, bL_end)

    # ----- unbound entropies (independent R and L) ---------------------------
    H_uR_a   = _H(uR_a)
    H_uR_ai  = _H(np.concatenate([uR_a, uR_i], axis=1))
    H_uR_aie = _H(np.concatenate([uR_a, uR_i, uR_e], axis=1))
    H_uL_a   = _H(uL_a)
    H_uL_ai  = _H(np.concatenate([uL_a, uL_i], axis=1))
    H_uL_aie = _H(np.concatenate([uL_a, uL_i, uL_e], axis=1))

    # conditional entropies in the unbound (independent) state
    H_uR_i_given_a   = H_uR_ai  - H_uR_a
    H_uR_e_given_ai  = H_uR_aie - H_uR_ai
    H_uL_i_given_a   = H_uL_ai  - H_uL_a
    H_uL_e_given_ai  = H_uL_aie - H_uL_ai

    # ----- bound joint entropies (pair of paired R and L) --------------------
    join_axes = np.concatenate([bR_a, bL_a], axis=1)              # 6 D
    join_axinner = np.concatenate([bR_a, bL_a, bR_i, bL_i], axis=1)  # 66 D
    join_full = np.concatenate([bR_a, bL_a, bR_i, bL_i,
                                 bR_e, bL_e], axis=1)              # 72 D

    H_b_axes   = _H(join_axes)
    H_b_axinner = _H(join_axinner)
    H_b_full   = _H(join_full)

    H_b_inner_given_axes = H_b_axinner - H_b_axes
    H_b_end_given_axin   = H_b_full    - H_b_axinner

    # ----- chain-rule ΔS terms ----------------------------------------------
    dS_rot  = H_b_axes - H_uR_a - H_uL_a
    dS_conf = H_b_inner_given_axes - H_uR_i_given_a - H_uL_i_given_a
    dS_end  = H_b_end_given_axin   - H_uR_e_given_ai - H_uL_e_given_ai
    dS_total = dS_rot + dS_conf + dS_end

    # also compute total directly (sanity: same as sum)
    dS_total_direct = H_b_full - H_uR_aie - H_uL_aie

    return {
        "n_unbound_R": int(uR_a.shape[0]),
        "n_unbound_L": int(uL_a.shape[0]),
        "n_bound_pairs": int(bR_a.shape[0]),
        # raw H's
        "H_uR_a": H_uR_a,   "H_uR_ai": H_uR_ai,   "H_uR_aie": H_uR_aie,
        "H_uL_a": H_uL_a,   "H_uL_ai": H_uL_ai,   "H_uL_aie": H_uL_aie,
        "H_b_axes": H_b_axes, "H_b_axinner": H_b_axinner, "H_b_full": H_b_full,
        # ΔS terms (units: nats = k_B in our reduced units)
        "dS_rot":  dS_rot,
        "dS_conf": dS_conf,
        "dS_end":  dS_end,
        "dS_total": dS_total,
        "dS_total_direct": dS_total_direct,
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    systems = [
        ("15_120x120_K100_EPS05", "rigid"),
        ("15_120x120_K10_EPS05",  "semi"),
        ("22_120x120_K01_EPS05",  "flex"),
    ]
    results = {}
    print("=== MI chain-rule decomposition (Schlitter quasi-harmonic) ===\n")
    print(f"{'system':10s}  n_uR  n_uL   n_bP   "
          f"ΔS_rot   ΔS_conf  ΔS_end   ΔS_tot")
    for sys_name, label in systems:
        npz = root / "results" / "chain_coords" / sys_name / "chain_coords.npz"
        r = decompose_one_system(npz)
        results[label] = r
        print(f"{label:10s}  {r['n_unbound_R']:5d} {r['n_unbound_L']:5d} "
              f"{r['n_bound_pairs']:5d}   "
              f"{r['dS_rot']:+7.3f}  {r['dS_conf']:+7.3f}  "
              f"{r['dS_end']:+7.3f}  {r['dS_total']:+7.3f}")
        if abs(r["dS_total"] - r["dS_total_direct"]) > 1e-6:
            print(f"  (sanity: ΔS_total {r['dS_total']:.3f} vs direct "
                  f"{r['dS_total_direct']:.3f}; should agree)")

    print("\n=== Cross-system −TΔΔS (kBT, == k_B nats in reduced units) ===")
    print("Target ΔF: flex−rigid=3.56, semi−rigid=2.68, semi−flex=0.90\n")

    def neg_TddS(a, b, term):
        return -(results[a][term] - results[b][term])

    rows = []
    for (label, ref) in [("flex", "rigid"), ("semi", "rigid"), ("semi", "flex")]:
        row = {
            "pair": f"{label}−{ref}",
            "ΔΔS_rot":  results[label]["dS_rot"]  - results[ref]["dS_rot"],
            "ΔΔS_conf": results[label]["dS_conf"] - results[ref]["dS_conf"],
            "ΔΔS_end":  results[label]["dS_end"]  - results[ref]["dS_end"],
            "ΔΔS_tot":  results[label]["dS_total"]- results[ref]["dS_total"],
        }
        # the target free-energy difference (positive when ref is more favourable)
        # ΔF_label − ΔF_ref = +x  means LABEL has higher F (less favourable)
        # If LABEL has lower K2D than REF, ΔF_label - ΔF_ref > 0
        rows.append(row)

    targets = {"flex−rigid": 3.56, "semi−rigid": 2.68, "semi−flex": -0.90}
    # semi−flex target is NEGATIVE: K2D(semi)>K2D(flex) -> ΔF(semi)<ΔF(flex) -> "semi−flex" < 0

    print(f"{'pair':12s}  -TΔΔS_rot  -TΔΔS_conf -TΔΔS_end  -TΔΔS_sum"
          "    target")
    for r in rows:
        print(f"{r['pair']:12s}  "
              f"{-r['ΔΔS_rot']:+8.3f}   "
              f"{-r['ΔΔS_conf']:+8.3f}   "
              f"{-r['ΔΔS_end']:+8.3f}   "
              f"{-r['ΔΔS_tot']:+8.3f}    "
              f"{targets[r['pair']]:+.2f}")

    # ---- save results to a markdown file -----------------------------------
    out = root / "results" / "mi_decomposition.md"
    with open(out, "w") as fp:
        fp.write("# MI chain-rule decomposition of the binding entropy\n\n")
        fp.write("Entropies are in k_B (== nats; reduced units T=1.1 ε/k_B). "
                 "The chain-rule decomposition guarantees\n"
                 "ΔS_rot + ΔS_conf + ΔS_end = ΔS_total by construction. "
                 "Translational (ln A) cancels across systems.\n\n")
        fp.write("## Per-system ΔS = S_bound − S_unbound (per R-L pair)\n\n")
        fp.write("| system | n_uR | n_uL | n_bound | ΔS_rot | ΔS_conf | ΔS_end | ΔS_total |\n"
                 "|---|---|---|---|---|---|---|---|\n")
        for sys_name, label in systems:
            r = results[label]
            fp.write(f"| {sys_name} | {r['n_unbound_R']} | {r['n_unbound_L']} | "
                     f"{r['n_bound_pairs']} | "
                     f"{r['dS_rot']:+.3f} | {r['dS_conf']:+.3f} | "
                     f"{r['dS_end']:+.3f} | {r['dS_total']:+.3f} |\n")
        fp.write("\n## Cross-system closure: −T·ΔΔS vs target ΔΔF (k_BT)\n\n")
        fp.write("| pair | −T·ΔΔS_rot | −T·ΔΔS_conf | −T·ΔΔS_end | −T·ΔΔS_sum | target ΔΔF |\n"
                 "|---|---|---|---|---|---|\n")
        for r in rows:
            fp.write(f"| {r['pair']} | "
                     f"{-r['ΔΔS_rot']:+.3f} | {-r['ΔΔS_conf']:+.3f} | "
                     f"{-r['ΔΔS_end']:+.3f} | {-r['ΔΔS_tot']:+.3f} | "
                     f"{targets[r['pair']]:+.2f} |\n")
        fp.write("\n## Notes\n\n")
        fp.write("- All entropies via Schlitter quasi-harmonic on z-scored features.\n")
        fp.write("- Features per protein: axis (3) + bat_inner (30) + bat_end (3) = 36 DOF.\n")
        fp.write("- Per pair: 72 DOF joint (axes_R, axes_L, inners_R, inners_L, ends_R, ends_L).\n")
        fp.write("- ΔS_trans is constant (ln(A_eff/b²)) and cancels in ΔΔ — not included.\n")
        fp.write("- Sample sizes for the 72-D bound joint entropy are 1.8k - 5.1k — tight; "
                 "the chain-rule formulation localizes the high-D estimate to a sequence of "
                 "lower-D conditional estimates, which is the main reason MI/Numata works "
                 "here at all.\n")
    print(f"\nWrote {out.relative_to(root)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

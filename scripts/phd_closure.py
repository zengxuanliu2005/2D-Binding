"""Assemble the PhD's S1-S23 ΔF decomposition into a closure attempt.

For each system, compute the four terms F_t, F_c, F_bond, F_rot at the
per-pair level using inputs from `phd_inputs.py` and formulas from
`phd_formula.py`. Then for each of the three pair comparisons
(flex−rigid, semi−rigid, semi−flex) compute ΔΔF_term and ΔΔF_sum, and
compare against the target ΔΔF from CLAUDE.md.

Per-pair convention (matches PhD's S6-S7 algebra and her per-system
numbers on page S3):

    F_t_pair    = F_trans (S2/S6, applied once per pair from S7's
                  ΔF = (D/Re)² − ln(σb²) − 1 derivation;
                  effectively cancels across systems if σ is the same)
    F_c_pair    = F_conf (single-chain D and Re; per-pair as PhD uses it)
    F_bond_pair = F_bond (S17 with n_b dropped — geometric capture only)
    F_rot_pair  = F_rot  (S22-S23 ratio)
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from phd_inputs import load_all, AREA, B, R_MAX  # noqa: E402
from phd_formula import F_trans, F_conf, F_bond, F_rot  # noqa: E402

TARGETS = {"flex−rigid": +3.56, "semi−rigid": +2.68, "semi−flex": -0.90}
LABELS = ("rigid", "semi", "flex")


def regime_for(label: str) -> str:
    return "2D" if label == "rigid" else "3D"


def per_system_terms(inputs, n_bins_marg: int = 16,
                      n_bins_joint: int = 6) -> dict[str, dict]:
    """Compute the four ΔF terms per system, per pair (k_B T)."""
    out = {}
    for label in LABELS:
        i = inputs[label]
        # F_t: per protein, applied once per pair from S7 algebra
        # (ΔF includes -ln σb² + 1 = -F_trans).
        F_t_R = F_trans(i.n_R, AREA, B)
        F_t_L = F_trans(i.n_L, AREA, B)
        # use R density as the per-pair σ (R and L densities equal by symmetry)
        Ft_pair = F_t_R
        # F_c: PhD applies S4 once per pair with single-chain D and Re.
        Fc_chain = F_conf(i.D_bound, i.R_e_free)
        Fc_pair = Fc_chain
        # F_bond: geometric capture only — n_b dropped.
        Fb_pair = F_bond(B, AREA, i.L, regime_for(label))
        # F_rot: histograms on S² / S²×S²
        rot = F_rot(
            i.axes_R_unbound, i.axes_L_unbound,
            i.axes_R_bound,   i.axes_L_bound,
            n_bins_marg=n_bins_marg, n_bins_joint=n_bins_joint,
        )
        out[label] = {
            "F_trans_per_protein_R": F_t_R,
            "F_trans_per_protein_L": F_t_L,
            "F_trans_pair":          Ft_pair,
            "F_conf_per_chain":      Fc_chain,
            "F_conf_pair":           Fc_pair,
            "F_bond_pair":           Fb_pair,
            "F_rot_pair":            rot["F_rot"],
            "omega_R":               rot["omega_R"],
            "omega_L":               rot["omega_L"],
            "omega_RL":              rot["omega_RL"],
            "omega_ratio":           rot["ratio"],
            "regime":                regime_for(label),
        }
    return out


def cross_pair_table(per_sys: dict) -> list[dict]:
    """Compute ΔΔF for each pair comparison and per term."""
    rows = []
    pair_specs = [("flex−rigid", "flex", "rigid"),
                  ("semi−rigid", "semi", "rigid"),
                  ("semi−flex",  "semi", "flex")]
    for name, a, b in pair_specs:
        sa, sb = per_sys[a], per_sys[b]
        ddF_t    = sa["F_trans_pair"] - sb["F_trans_pair"]
        ddF_c    = sa["F_conf_pair"]  - sb["F_conf_pair"]
        ddF_bond = sa["F_bond_pair"]  - sb["F_bond_pair"]
        ddF_rot  = sa["F_rot_pair"]   - sb["F_rot_pair"]
        ddF_sum  = ddF_t + ddF_c + ddF_bond + ddF_rot
        tgt = TARGETS[name]
        rows.append({
            "pair":     name,
            "ddF_t":    ddF_t,
            "ddF_c":    ddF_c,
            "ddF_bond": ddF_bond,
            "ddF_rot":  ddF_rot,
            "ddF_sum":  ddF_sum,
            "target":   tgt,
            "gap":      ddF_sum - tgt,
            "closed":   100.0 * ddF_sum / tgt if tgt != 0 else float("nan"),
        })
    return rows


def main():
    inputs = load_all()
    per_sys = per_system_terms(inputs)

    # ---- per-system table ----
    print("=== Per-system inputs and four-term decomposition (k_B T) ===\n")
    print(f"{'label':6s}  {'regime':6s}  {'n_b':>6s}  {'R_e':>6s}  {'D':>6s}  "
          f"{'L':>6s}  {'F_t':>8s}  {'F_c':>8s}  {'F_bond':>8s}  {'F_rot':>8s}  "
          f"{'ω_ratio':>8s}")
    for label in LABELS:
        i = inputs[label]; s = per_sys[label]
        print(f"{label:6s}  {s['regime']:6s}  {i.n_b_per_frame:6.2f}  "
              f"{i.R_e_free:6.3f}  {i.D_bound:6.3f}  {i.L:6.3f}  "
              f"{s['F_trans_pair']:+8.3f}  {s['F_conf_pair']:+8.3f}  "
              f"{s['F_bond_pair']:+8.3f}  {s['F_rot_pair']:+8.3f}  "
              f"{s['omega_ratio']:8.3f}")

    # ---- cross-system closure ----
    rows = cross_pair_table(per_sys)
    print("\n=== Cross-system ΔΔF (k_B T) ===\n")
    print(f"{'pair':12s}  {'ΔΔF_t':>9s}  {'ΔΔF_c':>9s}  {'ΔΔF_bond':>9s}  "
          f"{'ΔΔF_rot':>9s}  {'ΔΔF_sum':>9s}  {'target':>7s}  "
          f"{'gap':>7s}  {'closed':>7s}")
    for r in rows:
        print(f"{r['pair']:12s}  {r['ddF_t']:+9.3f}  {r['ddF_c']:+9.3f}  "
              f"{r['ddF_bond']:+9.3f}  {r['ddF_rot']:+9.3f}  "
              f"{r['ddF_sum']:+9.3f}  {r['target']:+7.2f}  "
              f"{r['gap']:+7.3f}  {r['closed']:+6.0f}%")

    # ---- save npz + markdown ----
    root = Path(__file__).resolve().parent.parent
    out_npz = root / "results" / "phd_closure.npz"
    payload = {}
    for label in LABELS:
        for k, v in per_sys[label].items():
            if isinstance(v, (int, float)):
                payload[f"{label}__{k}"] = float(v)
        payload[f"{label}__n_b"] = inputs[label].n_b_per_frame
        payload[f"{label}__R_e"] = inputs[label].R_e_free
        payload[f"{label}__D"]   = inputs[label].D_bound
        payload[f"{label}__L"]   = inputs[label].L
    payload["pair_names"]    = np.array([r["pair"]    for r in rows])
    payload["pair_ddF_t"]    = np.array([r["ddF_t"]   for r in rows])
    payload["pair_ddF_c"]    = np.array([r["ddF_c"]   for r in rows])
    payload["pair_ddF_bond"] = np.array([r["ddF_bond"] for r in rows])
    payload["pair_ddF_rot"]  = np.array([r["ddF_rot"]  for r in rows])
    payload["pair_ddF_sum"]  = np.array([r["ddF_sum"]  for r in rows])
    payload["pair_target"]   = np.array([r["target"]   for r in rows])
    np.savez(out_npz, **payload)
    print(f"\nSaved {out_npz.relative_to(root)}.")

    # `phd_closure.md` is a curated write-up — don't auto-overwrite it.
    # The latest numeric tables go into `phd_closure_data.md` for diffing
    # against the curated narrative.
    out_md = root / "results" / "phd_closure_data.md"
    with open(out_md, "w") as fp:
        fp.write("# ΔΔF closure via the PhD's S1-S23 framework\n\n")
        fp.write("Each pair value is per R-L pair, in k_B T.\n\n")
        fp.write("## Per-system inputs\n\n")
        fp.write(f"`R_max = {R_MAX} σ`, `b = {B} σ`, `A = {AREA} σ²`.\n\n")
        fp.write("| label | regime | n_b/frame | R_e (σ) | D (σ) | L (σ) |\n"
                 "|---|---|---|---|---|---|\n")
        for label in LABELS:
            i = inputs[label]; s = per_sys[label]
            fp.write(f"| {label} | {s['regime']} | {i.n_b_per_frame:.2f} "
                     f"| {i.R_e_free:.3f} | {i.D_bound:.3f} | {i.L:.3f} |\n")
        fp.write("\n## Per-system four-term decomposition (k_B T per pair)\n\n")
        fp.write("| label | F_t | F_c | F_bond | F_rot | ω_RL/(ω_R·ω_L) |\n"
                 "|---|---|---|---|---|---|\n")
        for label in LABELS:
            s = per_sys[label]
            fp.write(f"| {label} | {s['F_trans_pair']:+.3f} | "
                     f"{s['F_conf_pair']:+.3f} | {s['F_bond_pair']:+.3f} | "
                     f"{s['F_rot_pair']:+.3f} | {s['omega_ratio']:.3f} |\n")
        fp.write("\n## Cross-system closure (k_B T)\n\n")
        fp.write("| pair | ΔΔF_t | ΔΔF_c | ΔΔF_bond | ΔΔF_rot | ΔΔF_sum | "
                 "target | gap | closed |\n|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            fp.write(f"| {r['pair']} | {r['ddF_t']:+.3f} | {r['ddF_c']:+.3f} "
                     f"| {r['ddF_bond']:+.3f} | {r['ddF_rot']:+.3f} | "
                     f"**{r['ddF_sum']:+.3f}** | **{r['target']:+.2f}** | "
                     f"{r['gap']:+.3f} | {r['closed']:+.0f}% |\n")
        fp.write("\n## Notes\n\n")
        fp.write("- F_t is per-protein from S1; pair contribution = 2 · F_t.\n")
        fp.write("- F_c is per chain from S4 with the 1.5 prefactor; pair = 2 · F_c.\n")
        fp.write("- F_bond is per pair from S17 (with the +1 constant absorbed); "
                 "regime 2D for rigid, 3D for semi/flex per S18-S19.\n")
        fp.write("- F_rot is per pair from S22-S23, computed by histogram "
                 "differential entropy on S² for ω_R, ω_L and S²×S² for ω_RL "
                 "(NOT Schlitter on the in-plane disk — that's the wrong manifold).\n")
    print(f"Wrote {out_md.relative_to(root)}.")
    return rows


if __name__ == "__main__":
    main()

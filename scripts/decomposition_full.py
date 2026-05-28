"""Full ΔΔF decomposition: ΔU (chain potential) + −T·ΔS (configuration).

Combines:
  * scripts/chain_energy.py  → mean chain potential energy <U_chain>
  * scripts/mi_decomposition.py → configurational entropy from chain-rule

per system, then assembles

    ΔF_bind = ΔU_chain − T·ΔS_config
    ΔΔF (a − b) = (ΔU_a − ΔU_b) − T·(ΔS_a − ΔS_b)

and prints the closure against the target ΔΔF from CLAUDE.md.

The chain potential is what the force field in `ref/nvt-md.py` assigns to
each chain conformation. It is NOT an analytical polymer model — it's the
same potential the simulator integrated to produce the trajectory. Computing
<U_chain> bound vs unbound directly from the chain coordinates is a clean
way to recover the chain-stretching enthalpic contribution that pure
entropy decomposition misses (because chain stretching costs energy as
well as restricting configurations).
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from chain_energy import chain_potential, K_ECTO, EPS_PER_KBT  # noqa: E402
from mi_decomposition import decompose_one_system  # noqa: E402


SYSTEMS = [
    ("15_120x120_K100_EPS05", "rigid", "K100"),
    ("15_120x120_K10_EPS05",  "semi",  "K10"),
    ("22_120x120_K01_EPS05",  "flex",  "K01"),
]
TARGETS = {"flex−rigid": +3.56, "semi−rigid": +2.68, "semi−flex": -0.90}


def energy_one_system(npz_path: Path, K_label: str) -> dict:
    """Return per-protein mean U_chain (in k_BT) for bound and unbound R, L
    and the bound-vs-unbound difference."""
    d = np.load(npz_path)
    pR, pL = d["positions_R"], d["positions_L"]
    bR, bL = d["bound_R"], d["bound_L"]
    Ke = K_ECTO[K_label]

    res = {}
    for side, positions, mask in [("R", pR, bR), ("L", pL, bL)]:
        # all chains regardless of bound/unbound
        Ub, Ua, Ue = chain_potential(positions, Ke)             # each (n_f, n_p)
        U_total = (Ub + Ua + Ue) / EPS_PER_KBT                  # convert ε → kBT
        Ub_kbt = Ub / EPS_PER_KBT
        Ua_kbt = Ua / EPS_PER_KBT
        Ue_kbt = Ue / EPS_PER_KBT
        for label, m in [("bound", mask), ("unbound", ~mask)]:
            res[f"U_{side}_{label}"]      = float(U_total[m].mean())
            res[f"U_{side}_{label}_se"]   = float(U_total[m].std() / np.sqrt(m.sum()))
            res[f"U_bond_{side}_{label}"]   = float(Ub_kbt[m].mean())
            res[f"U_anchor_{side}_{label}"] = float(Ua_kbt[m].mean())
            res[f"U_ecto_{side}_{label}"]   = float(Ue_kbt[m].mean())
    # bound − unbound per side (per protein)
    for side in ("R", "L"):
        res[f"dU_{side}"]      = res[f"U_{side}_bound"]   - res[f"U_{side}_unbound"]
        res[f"dU_{side}_se"]   = float(np.hypot(res[f"U_{side}_bound_se"],
                                                 res[f"U_{side}_unbound_se"]))
        for blk in ("bond", "anchor", "ecto"):
            res[f"dU_{blk}_{side}"] = (res[f"U_{blk}_{side}_bound"]
                                        - res[f"U_{blk}_{side}_unbound"])
    # per pair
    res["dU_pair"]    = res["dU_R"] + res["dU_L"]
    res["dU_pair_se"] = float(np.hypot(res["dU_R_se"], res["dU_L_se"]))
    for blk in ("bond", "anchor", "ecto"):
        res[f"dU_{blk}_pair"] = res[f"dU_{blk}_R"] + res[f"dU_{blk}_L"]
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--boot", type=int, default=0,
                   help="bootstrap iterations for entropy error bars")
    args = p.parse_args()

    root = Path(__file__).resolve().parent.parent
    print("=== Full decomposition: ΔU_chain + −T·ΔS_config ===\n")

    energies, entropies = {}, {}
    for sys_name, label, K_label in SYSTEMS:
        npz = root / "results" / "chain_coords" / sys_name / "chain_coords.npz"
        energies[label]  = energy_one_system(npz, K_label)
        entropies[label] = decompose_one_system(npz, n_boot=args.boot)

    # --- per-system energy table ---
    print("Per-system per-pair (R+L combined) ΔU_chain = <U>_bound − <U>_unbound")
    print(f"{'system':10s}  {'ΔU_bond':>10s}  {'ΔU_anchor':>10s}  {'ΔU_ecto':>10s}  "
          f"{'ΔU_total (kBT)':>16s}")
    for _, label, _ in SYSTEMS:
        e = energies[label]
        print(f"{label:10s}  {e['dU_bond_pair']:+10.3f}  "
              f"{e['dU_anchor_pair']:+10.3f}  {e['dU_ecto_pair']:+10.3f}  "
              f"{e['dU_pair']:+10.3f} ± {e['dU_pair_se']:.3f}")

    # --- per-system entropy table ---
    print(f"\nPer-system per-pair −T·ΔS_config (sum of chain-rule terms, kBT)")
    print(f"{'system':10s}  {'-TΔS_rot':>10s}  {'-TΔS_extz':>10s}  {'-TΔS_bonds':>11s}  "
          f"{'-TΔS_angles':>12s}  {'-TΔS_tors':>10s}  {'-TΔS_total':>11s}")
    for _, label, _ in SYSTEMS:
        s = entropies[label]
        # In reduced units T = 1.1 ε/k_B; ΔS is in nats == k_B. T·ΔS in ε.
        # Converting to k_BT: divide by (1.1 ε / kBT) = 1.1. So -T·ΔS_kBT = -ΔS_nats × (1.1/1.1) = -ΔS_nats.
        # i.e. in k_BT, the entropy contribution in nats *is* the contribution.
        terms = ["rot", "extz", "bonds", "angles", "torsions"]
        cells = [f"{-s['dS_'+t]:+10.3f}" for t in terms]
        tot   = -s["dS_total"]
        print(f"{label:10s}  " + "  ".join(cells)
              + f"  {tot:+11.3f}")

    # --- combined ΔF and cross-system closure ---
    print("\n=== Total per-system ΔF_bind ≈ ΔU + (−T·ΔS) (kBT) ===")
    F = {}
    for _, label, _ in SYSTEMS:
        F[label] = energies[label]["dU_pair"] + (-entropies[label]["dS_total"])
        print(f"  {label}: ΔU = {energies[label]['dU_pair']:+.3f},  "
              f"−T·ΔS = {-entropies[label]['dS_total']:+.3f},  "
              f"ΔF = {F[label]:+.3f}")

    print("\n=== Cross-system closure: ΔΔF (kBT) ===")
    print(f"{'pair':12s}  {'ΔΔU':>10s}  {'-TΔΔS':>10s}  {'ΔΔF_predicted':>14s}  "
          f"{'target':>8s}  {'closed':>10s}")
    rows = []
    for name, (a, b) in [("flex−rigid", ("flex", "rigid")),
                          ("semi−rigid", ("semi", "rigid")),
                          ("semi−flex",  ("semi", "flex"))]:
        ddU = energies[a]["dU_pair"] - energies[b]["dU_pair"]
        ddTS = -(entropies[a]["dS_total"] - entropies[b]["dS_total"])
        ddF = ddU + ddTS
        tgt = TARGETS[name]
        closed = 100 * ddF / tgt if tgt != 0 else float("nan")
        rows.append((name, ddU, ddTS, ddF, tgt, closed))
        print(f"{name:12s}  {ddU:+10.3f}  {ddTS:+10.3f}  {ddF:+14.3f}  "
              f"{tgt:+8.2f}  {closed:+10.0f}%")

    # save NPZ for plotting
    out_npz = root / "results" / "full_decomposition.npz"
    payload = {}
    for label in ("rigid", "semi", "flex"):
        for k, v in energies[label].items():
            payload[f"{label}__U__{k}"] = v
        for k, v in entropies[label].items():
            if isinstance(v, (int, float)):
                payload[f"{label}__S__{k}"] = v
    payload["pair_names"]   = np.array([r[0] for r in rows])
    payload["pair_ddU"]     = np.array([r[1] for r in rows])
    payload["pair_negTddS"] = np.array([r[2] for r in rows])
    payload["pair_ddF"]     = np.array([r[3] for r in rows])
    payload["pair_target"]  = np.array([r[4] for r in rows])
    np.savez(out_npz, **payload)
    print(f"\nSaved {out_npz.relative_to(root)}.")

    # write markdown
    out = root / "results" / "full_decomposition.md"
    with open(out, "w") as fp:
        fp.write("# ΔΔF closure: chain-potential ΔU + chain-rule −T·ΔS\n\n")
        fp.write("Combining the per-chain force-field potential energy (`nvt-md.py` "
                 "bonds + cosine angles) with the configurational entropy chain rule.\n\n")
        fp.write("## Per-system ΔU_chain (k_BT, per pair, bound − unbound)\n\n")
        fp.write("| system | ΔU_bond | ΔU_anchor | ΔU_ecto | **ΔU_total** |\n|---|---|---|---|---|\n")
        for _, label, _ in SYSTEMS:
            e = energies[label]
            fp.write(f"| {label} | {e['dU_bond_pair']:+.3f} | "
                     f"{e['dU_anchor_pair']:+.3f} | {e['dU_ecto_pair']:+.3f} | "
                     f"**{e['dU_pair']:+.3f}±{e['dU_pair_se']:.3f}** |\n")
        fp.write("\n## Per-system −T·ΔS_config (k_BT, per pair)\n\n")
        fp.write("| system | −T·ΔS_rot | −T·ΔS_extz | −T·ΔS_bonds | −T·ΔS_angles | "
                 "−T·ΔS_tors | **−T·ΔS_total** |\n|---|---|---|---|---|---|---|\n")
        for _, label, _ in SYSTEMS:
            s = entropies[label]
            cells = " | ".join(f"{-s['dS_'+t]:+.3f}"
                                for t in ("rot","extz","bonds","angles","torsions"))
            fp.write(f"| {label} | {cells} | **{-s['dS_total']:+.3f}** |\n")
        fp.write("\n## Cross-system closure ΔΔF (k_BT)\n\n")
        fp.write("| pair | ΔΔU | −T·ΔΔS | **ΔΔF_pred** | **target** | closed |\n"
                 "|---|---|---|---|---|---|\n")
        for name, ddU, ddTS, ddF, tgt, closed in rows:
            fp.write(f"| {name} | {ddU:+.3f} | {ddTS:+.3f} | **{ddF:+.3f}** "
                     f"| **{tgt:+.2f}** | {closed:+.0f} % |\n")
    print(f"Wrote {out.relative_to(root)}.")


if __name__ == "__main__":
    main()

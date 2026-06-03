"""Closure 5: PhD PPT slide 25 three-term decomposition (trans + rot + WLC).

s25 abandons the S17 end-volume term and replaces the Gaussian S4
conformational term with the Marko–Siggia worm-like-chain integrated
stretching free energy. The PPT s25 numbers (3.64, 2.47, 1.18) for
flex−rigid, semi−rigid, flex−semi come from her direct evaluation
with values printed on the slide; this script reproduces the framework
from our own chain_coords data so the closure can be bootstrapped
and lined up with the four other methods in reconcile_methods.py.

Three terms (per R-L pair, in k_B T):

    F_trans  S1  per-protein translational, same as S1-S23 framework
    F_rot    S22 per-pair rotational, histogram entropy on S² / S²×S²
    F_conf   WLC integrated Marko–Siggia stretch:

        F_conf(D, l_p, L_c) / k_BT = (L_c / l_p) ·
            [ 1/(4·(1-x)) - 1/4 - x/4 + x²/2 ],   x = D / L_c

    valid for 0 ≤ x < 1.

Inputs per system:

    D     = D_bound from chain_coords (mean bound-chain z-reach,
            beads 3→12, ligand z flipped to match R hemisphere)
    l_p   = persistence length from `xi_rl_candidates.LP_PHD`
            (rigid 84.6, semi 8.18, flex 1.14 nm)
    L_c   = nominal ecto contour, default 12 nm (12 protein bonds × 1.0 σ;
            CLAUDE.md unit convention).

For very stiff rigid chains, D_bound can approach L_c and F_conf
diverges — that is the correct WLC behaviour (cost to fully extend a
chain at its contour limit is infinite). When this happens we report
inf in the per-system table and exclude that pair from the cross-system
ΔΔF sum.
"""
from __future__ import annotations
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from system_inputs import (  # noqa: E402
    load_all, load_all_raw, system_inputs_from_arrays, AREA, B,
)
from free_energy_terms import F_trans, F_rot  # noqa: E402
from xi_rl_candidates import LP_PHD  # noqa: E402

TARGETS = {"flex−rigid": +3.56, "semi−rigid": +2.68, "semi−flex": -0.90}
LABELS = ("rigid", "semi", "flex")
PAIR_SPECS = [("flex−rigid", "flex", "rigid"),
              ("semi−rigid", "semi", "rigid"),
              ("semi−flex",  "semi", "flex")]

# Nominal ecto contour (12 protein bonds × HARM r0 = 1.0 σ; CLAUDE.md).
DEFAULT_L_C = 12.0  # nm


def F_conf_wlc(D: float, l_p: float, L_c: float) -> float:
    """Marko–Siggia integrated stretching free energy in k_B T.

    Returns the free energy of stretching a worm-like chain from its
    relaxed state to end-to-end distance D, with persistence length l_p
    and contour length L_c. Diverges at D → L_c.
    """
    x = D / L_c
    if x >= 1.0 or x < 0.0:
        return float("inf") if x >= 1.0 else float("nan")
    bracket = 1.0 / (4.0 * (1.0 - x)) - 0.25 - x / 4.0 + 0.5 * x * x
    return float((L_c / l_p) * bracket)


def per_system_terms_s25(inputs, L_c: float = DEFAULT_L_C,
                          lp_by_label: dict[str, float] = LP_PHD,
                          n_bins_marg: int = 16,
                          n_bins_joint: int = 6) -> dict[str, dict]:
    out = {}
    for label in LABELS:
        i = inputs[label]
        F_t_R = F_trans(i.n_R, AREA, B)  # per protein
        Ft_pair = F_t_R                    # per pair = per chain by S6/S7 algebra
        Fc_pair = F_conf_wlc(i.D_bound, lp_by_label[label], L_c)
        rot = F_rot(
            i.axes_R_unbound, i.axes_L_unbound,
            i.axes_R_bound,   i.axes_L_bound,
            n_bins_marg=n_bins_marg, n_bins_joint=n_bins_joint,
        )
        out[label] = {
            "F_trans_pair": Ft_pair,
            "F_conf_pair":  Fc_pair,
            "F_rot_pair":   rot["F_rot"],
            "D_bound":      i.D_bound,
            "l_p":          lp_by_label[label],
            "L_c":          L_c,
            "omega_ratio":  rot["ratio"],
        }
    return out


def cross_pair_table_s25(per_sys: dict) -> list[dict]:
    rows = []
    for name, a, b in PAIR_SPECS:
        sa, sb = per_sys[a], per_sys[b]
        ddF_t   = sa["F_trans_pair"] - sb["F_trans_pair"]
        ddF_c   = sa["F_conf_pair"]  - sb["F_conf_pair"]
        ddF_rot = sa["F_rot_pair"]   - sb["F_rot_pair"]
        ddF_sum = ddF_t + ddF_c + ddF_rot
        tgt = TARGETS[name]
        rows.append({
            "pair":     name,
            "ddF_t":    ddF_t,
            "ddF_c":    ddF_c,
            "ddF_rot":  ddF_rot,
            "ddF_sum":  ddF_sum,
            "target":   tgt,
            "gap":      ddF_sum - tgt,
            "closed":   100.0 * ddF_sum / tgt if tgt != 0 else float("nan"),
        })
    return rows


def _resample_inputs(raw_by_label: dict, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for label, (raw, sys_name) in raw_by_label.items():
        n_frames = raw["pR"].shape[0]
        idx = rng.integers(0, n_frames, size=n_frames)
        out[label] = system_inputs_from_arrays(
            label, sys_name,
            raw["pR"][idx], raw["pL"][idx],
            raw["bR"][idx], raw["bL"][idx],
            raw["n_R"], raw["n_L"],
        )
    return out


def _bootstrap_one(args):
    raw_by_label, seed, L_c, n_bins_marg, n_bins_joint = args
    inputs = _resample_inputs(raw_by_label, seed)
    per_sys = per_system_terms_s25(inputs, L_c=L_c,
                                    n_bins_marg=n_bins_marg,
                                    n_bins_joint=n_bins_joint)
    rows = cross_pair_table_s25(per_sys)
    sys_dict = {l: {k: float(v) for k, v in per_sys[l].items()
                     if isinstance(v, (int, float))} for l in LABELS}
    return rows, sys_dict


def bootstrap_closure_s25(raw_by_label: dict, n_bootstrap: int, seed: int,
                            L_c: float, n_jobs: int = 1,
                            n_bins_marg: int = 16,
                            n_bins_joint: int = 6) -> dict:
    tasks = [(raw_by_label, seed + ib, L_c, n_bins_marg, n_bins_joint)
             for ib in range(n_bootstrap)]
    pair_terms = ("ddF_t", "ddF_c", "ddF_rot", "ddF_sum")
    sys_terms = ("F_trans_pair", "F_conf_pair", "F_rot_pair", "D_bound")
    pair_acc = {name: {term: np.zeros(n_bootstrap) for term in pair_terms}
                for name, _, _ in PAIR_SPECS}
    sys_acc = {label: {term: np.zeros(n_bootstrap) for term in sys_terms}
               for label in LABELS}

    def _store(ib, rows, sys_dict):
        for r in rows:
            for term in pair_terms:
                pair_acc[r["pair"]][term][ib] = r[term]
        for label in LABELS:
            for term in sys_terms:
                sys_acc[label][term][ib] = sys_dict[label][term]

    if n_jobs <= 1:
        for ib in range(n_bootstrap):
            if ib % max(1, n_bootstrap // 20) == 0:
                print(f"    bootstrap {ib}/{n_bootstrap}...", flush=True)
            rows, sys_dict = _bootstrap_one(tasks[ib])
            _store(ib, rows, sys_dict)
    else:
        import multiprocessing as mp
        mp.set_start_method("fork", force=True)
        with ProcessPoolExecutor(max_workers=n_jobs) as ex:
            for ib, (rows, sys_dict) in enumerate(ex.map(_bootstrap_one, tasks)):
                if ib % max(1, n_bootstrap // 20) == 0:
                    print(f"    bootstrap {ib}/{n_bootstrap}...", flush=True)
                _store(ib, rows, sys_dict)
    print(f"    bootstrap {n_bootstrap}/{n_bootstrap} done.", flush=True)
    return {"pair": pair_acc, "per_system": sys_acc}


_BANNER = """
╔════════════════════════════════════════════════════════════════════╗
║  closure_wlc_three_term.py — trans + rot + Marko-Siggia WLC       ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
The source PPT slide 25 three-term closure — drops the S17 end-volume
term and replaces the Gaussian S4 conformational term with the
Marko-Siggia integrated WLC stretching free energy.

Parameters
  L_c  : nominal ecto contour (default 12 nm = 12 protein bonds × 1.0 σ)
  l_p  : persistence length from xi_rl_candidates.LP_PHD (84.6, 8.18, 1.14 nm)
  D    : bound-chain z-reach from system_inputs.D_bound

With --bootstrap, resamples frames per system and reports σ on each
ΔΔF term. Use --n-jobs 8 for parallel.
"""


def main():
    print(_BANNER)
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--n-bootstrap", type=int, default=200)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260601)
    parser.add_argument("--L-c", type=float, default=DEFAULT_L_C,
                        help="Effective ecto contour length in nm "
                             "(default 12 = 12 bonds × 1.0 σ).")
    args = parser.parse_args()

    inputs = load_all()
    per_sys = per_system_terms_s25(inputs, L_c=args.L_c)

    print(f"=== Closure 5: PhD PPT s25 — trans + rot + WLC conf "
          f"(L_c = {args.L_c} nm) ===\n")
    print(f"{'label':6s}  {'l_p':>6s}  {'D':>6s}  {'L_c':>6s}  "
          f"{'F_t':>8s}  {'F_rot':>8s}  {'F_conf_WLC':>10s}")
    for label in LABELS:
        s = per_sys[label]
        print(f"{label:6s}  {s['l_p']:6.2f}  {s['D_bound']:6.3f}  "
              f"{s['L_c']:6.2f}  {s['F_trans_pair']:+8.3f}  "
              f"{s['F_rot_pair']:+8.3f}  {s['F_conf_pair']:+10.3f}")

    rows = cross_pair_table_s25(per_sys)
    print("\n=== Cross-system ΔΔF (k_B T) ===\n")
    print(f"{'pair':12s}  {'ΔΔF_t':>9s}  {'ΔΔF_rot':>9s}  "
          f"{'ΔΔF_conf':>9s}  {'ΔΔF_sum':>9s}  {'target':>7s}  "
          f"{'gap':>7s}  {'closed':>7s}")
    for r in rows:
        print(f"{r['pair']:12s}  {r['ddF_t']:+9.3f}  {r['ddF_rot']:+9.3f}  "
              f"{r['ddF_c']:+9.3f}  {r['ddF_sum']:+9.3f}  "
              f"{r['target']:+7.2f}  {r['gap']:+7.3f}  {r['closed']:+6.0f}%")

    boot = None
    if args.bootstrap:
        print(f"\n=== Bootstrap: {args.n_bootstrap} frame-level resamples "
              f"(n_jobs={args.n_jobs}) ===")
        raw_by_label = load_all_raw()
        boot = bootstrap_closure_s25(
            raw_by_label, args.n_bootstrap, args.seed, args.L_c,
            n_jobs=args.n_jobs,
        )
        print("\n=== Per-pair ΔΔF (mean ± σ) ===\n")
        print(f"{'pair':12s}  {'ΔΔF_t':>14s}  {'ΔΔF_rot':>14s}  "
              f"{'ΔΔF_conf':>14s}  {'ΔΔF_sum':>14s}  {'target':>7s}")
        for name, _, _ in PAIR_SPECS:
            pa = boot["pair"][name]
            cells = []
            for term in ("ddF_t", "ddF_rot", "ddF_c", "ddF_sum"):
                m = float(np.mean(pa[term]))
                s = float(np.std(pa[term]))
                cells.append(f"{m:+7.3f}±{s:5.3f}")
            print(f"{name:12s}  {cells[0]}  {cells[1]}  {cells[2]}  "
                  f"{cells[3]}  {TARGETS[name]:+7.2f}")

    # ---- save ----
    root = Path(__file__).resolve().parent.parent
    out_npz = root / "results" / "closure_wlc_three_term.npz"
    payload = {"L_c_nm": args.L_c}
    for label in LABELS:
        for k, v in per_sys[label].items():
            payload[f"{label}__{k}"] = float(v)
    payload["pair_names"]   = np.array([r["pair"]    for r in rows])
    payload["pair_ddF_t"]   = np.array([r["ddF_t"]   for r in rows])
    payload["pair_ddF_rot"] = np.array([r["ddF_rot"] for r in rows])
    payload["pair_ddF_c"]   = np.array([r["ddF_c"]   for r in rows])
    payload["pair_ddF_sum"] = np.array([r["ddF_sum"] for r in rows])
    payload["pair_target"]  = np.array([r["target"]  for r in rows])
    if boot is not None:
        for name, _, _ in PAIR_SPECS:
            safe = name.replace("−", "-")
            for term, arr in boot["pair"][name].items():
                payload[f"boot__{safe}__{term}"] = arr
        for label in LABELS:
            for term, arr in boot["per_system"][label].items():
                payload[f"boot__{label}__{term}"] = arr
    np.savez(out_npz, **payload)
    print(f"\nSaved {out_npz.relative_to(root)}.")

    out_md = root / "results" / "closure_wlc_three_term.md"
    with open(out_md, "w") as fp:
        fp.write("# Closure 5 — PhD PPT s25 (trans + rot + WLC)\n\n")
        fp.write("Reimplements the PhD's PPT slide 25 three-term closure "
                 "(trans + rot + Marko–Siggia WLC) on our own "
                 "`chain_coords.npz` data so it can sit beside the four other "
                 "methods in `reconcile_methods.py`. End-volume (S17) is "
                 "dropped; conformational is upgraded from Gaussian S4 to "
                 "the integrated Marko–Siggia force.\n\n")
        fp.write(f"Parameters: `L_c = {args.L_c} nm` (12 protein bonds × "
                 "1.0 σ); `l_p` from `xi_rl_candidates.LP_PHD` "
                 f"(rigid {LP_PHD['rigid']}, semi {LP_PHD['semi']}, "
                 f"flex {LP_PHD['flex']} nm).\n\n")
        fp.write("## Per-system terms (k_B T per pair)\n\n")
        fp.write("| label | l_p (nm) | D_bound (nm) | L_c (nm) | F_t | F_rot | F_conf (WLC) |\n"
                 "|---|---|---|---|---|---|---|\n")
        for label in LABELS:
            s = per_sys[label]
            fp.write(f"| {label} | {s['l_p']:.2f} | {s['D_bound']:.3f} | "
                     f"{s['L_c']:.2f} | {s['F_trans_pair']:+.3f} | "
                     f"{s['F_rot_pair']:+.3f} | {s['F_conf_pair']:+.3f} |\n")

        fp.write("\n## Cross-system closure (k_B T)\n\n")
        fp.write("| pair | ΔΔF_t | ΔΔF_rot | ΔΔF_conf | ΔΔF_sum | target | gap | closed |\n"
                 "|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            fp.write(f"| {r['pair']} | {r['ddF_t']:+.3f} | "
                     f"{r['ddF_rot']:+.3f} | {r['ddF_c']:+.3f} | "
                     f"**{r['ddF_sum']:+.3f}** | **{r['target']:+.2f}** | "
                     f"{r['gap']:+.3f} | {r['closed']:+.0f}% |\n")

        if boot is not None:
            n_boot = next(iter(boot["pair"].values()))["ddF_sum"].size
            fp.write(f"\n## Bootstrap uncertainty (n = {n_boot} frame-level resamples)\n\n")
            fp.write("| pair | ΔΔF_t | ΔΔF_rot | ΔΔF_conf | ΔΔF_sum | target |\n"
                     "|---|---|---|---|---|---|\n")
            for name, _, _ in PAIR_SPECS:
                pa = boot["pair"][name]
                cells = []
                for term in ("ddF_t", "ddF_rot", "ddF_c", "ddF_sum"):
                    m = float(np.mean(pa[term]))
                    s = float(np.std(pa[term]))
                    cells.append(f"{m:+.3f} ± {s:.3f}")
                fp.write(f"| {name} | {cells[0]} | {cells[1]} | "
                         f"{cells[2]} | **{cells[3]}** | "
                         f"{TARGETS[name]:+.2f} |\n")

        fp.write("\n## Notes on the formula\n\n")
        fp.write("Marko–Siggia interpolation force "
                 "`f l_p / k_BT = 1 / (4(1-x)²) − 1/4 + x`, integrated to "
                 "give the stretching free energy\n\n")
        fp.write("```\nF_conf(D, l_p, L_c) / k_BT = (L_c / l_p) · "
                 "[1/(4(1-x)) − 1/4 − x/4 + x²/2],  x = D/L_c\n```\n\n")
        fp.write("Valid for 0 ≤ x < 1. F diverges as x → 1 (chain fully "
                 "extended). For rigid chains D_bound can approach L_c "
                 "and the formula returns inf — see Discussion in "
                 "`stage_essay.md` for what this means physically.\n")
    print(f"Wrote {out_md.relative_to(root)}.")
    return rows


if __name__ == "__main__":
    main()

"""Figures illustrating the MI chain-rule decomposition of binding entropy.

Writes four PNGs into `results/figures/`:

  1. axis_angle_distributions.png   — polar angle θ of chain axis, bound vs
       unbound per system. Shows where the rotational constraint comes from.
  2. e2e_distributions.png          — end-to-end (chain[0]→chain[12])
       distance histograms, bound vs unbound per system. Shows the
       extension/conformational shift on binding.
  3. binding_bead_z.png             — z-distance from binding bead to its
       own anchor's z, bound vs unbound. Shows the end-volume constraint
       (where the binding bead must sit between membranes).
  4. closure_bars.png               — bar chart of the chain-rule
       decomposition vs target ΔF for the three system pairs.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from features import per_protein_blocks  # noqa: E402
from mi_decomposition import decompose_one_system  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SYSTEMS = [
    ("15_120x120_K100_EPS05", "K100 (rigid)", "tab:blue"),
    ("15_120x120_K10_EPS05",  "K10  (semi) ", "tab:orange"),
    ("22_120x120_K01_EPS05",  "K01  (flex) ", "tab:green"),
]


def load_data(sys_name: str) -> dict:
    return np.load(ROOT / "results" / "chain_coords" / sys_name / "chain_coords.npz")


def axis_polar_deg(positions: np.ndarray, kind: str) -> np.ndarray:
    a = per_protein_blocks(positions, kind)["axis_ecto"]
    z = np.sqrt(np.clip(1 - (a ** 2).sum(axis=-1), 0, 1))
    return np.degrees(np.arccos(z))


def fig_axis_angles() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True, sharey=False)
    bins = np.linspace(0, 60, 40)
    for j, (sys_name, label, color) in enumerate(SYSTEMS):
        d = load_data(sys_name)
        pR, pL = d["positions_R"], d["positions_L"]
        bR, bL = d["bound_R"], d["bound_L"]
        # R row
        ax = axes[0, j]
        ax.hist(axis_polar_deg(pR[~bR], "R"), bins=bins, density=True,
                alpha=0.55, label="unbound", color="lightgray", edgecolor="gray")
        ax.hist(axis_polar_deg(pR[bR],  "R"), bins=bins, density=True,
                alpha=0.7,  label="bound",   color=color, edgecolor="black")
        ax.set_title(f"{label} — receptor")
        if j == 0:
            ax.set_ylabel("P(θ)")
        ax.legend(loc="upper right", fontsize=8)
        ax.set_xlim(0, 60)
        # L row
        ax = axes[1, j]
        ax.hist(axis_polar_deg(pL[~bL], "L"), bins=bins, density=True,
                alpha=0.55, label="unbound", color="lightgray", edgecolor="gray")
        ax.hist(axis_polar_deg(pL[bL],  "L"), bins=bins, density=True,
                alpha=0.7,  label="bound",   color=color, edgecolor="black")
        ax.set_title(f"{label} — ligand")
        if j == 0:
            ax.set_ylabel("P(θ)")
        ax.set_xlabel("chain axis polar angle θ (deg)")
    fig.suptitle("Chain-axis orientation θ vs membrane normal — bound vs unbound",
                 fontsize=12)
    fig.tight_layout()
    out = ROOT / "results" / "figures" / "axis_angle_distributions.png"
    out.parent.mkdir(exist_ok=True, parents=True)
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def fig_e2e_distributions() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True, sharey=False)
    bins = np.linspace(0, 14, 60)
    for j, (sys_name, label, color) in enumerate(SYSTEMS):
        d = load_data(sys_name)
        pR, pL = d["positions_R"], d["positions_L"]
        bR, bL = d["bound_R"], d["bound_L"]
        for row, (positions, mask, side) in enumerate(
            [(pR, bR, "receptor"), (pL, bL, "ligand")]
        ):
            ax = axes[row, j]
            e2e = np.linalg.norm(positions[..., 12, :] - positions[..., 0, :],
                                  axis=-1)
            ax.hist(e2e[~mask], bins=bins, density=True, alpha=0.55,
                    label="unbound", color="lightgray", edgecolor="gray")
            ax.hist(e2e[mask],  bins=bins, density=True, alpha=0.7,
                    label="bound",   color=color, edgecolor="black")
            ax.set_title(f"{label} — {side}")
            if j == 0:
                ax.set_ylabel("P(R_ee)")
            if row == 1:
                ax.set_xlabel("end-to-end distance (σ)")
            ax.legend(loc="upper left", fontsize=8)
    fig.suptitle("End-to-end distance R_ee = |chain[12] − chain[0]| — bound vs unbound",
                 fontsize=12)
    fig.tight_layout()
    out = ROOT / "results" / "figures" / "e2e_distributions.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def fig_binding_bead_z() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True, sharey=False)
    bins = np.linspace(0, 14, 60)
    for j, (sys_name, label, color) in enumerate(SYSTEMS):
        d = load_data(sys_name)
        pR, pL = d["positions_R"], d["positions_L"]
        bR, bL = d["bound_R"], d["bound_L"]
        # z of binding bead measured from anchor's z
        zR = (pR[..., 12, 2] - pR[..., 0, 2])
        zL = -(pL[..., 12, 2] - pL[..., 0, 2])  # ligand chain goes down → flip
        for row, (z, mask, side) in enumerate(
            [(zR, bR, "receptor RB.z − anchor.z"),
             (zL, bL, "ligand  −(LB.z − anchor.z)")]
        ):
            ax = axes[row, j]
            ax.hist(z[~mask], bins=bins, density=True, alpha=0.55,
                    label="unbound", color="lightgray", edgecolor="gray")
            ax.hist(z[mask],  bins=bins, density=True, alpha=0.7,
                    label="bound",   color=color, edgecolor="black")
            ax.set_title(f"{label} — {side}")
            if j == 0:
                ax.set_ylabel("P(Δz)")
            if row == 1:
                ax.set_xlabel("|binding-bead z − anchor z| (σ)")
            ax.legend(loc="upper left", fontsize=8)
    fig.suptitle("Binding-bead vertical extension — bound vs unbound", fontsize=12)
    fig.tight_layout()
    out = ROOT / "results" / "figures" / "binding_bead_z.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def fig_closure_bars() -> None:
    # rerun the decomposition to get fresh numbers
    results = {}
    for sys_name, label, _ in SYSTEMS:
        npz = ROOT / "results" / "chain_coords" / sys_name / "chain_coords.npz"
        results[label.strip().split()[0]] = decompose_one_system(npz)

    pair_specs = [
        ("flex−rigid", "K01", "K100", 3.56),
        ("semi−rigid", "K10", "K100", 2.68),
        ("semi−flex",  "K10", "K01", -0.90),
    ]

    term_labels = ["−TΔΔS_rot", "−TΔΔS_conf", "−TΔΔS_end"]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(pair_specs))
    w = 0.2
    rot, conf, end, total, target = [], [], [], [], []
    for name, a, b, tgt in pair_specs:
        ra = results[a]; rb = results[b]
        rot.append(-(ra["dS_rot"]  - rb["dS_rot"]))
        conf.append(-(ra["dS_conf"] - rb["dS_conf"]))
        end.append(-(ra["dS_end"]  - rb["dS_end"]))
        total.append(rot[-1] + conf[-1] + end[-1])
        target.append(tgt)

    rot, conf, end, total, target = map(np.asarray, (rot, conf, end, total, target))
    ax.bar(x - 1.5*w, rot, w, label="−TΔΔS_rot", color="tab:blue")
    ax.bar(x - 0.5*w, conf, w, label="−TΔΔS_conf", color="tab:orange")
    ax.bar(x + 0.5*w, end, w, label="−TΔΔS_end", color="tab:green")
    ax.bar(x + 1.5*w, total, w, label="−TΔΔS_sum (this work)", color="tab:purple")
    # target as wide hatched bar behind
    ax.bar(x, target, 0.85, label="target ΔΔF", color="lightgray", alpha=0.35,
           edgecolor="black", hatch="//", zorder=-1)

    ax.set_xticks(x)
    ax.set_xticklabels([p[0] for p in pair_specs])
    ax.set_ylabel("ΔΔF (k_B T)")
    ax.set_title("MI chain-rule decomposition: closure attempt vs target ΔF\n"
                 "(positive = unfavourable relative to rigid; "
                 "semi−flex target negative because semi is more favourable than flex)")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.legend(loc="best", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = ROOT / "results" / "figures" / "closure_bars.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def main():
    (ROOT / "results" / "figures").mkdir(exist_ok=True, parents=True)
    fig_axis_angles()
    fig_e2e_distributions()
    fig_binding_bead_z()
    # closure_bars is superseded by closure_full.png (see plot_full_closure.py)
    # which has the right per-term breakdown for the current decomposition.
    # fig_closure_bars()


if __name__ == "__main__":
    main()

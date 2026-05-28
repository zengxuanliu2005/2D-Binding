"""Closure bar chart showing ΔU_chain + −T·ΔS_config vs target ΔΔF.

Reads `results/full_decomposition.npz` (produced by
`scripts/decomposition_full.py`) and plots the per-pair ΔΔF prediction
broken into the chain-potential and entropy contributions, with the
target ΔΔF shown as a transparent reference bar.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def main():
    root = Path(__file__).resolve().parent.parent
    d = np.load(root / "results" / "full_decomposition.npz", allow_pickle=True)
    pairs   = list(d["pair_names"])
    ddU     = d["pair_ddU"]
    ddTS    = d["pair_negTddS"]
    ddF     = d["pair_ddF"]
    target  = d["pair_target"]

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(pairs))
    w = 0.2
    ax.bar(x - 1.5 * w, ddU,   w, label="ΔΔU_chain",       color="tab:red")
    ax.bar(x - 0.5 * w, ddTS,  w, label="−T·ΔΔS_config",   color="tab:blue")
    ax.bar(x + 0.5 * w, ddF,   w, label="ΔΔF_pred = ΔΔU − T·ΔΔS",
           color="tab:purple")
    ax.bar(x + 0.0,      target, 0.85, label="target ΔΔF",
           color="lightgray", alpha=0.30, edgecolor="black", hatch="//",
           zorder=-1)
    ax.set_xticks(x)
    ax.set_xticklabels(pairs)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("ΔΔF (k_B T)")
    ax.set_title("Closure attempt: chain potential + chain-rule entropy vs target ΔΔF")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    out = root / "results" / "figures" / "closure_full.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"wrote {out.relative_to(root)}")

    # Companion: per-system ΔU breakdown (bond / anchor / ecto)
    rigid_b = float(d["rigid__U__dU_bond_pair"]); rigid_a = float(d["rigid__U__dU_anchor_pair"]); rigid_e = float(d["rigid__U__dU_ecto_pair"])
    semi_b  = float(d["semi__U__dU_bond_pair"]);  semi_a  = float(d["semi__U__dU_anchor_pair"]);  semi_e  = float(d["semi__U__dU_ecto_pair"])
    flex_b  = float(d["flex__U__dU_bond_pair"]);  flex_a  = float(d["flex__U__dU_anchor_pair"]);  flex_e  = float(d["flex__U__dU_ecto_pair"])

    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = ["rigid", "semi", "flex"]
    bond_vals   = [rigid_b, semi_b, flex_b]
    anchor_vals = [rigid_a, semi_a, flex_a]
    ecto_vals   = [rigid_e, semi_e, flex_e]
    x = np.arange(len(labels))
    w = 0.25
    ax.bar(x - w, bond_vals,   w, label="bonds",  color="tab:blue")
    ax.bar(x,     anchor_vals, w, label="anchor angles", color="tab:orange")
    ax.bar(x + w, ecto_vals,   w, label="ecto angles", color="tab:green")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("ΔU per pair (k_B T)")
    ax.set_title("Chain potential energy change on binding\n"
                 "(bound minus unbound, per R-L pair)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    out2 = root / "results" / "figures" / "energy_breakdown.png"
    fig.savefig(out2, dpi=130)
    plt.close(fig)
    print(f"wrote {out2.relative_to(root)}")


if __name__ == "__main__":
    main()

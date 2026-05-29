"""Bar chart of the four-term PhD ΔΔF decomposition vs target ΔΔF."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def main():
    root = Path(__file__).resolve().parent.parent
    d = np.load(root / "results" / "phd_closure.npz", allow_pickle=True)
    pairs = list(d["pair_names"])
    ddF_t    = d["pair_ddF_t"]
    ddF_c    = d["pair_ddF_c"]
    ddF_bond = d["pair_ddF_bond"]
    ddF_rot  = d["pair_ddF_rot"]
    ddF_sum  = d["pair_ddF_sum"]
    target   = d["pair_target"]

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(pairs))
    w = 0.15
    ax.bar(x - 2 * w, ddF_t,    w, label="ΔΔF_t (translational)",
           color="tab:gray")
    ax.bar(x - 1 * w, ddF_c,    w, label="ΔΔF_c (conformational, S4)",
           color="tab:red")
    ax.bar(x + 0 * w, ddF_bond, w, label="ΔΔF_bond (end-volume, S17-S19)",
           color="tab:green")
    ax.bar(x + 1 * w, ddF_rot,  w, label="ΔΔF_rot (rotational, S22-S23)",
           color="tab:blue")
    ax.bar(x + 2 * w, ddF_sum,  w, label="ΔΔF_pred (this work)",
           color="tab:purple")
    # target as wide hatched bar behind
    ax.bar(x, target, 0.95, label="target ΔΔF",
           color="lightgray", alpha=0.30, edgecolor="black", hatch="//",
           zorder=-1)
    ax.set_xticks(x)
    ax.set_xticklabels(pairs)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("ΔΔF (k_B T)")
    ax.set_title("PhD's S1–S23 four-term decomposition vs target ΔΔF\n"
                 "(semi−rigid closes to 100 %; flex−rigid and semi−flex within "
                 "~0.4 k_BT of target)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    out = root / "results" / "figures" / "closure_phd.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"wrote {out.relative_to(root)}")


if __name__ == "__main__":
    main()

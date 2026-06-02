"""Plot K2D(ξ⊥) prediction overlaid on the off-site slab simulation data."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent

SYSTEMS = [
    ("rigid", "K100 (rigid)", "a"),
    ("semi", "K10 (semi)", "b"),
    ("flex", "K01 (flex)", "c"),
]

COLORS = {"rigid": "#1f77b4", "semi": "#ff7f0e", "flex": "#2ca02c"}


def hu_curve(xi, k2d_max, xi_rl):
    return k2d_max / np.sqrt(1.0 + (xi / xi_rl) ** 2)


def main():
    data = np.load(ROOT / "results" / "k2d_xi_curves.npz", allow_pickle=True)
    xi = data["xi_perp"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)

    for ax, (label, name, panel) in zip(axes, SYSTEMS):
        color = COLORS[label]
        k2d_xi_shape = data[f"{label}__k2d_xi"]
        A_ours = float(data[f"{label}__fit_A_ours"])
        k2d_max_hu = float(data[f"{label}__fit_k2d_max_hu"])
        xi_rl_hu = float(data[f"{label}__fit_xi_rl_hu"])
        rmse_rel_ours = float(data[f"{label}__fit_rmse_rel_ours"]) * 100
        rmse_rel_hu = float(data[f"{label}__fit_rmse_rel_hu"]) * 100
        r2_ours = float(data[f"{label}__fit_r2_ours"])
        r2_hu = float(data[f"{label}__fit_r2_hu"])
        xi_data = data[f"{label}__data_xi"]
        k2d_data = data[f"{label}__data_k2d"]

        # absolute curves in nm²
        k2d_curve_ours = A_ours * k2d_xi_shape
        k2d_curve_hu = hu_curve(xi, k2d_max_hu, xi_rl_hu)
        k2d_max_ours = A_ours * k2d_xi_shape[0]

        # data points
        data_label = "K=1 data (different stiffness)" if label == "flex" else "slab data"
        ax.scatter(xi_data, k2d_data, marker="o", s=35, facecolors="none",
                   edgecolors="k", linewidths=1.2, label=data_label, zorder=3)

        # curves
        ax.plot(xi, k2d_curve_ours, "-", color=color, linewidth=2.0,
                label=f"ours (1 param)\nK₂D,max={k2d_max_ours:.0f}\nRMSE={rmse_rel_ours:.1f}% R²={r2_ours:.3f}")
        ax.plot(xi, k2d_curve_hu, "--", color="0.3", linewidth=1.5,
                label=f"Hu (2 params)\nK₂D,max={k2d_max_hu:.0f} ξ_RL={xi_rl_hu:.2f}\nRMSE={rmse_rel_hu:.1f}% R²={r2_hu:.3f}")

        ax.set_xlabel("ξ⊥ (σ = nm)", fontsize=11)
        ax.set_ylabel("K₂D (nm²)", fontsize=11)
        ax.set_title(f"({panel}) {name}", fontsize=12)
        ax.legend(fontsize=8, loc="upper right")
        ax.set_xlim(0, 3.0)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "K₂D(ξ⊥): convolution of measured K₂D(l) vs Hu master curve, against slab data",
        fontsize=13, y=1.02,
    )

    out_dir = ROOT / "results" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / "k2d_xi_prediction.png"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    print(f"Saved {out_png.relative_to(ROOT)}")
    plt.close(fig)


if __name__ == "__main__":
    main()

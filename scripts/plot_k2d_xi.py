"""Plot K2D(ξ⊥) prediction — 3-panel comparison against Gaussian benchmark."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


ROOT = Path(__file__).resolve().parent.parent

SYSTEMS = [
    ("rigid", "K100 (rigid)", "a"),
    ("semi", "K10 (semi)", "b"),
    ("flex", "K01 (flex)", "c"),
]

COLORS = {"rigid": "#1f77b4", "semi": "#ff7f0e", "flex": "#2ca02c"}


def main():
    data = np.load(ROOT / "results" / "k2d_xi_curves.npz", allow_pickle=True)
    xi = data["xi_perp"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)

    for ax, (label, name, panel) in zip(axes, SYSTEMS):
        conv = data[f"{label}__k2d_xi_norm"]
        hu = data[f"{label}__k2d_hu_norm"]
        color = COLORS[label]

        ax.plot(xi, conv, "-", color=color, linewidth=2.0, label="conv(K₂D_eff, P)")
        ax.plot(xi, hu, "--", color="0.3", linewidth=1.5, label="Gaussian benchmark")

        # shade the deviation
        ax.fill_between(xi, conv, hu, alpha=0.12, color=color)

        ax.set_xlabel("ξ⊥ (σ = nm)", fontsize=11)
        ax.set_ylabel("K₂D(ξ⊥) / K₂D(0)", fontsize=11)
        ax.set_title(f"({panel}) {name}", fontsize=12)
        ax.legend(fontsize=9, loc="upper right")
        ax.set_xlim(0, 3.0)
        ax.set_ylim(0, 1.05)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "K₂D(ξ⊥) from Weikl 2016 Eq. (1) — measured K₂D(l) vs Gaussian benchmark",
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

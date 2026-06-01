"""PPT-style story figures for the raw tether partition K2D prototype."""
from __future__ import annotations

import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-2d-binding")

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.path import Path as MplPath


ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "results" / "figures"

COLORS = {
    "rigid": "#2b7bba",
    "semi": "#f28e2b",
    "flex": "#2ca25f",
    "old": "#9467bd",
    "new": "#1f9e89",
    "target": "#d9d9d9",
    "ink": "#202020",
    "muted": "#666666",
    "membrane": "#d8e7f2",
    "capture": "#ffdf80",
}

PAIR_LABELS = ["flex-rigid", "semi-rigid", "semi-flex"]
TARGET = np.array([3.56, 2.68, -0.90])


def setup_figure(figsize=(13.2, 7.2)):
    fig = plt.figure(figsize=figsize, facecolor="white")
    return fig


def add_arrow(ax, start, end, color="#333333", lw=2.0, mutation_scale=16):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=lw,
            mutation_scale=mutation_scale,
            shrinkA=0,
            shrinkB=0,
        ),
    )


def bezier(ax, points, color, lw=4.0, alpha=1.0, zorder=4):
    codes = [MplPath.MOVETO] + [MplPath.CURVE4] * (len(points) - 1)
    path = MplPath(points, codes)
    patch = patches.PathPatch(
        path, facecolor="none", edgecolor=color, lw=lw,
        alpha=alpha, capstyle="round", joinstyle="round", zorder=zorder
    )
    ax.add_patch(patch)


def labeled_box(ax, xy, w, h, title, body=None, fc="#ffffff", ec="#444444",
                title_size=13, body_size=10, lw=1.4):
    box = patches.FancyBboxPatch(
        xy, w, h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=fc, edgecolor=ec, linewidth=lw,
    )
    ax.add_patch(box)
    ax.text(xy[0] + w * 0.05, xy[1] + h * 0.68, title,
            fontsize=title_size, fontweight="bold", color=COLORS["ink"],
            va="center")
    if body:
        ax.text(xy[0] + w * 0.05, xy[1] + h * 0.36, body,
                fontsize=body_size, color=COLORS["muted"], va="center",
                linespacing=1.25)
    return box


def membrane(ax, y, label, orientation="bottom"):
    ax.add_patch(patches.Rectangle((0.06, y - 0.025), 0.88, 0.05,
                                   facecolor=COLORS["membrane"],
                                   edgecolor="#7aa6c2", linewidth=1.1))
    for x in np.linspace(0.08, 0.92, 22):
        ax.add_patch(patches.Circle((x, y + 0.022), 0.012,
                                    facecolor="#f6fbff",
                                    edgecolor="#7aa6c2", linewidth=0.5))
    ax.text(0.06, y + (0.065 if orientation == "bottom" else -0.075),
            label, fontsize=12, color=COLORS["muted"], va="center")


def draw_tether(ax, anchor, end, color, label, curve=0.12, lw=4.0,
                label_offset=(0.025, 0.0)):
    x0, y0 = anchor
    x1, y1 = end
    cx = (x0 + x1) / 2 + curve
    bezier(ax, [(x0, y0), (cx, y0), (cx, y1), (x1, y1)],
           color=color, lw=lw)
    ax.add_patch(patches.Circle(anchor, 0.022, facecolor=color,
                                edgecolor="white", linewidth=1.2, zorder=5))
    ax.add_patch(patches.Circle(end, 0.026, facecolor=color,
                                edgecolor="white", linewidth=1.2, zorder=6))
    ax.text(x1 + label_offset[0], y1 + label_offset[1], label,
            fontsize=11, color=color,
            fontweight="bold", va="center")


def fig_mechanism():
    fig = setup_figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.055, 0.94, "Raw tether partition picture",
            fontsize=24, fontweight="bold", color=COLORS["ink"])
    ax.text(0.057, 0.895,
            "One joint binding phase-space probability from raw trajectories",
            fontsize=13, color=COLORS["muted"])

    # Physical scene.
    membrane(ax, 0.22, "receptor membrane", "bottom")
    membrane(ax, 0.78, "ligand membrane", "top")
    ax.annotate("", xy=(0.10, 0.76), xytext=(0.10, 0.24),
                arrowprops=dict(arrowstyle="<->", lw=1.8, color="#555555"))
    ax.text(0.115, 0.50, "trial separation h", fontsize=12,
            color="#555555", rotation=90, va="center")

    draw_tether(ax, (0.28, 0.25), (0.43, 0.51), COLORS["rigid"], "R tether",
                curve=0.06, lw=4.2, label_offset=(-0.035, -0.045))
    draw_tether(ax, (0.64, 0.75), (0.50, 0.53), COLORS["semi"], "L tether",
                curve=-0.06, lw=4.2)

    # Endpoint clouds: rigid narrow, flex wide.
    ax.add_patch(patches.Ellipse((0.43, 0.51), 0.09, 0.07, angle=20,
                                 facecolor=COLORS["rigid"], alpha=0.12,
                                 edgecolor=COLORS["rigid"], linewidth=1.2))
    ax.add_patch(patches.Ellipse((0.50, 0.53), 0.20, 0.15, angle=-15,
                                 facecolor=COLORS["flex"], alpha=0.12,
                                 edgecolor=COLORS["flex"], linewidth=1.2))
    ax.text(0.31, 0.58, "endpoint distributions\nfrom raw traj.xyz",
            fontsize=11, color=COLORS["muted"], ha="left")

    # Capture disk and angle cones.
    ax.add_patch(patches.Circle((0.465, 0.52), 0.052,
                                facecolor=COLORS["capture"], alpha=0.55,
                                edgecolor="#c78f00", linewidth=1.2, zorder=2))
    ax.text(0.53, 0.46, "RB-LB capture\n+ angle gate",
            fontsize=11, color="#7a5a00")
    ax.plot([0.43, 0.465], [0.51, 0.52], color="#c78f00", lw=2.0)
    ax.plot([0.50, 0.465], [0.53, 0.52], color="#c78f00", lw=2.0)

    # Formula panel.
    formula = (
        r"$K_{2D}^{eff}(h) \propto K_0 \int p_R(X_R)\,p_L(X_L)$" "\n"
        r"$\qquad\qquad\times\,[\exp(-U_{bind}/k_BT)-1]\,dX_R\,dX_L$"
    )
    ax.add_patch(patches.FancyBboxPatch(
        (0.565, 0.800), 0.385, 0.125,
        boxstyle="round,pad=0.018,rounding_size=0.018",
        facecolor="white", edgecolor="#dddddd", linewidth=1.0,
        zorder=7,
    ))
    ax.text(0.59, 0.89, formula, fontsize=16, color=COLORS["ink"],
            ha="left", va="top", zorder=8)
    labeled_box(
        ax, (0.61, 0.59), 0.31, 0.17,
        "What changes vs four independent terms",
        "F_c, F_bond and F_rot are not added\nfrom overlapping marginals.\nThey enter once through a joint gate.",
        fc="#fbfbfb", ec="#bbbbbb", title_size=12, body_size=10
    )
    labeled_box(
        ax, (0.61, 0.35), 0.31, 0.16,
        "K2D,max proxy",
        r"scan h -> take max_h K2D_eff(h)" "\n"
        "microscopic K0 cancels in ratios",
        fc="#f7fcfb", ec=COLORS["new"], title_size=12, body_size=10
    )
    labeled_box(
        ax, (0.61, 0.13), 0.31, 0.14,
        "Raw inputs",
        "traj.xyz + mol.psf + bond log\n(no chain_coords cache for validation)",
        fc="#fffaf0", ec="#c78f00", title_size=12, body_size=10
    )
    add_arrow(ax, (0.54, 0.52), (0.61, 0.43), color=COLORS["new"], lw=2.3)

    out = FIG_DIR / "raw_tether_mechanism.png"
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def _raw_predictions():
    d = np.load(ROOT / "results" / "raw_tether_partition.npz")
    soft = {
        "rigid": float(d["rigid__max__soft_area"]),
        "semi": float(d["semi__max__soft_area"]),
        "flex": float(d["flex__max__soft_area"]),
    }
    hard = {
        "rigid": float(d["rigid__max__hard_area"]),
        "semi": float(d["semi__max__hard_area"]),
        "flex": float(d["flex__max__hard_area"]),
    }

    def rows(vals):
        return np.array([
            -math.log(vals["flex"] / vals["rigid"]),
            -math.log(vals["semi"] / vals["rigid"]),
            -math.log(vals["semi"] / vals["flex"]),
        ])

    return rows(soft), rows(hard)


def _old_prediction():
    d = np.load(ROOT / "results" / "closure_four_term.npz", allow_pickle=True)
    names = [str(x).replace("−", "-") for x in d["pair_names"]]
    values = dict(zip(names, d["pair_ddF_sum"]))
    return np.array([
        float(values["flex-rigid"]),
        float(values["semi-rigid"]),
        float(values["semi-flex"]),
    ])


def fig_closure_comparison():
    old = _old_prediction()
    raw_soft, raw_hard = _raw_predictions()

    fig = setup_figure((13.5, 7.0))
    ax = fig.add_axes([0.07, 0.16, 0.76, 0.72])
    x = np.arange(len(PAIR_LABELS))
    w = 0.20
    ax.bar(x - 1.5 * w, TARGET, w, label="target",
           color=COLORS["target"], edgecolor="#777777", hatch="//")
    ax.bar(x - 0.5 * w, old, w, label="old four-term",
           color=COLORS["old"], alpha=0.92)
    ax.bar(x + 0.5 * w, raw_soft, w, label="raw partition soft",
           color=COLORS["new"], alpha=0.95)
    ax.bar(x + 1.5 * w, raw_hard, w, label="raw partition hard gate",
           color="#6cc4a1", alpha=0.95)

    for xpos, vals, color in [
        (x - 0.5 * w, old, COLORS["old"]),
        (x + 0.5 * w, raw_soft, COLORS["new"]),
    ]:
        for xi, yi, tgt in zip(xpos, vals, TARGET):
            gap = yi - tgt
            va = "bottom" if yi >= 0 else "top"
            dy = 0.07 if yi >= 0 else -0.07
            ax.text(xi, yi + dy, f"{gap:+.2f}",
                    ha="center", va=va, fontsize=9, color=color,
                    fontweight="bold")

    ax.axhline(0, color="#333333", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(PAIR_LABELS, fontsize=12)
    ax.set_ylabel("DeltaDeltaF (kBT)", fontsize=12)
    ax.set_title("Closure improves when K2D is estimated as one raw joint phase-space probability",
                 fontsize=16, fontweight="bold", pad=14)
    ax.grid(axis="y", alpha=0.22)
    ax.legend(loc="upper right", fontsize=10, frameon=True)

    gap_old = np.abs(old - TARGET)
    gap_new = np.abs(raw_soft - TARGET)
    side = fig.add_axes([0.855, 0.19, 0.12, 0.66])
    side.axis("off")
    labeled_box(
        side, (0.0, 0.63), 1.0, 0.30,
        "Max gap",
        f"old: {gap_old.max():.2f} kBT\nraw: {gap_new.max():.2f} kBT",
        fc="#fbfbfb", ec="#bbbbbb", title_size=12, body_size=11
    )
    labeled_box(
        side, (0.0, 0.30), 1.0, 0.27,
        "Best hit",
        f"semi-flex\nraw gap {raw_soft[2]-TARGET[2]:+.3f} kBT",
        fc="#f7fcfb", ec=COLORS["new"], title_size=12, body_size=11
    )
    side.text(0.02, 0.10,
              "Numbers above bars\nare prediction-target gaps.",
              fontsize=9.5, color=COLORS["muted"], linespacing=1.25)

    out = FIG_DIR / "raw_vs_closure_four_term.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def flow_box(ax, center, w, h, title, body, fc, ec):
    x, y = center[0] - w / 2, center[1] - h / 2
    labeled_box(ax, (x, y), w, h, title, body, fc=fc, ec=ec,
                title_size=11.5, body_size=9.5, lw=1.4)


def fig_pipeline():
    fig = setup_figure((13.5, 7.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.055, 0.93, "Raw trajectory -> K2D,max ratio",
            fontsize=24, fontweight="bold", color=COLORS["ink"])
    ax.text(0.057, 0.885,
            "A validation path that keeps the polymer-tether partition function intact",
            fontsize=13, color=COLORS["muted"])

    centers = [
        (0.12, 0.62),
        (0.30, 0.62),
        (0.49, 0.62),
        (0.68, 0.62),
        (0.86, 0.62),
    ]
    titles = [
        "Raw inputs",
        "Stream features",
        "Sample pairs",
        "Integrate gate",
        "Take ratios",
    ]
    bodies = [
        "traj.xyz\nmol.psf\nbond log",
        "bead 3/11/12\nexclude bound chains",
        "unbound R x L\nscan separation h",
        "RB-LB distance\nangle factors\nsoft kernel",
        "max over h\nK0 cancels\nDeltaDeltaF",
    ]
    fcs = ["#fffaf0", "#f5fbff", "#f7fcfb", "#fff8dc", "#f9f7ff"]
    ecs = ["#c78f00", "#3d8fb8", COLORS["new"], "#c78f00", COLORS["old"]]
    for c, t, b, fc, ec in zip(centers, titles, bodies, fcs, ecs):
        flow_box(ax, c, 0.145, 0.20, t, b, fc, ec)
    for a, b in zip(centers[:-1], centers[1:]):
        add_arrow(ax, (a[0] + 0.078, a[1]), (b[0] - 0.078, b[1]),
                  color="#555555", lw=1.9)

    # Lower panel: conceptual data products.
    ax.add_patch(patches.FancyBboxPatch(
        (0.08, 0.18), 0.84, 0.25,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor="#fbfbfb", edgecolor="#dddddd", linewidth=1.2
    ))
    ax.text(0.105, 0.375, "What the prototype already shows",
            fontsize=14, fontweight="bold", color=COLORS["ink"])
    ax.text(0.105, 0.315,
            "1. z-reach alone closes only about 10-13%: endpoint height is not enough.",
            fontsize=11.5, color=COLORS["muted"])
    ax.text(0.105, 0.265,
            "2. adding radial binding + angular compatibility gives all signs;\n   max gap about 0.24 kBT.",
            fontsize=10.7, color=COLORS["muted"], linespacing=1.15)
    ax.text(0.105, 0.215,
            "3. flexible-system tail sampling is the remaining uncertainty;\n   next step is bootstrap/multi-seed.",
            fontsize=10.7, color=COLORS["muted"], linespacing=1.15)

    # Mini curve glyph.
    xs = np.linspace(0, 1, 120)
    for y0, color, shift, lab in [
        (0.29, COLORS["rigid"], 0.25, "rigid"),
        (0.275, COLORS["semi"], 0.48, "semi"),
        (0.260, COLORS["flex"], 0.68, "flex"),
    ]:
        xplot = 0.66 + 0.21 * xs
        yplot = y0 + 0.05 * np.exp(-((xs - shift) ** 2) / 0.025)
        ax.plot(xplot, yplot, color=color, lw=2.4)
        ax.text(0.885, yplot[-1], lab, fontsize=9.5, color=color, va="center")
    ax.text(0.67, 0.20, r"$K_{2D}^{eff}(h)$ curves -> maxima",
            fontsize=10.5, color=COLORS["muted"])

    out = FIG_DIR / "raw_tether_pipeline.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_mechanism()
    fig_closure_comparison()
    fig_pipeline()


if __name__ == "__main__":
    main()

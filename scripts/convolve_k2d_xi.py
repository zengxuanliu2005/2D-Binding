"""K2D(ξ⊥) prediction via Weikl 2016 Eq. (1) convolution.

Convolves measured K2D_eff(h) from raw_tether_partition.npz with a Gaussian
membrane-separation distribution P(h; l̄, ξ⊥), then maximizes over l̄ to get
K2D(ξ⊥). Compares to Gaussian-K2D(l) benchmark (Hu 2013 master curve).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit


SYSTEMS = [
    ("rigid", "K100 (rigid)"),
    ("semi", "K10 (semi)"),
    ("flex", "K01 (flex)"),
]

XI_PERP = np.arange(0.0, 3.05, 0.05)  # nm
ROOT = Path(__file__).resolve().parent.parent


def gaussian(x, a, x0, sigma):
    return a * np.exp(-((x - x0) ** 2) / (2 * sigma * sigma))


def fit_gaussian_peak(h, area):
    """Fit Gaussian around the peak of area(h). Returns (h_star, sigma, A)."""
    i_peak = int(np.argmax(area))
    # fit window: ±4σ guess from initial moment estimate
    h_peak = h[i_peak]
    a_peak = area[i_peak]
    # moment estimate of sigma
    half_max = a_peak / 2.0
    above = area >= half_max
    if np.sum(above) >= 2:
        h_above = h[above]
        fwhm = h_above[-1] - h_above[0]
        sigma_guess = fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    else:
        sigma_guess = 2.0
    sigma_guess = max(sigma_guess, 0.5)

    # restrict fit to ±4 sigma around peak
    mask = np.abs(h - h_peak) < 4.0 * sigma_guess
    h_fit = h[mask]
    area_fit = area[mask]

    popt, _ = curve_fit(
        gaussian, h_fit, area_fit,
        p0=[a_peak, h_peak, sigma_guess],
        bounds=([0, h_peak - 5, 0.1], [1e10, h_peak + 5, 10.0]),
        maxfev=10000,
    )
    return popt[1], popt[2], popt[0]  # h_star, sigma, A


def convolve_k2d(h, k2d_eff, xi_perp_values, l_bar_values):
    """Convolve K2D_eff(h) with Gaussian P(h; l̄, ξ⊥), maximize over l̄.

    Returns array of K2D(ξ⊥) values.
    """
    dh = h[1] - h[0]
    result = np.empty(len(xi_perp_values))

    for i, xi in enumerate(xi_perp_values):
        best = 0.0
        for l_bar in l_bar_values:
            # P(h; l_bar, xi) = exp(-(h-l_bar)^2/(2 xi^2)) / sqrt(2 pi xi^2)
            if xi < 0.01:
                # near-delta: pick value at h closest to l_bar
                idx = int(np.argmin(np.abs(h - l_bar)))
                val = k2d_eff[idx]
            else:
                weight = np.exp(-0.5 * ((h - l_bar) / xi) ** 2)
                weight /= math.sqrt(2.0 * math.pi) * xi
                val = np.sum(k2d_eff * weight) * dh
            if val > best:
                best = val
        result[i] = best

    return result


def hu_benchmark(xi, k2d_max, xi_rl):
    """Hu 2013 master curve: K2D(ξ⊥) = K2D,max / sqrt(1 + (ξ⊥/ξ_RL)²)."""
    return k2d_max / np.sqrt(1.0 + (xi / xi_rl) ** 2)


def main():
    npz_path = ROOT / "results" / "raw_tether_partition.npz"
    data = np.load(npz_path, allow_pickle=True)
    h = data["h"]
    dh = h[1] - h[0]

    # l̄ sweep: h range minus margins
    l_bar_pad = 1.0
    l_bar_values = np.arange(h[0] + l_bar_pad, h[-1] - l_bar_pad + 0.5 * dh, dh)

    curves = {}
    gauss_params = {}

    for label, name in SYSTEMS:
        k2d_eff = data[f"{label}__soft_area"]

        # --- empirical convolution ---
        k2d_xi = convolve_k2d(h, k2d_eff, XI_PERP, l_bar_values)
        curves[f"{label}__k2d_xi"] = k2d_xi

        # --- Gaussian benchmark: fit K2D_eff(h) to Gaussian ---
        h_star, xi_rl, a_peak = fit_gaussian_peak(h, k2d_eff)
        k2d_max_eff = a_peak  # at xi=0, convolution of Gaussian gives peak
        k2d_hu = hu_benchmark(XI_PERP, k2d_max_eff, xi_rl)
        curves[f"{label}__k2d_hu"] = k2d_hu
        gauss_params[label] = {
            "h_star": float(h_star),
            "xi_rl": float(xi_rl),
            "a_peak": float(a_peak),
        }

        print(f"[{label}] Gaussian fit: h*={h_star:.2f} σ, ξ_RL={xi_rl:.2f} σ, "
              f"K2D(0)={a_peak:.1f} (arb units)")

    # normalize to ξ⊥=0 for shape comparison
    for label, _ in SYSTEMS:
        for suffix in ("k2d_xi", "k2d_hu"):
            key = f"{label}__{suffix}"
            curves[f"{label}__{suffix}_norm"] = curves[key] / curves[key][0]

    # --- save ---
    out_npz = ROOT / "results" / "k2d_xi_curves.npz"
    out_md = ROOT / "results" / "k2d_xi_curves.md"
    out_npz.parent.mkdir(parents=True, exist_ok=True)

    payload = {"xi_perp": XI_PERP, "h": h, "l_bar_values": l_bar_values}
    for k, v in curves.items():
        payload[k] = v
    for label, d in gauss_params.items():
        for k, v in d.items():
            payload[f"{label}__gauss_{k}"] = v
    np.savez(out_npz, **payload)

    with open(out_md, "w") as fp:
        fp.write("# K2D(ξ⊥) prediction — Weikl 2016 Eq. (1) convolution\n\n")
        fp.write("Convolves measured `K2D_eff(h)` from `raw_tether_partition.npz` "
                 "with Gaussian `P(h; l̄, ξ⊥)` and maximizes over `l̄`.\n\n")
        fp.write("## Gaussian fit parameters (null-hypothesis benchmark)\n\n")
        fp.write("| system | h* (σ) | ξ_RL (σ) | K2D(ξ⊥=0) arb |\n")
        fp.write("|---|---:|---:|---:|\n")
        for label, name in SYSTEMS:
            p = gauss_params[label]
            fp.write(f"| {name} | {p['h_star']:.2f} | {p['xi_rl']:.2f} | {p['a_peak']:.1f} |\n")

        fp.write("\n## K2D(ξ⊥) curves (normalized to ξ⊥=0)\n\n")
        fp.write("| ξ⊥ (σ) | rigid conv | rigid Hu | semi conv | semi Hu | flex conv | flex Hu |\n")
        fp.write("|---:|---:|---:|---:|---:|---:|---:|\n")
        for i, xi in enumerate(XI_PERP):
            if i % 5 != 0:
                continue
            fp.write(f"| {xi:.2f} | "
                     f"{curves['rigid__k2d_xi_norm'][i]:.4f} | {curves['rigid__k2d_hu_norm'][i]:.4f} | "
                     f"{curves['semi__k2d_xi_norm'][i]:.4f} | {curves['semi__k2d_hu_norm'][i]:.4f} | "
                     f"{curves['flex__k2d_xi_norm'][i]:.4f} | {curves['flex__k2d_hu_norm'][i]:.4f} |\n")

        fp.write("\n## Interpretation\n\n")
        fp.write("- If `K2D(l)` were Gaussian, the convolution result (k2d_xi) would "
                 "match the Hu benchmark (k2d_hu) exactly.\n")
        fp.write("- Deviation between the two at moderate-to-large ξ⊥ reveals "
                 "non-Gaussian structure in the true `K2D_eff(h)`.\n")
        fp.write("- Rigid (K100): expected near-perfect overlap (Gaussian-like).\n")
        fp.write("- Flexible (K01): expected visible deviation — long tails in "
                 "endpoint distribution cause slower decay with ξ⊥.\n")

    print(f"\nSaved {out_npz.relative_to(ROOT)} and {out_md.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""Q1 Step 2: Extract microscopic candidate quantities for ξ_RL decomposition.

Uses existing chain_coords.npz (per-frame, per-chain bead positions) to compute:
  A. σ_R, σ_L: std of anchor-to-binding-bead z-projection (unbound chains)
  B. σ_complex: std of local separation for bound pairs (4 definitions)
  C. σ_K2D(l): Gaussian width of K2D_eff(h) from raw_tether_partition.npz
  D. k_RL: bond curvature (2nd derivative of radial potential at minimum)
  E. lp: persistence length from PhD PPT (constants)
  F. k_a_effective: from first ecto angle distribution
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parent.parent

SYSTEM_DIRS = {
    "rigid": "15_120x120_K100_EPS05",
    "semi": "15_120x120_K10_EPS05",
    "flex": "22_120x120_K01_EPS05",
}

SYSTEMS = [
    ("rigid", "K100"),
    ("semi", "K10"),
    ("flex", "K01"),
]

# Bead indices (0-indexed Python)
BEAD_ANCHOR = 2   # bead 3 in 1-indexed (RH for R, LH for L)
BEAD_BINDING = 11  # bead 12 in 1-indexed (RB for R, LB for L)
BEAD_ECTO_START = 3  # bead 4 = first ecto bead after anchor

# PhD PPT persistence lengths (nm)
LP_PHD = {"rigid": 84.6, "semi": 8.18, "flex": 1.14}

# Bond potential parameters (from ref/nvt-md.py, RLF_Tabs)
EPSILON = 15.0
SIGMA = 0.95
WF = 0.4
ANGLE_K = 15.0  # ε/rad²
ANGLE0_DEG = 10.0
KBT_IN_EPS = 1.1


def gaussian(x, a, x0, sigma):
    return a * np.exp(-((x - x0) ** 2) / (2 * sigma * sigma))


def radial_u_kbt(r):
    """Shifted-attractive LJ radial potential in kBT units.
    Replicates scripts/raw_tether_partition_k2d.py:radial_u_kbt()."""
    eps_kbt = EPSILON / KBT_IN_EPS
    if isinstance(r, np.ndarray):
        u = np.zeros_like(r, dtype=float)
        mask = r < 2.9
        rm = r[mask]
        u[mask] = eps_kbt * 4.0 * WF * (
            (SIGMA / rm) ** 12 - (SIGMA / rm) ** 6)
        return u
    else:
        if r >= 2.9:
            return 0.0
        return eps_kbt * 4.0 * WF * ((SIGMA / r) ** 12 - (SIGMA / r) ** 6)


def compute_k_rl():
    """Compute bond curvature k_RL = d²U/dr² at potential minimum.
    Returns (r_min, k_RL in kBT/σ², sqrt(kBT/k_RL) in σ).
    """
    # Find minimum numerically
    rs = np.linspace(0.8, 1.5, 1000)
    us = np.array([radial_u_kbt(r) for r in rs])
    i_min = np.argmin(us)
    r_min = rs[i_min]

    # Finite-difference 2nd derivative at minimum
    dr = rs[1] - rs[0]
    u_minus = radial_u_kbt(r_min - dr)
    u_0 = radial_u_kbt(r_min)
    u_plus = radial_u_kbt(r_min + dr)
    d2u = (u_plus - 2 * u_0 + u_minus) / (dr * dr)

    # For harmonic well: U(r) ≈ ½ k_RL (r - r_min)², so k_RL = d²U/dr²
    k_rl = d2u
    xi_bond = 1.0 / math.sqrt(k_rl)  # sqrt(kBT/k_RL) in σ (nm)
    return r_min, k_rl, xi_bond


def angle_factor_boltzmann(theta_deg):
    """exp(-K · (θ - θ0)² / (2 kBT)) for single angle."""
    K = ANGLE_K
    theta0_rad = math.radians(ANGLE0_DEG)
    theta_rad = np.radians(theta_deg)
    return np.exp(-K * (theta_rad - theta0_rad) ** 2 / (2 * KBT_IN_EPS))


def main():
    # --- D: Bond curvature (analytical, no MD needed) ---
    r_min, k_rl, xi_bond = compute_k_rl()
    print(f"D. Bond curvature:")
    print(f"   r_min = {r_min:.4f} σ")
    print(f"   k_RL = {k_rl:.2f} kBT/σ²")
    print(f"   sqrt(kBT/k_RL) = {xi_bond:.4f} σ (nm)")

    # --- Load K2D_eff(h) for σ_K2D(l) ---
    rtp = np.load(ROOT / "results" / "raw_tether_partition.npz", allow_pickle=True)
    h_grid = rtp["h"]
    dh = h_grid[1] - h_grid[0]

    results = {}
    for label, name in SYSTEMS:
        print(f"\n{'='*50}")
        print(f"{name} ({label})")
        print(f"{'='*50}")

        sys_dir = SYSTEM_DIRS[label]
        cc = np.load(ROOT / "results" / "chain_coords" / sys_dir / "chain_coords.npz",
                     allow_pickle=True)
        pos_R = cc["positions_R"]  # (n_frames, n_R, 13, 3)
        pos_L = cc["positions_L"]  # (n_frames, n_L, 13, 3)
        bound_R = cc["bound_R"]    # (n_frames, n_R) bool
        bound_L = cc["bound_L"]    # (n_frames, n_L) bool
        partner_R = cc["partner_R"]  # (n_frames, n_R) int (partner index in L)
        partner_L = cc["partner_L"]  # (n_frames, n_L) int (partner index in R)

        n_frames, n_R_chains, n_beads, _ = pos_R.shape
        n_L_chains = pos_L.shape[1]

        # --- A: Per-chain h distributions ---
        # h = z(binding_bead) - z(anchor_bead) for each chain
        h_R_all = pos_R[:, :, BEAD_BINDING, 2] - pos_R[:, :, BEAD_ANCHOR, 2]
        h_L_all = pos_L[:, :, BEAD_BINDING, 2] - pos_L[:, :, BEAD_ANCHOR, 2]

        # Unbound subset
        unbound_R = ~bound_R
        unbound_L = ~bound_L
        h_R_unbound = h_R_all[unbound_R]
        h_L_unbound = h_L_all[unbound_L]
        h_R_bound = h_R_all[bound_R]
        h_L_bound = h_L_all[bound_L]

        sigma_R_unbound = float(np.std(h_R_unbound))
        sigma_L_unbound = float(np.std(h_L_unbound))
        sigma_R_bound = float(np.std(h_R_bound)) if h_R_bound.size > 0 else np.nan
        sigma_L_bound = float(np.std(h_L_bound)) if h_L_bound.size > 0 else np.nan

        print(f"A. Per-chain h = z(bead12) - z(bead3):")
        print(f"   σ_R unbound = {sigma_R_unbound:.4f} σ, bound = {sigma_R_bound:.4f} σ")
        print(f"   σ_L unbound = {sigma_L_unbound:.4f} σ, bound = {sigma_L_bound:.4f} σ")
        print(f"   sqrt(σ_R² + σ_L²) unbound = {math.sqrt(sigma_R_unbound**2 + sigma_L_unbound**2):.4f} σ")
        print(f"   sqrt(σ_R² + σ_L²) bound = {math.sqrt(sigma_R_bound**2 + sigma_L_bound**2):.4f} σ")

        # --- B: Complex local-separation (bound pairs) ---
        # Collect z positions for bound R-L pairs
        z_R_anchor_bound = []
        z_L_anchor_bound = []
        z_R_bind_bound = []
        z_L_bind_bound = []

        for f in range(n_frames):
            for r_idx in range(n_R_chains):
                if bound_R[f, r_idx]:
                    l_partner = partner_R[f, r_idx]
                    if l_partner >= 0 and l_partner < n_L_chains:
                        z_R_anchor_bound.append(pos_R[f, r_idx, BEAD_ANCHOR, 2])
                        z_L_anchor_bound.append(pos_L[f, l_partner, BEAD_ANCHOR, 2])
                        z_R_bind_bound.append(pos_R[f, r_idx, BEAD_BINDING, 2])
                        z_L_bind_bound.append(pos_L[f, l_partner, BEAD_BINDING, 2])

        z_R_anchor_bound = np.array(z_R_anchor_bound)
        z_L_anchor_bound = np.array(z_L_anchor_bound)
        z_R_bind_bound = np.array(z_R_bind_bound)
        z_L_bind_bound = np.array(z_L_bind_bound)

        n_bound_pairs = len(z_R_anchor_bound)

        # 4 candidate definitions of h_complex
        h_c1 = z_R_anchor_bound - z_L_anchor_bound          # anchor-to-anchor
        h_c2 = z_R_bind_bound - z_L_bind_bound               # bind-to-bind
        h_c3 = (z_R_anchor_bound + z_L_anchor_bound) / 2    # midpoint (no reference)
        h_c4 = np.abs(z_R_bind_bound - z_L_bind_bound)       # absolute bind distance

        sigma_c1 = float(np.std(h_c1))
        sigma_c2 = float(np.std(h_c2))
        sigma_c3 = float(np.std(h_c3))
        sigma_c4 = float(np.std(h_c4))

        print(f"B. Complex local-separation (n_bound_pairs = {n_bound_pairs}):")
        print(f"   h_c1 (anchor-to-anchor): mean={np.mean(h_c1):.4f}, σ={sigma_c1:.4f} σ")
        print(f"   h_c2 (bind-to-bind):     mean={np.mean(h_c2):.4f}, σ={sigma_c2:.4f} σ")
        print(f"   h_c3 (anchor midpoint):  mean={np.mean(h_c3):.4f}, σ={sigma_c3:.4f} σ")
        print(f"   h_c4 (|bind-to-bind|):   mean={np.mean(h_c4):.4f}, σ={sigma_c4:.4f} σ")

        # --- C: σ_K2D(l) from K2D_eff(h) Gaussian fit ---
        soft_area = rtp[f"{label}__soft_area"]
        i_peak = int(np.argmax(soft_area))
        h_peak = h_grid[i_peak]
        a_peak = soft_area[i_peak]

        # Fit window: ±4σ around peak, initial sigma from FWHM
        half_max = a_peak / 2.0
        above = soft_area >= half_max
        if np.sum(above) >= 2:
            h_above = h_grid[above]
            fwhm = h_above[-1] - h_above[0]
            sigma_guess = fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        else:
            sigma_guess = 2.0
        sigma_guess = max(sigma_guess, 0.3)

        mask = np.abs(h_grid - h_peak) < 4.0 * sigma_guess
        h_fit = h_grid[mask]
        area_fit = soft_area[mask]

        popt, _ = curve_fit(
            gaussian, h_fit, area_fit,
            p0=[a_peak, h_peak, sigma_guess],
            bounds=([0, h_peak - 5, 0.1], [1e10, h_peak + 5, 10.0]),
            maxfev=10000,
        )
        sigma_k2d_l = float(popt[2])

        print(f"C. K2D_eff(h) Gaussian fit:")
        print(f"   h* = {popt[1]:.4f} σ, A_peak = {popt[0]:.1f}")
        print(f"   σ_K2D(l) = {sigma_k2d_l:.4f} σ")

        # --- F: Effective k_a from first ecto angle ---
        # First ecto angle: bead 2→3→4 (anchor→first ecto→second ecto)
        # In 0-indexed: beads 2, 3, 4
        def compute_angles(pos_chains):
            """Compute cos(angle) for bead triple (2,3,4) for all frames×chains."""
            v1 = pos_chains[:, :, 3, :] - pos_chains[:, :, 2, :]  # anchor→first ecto
            v2 = pos_chains[:, :, 4, :] - pos_chains[:, :, 3, :]  # first→second ecto
            # normalize
            n1 = np.linalg.norm(v1, axis=-1)
            n2 = np.linalg.norm(v2, axis=-1)
            cos_angle = np.sum(v1 * v2, axis=-1) / (n1 * n2 + 1e-20)
            cos_angle = np.clip(cos_angle, -1, 1)
            return np.degrees(np.arccos(cos_angle))

        angles_R = compute_angles(pos_R)  # (frames, n_R)
        angles_L = compute_angles(pos_L)  # (frames, n_L)

        # Only unbound chains (angles should be similar bound vs unbound for first ecto)
        angles_R_flat = angles_R[unbound_R]
        angles_L_flat = angles_L[unbound_L]
        angles_all = np.concatenate([angles_R_flat, angles_L_flat])

        # Fit P(cos θ) ∝ exp(-k_a · (1 - cos θ) / kBT)
        # Effective angle stiffness for the first ecto bond
        # Linear regime: (θ-180°)²
        # Convert to bending: for a straight chain, θ ≈ 180° (bead 3-4 vector
        # continuation). The angle we measure is the BEAD angle at the anchor
        # (beads 2-3-4), not the ecto angle. This is approximately the
        # anchor tilt angle.
        mean_angle = float(np.mean(angles_all))
        std_angle = float(np.std(angles_all))
        # k_a from Gaussian fit: P(θ) ∝ exp(-k_a · (θ-θ_mean)² / (2 kBT))
        # σ² = kBT/k_a → k_a = kBT/σ²
        k_a_eff = KBT_IN_EPS / (math.radians(std_angle) ** 2)

        print(f"F. First ecto angle (beads 2-3-4, anchor angle):")
        print(f"   mean = {mean_angle:.2f}°, σ = {std_angle:.4f}°")
        print(f"   k_a_eff = {k_a_eff:.2f} ε/rad² (= kBT/σ_θ²)")

        # Store
        results[label] = {
            "sigma_R_unbound": sigma_R_unbound,
            "sigma_L_unbound": sigma_L_unbound,
            "sigma_R_bound": sigma_R_bound,
            "sigma_L_bound": sigma_L_bound,
            "sigma_complex_c1": sigma_c1,
            "sigma_complex_c2": sigma_c2,
            "sigma_complex_c3": sigma_c3,
            "sigma_complex_c4": sigma_c4,
            "mean_complex_c1": float(np.mean(h_c1)),
            "mean_complex_c2": float(np.mean(h_c2)),
            "sigma_k2d_l": sigma_k2d_l,
            "h_peak": h_peak,
            "k_a_eff": k_a_eff,
            "mean_angle": mean_angle,
            "std_angle": std_angle,
            "n_bound_pairs": n_bound_pairs,
        }

    # --- Save ---
    out_npz = ROOT / "results" / "xi_rl_candidates.npz"
    payload = {"xi_bond": xi_bond, "k_rl": k_rl, "r_min": r_min}
    for label, d in results.items():
        for k, v in d.items():
            payload[f"{label}__{k}"] = v
    np.savez(out_npz, **payload)
    print(f"\nSaved {out_npz.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

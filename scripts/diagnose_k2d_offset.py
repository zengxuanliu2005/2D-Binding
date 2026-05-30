"""Q3: Diagnose rigid 22% absolute-K2D offset.

Tests:
  1. Bond-vector sampling convergence: does 24 samples under-sample the
     angular acceptance for rigid chains?
  2. Lateral disk integral normalization: check against numerical quadrature
  3. Angular factor normalization
  4. h-grid resolution effect at narrow K2D(l) peak
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# Bond potential parameters (from ref/nvt-md.py RLF_Tabs)
EPSILON = 15.0
SIGMA = 0.95  # LJ sigma
WF = 0.4
RCUT = 2.9
KBT_IN_EPS = 1.1

# U_c = 4 epsilon * [(1/2.5)^12 - (1/2.5)^6]
UC = 4.0 * EPSILON * ((1.0 / 2.5) ** 12 - (1.0 / 2.5) ** 6)

# Angular gate
ANGLE_K = 15.0
ANGLE0_DEG = 10.0

# Well bottom
R_MIN = (2.0 ** (1.0 / 6.0)) * SIGMA + WF
U_WELL_EPS = -EPSILON - UC  # ≈ -14.76 ε


def radial_u_eps(r):
    """Radial binding potential in ε units (exact replica of ref/nvt-md.py)."""
    r = np.asarray(r)
    shifted = np.maximum(r - WF, 1e-10)
    lj = 4.0 * EPSILON * ((SIGMA / shifted) ** 12 - (SIGMA / shifted) ** 6) - UC
    u = np.where(r <= R_MIN, U_WELL_EPS, lj)
    u = np.where(r < RCUT, u, 0.0)
    return u


def angle_factor_exact(theta_deg):
    """f_i(theta) = 1 if theta<=theta0, exp(-K*(theta-theta0)^2) otherwise."""
    theta_rad = np.radians(theta_deg)
    theta0_rad = np.radians(ANGLE0_DEG)
    excess = np.maximum(theta_rad - theta0_rad, 0.0)
    return np.exp(-ANGLE_K * excess ** 2)


def boltzmann_weight(r, theta_r_deg, theta_l_deg):
    """exp(-U_bind/kBT) where U_bind = U(r) * f(theta_R) * f(theta_L)."""
    u_eps = radial_u_eps(r)
    f_r = angle_factor_exact(theta_r_deg)
    f_l = angle_factor_exact(theta_l_deg)
    u_eff_eps = u_eps * f_r * f_l
    return np.exp(-u_eff_eps / KBT_IN_EPS)


def compute_bond_vector_integral_fixed_geometry(dz, theta_R_chain, theta_L_chain, n_quad):
    """Compute K2D contribution for one fixed geometry using high-res quadrature.

    For a given dz (z-separation) and chain orientations (theta_R, theta_L),
    integrate exp(-U/kBT) over the 2D lateral bond vector within the rcut disk.

    Returns (soft_integral, hard_integral).
    """
    rxy_max = math.sqrt(max(RCUT * RCUT - dz * dz, 0.0))
    if rxy_max <= 0:
        return 0.0, 0.0

    # Gauss-Legendre quadrature over rho² ∈ [0, rxy_max²]
    # and uniform over φ ∈ [0, 2π]
    # Use n_quad points in each dimension
    # rho² quadrature: map [-1,1] → [0, rxy_max²]
    xi, wi = np.polynomial.legendre.leggauss(n_quad)

    soft_int = 0.0
    hard_int = 0.0

    dphi = 2.0 * math.pi / n_quad

    for i in range(n_quad):
        rho_sq = (xi[i] + 1.0) / 2.0 * rxy_max * rxy_max
        rho = math.sqrt(rho_sq)
        w_rho = wi[i] / 2.0 * rxy_max * rxy_max  # Jacobian from [-1,1] to [0, rxy²]

        for j in range(n_quad):
            phi = j * dphi + dphi / 2.0
            rx = rho * math.cos(phi)
            ry = rho * math.sin(phi)
            r = math.sqrt(rx * rx + ry * ry + dz * dz)

            # Angles between chain direction and bond vector
            # Chain direction for R: pointing from anchor to binding bead (roughly -z)
            # For fixed geometry, we use general formula
            # Bond vector from RB to LB: (-rx, -ry, -dz) for R's perspective
            #                                (+rx, +ry, +dz) for L's perspective
            cos_theta_r = dz / max(r, 1e-10)  # assuming chain is along z
            theta_r = math.degrees(math.acos(np.clip(cos_theta_r, -1, 1)))
            theta_l = theta_r  # symmetric

            # More precise: angle between chain direction vector and bond vector
            # Chain points from anchor(head) toward binding bead
            # For R: chain is at some angle θ_R_chain from z-axis
            # For L: chain is at angle θ_L_chain from z-axis

            # Simplified: assume chain exactly along z → this gives UPPER BOUND
            # Full treatment needs chain orientation vectors

            bw = boltzmann_weight(r, theta_r, theta_l)

            # Jacobian for polar: ∫ f d²r = ∫₀^{2π} ∫₀^{rxy_max} f(r,φ) r dr dφ
            # Our quadrature: Σ wi_rho * f(rho_i, φ_j) (already includes rho factor in w_rho)
            soft_int += bw * w_rho * dphi

            # Hard gate
            if r <= 1.5 and theta_r <= 15.0 and theta_l <= 15.0:
                hard_int += 1.0 * w_rho * dphi

    return soft_int, hard_int


def mc_sample_fixed_geometry(dz, rxy_max, rng, n_samples):
    """MC estimate of lateral integral for fixed geometry (like raw partition code)."""
    soft_sum = 0.0
    hard_sum = 0.0

    for _ in range(n_samples):
        rho_sq = rng.random() * rxy_max * rxy_max
        rho = math.sqrt(rho_sq)
        phi = rng.random() * 2.0 * math.pi
        rx = rho * math.cos(phi)
        ry = rho * math.sin(phi)
        r = math.sqrt(rx * rx + ry * ry + dz * dz)

        cos_th = dz / max(r, 1e-10)
        theta_r = math.degrees(math.acos(np.clip(cos_th, -1, 1)))
        theta_l = theta_r

        bw = boltzmann_weight(r, theta_r, theta_l)
        soft_sum += bw

        if r <= 1.5 and theta_r <= 15.0 and theta_l <= 15.0:
            hard_sum += 1.0

    area_factor = math.pi * rxy_max * rxy_max
    return area_factor * soft_sum / n_samples, area_factor * hard_sum / n_samples


def main():
    print("=" * 70)
    print("Q3: Absolute K2D — diagnostic tests")
    print("=" * 70)

    # --- Check 0: Potential sanity ---
    print(f"\n--- Potential parameters ---")
    print(f"σ = {SIGMA}, wf = {WF}, ε = {EPSILON}, rcut = {RCUT}")
    print(f"r_min = {R_MIN:.4f} (2^(1/6)σ + wf)")
    print(f"U_c = {UC:.6f} ε")
    print(f"U_well = {U_WELL_EPS:.3f} ε = {U_WELL_EPS / KBT_IN_EPS:.2f} kBT")
    print(f"exp(-U_well/kBT) = {math.exp(-U_WELL_EPS / KBT_IN_EPS):.1f}")
    print(f"angular K = {ANGLE_K} ε/rad², θ0 = {ANGLE0_DEG}°")

    # --- Check 1: Nonzero radial integrand region ---
    # The integrand exp(-U/kBT) is large only for r near r_min and angles near θ0
    rs = np.linspace(SIGMA * 0.6, RCUT, 100)
    us = radial_u_eps(rs)
    u_min_idx = np.argmin(us)
    print(f"\n--- Radial potential check ---")
    print(f"U_min = {us[u_min_idx]:.3f} ε at r = {rs[u_min_idx]:.4f}")
    print(f"U=0 at r = {RCUT}")
    print(f"Effective radial range: r ∈ [{SIGMA*0.6:.2f}, {RCUT:.2f}]")

    # --- Check 2: Angular acceptance ---
    thetas = np.linspace(0, 30, 100)
    f_ang = angle_factor_exact(thetas)
    print(f"\n--- Angular factor check ---")
    print(f"f(θ=0°) = {angle_factor_exact(0):.4f}")
    print(f"f(θ=10°) = {angle_factor_exact(10):.4f}")
    print(f"f(θ=15°) = {angle_factor_exact(15):.6f}")
    print(f"f(θ=20°) = {angle_factor_exact(20):.6e}")
    # Angular acceptance width
    print(f"Angular acceptance FWHM ≈ {2 * 10 + 2 * math.sqrt(math.log(2)/ANGLE_K) * 180/math.pi:.1f}°")

    # --- Check 3: Bond-vector integral convergence ---
    print(f"\n--- Bond-vector integral convergence test ---")
    # Test case: dz = 0 (optimal geometry), chain along z
    dz_test = 0.0
    rxy_max = math.sqrt(RCUT * RCUT - dz_test * dz_test)

    # High-res reference
    ref_soft, ref_hard = compute_bond_vector_integral_fixed_geometry(
        dz_test, 0.0, 0.0, n_quad=64)
    print(f"Reference (64-pt quadrature): soft = {ref_soft:.6f} nm²")

    # MC convergence test
    rng = np.random.default_rng(42)
    for n_samples in [8, 24, 50, 100, 500, 2000]:
        mc_soft, _ = mc_sample_fixed_geometry(dz_test, rxy_max, rng, n_samples)
        err = abs(mc_soft - ref_soft) / ref_soft * 100
        print(f"  MC n={n_samples:4d}: soft = {mc_soft:.6f}, error = {err:.2f}%")

    # --- Check 4: dz-scan at fixed geometry ---
    print(f"\n--- K2D vs dz for fixed (θ_R=0, θ_L=0) geometry ---")
    dzs = np.linspace(0, RCUT * 0.95, 20)
    for dz in dzs:
        soft, _ = compute_bond_vector_integral_fixed_geometry(dz, 0.0, 0.0, n_quad=32)
        print(f"  dz = {dz:.2f}: soft = {soft:.4f} nm²")

    # --- Check 5: Lateral integral normalized to nm² ---
    print(f"\n--- Unit check ---")
    print(f"All lengths in σ = 1 nm")
    print(f"RCUT = {RCUT} nm")
    print(f"Maximum disk area = π × RCUT² = {math.pi * RCUT * RCUT:.2f} nm²")

    # --- Check 6: What should K2D,max be? ---
    # At dz=0, chain along z (optimal geometry):
    # r ranges from 0 to rxy_max = RCUT = 2.9
    # For r <= r_min, U = U_well → exp(-U_well/kBT) ≈ 6.7e5
    # Effective capture area ≈ π × r_min² × exp(-U_well/kBT)
    # But only for angles where both f_ang ≥ 0.5
    # Rough estimate:
    k2d_estimate = math.pi * R_MIN * R_MIN * math.exp(-U_WELL_EPS / KBT_IN_EPS)
    print(f"\n--- Rough K2D estimate (dz=0, chain along z) ---")
    print(f"π × r_min² × exp(-U_well/kBT) = π × {R_MIN:.4f}² × {math.exp(-U_WELL_EPS / KBT_IN_EPS):.1f}")
    print(f"  = {k2d_estimate:.1f} nm²")
    print(f"  This is the UPPER BOUND (perfect chain alignment, dz=0)")
    print(f"  Target: rigid K2D,max = 12705 nm²")
    print(f"  Our K2D_eff(h_peak): rigid = 9894 nm²")

    # --- Check 7: Angular factor effect on effective well depth ---
    print(f"\n--- Angular modulation effect ---")
    for theta_deg in [0, 5, 10, 12, 15, 20]:
        f = angle_factor_exact(theta_deg)
        u_eff = U_WELL_EPS * f * f / KBT_IN_EPS  # both R and L angles
        bw = math.exp(-u_eff)
        print(f"  θ_R = θ_L = {theta_deg:5.1f}°: f = {f:.6f}, U_eff = {u_eff:.2f} kBT, exp(-U_eff) = {bw:.1e}")

    # --- Check 8: Sensitivity of K2D to r_min placement ---
    print(f"\n--- Sensitivity to h-grid peak placement ---")
    print(f"R_min = {R_MIN:.4f} nm")
    print(f"At dz=0, r ranges from 0 to rcut, flat bottom for r < {R_MIN:.4f}")
    print(f"Flat-bottom well width = {R_MIN:.4f} nm (compared to LJ sigma = 0.95 nm)")
    disk_area_well = math.pi * R_MIN * R_MIN
    disk_area_total = math.pi * RCUT * RCUT
    print(f"Well disk area = πr_min² = {disk_area_well:.2f} nm²")
    print(f"Total disk area = πrcut² = {disk_area_total:.2f} nm²")
    print(f"Well fraction = {disk_area_well / disk_area_total * 100:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())

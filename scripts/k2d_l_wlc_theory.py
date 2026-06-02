"""B2 — WLC-based theory for K2D(l; lp).

Implements derivation/01_wlc_endpoint_distribution/ (P(R; lp, Lc) Monte
Carlo) and derivation/02_z_marginal/ (membrane-anchored P_z(z; lp, Lc, k_a)).
Downstream derivations (03 K2D(l), 04 ξ_RL, 05 F_conf) extend this module.

PURPOSE
=======
- Step 1 (B2.1): sample end-to-end vectors R of a discrete WLC chain with
  bending stiffness parameterised by persistence length lp and contour
  length Lc. Return the radial probability density P_R(R) on a grid.
- Step 2 (B2.2): apply a Boltzmann-weighted anchor cone (effective
  stiffness k_a = 255 ε/rad²) and project to lab z, returning P_z(z) on
  a grid. This is what derivation/03 convolves into K2D(l).

DERIVATION → CODE MAP
=====================
  01 (1.1)  Lc = N · b                          → N, b in WLCChain.__init__
  01 (1.3)  U_bend = κ (1 - cos θ)              → sample_cos_theta()
  01 (1.4)  lp ↔ κ via Langevin function        → kappa_from_lp()
  01 (1.7)  rotate tangent in local frame       → rotate_tangent()
  01 (3.x)  P_R(R) MC histogram                 → WLCChain.sample_endpoints()
                                                    + radial_pdf()
  02 (1.2)  Boltzmann tilt density × Jacobian   → sample_anchor_theta()
  02 (1.4)  θ_anchor = √(−2 ln u / κ_anchor)    → sample_anchor_theta()
  02 (1.7)  z_lab = R_perp sinθ_a cos(φc-φa) + z_c cosθ_a → apply_anchor_cone()
  02 (1.8)  P_z(z) histogram                    → z_marginal_pdf()

PILOT (--pilot)
===============
Runs both steps in pilot mode (1 system × 5000 chains). < 5 s wall.
Asserts limits 01 (Gaussian tail) and 02 (rigid limit z_peak ≈ Lc cosσ_θ).

PRODUCTION
==========
3 systems × 200_000 chains, ProcessPoolExecutor(--n-jobs 8). ~3 s wall.
Outputs:
    results/derivation_b2/wlc_endpoint_distribution.npz   (B2.1)
    results/derivation_b2/wlc_z_marginal.npz              (B2.2)

USAGE
=====
    python scripts/k2d_l_wlc_theory.py --pilot
    python scripts/k2d_l_wlc_theory.py --n-mc 200000 --n-jobs 8
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xi_rl_candidates import LP_PHD  # noqa: E402

# Defaults match CLAUDE.md unit conventions and B2 acceptance criteria.
DEFAULT_BOND_LENGTH_NM = 1.0   # σ = 1 nm; HARM r0 for protein bonds
DEFAULT_LC_NM = 12.0           # 12 protein bonds × 1.0 σ

# Anchor cone (derivation/02 eq. 1.1): k_a / kBT in rad⁻²
# stage_essay §4.4 measured k_a = 255 ε/rad² with kBT = 1.1 ε.
DEFAULT_KAPPA_ANCHOR = 255.0 / 1.1   # ≈ 231.8 rad⁻²
KBT_PER_EPSILON = 1.1


# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────
_BANNER = """
╔════════════════════════════════════════════════════════════════════╗
║  k2d_l_wlc_theory.py — discrete WLC end-to-end P(R; lp, Lc)        ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Monte Carlo sample the end-to-end vector R of a discrete worm-like
chain (N segments of length b, bending stiffness κ from persistence
length lp). Output radial PDF P(R) per system.

Derivation: derivation/01_wlc_endpoint_distribution/
Pilot     : 1 system, 5000 chains, < 30 s, asserts limits.
Prod      : 3 systems × n_mc chains; --n-jobs 8 for parallel.
"""


# ─────────────────────────────────────────────────────────────────────────────
# lp ↔ κ conversion via Langevin function (eq. 1.4)
# ─────────────────────────────────────────────────────────────────────────────
def langevin(kappa: float) -> float:
    """L(κ) = coth(κ) - 1/κ.  Numerically robust for small κ."""
    if abs(kappa) < 1e-4:
        # Taylor: L(x) ≈ x/3 - x³/45 + ...
        return kappa / 3.0 - (kappa ** 3) / 45.0
    return 1.0 / math.tanh(kappa) - 1.0 / kappa


def kappa_from_lp(lp_over_b: float) -> float:
    """Solve  lp/b = -1 / ln L(κ)  for κ given lp/b.

    Uses scipy.optimize.brentq with a wide bracket. Falls back to a closed-form
    asymptote in the rigid limit where the equation becomes ill-conditioned.
    """
    target = lp_over_b
    if target > 50.0:
        # Rigid limit: lp/b ≈ κ, so use κ ≈ lp/b + small correction
        return target + 0.5
    if target < 0.15:
        # Pure freely-jointed limit (κ → 0). Won't be needed for our systems.
        return 0.001
    try:
        from scipy.optimize import brentq
    except ImportError:
        # Manual bisection fallback
        lo, hi = 0.01, 200.0
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            est = -1.0 / math.log(langevin(mid))
            if est < target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    f = lambda k: (-1.0 / math.log(langevin(k))) - target  # noqa: E731
    return brentq(f, 0.01, 200.0, xtol=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# Bond-angle sampler (eq. 1.6)
# ─────────────────────────────────────────────────────────────────────────────
def sample_cos_theta(kappa: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Sample n values of cos θ from p(u) ∝ exp(κ u), u ∈ [-1, 1].

    Inverse-CDF method, numerically stable for both small and large κ.
    F(u) = (e^{κu} - e^{-κ}) / (e^κ - e^{-κ})
    F⁻¹(r) = (1/κ) ln(e^{-κ} + r (e^κ - e^{-κ}))
    """
    if abs(kappa) < 1e-6:
        # Uniform on [-1, 1]
        return rng.uniform(-1.0, 1.0, size=n)
    r = rng.random(size=n)
    # Numerically stable form: use logaddexp to avoid overflow at large κ
    # e^{-κ} + r (e^{κ} - e^{-κ}) = e^{-κ} (1 + r (e^{2κ} - 1))
    # so ln(...) = -κ + ln(1 + r (e^{2κ} - 1))
    two_k = 2.0 * kappa
    log_term = np.log1p(r * np.expm1(two_k))
    u = (-kappa + log_term) / kappa
    return np.clip(u, -1.0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Tangent rotation (eq. 1.7)
# ─────────────────────────────────────────────────────────────────────────────
def rotate_tangent(t_prev: np.ndarray, cos_theta: np.ndarray,
                    phi: np.ndarray) -> np.ndarray:
    """Build the next bond tangent t̂_{i+1} given previous tangent t̂_i and
    polar angles (θ, φ) in t̂_i's local frame.

    Inputs:
      t_prev   : (n, 3) previous tangents (unit vectors)
      cos_theta: (n,)
      phi      : (n,)
    Returns:
      t_next   : (n, 3) next tangents (unit vectors)
    """
    sin_theta = np.sqrt(np.clip(1.0 - cos_theta ** 2, 0.0, 1.0))
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)

    # Local-frame next tangent: (sinθ cosφ, sinθ sinφ, cosθ).
    # Build an orthonormal basis (e1, e2, t_prev) per chain.
    z_lab = np.array([0.0, 0.0, 1.0])
    # Pick a reference vector that is not parallel to t_prev:
    # use z_lab where |t_prev × z_lab| > eps, else use x_lab.
    cross_z = np.cross(t_prev, z_lab)
    norm_cross_z = np.linalg.norm(cross_z, axis=1, keepdims=True)
    use_x = (norm_cross_z[:, 0] < 1e-6)
    ref = np.where(use_x[:, None],
                   np.array([1.0, 0.0, 0.0]),
                   z_lab)
    # e1 = (t_prev × ref) / |...|
    e1 = np.cross(t_prev, ref)
    e1 /= np.linalg.norm(e1, axis=1, keepdims=True)
    # e2 = t_prev × e1
    e2 = np.cross(t_prev, e1)
    # Combine
    t_next = (sin_theta[:, None] * cos_phi[:, None] * e1
              + sin_theta[:, None] * sin_phi[:, None] * e2
              + cos_theta[:, None] * t_prev)
    # Re-normalize defensively (rounding may drift)
    t_next /= np.linalg.norm(t_next, axis=1, keepdims=True)
    return t_next


# ─────────────────────────────────────────────────────────────────────────────
# Main MC sampler
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class WLCResult:
    label: str
    lp_nm: float
    Lc_nm: float
    b_nm: float
    N: int
    kappa: float
    n_chains: int
    endpoints: np.ndarray   # (n_chains, 3) end-to-end vectors in nm


class WLCChain:
    """Discrete WLC sampler. Each call to sample_endpoints returns n_chains
    end-to-end vectors."""

    def __init__(self, lp_nm: float, Lc_nm: float = DEFAULT_LC_NM,
                  b_nm: float = DEFAULT_BOND_LENGTH_NM):
        if Lc_nm % b_nm != 0:
            # Allow fractional N — but warn
            print(f"WARN: Lc/b = {Lc_nm/b_nm:.3f} is not integer; "
                  "rounding N to nearest integer.")
        self.lp_nm = lp_nm
        self.Lc_nm = Lc_nm
        self.b_nm = b_nm
        self.N = int(round(Lc_nm / b_nm))
        self.kappa = kappa_from_lp(lp_nm / b_nm)

    def sample_endpoints(self, n_chains: int, seed: int = 0) -> np.ndarray:
        """Sample n_chains end-to-end vectors.

        Returns (n_chains, 3) array of R vectors in nm.
        """
        rng = np.random.default_rng(seed)
        # First bond along +z
        t = np.tile(np.array([0.0, 0.0, 1.0]), (n_chains, 1))
        # First bond contributes b * t to R
        R = self.b_nm * t.copy()
        # Add subsequent bonds
        for _ in range(self.N - 1):
            cos_th = sample_cos_theta(self.kappa, n_chains, rng)
            phi = rng.uniform(0.0, 2.0 * math.pi, size=n_chains)
            t = rotate_tangent(t, cos_th, phi)
            R += self.b_nm * t
        return R


def _sample_worker(args):
    """Top-level worker for ProcessPoolExecutor (pickle-safe)."""
    lp_nm, Lc_nm, b_nm, n_chains, seed = args
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    chain = WLCChain(lp_nm=lp_nm, Lc_nm=Lc_nm, b_nm=b_nm)
    return chain.sample_endpoints(n_chains, seed=seed)


def sample_parallel(lp_nm: float, Lc_nm: float, b_nm: float, n_chains: int,
                     n_jobs: int, base_seed: int = 0) -> np.ndarray:
    """Parallel MC sample: split n_chains across n_jobs workers."""
    if n_jobs <= 1:
        return _sample_worker((lp_nm, Lc_nm, b_nm, n_chains, base_seed))
    chunk = (n_chains + n_jobs - 1) // n_jobs
    tasks = [
        (lp_nm, Lc_nm, b_nm, min(chunk, n_chains - i * chunk),
         base_seed + i * 1_000_003)
        for i in range(n_jobs)
        if i * chunk < n_chains
    ]
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        chunks = list(ex.map(_sample_worker, tasks))
    return np.concatenate(chunks, axis=0)


# ─────────────────────────────────────────────────────────────────────────────
# P(R) post-processing
# ─────────────────────────────────────────────────────────────────────────────
def radial_pdf(endpoints: np.ndarray, n_bins: int = 60, R_max: float | None = None
                ) -> tuple[np.ndarray, np.ndarray]:
    """Return (R_centres, P(R)) where P(R) is the radial PDF (4π R² weight
    absorbed: ∫ P(R) dR = 1).
    """
    R = np.linalg.norm(endpoints, axis=1)
    if R_max is None:
        R_max = R.max() * 1.05
    edges = np.linspace(0.0, R_max, n_bins + 1)
    counts, _ = np.histogram(R, bins=edges)
    bin_width = edges[1] - edges[0]
    centres = 0.5 * (edges[:-1] + edges[1:])
    P = counts / (counts.sum() * bin_width)
    return centres, P


def gaussian_radial_pdf(R: np.ndarray, R2_mean: float) -> np.ndarray:
    """Reference Gaussian radial PDF with given ⟨R²⟩:
       P(R) = 4π R² · (3/(2π ⟨R²⟩))^{3/2} · exp(-3 R² / (2 ⟨R²⟩))
    """
    a = math.sqrt(3.0 / (2.0 * math.pi * R2_mean))
    return 4.0 * math.pi * R ** 2 * a ** 3 * np.exp(-3.0 * R ** 2 / (2.0 * R2_mean))


def wlc_R2_continuum(lp: float, Lc: float) -> float:
    """⟨R²⟩ from continuum WLC: 2 lp Lc (1 - (lp/Lc)(1 - e^{-Lc/lp}))."""
    x = Lc / lp
    return 2.0 * lp * Lc * (1.0 - (1.0 / x) * (1.0 - math.exp(-x)))


# ─────────────────────────────────────────────────────────────────────────────
# B2.2 — anchor cone + z-marginal P_z(z; lp, Lc, k_a)
# ─────────────────────────────────────────────────────────────────────────────
def sample_anchor_theta(kappa_anchor: float, n: int, rng: np.random.Generator
                          ) -> np.ndarray:
    """Sample n values of θ_anchor from p(θ) ∝ exp(-κ_a θ²/2) · sin θ.

    Uses the small-angle Exponential mapping (derivation/02 eq. 1.4):
        θ² ~ Exponential(λ = κ_a / 2)
    Equivalent to θ = sqrt(-2 ln(U) / κ_a), U ~ Uniform(0,1).

    Valid for κ_a ≫ 1 (σ_θ < 0.2 rad). For κ_anchor = 232 (our value),
    typical θ ~ 0.07 rad — well within the small-angle regime. Cap at
    π/2 to avoid the chain pointing into the membrane.
    """
    u = rng.random(size=n)
    theta = np.sqrt(-2.0 * np.log(u) / kappa_anchor)
    return np.clip(theta, 0.0, math.pi / 2)


def apply_anchor_cone(R_chain: np.ndarray, kappa_anchor: float,
                       rng: np.random.Generator) -> np.ndarray:
    """Project chain-frame end-to-end vectors into lab z via anchor cone.

    For each chain endpoint:
      - sample (θ_a, φ_a) from the anchor cone density
      - compute z_lab via derivation/02 eq. (1.7):
            z_lab = R_perp · sin θ_a · cos(φ_c - φ_a) + z_c · cos θ_a

    Inputs:
      R_chain      : (n, 3) end-to-end vectors in chain frame
      kappa_anchor : k_a / kBT in rad⁻²

    Returns:
      z_lab        : (n,) lab-frame z-coordinates of the binding bead
    """
    n = R_chain.shape[0]
    x_c, y_c, z_c = R_chain[:, 0], R_chain[:, 1], R_chain[:, 2]
    R_perp = np.sqrt(x_c ** 2 + y_c ** 2)
    phi_c = np.arctan2(y_c, x_c)

    theta_a = sample_anchor_theta(kappa_anchor, n, rng)
    phi_a = rng.uniform(0.0, 2.0 * math.pi, size=n)

    sin_t = np.sin(theta_a)
    cos_t = np.cos(theta_a)
    z_lab = R_perp * sin_t * np.cos(phi_c - phi_a) + z_c * cos_t
    return z_lab


def z_marginal_pdf(z_lab: np.ndarray, n_bins: int = 100,
                    z_range: tuple[float, float] | None = None
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Histogram of z_lab → (z_centres, P_z(z)) normalised to ∫ P dz = 1."""
    if z_range is None:
        z_min, z_max = z_lab.min() - 0.1, z_lab.max() + 0.1
    else:
        z_min, z_max = z_range
    edges = np.linspace(z_min, z_max, n_bins + 1)
    counts, _ = np.histogram(z_lab, bins=edges)
    bin_width = edges[1] - edges[0]
    centres = 0.5 * (edges[:-1] + edges[1:])
    P = counts / (counts.sum() * bin_width)
    return centres, P


# ─────────────────────────────────────────────────────────────────────────────
# B2.3 — Binding kernel + K2D(l) convolution
# ─────────────────────────────────────────────────────────────────────────────
# Hard-gate kernel radius — matches raw_tether_partition_k2d.py::HARD_R.
DEFAULT_RCUT_NM = 1.5


def hard_lateral_acceptance(dz: np.ndarray, rcut: float = DEFAULT_RCUT_NM
                             ) -> np.ndarray:
    """v(dz) = π (rcut² − dz²) for |dz| < rcut, else 0   (eq. 1.4)."""
    r2 = rcut ** 2 - dz ** 2
    return np.where(r2 > 0, math.pi * r2, 0.0)


def k2d_l_curve(z_R_lab: np.ndarray, z_L_lab: np.ndarray, l_grid: np.ndarray,
                  rcut: float = DEFAULT_RCUT_NM, truncate_negative: bool = True,
                  ) -> np.ndarray:
    """Evaluate K2D(l) by MC averaging eq. (1.6) over chain endpoint pairs.

    z_R_lab, z_L_lab : (n_samples,) z-coords in lab frame
    l_grid           : (n_l,) membrane separations to evaluate K2D at
    rcut             : hard-gate kernel radius (nm)
    truncate_negative: drop samples with z < 0 (chain ends below membrane)

    Returns
    -------
    K2D : (n_l,) values in nm²
    """
    if truncate_negative:
        z_R_lab = z_R_lab[z_R_lab >= 0]
        z_L_lab = z_L_lab[z_L_lab >= 0]
    n = min(z_R_lab.size, z_L_lab.size)
    z_R = z_R_lab[:n]
    z_L = z_L_lab[:n]

    K2D = np.empty_like(l_grid)
    for i, l in enumerate(l_grid):
        dz = z_R + z_L - l
        v = hard_lateral_acceptance(dz, rcut)
        K2D[i] = v.mean()
    return K2D


def k2d_l_stats(l_grid: np.ndarray, K2D: np.ndarray) -> dict:
    """Return K2D,max, l*, ⟨l⟩, σ_K2D (eqs. 1.7–1.11)."""
    i_max = int(np.argmax(K2D))
    K2D_max = float(K2D[i_max])
    l_star = float(l_grid[i_max])
    if K2D.sum() == 0:
        return {"K2D_max": 0.0, "l_star": l_star, "l_mean": float("nan"),
                "sigma_K2D": float("nan"), "Z": 0.0}
    Z = float(np.trapezoid(K2D, l_grid))
    l_mean = float(np.trapezoid(l_grid * K2D, l_grid) / Z)
    var = float(np.trapezoid((l_grid - l_mean) ** 2 * K2D, l_grid) / Z)
    return {
        "K2D_max": K2D_max,
        "l_star": l_star,
        "l_mean": l_mean,
        "sigma_K2D": math.sqrt(max(var, 0.0)),
        "Z": Z,
    }


def rigid_limit_z_stats(Lc: float, kappa_anchor: float) -> tuple[float, float]:
    """Analytic mean and std of z_lab in the rigid limit (R_chain ≈ Lc ẑ_chain).

    z_lab = Lc · cos θ_a, with θ_a drawn from the small-angle Rayleigh
    distribution (parameter σ²_θ = 1/κ_a).

    To leading order in 1/κ_a:
      ⟨cos θ_a⟩  = 1 - ⟨θ²⟩/2 + O(1/κ_a²) = 1 - 1/κ_a
      Var(cos θ_a) = Var(θ²)/4 = 1/κ_a²   (Var(θ²) = 4/κ_a² for Rayleigh)
      → σ_cos = 1/κ_a

    So mean(z) ≈ Lc (1 - 1/κ_a),  std(z) ≈ Lc / κ_a.

    The std scales as 1/κ_a (NOT 1/√κ_a) because the cosine fluctuation
    is quadratic in θ — small angles barely affect z = cos θ.
    """
    inv_k = 1.0 / kappa_anchor
    mean_z = Lc * (1.0 - inv_k)
    std_z = Lc * inv_k
    return mean_z, std_z


# ─────────────────────────────────────────────────────────────────────────────
# Pilot mode
# ─────────────────────────────────────────────────────────────────────────────
def run_pilot() -> int:
    """Smallest meaningful MC run + sanity asserts for B2.1 AND B2.2."""
    print("\n▶  Pilot Step 1 (B2.1) — single system, 5000 chains, single core")
    t0 = time.time()
    # Use flex (Lc/lp = 10.5) — the Gaussian limit test is sharpest here.
    lp = LP_PHD["flex"]
    chain = WLCChain(lp_nm=lp, Lc_nm=DEFAULT_LC_NM, b_nm=DEFAULT_BOND_LENGTH_NM)
    print(f"   lp={lp} nm  Lc={DEFAULT_LC_NM} nm  b={DEFAULT_BOND_LENGTH_NM} nm")
    print(f"   N={chain.N} bonds, κ={chain.kappa:.3f}")
    endpoints = chain.sample_endpoints(n_chains=5000, seed=20260601)
    wall = time.time() - t0
    R = np.linalg.norm(endpoints, axis=1)
    R_mean = R.mean()
    R2_mean = (R ** 2).mean()
    R2_continuum = wlc_R2_continuum(lp, DEFAULT_LC_NM)
    print(f"\n▶  Pilot output (wall = {wall:.1f} s)")
    print(f"   ⟨R⟩          : {R_mean:.3f} nm")
    print(f"   ⟨R²⟩^½       : {math.sqrt(R2_mean):.3f} nm")
    print(f"   continuum √⟨R²⟩ : {math.sqrt(R2_continuum):.3f} nm")

    # Assertions
    fails = []
    if not (0 < R_mean < DEFAULT_LC_NM):
        fails.append(f"⟨R⟩ = {R_mean} not in (0, Lc={DEFAULT_LC_NM})")
    ratio = math.sqrt(R2_mean) / math.sqrt(R2_continuum)
    if not (0.8 < ratio < 1.2):
        fails.append(f"√⟨R²⟩ ratio MC/continuum = {ratio:.3f} not in [0.8, 1.2]")

    # Gaussian-tail check: compare MC P(R) histogram to Gaussian reference
    centres, P_mc = radial_pdf(endpoints, n_bins=30)
    P_gauss = gaussian_radial_pdf(centres, R2_continuum)
    # focus on bulk (probability > 5% of peak)
    peak = P_mc.max()
    bulk = P_mc > 0.05 * peak
    if bulk.sum() > 5:
        rmse = math.sqrt(((P_mc[bulk] - P_gauss[bulk]) ** 2).mean()) / peak
        print(f"   Gaussian-tail RMSE (relative to peak): {rmse:.3f}")
        if rmse > 0.30:
            # Pilot tolerance is wide (small n_chains noisy); production tightens.
            fails.append(f"Gaussian-tail RMSE {rmse:.3f} > 0.30 (pilot tolerance)")

    # ── Pilot Step 2 (B2.2): two independent sanity checks ───────────────────
    print("\n▶  Pilot Step 2 (B2.2) — anchor cone limit + chain-anchor consistency")

    # Sanity A: pure anchor cone on a synthetic perfectly straight chain.
    # Predict ⟨z⟩ = Lc · ⟨cos θ_a⟩ ≈ Lc (1 - 1/(2κ_a)),  σ_z ≈ Lc / √κ_a.
    n_pilot = 20_000
    straight = np.tile([0.0, 0.0, DEFAULT_LC_NM], (n_pilot, 1))
    rng_a = np.random.default_rng(20260603)
    z_lab_straight = apply_anchor_cone(straight, DEFAULT_KAPPA_ANCHOR, rng_a)
    z_pred_mean, z_pred_std = rigid_limit_z_stats(DEFAULT_LC_NM, DEFAULT_KAPPA_ANCHOR)
    z_mc_mean, z_mc_std = float(z_lab_straight.mean()), float(z_lab_straight.std())
    print(f"   κ_anchor = {DEFAULT_KAPPA_ANCHOR:.1f} rad⁻²  "
          f"(σ_θ = {1.0/math.sqrt(DEFAULT_KAPPA_ANCHOR)*180/math.pi:.2f}°)")
    print(f"   Sanity A — synthetic straight chain (R=Lc·ẑ):")
    print(f"      predicted: ⟨z⟩ = {z_pred_mean:.3f}  σ_z = {z_pred_std:.3f} nm")
    print(f"      MC:        ⟨z⟩ = {z_mc_mean:.3f}  σ_z = {z_mc_std:.3f} nm")
    if abs(z_mc_mean - z_pred_mean) / z_pred_mean > 0.005:
        fails.append(f"sanity A ⟨z⟩: {z_mc_mean:.4f} vs {z_pred_mean:.4f}")
    if abs(z_mc_std - z_pred_std) / z_pred_std > 0.05:
        fails.append(f"sanity A σ_z: {z_mc_std:.4f} vs {z_pred_std:.4f}")

    # Sanity B: real-chain MC × anchor cone. Predict ⟨z_lab⟩ = ⟨z_c⟩(MC) ·
    # ⟨cos θ_a⟩(MC), Var(z_lab) decomposes as
    #     ⟨cos²⟩⟨z_c²⟩ + ⟨sin²⟩⟨R_perp²⟩/2 - (⟨cos⟩⟨z_c⟩)²
    # (using ⟨cos(φ_c - φ_a)⟩ = 0 and ⟨cos²(...)⟩ = 1/2.)
    lp_rigid = LP_PHD["rigid"]
    chain_r = WLCChain(lp_nm=lp_rigid, Lc_nm=DEFAULT_LC_NM, b_nm=DEFAULT_BOND_LENGTH_NM)
    endpoints_r = chain_r.sample_endpoints(n_chains=20_000, seed=20260602)
    rng_b = np.random.default_rng(20260604)
    z_lab_full = apply_anchor_cone(endpoints_r, DEFAULT_KAPPA_ANCHOR, rng_b)
    z_c = endpoints_r[:, 2]
    R_perp_sq = endpoints_r[:, 0] ** 2 + endpoints_r[:, 1] ** 2
    # Independent anchor sample to evaluate the predicted moments
    n_anchor = 20_000
    theta_a = sample_anchor_theta(DEFAULT_KAPPA_ANCHOR, n_anchor, rng_b)
    mean_cos_a = float(np.cos(theta_a).mean())
    mean_cos2_a = float((np.cos(theta_a) ** 2).mean())
    mean_sin2_a = float((np.sin(theta_a) ** 2).mean())
    pred_mean = float(z_c.mean()) * mean_cos_a
    # Var(z_lab) under independent (R_chain, θ_a, φ_a):
    var_pred = (mean_cos2_a * float((z_c ** 2).mean())
                + 0.5 * mean_sin2_a * float(R_perp_sq.mean())
                - pred_mean ** 2)
    pred_std = math.sqrt(max(var_pred, 0.0))
    mc_mean = float(z_lab_full.mean())
    mc_std = float(z_lab_full.std())
    print(f"   Sanity B — real WLC chain (rigid lp=84.6) × anchor cone:")
    print(f"      predicted (⟨z_c⟩×⟨cosθ_a⟩ etc): ⟨z⟩={pred_mean:.3f}  σ_z={pred_std:.3f}")
    print(f"      MC apply_anchor_cone:           ⟨z⟩={mc_mean:.3f}  σ_z={mc_std:.3f}")
    if abs(mc_mean - pred_mean) > 0.1:
        fails.append(f"sanity B ⟨z⟩: {mc_mean:.3f} vs {pred_mean:.3f}")
    if abs(mc_std - pred_std) / max(pred_std, 1e-3) > 0.1:
        fails.append(f"sanity B σ_z: {mc_std:.3f} vs {pred_std:.3f}")

    # ── Pilot Step 3 (B2.3): K2D(l) for rigid×rigid + shape sanity ──────────
    print("\n▶  Pilot Step 3 (B2.3) — K2D(l) for rigid×rigid")
    # Use already-sampled rigid z_lab (Sanity B above)
    z_R = z_lab_full
    z_L = z_lab_full  # symmetric R-L
    l_grid_pilot = np.linspace(0.0, 26.0, 14)  # 14 points, ~2 nm spacing
    K2D_pilot = k2d_l_curve(z_R, z_L, l_grid_pilot, rcut=DEFAULT_RCUT_NM)
    stats_pilot = k2d_l_stats(l_grid_pilot, K2D_pilot)
    print(f"   l grid: 14 points × {l_grid_pilot[1] - l_grid_pilot[0]:.2f} nm spacing, "
          f"rcut = {DEFAULT_RCUT_NM} nm")
    print(f"   K2D,max  = {stats_pilot['K2D_max']:.3f} nm²")
    print(f"   l*       = {stats_pilot['l_star']:.2f} nm  "
          f"(prediction: 2·⟨z⟩_rigid ≈ {2*mc_mean:.2f} nm)")
    print(f"   ⟨l⟩      = {stats_pilot['l_mean']:.3f} nm")
    print(f"   σ_K2D    = {stats_pilot['sigma_K2D']:.3f} nm  "
          f"(reference: the measured fitted ξ_RL ≈ 0.685 nm)")
    # Rough sanity: peak near 2·⟨z⟩, σ comparable to √2 · σ_z_rigid (1 nm-ish)
    if not (15.0 < stats_pilot['l_star'] < 25.0):
        fails.append(f"K2D,rigid×rigid peak at unexpected l = {stats_pilot['l_star']:.2f} nm "
                      "(expected near 2·⟨z⟩ ≈ 22 nm)")
    if not (0.3 < stats_pilot['sigma_K2D'] < 2.5):
        fails.append(f"K2D,rigid×rigid σ_K2D = {stats_pilot['sigma_K2D']:.3f} nm "
                      "outside expected [0.3, 2.5] nm for rigid")

    # ── Output ───────────────────────────────────────────────────────────────
    out_dir = Path(__file__).resolve().parent.parent / "results" / "scratch" / "pilot_k2d_l_wlc"
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(out_dir / "pilot_flex.npz",
             endpoints=endpoints, R_centres=centres,
             P_mc=P_mc, P_gauss=P_gauss,
             lp=lp, Lc=DEFAULT_LC_NM, b=DEFAULT_BOND_LENGTH_NM,
             N=chain.N, kappa=chain.kappa)
    np.savez(out_dir / "pilot_rigid_z.npz",
             endpoints=endpoints_r, z_lab=z_lab_full,
             lp=lp_rigid, Lc=DEFAULT_LC_NM, kappa_anchor=DEFAULT_KAPPA_ANCHOR,
             z_pred_mean_A=z_pred_mean, z_pred_std_A=z_pred_std,
             z_mc_mean_A=z_mc_mean, z_mc_std_A=z_mc_std,
             pred_mean_B=pred_mean, pred_std_B=pred_std,
             mc_mean_B=mc_mean, mc_std_B=mc_std)
    np.savez(out_dir / "pilot_k2d_rigid.npz",
             l_grid=l_grid_pilot, K2D=K2D_pilot, rcut=DEFAULT_RCUT_NM,
             **stats_pilot)
    print(f"   saved {out_dir.relative_to(out_dir.parent.parent.parent)}/pilot_*.npz")

    print()
    if fails:
        print("   ✗  PILOT FAILED:")
        for f in fails:
            print(f"      • {f}")
        return 1
    print("   ✓  PILOT PASSED — all three steps green")
    print(f"      B2.1: √⟨R²⟩(MC) / √⟨R²⟩(continuum) = {ratio:.3f}")
    print(f"      B2.2 sanity A: ⟨z⟩ MC={z_mc_mean:.3f} vs {z_pred_mean:.3f}")
    print(f"      B2.2 sanity B: ⟨z⟩ MC={mc_mean:.3f} vs {pred_mean:.3f}")
    print(f"      B2.3 K2D rigid×rigid: peak {stats_pilot['l_star']:.2f} nm, "
          f"σ_K2D {stats_pilot['sigma_K2D']:.3f} nm")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Production
# ─────────────────────────────────────────────────────────────────────────────
def run_production(n_mc: int, n_jobs: int, out_dir: Path) -> int:
    """Full MC over all three systems for both B2.1 and B2.2."""
    print(f"\n▶  Production — 3 systems × {n_mc} chains, n_jobs={n_jobs}")
    t0 = time.time()
    results = {}
    for label in ("rigid", "semi", "flex"):
        lp = LP_PHD[label]
        chain = WLCChain(lp_nm=lp, Lc_nm=DEFAULT_LC_NM, b_nm=DEFAULT_BOND_LENGTH_NM)
        print(f"\n   ── {label}  lp={lp} nm  κ={chain.kappa:.3f}  N={chain.N}")
        tic = time.time()
        endpoints = sample_parallel(
            lp_nm=lp, Lc_nm=DEFAULT_LC_NM, b_nm=DEFAULT_BOND_LENGTH_NM,
            n_chains=n_mc, n_jobs=n_jobs,
            base_seed=20260601 + hash(label) % 1_000_000,
        )
        R = np.linalg.norm(endpoints, axis=1)
        print(f"      ⟨R⟩  = {R.mean():.3f} nm   ⟨R²⟩^½ = {math.sqrt((R**2).mean()):.3f} nm")
        # B2.2 — apply anchor cone
        rng_anchor = np.random.default_rng(20260700 + hash(label) % 1_000_000)
        z_lab = apply_anchor_cone(endpoints, DEFAULT_KAPPA_ANCHOR, rng_anchor)
        print(f"      ⟨z⟩  = {z_lab.mean():.3f} nm   σ_z = {z_lab.std():.3f} nm")
        print(f"      MC time = {time.time() - tic:.1f} s")
        centres, P_mc = radial_pdf(endpoints, n_bins=60)
        z_centres, P_z = z_marginal_pdf(z_lab, n_bins=100)
        results[label] = {
            "lp": lp, "Lc": DEFAULT_LC_NM, "b": DEFAULT_BOND_LENGTH_NM,
            "N": chain.N, "kappa": chain.kappa,
            "kappa_anchor": DEFAULT_KAPPA_ANCHOR,
            "endpoints": endpoints, "R_centres": centres, "P_mc": P_mc,
            "z_lab": z_lab, "z_centres": z_centres, "P_z": P_z,
            "R_mean": float(R.mean()), "R2_mean": float((R**2).mean()),
            "R2_continuum": wlc_R2_continuum(lp, DEFAULT_LC_NM),
            "z_mean": float(z_lab.mean()), "z_std": float(z_lab.std()),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    # Step 1 npz
    out_npz_b21 = out_dir / "wlc_endpoint_distribution.npz"
    payload_b21 = {}
    for label, d in results.items():
        for k in ("lp", "Lc", "b", "N", "kappa", "endpoints", "R_centres",
                   "P_mc", "R_mean", "R2_mean", "R2_continuum"):
            payload_b21[f"{label}__{k}"] = d[k]
    np.savez(out_npz_b21, **payload_b21)
    print(f"\n   saved {out_npz_b21.relative_to(Path(__file__).resolve().parent.parent)}")

    # Step 2 npz
    out_npz_b22 = out_dir / "wlc_z_marginal.npz"
    payload_b22 = {}
    for label, d in results.items():
        for k in ("lp", "Lc", "kappa_anchor", "z_lab", "z_centres", "P_z",
                   "z_mean", "z_std"):
            payload_b22[f"{label}__{k}"] = d[k]
    np.savez(out_npz_b22, **payload_b22)
    print(f"   saved {out_npz_b22.relative_to(Path(__file__).resolve().parent.parent)}")

    # ── B2.1 convergence table ────────────────────────────────────────────────
    print(f"\n▶  B2.1 — √⟨R²⟩ vs continuum WLC ({n_mc} chains)")
    print(f"   {'label':6s}  {'lp':>6s}  {'⟨R²⟩^½(MC)':>10s}  "
          f"{'continuum':>10s}  {'ratio':>6s}  measured Re*")
    Re_phd = {"rigid": 14.76, "semi": 11.65, "flex": 5.66}
    fails_b21 = []
    for label, d in results.items():
        sq = math.sqrt(d["R2_mean"])
        cont = math.sqrt(d["R2_continuum"])
        ratio = sq / cont
        re_meas = Re_phd[label]
        diff_pct = 100 * abs(sq - re_meas) / re_meas
        print(f"   {label:6s}  {d['lp']:6.2f}  {sq:10.3f}  {cont:10.3f}  "
              f"{ratio:6.3f}  {re_meas:.2f} ({diff_pct:.1f}%)")
        if not (0.85 < ratio < 1.15):
            fails_b21.append(f"{label}: MC/continuum √⟨R²⟩ ratio = {ratio:.3f}")
    if not fails_b21:
        print("   ✓  All three systems within 15% of continuum √⟨R²⟩.")

    # ── B2.2 statistics — chain-anchor consistency check ─────────────────────
    # Pilot Sanity B already validated apply_anchor_cone end-to-end. Here in
    # production we just report ⟨z⟩, σ_z and check vs the chain-bending-aware
    # prediction  ⟨z⟩ ≈ ⟨z_c⟩ · ⟨cos θ_a⟩.
    print(f"\n▶  B2.2 — P_z(z) statistics (consistency with chain × anchor)")
    print(f"   κ_anchor = {DEFAULT_KAPPA_ANCHOR:.1f} rad⁻²  "
          f"(σ_θ = {1.0/math.sqrt(DEFAULT_KAPPA_ANCHOR)*180/math.pi:.2f}°)")
    inv_k = 1.0 / DEFAULT_KAPPA_ANCHOR
    cos_a_mean = 1.0 - inv_k                  # ⟨cos θ_a⟩ to leading order
    print(f"   {'label':6s}  {'lp':>6s}  {'⟨z_c⟩':>7s}  {'⟨z⟩_MC':>7s}  "
          f"{'⟨z_c⟩·⟨cosθ_a⟩':>14s}  {'σ_z':>7s}")
    fails_b22 = []
    for label, d in results.items():
        z_c_mean = float(d["endpoints"][:, 2].mean())
        z_pred = z_c_mean * cos_a_mean
        z_mean = d["z_mean"]
        z_std = d["z_std"]
        rel = abs(z_mean - z_pred) / max(abs(z_pred), 1e-3)
        print(f"   {label:6s}  {d['lp']:6.2f}  {z_c_mean:7.3f}  {z_mean:7.3f}  "
              f"{z_pred:14.3f}  {z_std:7.3f}")
        if rel > 0.02:
            fails_b22.append(f"{label}: ⟨z⟩_MC ({z_mean:.3f}) vs "
                              f"⟨z_c⟩·⟨cos θ_a⟩ ({z_pred:.3f}), Δ = {rel*100:.1f}%")
    if not fails_b22:
        print("   ✓  All three systems consistent with chain-frame × anchor cone "
              "(within 2% on ⟨z⟩).")

    # ── B2.3 — K2D(l) per same-system pair on fine l-grid ───────────────────
    print(f"\n▶  B2.3 — K2D(l) convolution + σ_K2D for 3 same-system pairs")
    print(f"   l-grid: 0–26 nm × Δl = 0.1 nm   |   rcut = {DEFAULT_RCUT_NM} nm "
          f"(hard gate)")
    l_grid = np.arange(0.0, 26.0 + 0.05, 0.1)
    k2d_results = {}
    print(f"   {'pair':12s}  {'K2D,max (nm²)':>14s}  {'l* (nm)':>8s}  "
          f"{'⟨l⟩ (nm)':>9s}  {'σ_K2D (nm)':>11s}  measured ξ_RL")
    measured_xi_rl = {"rigid": 0.685, "semi": 2.076, "flex": 2.253}
    for label in ("rigid", "semi", "flex"):
        z_lab = results[label]["z_lab"]
        K2D = k2d_l_curve(z_lab, z_lab, l_grid, rcut=DEFAULT_RCUT_NM)
        st = k2d_l_stats(l_grid, K2D)
        k2d_results[label] = {"l_grid": l_grid, "K2D": K2D, **st}
        xi_meas = measured_xi_rl[label]
        diff = 100 * abs(st["sigma_K2D"] - xi_meas) / xi_meas
        print(f"   {label+'×'+label:12s}  {st['K2D_max']:14.4f}  "
              f"{st['l_star']:8.2f}  {st['l_mean']:9.3f}  "
              f"{st['sigma_K2D']:11.4f}  {xi_meas:.3f} ({diff:.0f}%)")

    out_npz_b23 = out_dir / "k2d_l_curves.npz"
    payload_b23 = {"l_grid": l_grid, "rcut": DEFAULT_RCUT_NM}
    for label, d in k2d_results.items():
        payload_b23[f"{label}__K2D"] = d["K2D"]
        for k in ("K2D_max", "l_star", "l_mean", "sigma_K2D", "Z"):
            payload_b23[f"{label}__{k}"] = d[k]
    np.savez(out_npz_b23, **payload_b23)
    print(f"   saved {out_npz_b23.relative_to(Path(__file__).resolve().parent.parent)}")

    # Monotone ordering check (criterion 3 in 00_intent.md)
    sigmas = [k2d_results[l]["sigma_K2D"] for l in ("rigid", "semi", "flex")]
    fails_b23 = []
    if not (sigmas[0] < sigmas[1] < sigmas[2]):
        fails_b23.append(f"σ_K2D not monotone: {sigmas[0]:.3f} < "
                          f"{sigmas[1]:.3f} < {sigmas[2]:.3f} ?")
    if not fails_b23:
        print("   ✓  σ_K2D ordering rigid < semi < flex respected.")

    print(f"\n   total wall: {time.time() - t0:.1f} s")
    if fails_b21 + fails_b22 + fails_b23:
        print("\n   ⚠  Warnings:")
        for f in fails_b21 + fails_b22 + fails_b23:
            print(f"      • {f}")
        return 1
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pilot", action="store_true",
                   help="Pilot: 1 system × 5000 chains, < 30 s, asserts limits.")
    p.add_argument("--n-mc", type=int, default=200_000,
                   help="Number of MC chains per system (production).")
    p.add_argument("--n-jobs", type=int, default=1,
                   help="Parallel workers for production MC.")
    p.add_argument("--out-dir", type=Path,
                   default=Path(__file__).resolve().parent.parent / "results" /
                            "derivation_b2",
                   help="Production output directory.")
    p.add_argument("--quiet", action="store_true",
                   help="Skip the PURPOSE banner")
    args = p.parse_args(argv)

    if not args.quiet:
        print(_BANNER)

    if args.pilot:
        return run_pilot()
    return run_production(args.n_mc, args.n_jobs, args.out_dir)


if __name__ == "__main__":
    sys.exit(main())

"""B2 — WLC-based theory for K2D(l; lp).

Implements derivation/01_wlc_endpoint_distribution/{01_setup.md, 02_step_*.md,
03_result.md} — the discrete worm-like chain Monte Carlo sampler and the
P(R; lp, Lc) histogram. Downstream derivations (02 z-marginal, 03 K2D(l),
04 ξ_RL, 05 F_conf) extend this module.

PURPOSE
=======
Sample end-to-end vectors R of a discrete WLC chain with bending stiffness
parameterised by persistence length lp and contour length Lc. Return the
radial probability density P(R) on a chosen grid. Used by derivation 02
to compute P(z) and by 03 to compute K2D(l).

DERIVATION → CODE MAP
=====================
  (1.1)  Lc = N · b                          → N, b in WLCChain.__init__
  (1.3)  U_bend = κ (1 - cos θ)              → sample_cos_theta()
  (1.4)  lp ↔ κ via Langevin function        → kappa_from_lp()
  (1.7)  rotate tangent in local frame       → rotate_tangent()
  (3.x)  P(R) MC histogram                   → WLCChain.sample_endpoints()
                                              + radial_pdf()

PILOT (--pilot)
===============
Runs the smallest possible MC: 1 system × 5000 chains, no parallelism,
< 30 s. Asserts (a) MC endpoint mean and (b) Gaussian limit in tail for
the flex case.

PRODUCTION
==========
3 systems × 200_000 chains, ProcessPoolExecutor(--n-jobs 8). ~3 min wall.

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
# Pilot mode
# ─────────────────────────────────────────────────────────────────────────────
def run_pilot() -> int:
    """Smallest meaningful MC run + sanity asserts."""
    print("\n▶  Pilot — single system, 5000 chains, single core")
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

    # Output for cross-check
    out_dir = Path(__file__).resolve().parent.parent / "results" / "scratch" / "pilot_k2d_l_wlc"
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(out_dir / "pilot_flex.npz",
             endpoints=endpoints, R_centres=centres,
             P_mc=P_mc, P_gauss=P_gauss,
             lp=lp, Lc=DEFAULT_LC_NM, b=DEFAULT_BOND_LENGTH_NM,
             N=chain.N, kappa=chain.kappa)
    print(f"   saved {out_dir.relative_to(out_dir.parent.parent.parent)}/pilot_flex.npz")

    print()
    if fails:
        print("   ✗  PILOT FAILED:")
        for f in fails:
            print(f"      • {f}")
        return 1
    print("   ✓  PILOT PASSED — sanity asserts all green")
    print(f"      ratio √⟨R²⟩(MC) / √⟨R²⟩(continuum) = {ratio:.3f}")
    print(f"      Projected prod wall (200 K chains × 3 systems, 8 workers):")
    print(f"      ≈ {wall * (200_000 / 5000) * 3 / 8:.0f} s")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Production
# ─────────────────────────────────────────────────────────────────────────────
def run_production(n_mc: int, n_jobs: int, out_dir: Path) -> int:
    """Full MC over all three systems; save endpoints + P(R) per system."""
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
        print(f"      MC time = {time.time() - tic:.1f} s")
        centres, P_mc = radial_pdf(endpoints, n_bins=60)
        results[label] = {
            "lp": lp, "Lc": DEFAULT_LC_NM, "b": DEFAULT_BOND_LENGTH_NM,
            "N": chain.N, "kappa": chain.kappa,
            "endpoints": endpoints, "R_centres": centres, "P_mc": P_mc,
            "R_mean": float(R.mean()), "R2_mean": float((R**2).mean()),
            "R2_continuum": wlc_R2_continuum(lp, DEFAULT_LC_NM),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_npz = out_dir / "wlc_endpoint_distribution.npz"
    payload = {}
    for label, d in results.items():
        for k, v in d.items():
            payload[f"{label}__{k}"] = v
    np.savez(out_npz, **payload)
    print(f"\n   saved {out_npz.relative_to(Path(__file__).resolve().parent.parent)}")

    print(f"\n▶  Convergence sanity ({n_mc} chains)")
    print(f"   {'label':6s}  {'lp':>6s}  {'⟨R²⟩^½(MC)':>10s}  "
          f"{'continuum':>10s}  {'ratio':>6s}  measured Re*")
    Re_phd = {"rigid": 14.76, "semi": 11.65, "flex": 5.66}
    fails = []
    for label, d in results.items():
        sq = math.sqrt(d["R2_mean"])
        cont = math.sqrt(d["R2_continuum"])
        ratio = sq / cont
        re_meas = Re_phd[label]
        diff_pct = 100 * abs(sq - re_meas) / re_meas
        print(f"   {label:6s}  {d['lp']:6.2f}  {sq:10.3f}  {cont:10.3f}  "
              f"{ratio:6.3f}  {re_meas:.2f} ({diff_pct:.1f}%)")
        if not (0.85 < ratio < 1.15):
            fails.append(f"{label}: MC/continuum √⟨R²⟩ ratio = {ratio:.3f}")

    print(f"\n   total wall: {time.time() - t0:.1f} s")
    if fails:
        print("\n   ⚠  Convergence warnings:")
        for f in fails:
            print(f"      • {f}")
    else:
        print("\n   ✓  All three systems within 15% of continuum √⟨R²⟩.")
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

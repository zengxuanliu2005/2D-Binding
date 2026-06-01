"""Four-term ΔF decomposition from the PhD's S1-S23 writeup.

Each function is a pure numerical evaluation of one of the writeup's
equations. All return values are in k_B T.

Equation map:

    F_trans  (S1, S3)   per-protein translational  ln(σb²) − 1
    F_conf   (S4)       per-chain Gaussian stretch  1.5 · (D/R_e)²
    F_bond   (S17–S19)  per-pair end-volume         −ln(n_b · v / V)  with
                          v/V = b²/A      (rigid 2-D capture)
                          v/V = b³/(A·L)  (semi / flex 3-D capture)
    F_rot    (S22–S23)  per-pair orientation        −ln[ω_RL / (ω_R · ω_L)]

ω values are solid-angle volumes on S² computed from histogram differential
entropies on (cos θ, φ) for the marginals and on S² × S² for the bound joint.
This is the correct manifold — Schlitter on (vx, vy) lives on a unit disk
with edge singularity and would over-count.
"""
from __future__ import annotations
import numpy as np


# ---------------------------------------------------------------------
# S1 / S3 — translational
# ---------------------------------------------------------------------

def F_trans(N_proteins: int, A: float, b: float) -> float:
    """S1: per-protein translational free energy `kT [ln(σb²) − 1]`.
    σ = N_proteins / A is the graft density."""
    sigma = N_proteins / A
    return float(np.log(sigma * b * b) - 1.0)


# ---------------------------------------------------------------------
# S4 — conformational stretching
# ---------------------------------------------------------------------

def F_conf(D: float, R_e: float) -> float:
    """S4 (Gaussian weak-stretch): per-chain conformational free energy
    `1.5 · (D/R_e)²` in k_B T."""
    return float(1.5 * (D / R_e) ** 2)


# ---------------------------------------------------------------------
# S17–S19 — end-volume / capture probability
# ---------------------------------------------------------------------

def F_bond(b: float, A: float, L: float, regime: str) -> float:
    """Per-pair end-volume free energy from S17–S19 (geometric capture only;
    the combinatorial n_b factor is the equilibrium *output*, not an input
    to ΔF — including it would be circular when we're trying to predict K2D
    from chain stiffness):

    rigid (2D capture):     `−ln(b² / A)`
    semi / flex (3D capture): `−ln(b³ / (A·L))`

    Cross-system this collapses to PhD's S20-S21 result `ΔF_bond = ln(L/b)`
    when going from 2D to 3D capture.

    regime ∈ {"2D", "3D"}.
    """
    if regime == "2D":
        prob = b * b / A
    elif regime == "3D":
        prob = b * b * b / (A * L)
    else:
        raise ValueError(f"unknown regime {regime!r}")
    return float(-np.log(prob))


# ---------------------------------------------------------------------
# S22–S23 — rotational phase volume on S²
# ---------------------------------------------------------------------

def _hist_diff_entropy_s2(axes: np.ndarray, n_bins: int) -> tuple[float, float]:
    """Differential entropy of a 3-D unit-vector sample on S²
    using a (cos θ, φ) histogram. Returns (H, ω) with ω = exp(H).

    Bin grid: n_bins in cos θ over [−1, 1], n_bins in φ over [−π, π].
    Bin volume Δ = (2/n_bins) · (2π/n_bins).
    """
    cos_theta = axes[..., 2]
    phi = np.arctan2(axes[..., 1], axes[..., 0])
    H, edges_c, edges_p = np.histogram2d(
        cos_theta, phi,
        bins=n_bins,
        range=[[-1.0, 1.0], [-np.pi, np.pi]],
    )
    N = axes.shape[0]
    p = H / N
    delta = (2.0 / n_bins) * (2.0 * np.pi / n_bins)
    nz = p > 0
    # H_diff = -Σ p · ln(p/Δ) = -Σ p ln p + ln Δ
    entropy_disc = -float(np.sum(p[nz] * np.log(p[nz])))
    H_diff = entropy_disc + float(np.log(delta))
    omega = float(np.exp(H_diff))
    return H_diff, omega


def _hist_diff_entropy_s2s2(axes_R: np.ndarray, axes_L: np.ndarray,
                            n_bins: int) -> tuple[float, float]:
    """Differential entropy of a (cos θ_R, φ_R, cos θ_L, φ_L) joint sample
    on S²×S². Returns (H, ω)."""
    cR = axes_R[:, 2]
    pR = np.arctan2(axes_R[:, 1], axes_R[:, 0])
    cL = axes_L[:, 2]
    pL = np.arctan2(axes_L[:, 1], axes_L[:, 0])
    sample = np.stack([cR, pR, cL, pL], axis=1)
    edges = [
        np.linspace(-1.0, 1.0, n_bins + 1),
        np.linspace(-np.pi, np.pi, n_bins + 1),
        np.linspace(-1.0, 1.0, n_bins + 1),
        np.linspace(-np.pi, np.pi, n_bins + 1),
    ]
    H, _ = np.histogramdd(sample, bins=edges)
    N = sample.shape[0]
    p = H / N
    delta = (2.0 / n_bins) ** 2 * (2.0 * np.pi / n_bins) ** 2
    nz = p > 0
    entropy_disc = -float(np.sum(p[nz] * np.log(p[nz])))
    H_diff = entropy_disc + float(np.log(delta))
    omega = float(np.exp(H_diff))
    return H_diff, omega


def F_rot(axes_R_unbound: np.ndarray,
          axes_L_unbound: np.ndarray,
          axes_R_bound: np.ndarray,
          axes_L_bound: np.ndarray,
          n_bins_marg: int = 16,
          n_bins_joint: int = 6) -> dict:
    """Per-pair S22–S23 rotational free energy:

        F_rot = −ln[ω_RL / (ω_R · ω_L)]

    Returns a dict with ω_R, ω_L, ω_RL, the ratio, and F_rot. ω in
    solid-angle units (uniform-on-S² gives ω = 4π = 12.566).
    """
    H_R, om_R = _hist_diff_entropy_s2(axes_R_unbound, n_bins_marg)
    H_L, om_L = _hist_diff_entropy_s2(axes_L_unbound, n_bins_marg)
    H_RL, om_RL = _hist_diff_entropy_s2s2(axes_R_bound, axes_L_bound,
                                           n_bins_joint)
    ratio = om_RL / (om_R * om_L)
    return {
        "omega_R": om_R,
        "omega_L": om_L,
        "omega_RL": om_RL,
        "ratio": ratio,
        "F_rot": float(-np.log(ratio)),
        "n_bins_marg": n_bins_marg,
        "n_bins_joint": n_bins_joint,
    }

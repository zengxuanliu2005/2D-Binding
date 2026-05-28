"""Quasi-harmonic (Schlitter) differential entropy for the MI decomposition.

Schlitter's classical-limit formula:

    H_QH(X) = (d/2)·ln(2πe) + (1/2)·ln det Cov(X)        (nats)

For features standardised per-dimension, the (d/2)·ln(2πe) term drops out of
ΔH between bound and unbound at the same d, so what matters is

    H_QH^std(X) = (1/2)·ln det Cov_std(X) + (d/2)·ln(2πe)

The Schlitter mutual information is then

    I_QH(R; L) = H_QH(R) + H_QH(L) − H_QH(R, L)
               = (1/2)·ln (det Cov(R) · det Cov(L) / det Cov(R, L)).

By construction I_QH ≥ 0 (Cov(R, L) is block-PSD), so the sign sanity holds
even in high dimensions. The Gaussian assumption can over- or under-estimate
non-Gaussian contributions (notably torsions in the floppy K01 chain), but
not by sign — making this the right first cut for the closure attempt.
"""
from __future__ import annotations
import numpy as np


_LOG_2PI_E = float(np.log(2.0 * np.pi * np.e))


def qh_entropy(X: np.ndarray, ddof: int = 1, ridge: float = 1e-8) -> float:
    """Schlitter quasi-harmonic entropy of `X` (shape (N, d)), in nats.

    Uses eigenvalue summation rather than slogdet to gracefully handle
    rank-deficient covariance: any eigenvalue < `ridge * max(eigvals)` is
    floored, which corresponds to assuming the rank-deficient directions
    have at least this much variance. Same floor is applied bound and
    unbound, so the regularisation cancels in ΔS.
    """
    X = np.ascontiguousarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    N, d = X.shape
    if N < d + 2:
        return float("nan")
    C = np.cov(X, rowvar=False, ddof=ddof)
    C = np.atleast_2d(C)
    eigvals = np.linalg.eigvalsh(C)
    # ensure positive: replace any eigenvalue below ridge*max with ridge*max
    floor = ridge * max(float(eigvals[-1]), 1e-30)
    eigvals = np.maximum(eigvals, floor)
    return 0.5 * d * _LOG_2PI_E + 0.5 * float(np.sum(np.log(eigvals)))


def qh_mutual_info(X_R: np.ndarray, X_L: np.ndarray) -> float:
    """Schlitter MI between two sets of features (shape (N, d_R), (N, d_L))."""
    H_R = qh_entropy(X_R)
    H_L = qh_entropy(X_L)
    H_joint = qh_entropy(np.concatenate([X_R, X_L], axis=1))
    return H_R + H_L - H_joint

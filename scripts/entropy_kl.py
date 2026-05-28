"""Kozachenko–Leonenko (KL) differential entropy estimator.

For a sample matrix `X` of shape (N, d), the KL estimator is

    H(X) = ψ(N) − ψ(k) + d·ln(2) + (d/N) Σ ln(ε_i)        (L∞ norm)

where `ε_i` is the distance from sample i to its k-th nearest neighbour
(excluding i itself). With the L∞ (max) norm, the unit-ball volume drops
out and we recover the Singh–Hnizdo form above.

For the Numata-style chain-rule decomposition, the conditional entropy is

    H(Y | Z) = H(Y, Z) − H(Z)

so we never have to estimate a conditional entropy directly — all four
binding-decomposition terms reduce to differences of joint entropies that
this function knows how to compute.

Bias scaling: variance of `H_KL` ≈ O(1/k) plus an O(1/N) joint factor.
We use k=4 by default — a standard choice in the Kraskov-Stögbauer-
Grassberger family that balances bias and variance for d ≲ 100.
"""
from __future__ import annotations
import numpy as np
from scipy.spatial import cKDTree
from scipy.special import digamma


def kl_entropy(X: np.ndarray, k: int = 4) -> float:
    """Differential entropy of d-D samples (units: nats)."""
    X = np.ascontiguousarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    N, d = X.shape
    if N <= k + 1:
        return float("nan")
    tree = cKDTree(X)
    dists, _ = tree.query(X, k=k + 1, p=np.inf)
    eps = dists[:, -1]
    eps = np.maximum(eps, 1e-12)
    return float(digamma(N) - digamma(k) + d * np.log(2.0)
                 + d * np.mean(np.log(eps)))


def kl_entropy_bootstrap(X: np.ndarray, k: int = 4, n_boot: int = 50,
                          rng_seed: int = 0) -> tuple[float, float]:
    """Return (mean H, bootstrap standard error)."""
    rng = np.random.default_rng(rng_seed)
    H0 = kl_entropy(X, k)
    N = X.shape[0]
    H_boot = []
    for _ in range(n_boot):
        idx = rng.integers(0, N, size=N)
        H_boot.append(kl_entropy(X[idx], k))
    return H0, float(np.std(H_boot))

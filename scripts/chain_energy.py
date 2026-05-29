"""Per-chain potential energy from the `nvt-md.py` force field.

For each frame of `traj.xyz` and each chain, compute the intrinsic chain
potential energy U_chain = U_bond + U_angle. The chain has 12 harmonic
bonds and 11 interior cosine angles; the bonds use the same parameters
across all three K-systems but the *ecto-domain* angle stiffness depends
on the system label:

    K100:  K_ecto = 100      (rigid)
    K10 :  K_ecto = 10       (semi)
    K01 :  K_ecto = 0.1      (flex)

Anchor angles (chain_mid ∈ {1, 2, 3} — RT-RT-RT, RT-RT-RH-ish, RT-RH-RE)
stay at K = 100 in all three systems (CLAUDE.md / session 1 finding).

Formulas (from `ref/nvt-md.py`):

    U_bond(b)  = ½·K_bond·(b − r0)²            with K_bond = 100, r0 = 1.0
    U_angle(θ) = K·(1 − cos(θ − θ0))           with θ0 = 180° (= π)
              = K·(1 + cos θ)                  (since cos(θ − π) = −cos θ)

All energies in simulation `ε` units. Convert to k_B T by dividing by
1.1 (kBT ≡ 1.1 ε in the project's unit system).
"""
from __future__ import annotations
import numpy as np


# Force-field constants from ref/nvt-md.py
K_BOND = 100.0       # all protein bonds
R0_BOND = 1.0
K_ANCHOR = 100.0     # anchor-side angles, fixed across systems
THETA0 = np.pi       # equilibrium angle (180°), so cos(θ − θ0) = −cos θ

# Per-system ecto-angle stiffness (label → K value)
K_ECTO = {
    "K100": 100.0,
    "K10":  10.0,
    "K01":  0.1,
}

EPS_PER_KBT = 1.1     # kBT = 1.1 ε


def chain_potential(chain: np.ndarray, K_ecto: float
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute (U_bond, U_angle_anchor, U_angle_ecto) per chain, in ε units.

    chain : (..., 13, 3) Cartesians (assumed PBC-unwrapped per chain).
    K_ecto: ecto-angle stiffness for this system.

    Returns three (...,) arrays so the caller can attribute the
    rigid-vs-flex difference to either bonds or one of the angle bands.
    """
    # bonds: 12 length values
    bonds = np.diff(chain, axis=-2)                                # (..., 12, 3)
    b = np.linalg.norm(bonds, axis=-1)                             # (..., 12)
    U_bond = 0.5 * K_BOND * (b - R0_BOND) ** 2
    U_bond_total = U_bond.sum(axis=-1)                             # (...,)

    # interior angles at chain_mid = 1..11; vectors point AWAY from middle
    v1 = chain[..., :-2, :] - chain[..., 1:-1, :]                  # (..., 11, 3)
    v2 = chain[..., 2:, :]  - chain[..., 1:-1, :]
    cos_theta = np.einsum("...ij,...ij->...i", v1, v2) / (
        np.linalg.norm(v1, axis=-1) * np.linalg.norm(v2, axis=-1)
    )
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    # U_angle = K·(1 − cos(θ − π)) = K·(1 + cos θ)
    one_plus_cos = 1.0 + cos_theta                                 # (..., 11)
    # split anchor (chain_mid 1, 2, 3 → array indices 0, 1, 2) vs ecto (3..10)
    U_anchor_per = K_ANCHOR * one_plus_cos[..., :3]
    U_ecto_per   = K_ecto   * one_plus_cos[..., 3:]
    return U_bond_total, U_anchor_per.sum(axis=-1), U_ecto_per.sum(axis=-1)


def chain_potential_total(chain: np.ndarray, K_ecto: float) -> np.ndarray:
    """Total U_chain = U_bond + U_anchor + U_ecto, in ε units."""
    Ub, Ua, Ue = chain_potential(chain, K_ecto)
    return Ub + Ua + Ue

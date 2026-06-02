---
purpose: "Mutual-information based decomposition of inter-chain coupling (auto-generated)"
audience: "exploratory; not currently in 5-method consensus"
status: current
generated_by: scripts/mi_decomposition.py
related: "none"
---

# MI chain-rule decomposition (hybrid estimator, with bootstrap σ)

Five chain-rule blocks per protein:

    axis_ecto (2) → ext_z (1) → bonds (12) → angles (11) → torsions (10)

Schlitter (chain rule) for the first four; cyclic kNN for torsions
(treated as independent of the linear blocks — see script docstring).

## Per-system ΔS terms (k_B, bootstrap σ in parens)

| system | n_uR | n_uL | n_bP | ΔS_rot | ΔS_extz | ΔS_bonds | ΔS_angles | ΔS_torsions | **ΔS_total** |
|---|---|---|---|---|---|---|---|---|---|
| 15_120x120_K100_EPS05 | 2360 | 2360 | 5140 | -1.204 | -0.985 | -0.110 | -0.187 | -0.017 | **-2.503** |
| 15_120x120_K10_EPS05 | 5541 | 5541 | 1959 | -1.075 | -1.053 | +0.001 | -0.651 | -0.035 | **-2.813** |
| 22_120x120_K01_EPS05 | 20165 | 20165 | 1835 | -1.237 | -0.558 | -0.099 | -0.689 | -0.031 | **-2.615** |

## Cross-system −T·ΔΔS vs target ΔΔF (k_BT)

| pair | −T·ΔΔS_rot | −T·ΔΔS_extz | −T·ΔΔS_bonds | −T·ΔΔS_angles | −T·ΔΔS_torsions | **−T·ΔΔS_sum** | **target** | closed |
|---|---|---|---|---|---|---|---|---|
| flex−rigid | +0.03 | -0.43 | -0.01 | +0.50 | +0.01 | **+0.11** | **+3.56** | +3 % |
| semi−rigid | -0.13 | +0.07 | -0.11 | +0.46 | +0.02 | **+0.31** | **+2.68** | +12 % |
| semi−flex | -0.16 | +0.49 | -0.10 | -0.04 | +0.00 | **+0.20** | **-0.90** | -22 % |

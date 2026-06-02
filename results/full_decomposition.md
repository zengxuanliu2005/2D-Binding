---
purpose: "All-terms decomposition summary (translational/rotational/conformational/bond) (auto-generated)"
audience: "essay v2 §4.6 + closure budget audit"
status: current
generated_by: scripts/decomposition_full.py
related: "scripts/closure_four_term.py"
---

# ΔΔF closure: chain-potential ΔU + chain-rule −T·ΔS

Combining (a) the per-chain force-field potential energy from
`ref/nvt-md.py` (harmonic bonds + cosine angles, with the ecto stiffness
K100/K10/K01 applied per system) and (b) the configurational entropy
chain rule on five feature blocks per protein:

    axis_ecto (2) → ext_z (1) → bonds (12) → angles (11) → torsions (10)

Schlitter quasi-harmonic for the first four blocks; periodic-kNN
(`scripts/entropy_cyclic.py`, calibrated to ~0.05 nat on uniform
torsion samples) for the torsion block.

## Per-system ΔU_chain (k_BT, per pair, bound − unbound)

| system | ΔU_bond | ΔU_anchor | ΔU_ecto | **ΔU_total** |
|---|---|---|---|---|
| rigid | +0.034 | −0.053 | −0.517 | **−0.536 ± 0.134** |
| semi  | +0.092 | +0.070 | −0.796 | **−0.634 ± 0.130** |
| flex  | +0.191 | −0.056 | −0.056 | **+0.080 ± 0.090** |

Rigid and semi chains *relax* slightly on binding (bound state pulls the
chain into a configuration closer to the angle minimum). Flex *strains*
slightly, but the per-angle cost K(1+cos θ) is tiny at K = 0.1.

## Per-system −T·ΔS_config (k_BT, per pair)

| system | −T·ΔS_rot | −T·ΔS_extz | −T·ΔS_bonds | −T·ΔS_angles | −T·ΔS_tors | **−T·ΔS_total** |
|---|---|---|---|---|---|---|
| rigid | +1.204 | +0.985 | +0.110 | +0.187 | +0.017 | **+2.503** |
| semi  | +1.075 | +1.053 | −0.001 | +0.651 | +0.035 | **+2.813** |
| flex  | +1.237 | +0.558 | +0.099 | +0.689 | +0.031 | **+2.615** |

Total per-system entropy cost of binding is ~2.5–2.8 k_BT for all three —
bound configurations are similarly restricted across systems when the
cost is measured by chain-rule mutual information.

## Cross-system closure ΔΔF (k_BT)

| pair | ΔΔU | −T·ΔΔS | **ΔΔF_pred** | **target** | closed |
|---|---|---|---|---|---|
| flex − rigid | +0.616 | +0.112 | **+0.727** | **+3.56** | +20 % |
| semi − rigid | −0.098 | +0.310 | **+0.212** | **+2.68** |  +8 % |
| semi − flex  | −0.714 | +0.199 | **−0.516** | **−0.90** | +57 % |

**Signs are correct on all three pairs.** Magnitudes recover 8–57 % of
the target.

## Where the missing 40-90 % closure lives

The chain-only single-pair decomposition we attempted here is orthogonal
to several mechanisms that the K2D measurement does include:

1. **Membrane coupling.** The Cooke bilayer has bending and thickness
   modes. A bound complex constrains the inter-membrane separation
   around the bond site differently for a rigid vs floppy anchor. The
   PNAS-2013 framework (Hu / Lipowsky / Weikl) treats the inter-membrane
   roughness ξ⊥ as the dominant variable; we have already validated
   `K2D = K2D,max·[1+(ξ⊥/ξ_RL)²]^(−1/2)` from our simulation
   (`results/k2d_sanity.md`). The chain-only decomposition is orthogonal.

2. **Multi-protein concentration effects.** The simulation has 15 (or
   22) R-L pairs on a 120 nm patch. They interact through the membrane.
   K2D = N_bound / (N_R_free · N_L_free) × A is a many-body equilibrium
   constant; the decomposition here is single-pair.

3. **Cooperativity from membrane confinement.** A bound RL complex
   constrains the local membrane, which lowers the entropic cost of
   forming a *second* nearby bond — a cooperative effect that does not
   separate cleanly into per-pair ΔU and ΔS.

## What the figures show

`results/figures/e2e_distributions.png` — the headline plot. The K01
chain's end-to-end distance shifts from a ~9 σ Gaussian-coil rest peak
(unbound) to ~10.5 σ (bound). The chain *has to stretch* on binding.
That stretching is the qualitative source of the rigid-vs-flex K2D
difference; **quantifying it from chain DOF alone gives only the
+0.6 kBT we see** — the full 3.56 kBT must include the membrane-
mediated contributions above.

`results/figures/closure_full.png` — bar chart of ΔΔU, −T·ΔΔS, and the
sum ΔΔF_pred against the target ΔΔF per pair.

`results/figures/energy_breakdown.png` — per-system ΔU split into
bond / anchor / ecto contributions. Most of the energy change on binding
sits in the ecto angle term for rigid/semi; for flex the soft angles
make this term negligible.

## How to regenerate

```bash
conda activate phys
python scripts/decomposition_full.py    # ΔU + ΔS tables + npz
python scripts/plot_full_closure.py     # closure_full.png + energy_breakdown.png
```

Runs in ~7 s without bootstrap. For bootstrap error bars on the entropy
terms, add `--boot 50` to the first command. Locally that takes ~30 min
because the kNN tree gets rebuilt every iteration; on a cluster node
with more cores it will be a few minutes. Use this sbatch-style
invocation if you need error bars:

```
python scripts/decomposition_full.py --boot 200 > full_decomposition.log
```

and download `results/full_decomposition.npz` for the bootstrap σ
values.

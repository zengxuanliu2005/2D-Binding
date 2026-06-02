---
type: derivation
status: accepted
date: 2026-06-02
summary: "01_setup — F_conf = -ln P_z(D) formulation; cross-pair table; relation to Marko-Siggia (05_fconf_selfconsistency)"
derivation_folder: 05_fconf_selfconsistency
step: setup
inputs: derivation/02 P_z(z) histogram; closure_wlc_three_term D_bound + F_conf_wlc()
outputs: equations (1.1)-(1.6); the MS-vs-B2 physical decomposition
agent_read_when:
  - working on 05_fconf_selfconsistency
  - need to know the formal relation between -ln P_z and Marko-Siggia F
---

# 01_setup — F_conf from -ln P_z(D) and its relation to Marko-Siggia

## B2 estimator (this work)

The B2.2 z-marginal P_z(z; lp, Lc, κ_a) is the lab-frame probability
density of the chain binding bead (chain[12], the bead that participates
in R-L binding) at height z, given:

- WLC chain with persistence length lp, contour length Lc = 12 nm
- a harmonic anchor cone at z = 0 with stiffness κ_a = 232 rad⁻²

P_z is unimodal with peak at z = z_mode(lp) ≤ Lc·⟨cos θ_a⟩ and width
σ_z(lp). For chains with their binding bead constrained at z = D
(which is the "bound" state in our MD), the conformational free energy
relative to the unconstrained peak is

  F_conf^(B2)(D) = −ln P_z(D)                                    (1.1)

in natural units of kBT. The constant of integration (P_z's
normalisation) drops out in cross-system ΔΔF as long as we use the
same P_z definition (per nm) for both systems.

### Why anchor cone matters here (but not in MS)

P_z is the **lab-z marginal of a membrane-anchored chain**. Going from
the chain frame (R is the end-to-end vector) to the lab frame requires:

  z_lab = R·cos(θ_chain - θ_anchor) + R_perp·sin(θ_anchor)·cos(φ)  (1.2)

(see derivation/02 eq. (1.7)). The anchor angle θ_anchor is drawn from
the cone Rayleigh distribution with σ_θ² = 1/κ_a (small-angle limit).
For rigid (lp ≫ Lc, R ≈ Lc, narrow chain), the chain frame is well
defined and z_lab fluctuations are dominated by the anchor cone:

  σ_z^rigid ≈ Lc / κ_a + (small chain contribution)               (1.3)

For flex (lp ≪ Lc, R broadly distributed, chain frame ill-defined), the
anchor cone barely changes the lab z-distribution because z_chain
already has order-Lc fluctuations dwarfing the cone:

  σ_z^flex ≈ σ_z^chain × O(1)                                     (1.4)

## Marko-Siggia estimator (B1 / PPT s25)

Marko-Siggia integrated WLC gives the work to stretch a free (no
anchor) WLC chain from its natural length L₀ to extension D:

  F^(MS)(D) = (Lc/lp) · [1/(4(1-x)) − 1/4 − x/4 + x²/2],  x = D/Lc  (1.5)

This is the formula in `scripts/closure_wlc_three_term.py:F_conf_wlc()`.
It is **agnostic to membrane anchoring** — the chain is free to rotate
in 3D. The reference state is the chain's natural extension (where
F^MS = 0), not the lab z-coordinate.

For Lc/lp ≪ 1 (rigid: 12/84.6 = 0.142), even at x = 0.76 (D = 9.15,
Lc = 12) F^MS is small (0.13 kBT) because the chain has small entropic
spring constant. For Lc/lp ≫ 1 (flex: 12/1.14 = 10.5), F^MS is large
(3.38 kBT at the same x) — entropic cost of stretching a floppy chain.

## Anchor-cone surcharge

The difference between B2 and MS isolates a single physical quantity:

  Δ_anchor(label) = F_conf^(B2)(label) − F_conf^(MS)(label)        (1.6)

Δ_anchor is the cost of *holding the chain orientation* (via the cone),
on top of the chain-internal stretching cost MS computes. It is large
for stiff chains (which need very narrow cone to keep ⟨z⟩ near Lc),
small for floppy chains (chain endpoint position dominated by chain
internal entropy, not anchor orientation).

This decomposition is the headline scientific insight of derivation/05.

## Cross-pair table

Per pair (A − B) ∈ {(flex, rigid), (semi, rigid), (semi, flex)}, we
compute and tabulate four numbers:

| name | formula | source |
|---|---|---|
| ΔΔF_conf^(B2)   | F_conf^(B2)(A, D_A) − F_conf^(B2)(B, D_B)       | this step |
| ΔΔF_conf^(MS)   | F_conf^(MS)(A, D_A, lp_A, Lc) − same(B)         | B1 reimpl |
| ΔΔF_sum^(s25)   | senior PPT s25 closure total (trans+rot+MS)     | PPT slide 25 |

Note ΔΔF_sum^(s25) is not directly F_conf — it includes trans+rot. We
display it for context (to know the target the closure aims at).

## Bootstrap σ

Frame-resample of z_lab indices with replacement (200 K samples per
system, 200 bootstrap iterations). Per-iter: redo histogram, redo
linear-interp at D_bound, redo −ln. Cross-pair σ via paired bootstrap
(same iter index across systems → exact propagation of correlated MC
noise into the difference). Production σ on F_conf < 0.08 kBT per
system and < 0.1 kBT per pair — see 03_result § "Bootstrap quality".

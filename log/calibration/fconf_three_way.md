---
type: calibration
status: open
date: 2026-06-02
last_updated: 2026-06-02
summary: "Running comparison of F_conf via three estimators: B1 Marko-Siggia (chain stretch only), B2.5 -ln P_z (membrane-anchored), PPT s25 closure total — reveals anchor-cone surcharge +3.8 kBT for rigid"
prediction_source: "derivation/05_fconf_selfconsistency F_conf^(B2); B1 Marko-Siggia integrated WLC"
measurement_source: "PPT s25 closure total + senior's measured ΔΔF_K2D (raw partition)"
agreement_summary: "B2 and MS agree on flex (Δ < 0.05 kBT), disagree on rigid by 3.8 kBT (anchor-cone surcharge)"
next_check_when:
  - cluster slab MD returns measured F_conf via constrained-h Boltzmann inversion
  - senior bundle full-data returns chain_coords with bias-free D_bound
  - reflection BC replaces z<0 truncation (would shift flex by ~0.5 kBT)
related_decisions: [001, 004]
related_sessions: [session5_b2_1_2_3, session6_b2_4_5]
agent_read_when:
  - working on F_conf or closure budget revision
  - cluster slab data arrives
  - essay v2 §5.3 / §4.6 revision
---

# Calibration — F_conf three ways (B1 MS / B2.5 -ln P_z / PPT s25)

## Per-system F_conf (kBT) — running table

| date | source | rigid | semi | flex | session |
|---|---|---:|---:|---:|---|
| 2026-06-02 | B2.5 -ln P_z (this work) | **+3.91 ± 0.08** | **+2.02 ± 0.02** | **+3.34 ± 0.03** | session6_b2_4_5 |
| 2026-06-02 | B1 Marko-Siggia (Lc=12) | +0.13 | +0.80 | +3.38 | session1_a1_a3_b1 |
| (target)   | PPT s25 closure F_conf (implicit) | ? | ? | ? | senior bundle pending |

Anchor-cone surcharge Δ_anchor = F^(B2) − F^(MS):

| system | Δ_anchor | lp (nm) | reading |
|---|---:|---:|---|
| rigid | +3.785 kBT | 84.6 | MS undercounts by 30× (chain orientation cost ignored) |
| semi  | +1.212 kBT | 8.18 | partial cone visibility |
| flex  | −0.044 kBT | 1.14 | anchor cone invisible (chain entropy dominates) |

Monotone decreasing in lp — exactly the qualitative prediction from
derivation/05 00_intent acceptance criterion 4.

## Cross-pair ΔΔF_conf (kBT)

| pair | ΔΔF^(B2) ± σ | ΔΔF^(MS, B1) | ΔΔF_sum^(PPT s25 closure target) |
|---|---:|---:|---:|
| flex − rigid | −0.576 ± 0.084 | +3.253 | +3.640 |
| semi − rigid | −1.898 ± 0.076 | +0.675 | +2.470 |
| semi − flex  | −1.322 ± 0.040 | −2.577 | −1.180 |

(PPT total = trans + rot + MS conf, not just F_conf — included for
context only.)

## Three configurations of closure with B2

If we substitute ΔΔF_conf^(B2) for ΔΔF_conf^(MS) in the B1 3-term
closure, the totals become:

| pair | ΔΔF^(B1 sum, MS) | ΔΔF^(B2 sum) | PPT target |
|---|---:|---:|---:|
| flex − rigid | +5.231 | +1.40 | +3.640 |
| semi − rigid | +2.053 | −0.32 | +2.470 |
| semi − flex  | −3.178 | −1.91 | −1.180 |

So substituting B2 makes the closure **under-shoot** the PPT target —
opposite direction from B1's overshoot. Neither hits the target alone;
the truth likely involves the cluster-data D_bound (A1 bias correction)
AND a closure budget revision (e.g., including σ_p from membrane
fluctuations).

## What this calibration measures

The **anchor-cone surcharge** Δ_anchor isolates the orientation cost
of holding a stiff chain near vertical via the harmonic anchor (κ_a ≈
232 rad⁻²). For rigid this is the dominant F_conf contribution; for
flex it's invisible. This is a clean physical decomposition that PPT
s25 (which used pure MS) implicitly ignores.

The decomposition F_conf^(real) ≈ F^(MS) + Δ_anchor is the headline
narrative for essay v2 §5.3.

## What would resolve

- **Senior bundle full-data F_conf**: would tell us whether MS or B2
  is closer to the "true" PPT s25 F_conf for each system. Pending
  bundle return.
- **Cluster slab D_bound**: removes A1 sampling bias from D_bound.
  Would shift B2 F_conf for rigid by ~0.5 kBT; flex unchanged.
- **Reflection BC**: changes flex F_conf by ~0.5 kBT (drops below MS by
  the truncation correction).
- **Soft-Boltzmann kernel**: orthogonal effect; doesn't change F_conf
  but changes σ_K2D in derivation/03.

## Action triggers (per playbook log/decisions/007)

When senior data arrives:

- **On σ(R_z) rigid > 0.55 nm** → playbook S3: B2.2 σ_z calibration
  resolves; this means re-running `scripts/fconf_b2_selfconsistency.py`
  with senior's σ_z gives potentially shifted F_conf values; append row
  "B2.5 + senior_σ_z" with new numbers; note that Δ_anchor magnitude is
  what matters for the narrative — the absolute B2 F_conf may shift but
  the rigid/flex monotone trend should persist.
- **On per-system k_a > 10% spread** → playbook S4: re-derive B2.2 with
  per-system k_a, rerun B2.5; append row "B2.5 + per-system k_a"; flip
  Δ_anchor numbers accordingly.
- **On slab D_bound (bias-corrected)** → if slab data lands and gives
  rigid D_bound ≠ 9.154 nm (e.g., shifted by ~0.5 nm per A1 diagnosis):
  append row "B2.5 + slab D_bound" with shifted numbers; mark
  `derivation/05/05_open_questions.md` Q2 as resolved (or refined).
- **On reflection BC replacing z<0 truncation in derivation/06**:
  append row "B2.5 + reflection BC"; expect flex Δ_anchor stays ≈ 0
  (the truncation is what currently makes it perfectly cancel; reflection
  may shift it by ~0.5 kBT).

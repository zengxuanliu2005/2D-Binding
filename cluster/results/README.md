---
purpose: 'Convention: Claude writes <date>_analysis.md per round of senior-side data'
audience: Claude (writes); user (reads conclusions)
status: current
---

# cluster/results/ — Claude writes senior-side analysis conclusions here

## Purpose

For each round of senior-side raw outputs in
`cluster/outputs/<date>_round<N>/`, Claude reads them, compares to our
laptop's s001-only results in `results/`, and writes the diff +
interpretation here.

## Convention

```
cluster/results/
├── 2026-06-05_round1_analysis.md     # diff vs s001, interpretation
├── 2026-06-05_round1_figures/        # (optional) diff plots
│   └── ddF_full_vs_s001.png
├── 2026-06-05_round1_next_actions.md # what to ask senior next (if anything)
└── 2026-06-09_round2_verdict.md      # data-volume hypothesis CONFIRMED / REJECTED
```

The `*_analysis.md` template (MUST include the B-revision impact section
per ADR 007 — `log/decisions/007_loop2_b_revision_playbook.md`):

```markdown
---
type: analysis
status: draft   # or accepted when verdict locked
date: <YYYY-MM-DD>
round: N
summary: "<one-line: did §0 hypothesis confirm and what B revisions fire>"
related_release: cluster/RELEASES.md row <date>   # which tarball senior ran
related_decisions: [005, 007]
related_calibration: [b2_vs_measured_xi_rl, closure_methods_consensus, fconf_three_way, b2_chain_completeness]
---

# Round <N> analysis (<date>)

## Inputs read
- cluster/outputs/<date>_round<N>/closure_four_term.npz
- cluster/outputs/<date>_round<N>/closure_wlc_three_term.npz
- cluster/outputs/<date>_round<N>/raw_tether_partition.npz
- cluster/outputs/<date>_round<N>/diagnose_bias.txt
- (for diff) local results/closure_four_term.npz etc

## Key numbers

| metric | s001 (laptop) | senior's full data | Δ | verdict |
|---|---|---|---|---|
| closure_four_term ΔΔF flex−rigid | +3.99 ± 0.03 | <value> | <diff> | <converged/diverged> |
| closure_wlc_three_term ΔΔF flex−rigid | +5.23 ± 0.04 | <value> | ... | ... |
| raw_tether rigid K2D (nm²) | 9844 ± 304 | <value> | ... | ... |
| diagnose bound R Δz (nm) | −0.26 | <value> | ... | ... |
| σ(R_z) rigid (chain_coords ext) | ... | <value> | ... | S3? |
| k_a_eff per system (mean ± std)  | 255 ± 3 | <values> | ... | S4? |

## B-revision impact (per playbook log/decisions/007)

For each senior data field, identify which Conflict Map scenario (S1-S8)
fires, then apply the prescribed action from playbook 007. **Every row that
fires MUST produce a concrete file edit** (derivation/calibration/session
log) — no soft "TBD" rows allowed.

| senior data field | observed | fires? | derivation/0X/05_open_questions update | calibration row to flip | re-run? |
|---|---|---|---|---|---|
| ΔΔF flex-rigid ≈ 3.64 kBT (PPT) | <obs>  | S1?   | derivation/05 Q3 resolved | closure_methods_consensus row | rerun B1 with merged → expect 3.64 |
| ΔΔF flex-rigid ≠ 3.64 AND ≠ 5.23 | <obs>  | S2?   | (Lc question to senior first) | b2_vs_pptx_re append | rerun B2.1-2.5 with Lc=25 if confirmed |
| σ(R_z) rigid > 0.55 nm           | <obs>  | S3?   | derivation/02 Q2 resolved | b2_vs_measured_xi_rl (a); b2_chain_completeness 19/20 | rerun xi_rl_lp_prediction with new σ_z |
| k_a per system spread > 10%      | <obs>  | S4?   | (no closure; new derivation work) | new ADR 008; b2_vs_measured_xi_rl ratio test | rerun B2.2-2.5 with per-system k_a |
| slab K2D(l) shape RMSE < 10%     | (TBD)  | S5?   | (validates; no edit) | b2_vs_measured_xi_rl resolved-by-slab | optional new essay figure |
| slab K2D(l) shape RMSE > 20%     | (TBD)  | S6?   | per-system: derivation/06_* new | b2_chain_completeness B2.3 criterion 1/2 may flip | new derivation/06 folder |
| slab K2D,max ratios ≠ 12705:875:362 | (TBD) | S7? | (no closure; targets change) | new ADR 009; reconcile_methods.py TARGET | rerun reconcile + 5-method consensus |
| metadata: ξ_RL fit is fixed-h slab | (TBD) | S8?   | derivation/04 Q3 (c) closed | b2_vs_measured_xi_rl drop factor (c) | none |

(Tick `(TBD)` rows are slab-data dependent — leave as "no observation yet" if
Round N is only senior bundle (no slab). When slab MD lands, a new round of
Loop 2 analysis revisits them.)

## §0 hypothesis decision

✓ Hypothesis CONFIRMED — full data closes the gap; essay §4.5/§5.4 rewrite as "closed".
✗ Hypothesis REJECTED — bias persists; we need Workstream C (constrained-h slab MD).
? Need more rounds — specific follow-up: <what to ask senior>

## Next actions
- For user: <commit / sync / next step>
- For senior (if any): <next request>
- For Claude (Session 6d+): <which derivation edits + calibration flips + session log to write per the B-revision impact table>
```

## Round termination

Final round closes with a `<date>_round<N>_verdict.md` that fully
states whether the data-volume hypothesis is CONFIRMED, REJECTED, or
still TBD with reasons. This verdict drives whether we go to D1+D2
(essay v2) or Workstream C (constrained-h MD).

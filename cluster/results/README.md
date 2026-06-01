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

The `*_analysis.md` template:

```markdown
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

## Interpretation

<bullets explaining what these numbers mean for the data-volume hypothesis>

## Decision

✓ Hypothesis CONFIRMED — full data closes the gap; essay §4.5/§5.4
  rewrite as "closed".
✗ Hypothesis REJECTED — bias persists; we need Workstream C
  (constrained-h slab MD).
? Need more rounds — specific follow-up: <what to ask senior>

## Next actions
- For user: <commit / sync / next step>
- For senior (if any): <next request>
```

## Round termination

Final round closes with a `<date>_round<N>_verdict.md` that fully
states whether the data-volume hypothesis is CONFIRMED, REJECTED, or
still TBD with reasons. This verdict drives whether we go to D1+D2
(essay v2) or Workstream C (constrained-h MD).

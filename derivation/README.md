# derivation/ — step-by-step theory work

Per the project conventions (see plan `Derivation Documentation Conventions`),
every analytical / numerical derivation lives in its own subfolder here. The
goal is to make the work **reproducible and reviewable** months later — if a
reviewer or future-Claude asks "why this approximation?", the answer is one
markdown file away.

## Subfolder layout

```
derivation/
├── 01_wlc_endpoint_distribution/   # B2.1 — P(R; lp, Lc) from WLC chain
├── 02_z_marginal/                  # B2.2 — P(z; lp, Lc) for membrane-anchored R
├── 03_k2d_l_kernel/                # B2.3 — K2D(l) = ∫ P_z^R · P_z^L · K_bond
├── 04_xi_rl_from_lp/               # B2.4 — σ_K2D(l) → ξ_RL prediction
└── 05_fconf_selfconsistency/       # B2.5 — F_conf reback-out vs B1
```

## File convention inside each subfolder

| file | content |
|---|---|
| `00_intent.md`    | what problem this step solves; why prior approaches fail; success criterion |
| `01_setup.md`     | model + coordinate system + units; reference equations from literature |
| `02_step_*.md`    | each key substitution/approximation in its own file with WHY |
| `03_result.md`    | closed form (or semi-numerical result); limiting-case checks |
| `04_numerics.md`  | how it's implemented in code; grid/sample choices; validation tables |
| `05_open_questions.md` | known caveats; what we'd do next round |

Each `.md` starts with a status block:

```
> **Status**: drafting / under-review / accepted / superseded-by-NN
> **Date**: YYYY-MM-DD
> **Author**: Claude (Opus 4.7)
> **Inputs**: [files / measurements / prior derivations]
> **Outputs**: [equations / numerical tables]
```

## Status legend

- `drafting`      — write in progress, numbers not validated
- `under-review`  — numbers computed; cross-check pending
- `accepted`      — written into `stage_essay.md`; no further changes expected
- `superseded-by-NN` — replaced by `derivation/<NN>/`; kept for history

## Equation references

Within a subfolder, equations are numbered `(1.1)`, `(1.2)`, … Cross-file
references use `<folder>/<file>:(N.M)`, e.g. `01_wlc_endpoint_distribution/03_result.md:(3.4)`.

Code files that implement a derivation list the equation numbers in their
docstring, e.g. `scripts/k2d_l_wlc_theory.py` says
`"Implements derivation/01_wlc_endpoint_distribution/03_result.md:(3.1)–(3.4)"`.

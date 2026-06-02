---
type: onboarding
status: accepted
date: 2026-06-02
summary: "Index + conventions for derivation/: each theory step lives in its own NN_topic_slug/ subfolder with 5 standard md files (intent / setup / result / numerics / open_questions). 02_step_*.md is optional when key approximations need their own page."
agent_read_when:
  - starting a new derivation subfolder
  - need to know the 5-file structure or status flow
  - looking up which subfolder owns a particular formula
agent_skip_when:
  - working purely on a single existing derivation/<NN>/ — read that folder's 00_intent.md instead
---

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

The 5 files below are mandatory. `02_step_*.md` is **optional** — included
only when the derivation has multiple distinct approximation steps each
needing their own WHY-page; for derivations 01-05 the setup is a single
coherent block and we folded the steps into `01_setup.md`.

| file | content | required? |
|---|---|---|
| `00_intent.md`    | what problem this step solves; why prior approaches fail; success criterion | ✓ |
| `01_setup.md`     | model + coordinate system + units; reference equations; **WHY each approximation** | ✓ |
| `02_step_*.md`    | each key substitution/approximation in its own file with WHY | optional (none used in 01-05) |
| `03_result.md`    | closed form (or semi-numerical result); limiting-case checks | ✓ |
| `04_numerics.md`  | how it's implemented in code; grid/sample choices; validation tables | ✓ |
| `05_open_questions.md` | known caveats; what we'd do next round | ✓ |

Each `.md` starts with a YAML frontmatter block (mandatory, per session
6a Tier 1 convention):

```yaml
---
type: derivation
status: drafting | under-review | accepted | superseded-by-NN
date: YYYY-MM-DD
summary: "<one-line self-contained summary>"
derivation_folder: NN_topic_slug
step: intent | setup | step | result | numerics | open_questions
inputs: <files / measurements / prior derivations>
outputs: <equations / numerical tables>
agent_read_when:
  - <when a future agent should read this>
---
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

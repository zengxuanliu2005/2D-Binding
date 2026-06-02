---
type: session
status: accepted
date: 2026-06-01
session_type: infra
duration_hours: 2
summary: Collapsed bundle_for_senior/ into cluster/, created 4 IO loop dirs, renamed 5 phd_* files by purpose, added banners to 8 analysis scripts
agent_read_when:
  - need to find a script that was renamed from phd_*
  - asking why cluster/scripts/ contains analysis modules that look like duplicates of scripts/
  - looking for the "bundle" mentioned in older session logs
related_decisions: [005]
key_outputs:
  commits: [293c28d]
  artifacts:
    - cluster/ (restructured, bundle/ removed)
    - scripts/ (5 files renamed)
    - results/ (5 result files renamed)
followups:
  blockers: []
  tasks: []
---

# Session 3 — Architecture Refactor

## What we did

Three coordinated changes per user feedback at end of session 2:

### 1. Collapse cluster/bundle_for_senior/

| from | to |
|---|---|
| `cluster/bundle_for_senior/run_full_analysis.sh` | `cluster/run_analysis.sh` |
| `cluster/bundle_for_senior/README_zh.md`         | `cluster/README_for_senior_zh.md` |
| `cluster/bundle_for_senior/expected_output_layout.md` | `cluster/analysis/expected_output_layout.md` |
| `cluster/bundle_for_senior/requirements.txt`     | `cluster/requirements.txt` |
| `cluster/bundle_for_senior/src/*`                | `cluster/scripts/` (deduped) |

`cluster/` itself is now what gets tar'd and shipped to senior.
`tar czf cluster-for-senior.tgz --exclude=cluster/trial cluster/` is the
single packaging command.

### 2. Four IO loop directories

```
cluster/
├── outputs/            ← senior pushes distilled tarballs here
├── results/            → Claude writes senior-side analysis here
└── trial/
    ├── outputs/        ← user pastes trial .out files here
    └── results/        → Claude writes trial diagnoses + script patches here
```

Each has a README.md documenting the round protocol (one dated subdir
per round; final round closes with `<date>_round<N>_verdict.md`).

→ ADR 005 documents this.

### 3. Purpose-based renames

| old | new |
|---|---|
| `phd_inputs.py`                    | `system_inputs.py` |
| `phd_formula.py`                   | `free_energy_terms.py` |
| `phd_closure.py`                   | `closure_four_term.py` |
| `phd_closure_s25.py`               | `closure_wlc_three_term.py` |
| `diagnose_rigid_sample_bias.py`    | `diagnose_bound_vs_unbound.py` |
| `plot_phd_closure.py`              | `plot_closure_four_term.py` |

Result files renamed in parallel:
- `results/phd_closure.{md,npz}` → `results/closure_four_term.{md,npz}`
- `results/phd_closure_s25.{md,npz}` → `results/closure_wlc_three_term.{md,npz}`
- `results/phd_closure_data.md` → `results/closure_four_term_data.md`
- `results/figures/closure_phd.png` → `results/figures/closure_four_term.png`

5 banners added to analysis script `main()` functions:
- `closure_four_term`, `closure_wlc_three_term`, `raw_tether_partition_k2d`,
  `diagnose_bound_vs_unbound`, `reconcile_methods` — each prints PURPOSE
  on entry.

## Verification

`python scripts/closure_four_term.py --bootstrap --n-bootstrap 5 --n-jobs 2`
produces same point estimates as the pre-rename `phd_closure.py` —
refactor is behavior-preserving.

## Decisions made

- **005** (executed) double-loop IO dirs.

## How to reproduce / inspect

```bash
git show 293c28d --stat | head -60
```

## Why this matters for future sessions

- `phd_*` references in OLDER docs / older session logs are historical
  artifacts — current code never uses these names.
- `cluster/scripts/*.py` and `scripts/*.py` ARE intentional duplicates;
  bundle (= cluster/) ships to senior who runs analysis without our repo.
  Diverging the two copies is a maintenance hazard — keep them in sync.

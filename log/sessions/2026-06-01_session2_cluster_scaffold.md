---
type: session
status: accepted
date: 2026-06-01
session_type: infra
duration_hours: 5
summary: Built cluster/ scaffold including env_setup, slurm, scripts, trial/ validation, and bundle_for_senior. Banner+PURPOSE+progress+OK/WARN/FAIL on all 18 user-facing scripts.
agent_read_when:
  - need to understand why cluster/ is structured the way it is
  - working on cluster scripts and want history before the refactor
  - checking which scripts existed before phd_* → purpose-named rename
related_decisions: [005, 006]
key_outputs:
  commits: [7bbd888]
  artifacts:
    - cluster/  (entire tree, 44 files / 6789 lines)
followups:
  blockers: []
  tasks: [refactor (session 3), trial round 1 (session 4)]
---

# Session 2 — cluster/ scaffold + bundle_for_senior

## What we did

After session 1, the strategy required cluster involvement (constrained-h
slab MD or full-data §0 test via senior bundle). Built scaffold from
scratch:

```
cluster/
├── env_setup/       check_env.sh + install_phys.sh
├── slurm/           _base + single_pilot + array_extract + array_slab_md
├── scripts/         extract_one_replica, merge_chain_coords, explore_replicas,
│                    nvt-md-constrained-h (skeleton), analyze_slab_traj (placeholder)
├── trial/           01-04 + README + REPORT_BACK
├── corrections/     README
├── analysis/        run_section0_full + run_slab_full
├── outputs/         (gitignored)
├── results/         (intentionally empty)
└── bundle_for_senior/
    ├── README_zh.md
    ├── requirements.txt
    ├── run_full_analysis.sh
    ├── expected_output_layout.md
    └── src/   (15 .py files copied from local scripts/)
```

## Conventions established this session

All user-facing scripts (trial + slurm + Python entry points + analysis
wrappers + bundle orchestrator) follow the same convention:

- ASCII banner box at top
- "PURPOSE" block printed at runtime
- Numbered sections with progress prints (▶ Step N/M — ...)
- OK / WARN / FAIL helper functions in shell scripts
- Final summary section explaining what passed and the next step

→ ADR 006 documents this.

## Pilot results

`cluster/scripts/extract_one_replica.py --pilot` on local s001 K100: **OK,
n_frames=50, 0.2 MB npz, ~3 s wall**. This validated the entire pipeline
shape before shipping.

## Known issues at end of session

3 problems flagged for session 3 refactor:
1. `bundle_for_senior/` is redundant — cluster/ itself IS the bundle (when
   tar'd minus trial/)
2. Missing `cluster/{outputs,results,trial/outputs,trial/results}/` IO loop
   dirs with READMEs — would enable structured round-trip with user + senior
3. `phd_*` filenames (phd_inputs, phd_closure, ...) are colloquial. Rename
   by purpose.

## Decisions made

- **005** double-loop IO dirs (planned, executed in session 3)
- **006** banner+PURPOSE runtime print on all user-facing scripts

## How to reproduce / inspect

```bash
git show 7bbd888 --stat       # see all 44 files added this session
ls cluster/
bash cluster/env_setup/check_env.sh   # exits early since phys not present
                                       # (session 4 resolves this)
```

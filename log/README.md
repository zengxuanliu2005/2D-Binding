---
type: onboarding
status: accepted
date: 2026-06-02
summary: log/ holds the project's session memory — narrative session logs, ADR-style decisions, and running calibration tables. Frontmatter-driven for token-efficient agent consumption.
agent_read_when:
  - new agent landing in the repo for the first time
  - need to know what was decided and why (vs what code does)
  - want to understand which session produced which artifact
  - need to update a running calibration table
agent_skip_when:
  - just executing a clear task with known files
  - working purely in code (use docstrings / banners instead)
---

# log/ — project session memory

> Three layers, each with strict YAML frontmatter so any reading agent can
> decide in ≤ 10 lines whether to keep reading.

## Why this folder exists

| recorded where | what it captures |
|---|---|
| `plan` (user-dir + ExitPlanMode) | INTENT — what we plan to do |
| `CLAUDE.md` | ONBOARDING — what new agents need to know first |
| `derivation/` | THEORY — why the formula is what it is |
| `results/*.md` | DATA — distilled numbers from scripts |
| `git log` | CHANGES — granular per-commit diff |
| **`log/sessions/`** | **JOURNEY** — what we actually did in each session, including failed approaches |
| **`log/decisions/`** | **RATIONALE** — why we chose A over B, immutable once written |
| **`log/calibration/`** | **AGREEMENT** — running tables of prediction vs measurement |

## Layout

```
log/
├── README.md                            ← you are here (schema source of truth)
├── sessions/<YYYY-MM-DD>_<slug>.md      ← one per work session
├── decisions/<NNN>_<slug>.md            ← ADR-style numbered immutable
└── calibration/<topic>.md               ← running tables, append-most-recent
```

## Frontmatter schema

Every md in `log/` opens with a YAML frontmatter block delimited by `---`.
**The first ~10 lines must let a reading agent decide whether to keep
reading.** Anything below the frontmatter is optional context.

### Universal core (all types)

```yaml
---
type: session | decision | calibration | onboarding
status: drafting | under-review | accepted | superseded-by-<id> | deprecated
date: YYYY-MM-DD                   # creation date
summary: <1-line self-contained>   # what this doc IS, in one line
agent_read_when:                    # conditions for "keep reading"
  - <condition>
  - <condition>
---
```

### `type: session` extensions

```yaml
session_type: theory | infra | analysis | debugging | writing | meta
duration_hours: <int>
related_decisions: [adr_id, ...]
key_outputs:
  commits: [<hash>, ...]
  artifacts: [<path>, ...]
followups:
  blockers: [<short list>]
  tasks: [<task id>]
```

### `type: decision` extensions

```yaml
adr_id: <NNN>                       # zero-padded; allocated in order
alternatives_considered:
  - <1-line option>
  - <1-line option>
expected_revision_trigger: <new info that would reopen this>
related_sessions: [<slug>, ...]
related_calibration: [<topic>, ...]
```

### `type: calibration` extensions

```yaml
last_updated: YYYY-MM-DD
prediction_source: <path or formula>
measurement_source: <path or PPT slide>
agreement_summary: <ratio / RMSE / verdict line>
next_check_when: <data event that would update this>
related_decisions: [adr_id, ...]
```

## How agents should read this folder

### "I just landed in the repo"
1. Read `CLAUDE.md` — navigation map points you here if needed.
2. Read the most recent `log/sessions/` entry — frontmatter alone tells you the state.
3. Stop. Body of older sessions is rarely necessary unless re-deriving rationale.

### "I'm continuing a stalled workstream"
1. Read the most recent `log/sessions/<slug>.md` whose followups list mentions your workstream.
2. Follow `related_decisions` to relevant ADRs.
3. If calibration tables relate, check `next_check_when` to know if data has arrived.

### "I'm picking up after a conflict (cluster results vs theory disagree)"
1. Read `log/calibration/<topic>.md` — frontmatter `agreement_summary` is the headline.
2. Look at the most recent row in the table for context.
3. Follow `related_decisions` to find which ADRs may need revising.

## Conventions

- **Slugs**: lower_snake_case, short (≤ 4 words).
- **Numbering** (decisions/): zero-padded 3 digits, allocated in chronological order.
  Numbers ARE NEVER REUSED — superseded ADRs keep their number, get
  `status: superseded-by-<NNN>` instead.
- **Append, don't edit**: session logs are written once, immutable. If
  follow-up clarifies something, write a new session log that references
  the previous one.
- **Calibration tables**: rows append newest-on-top. Each row notes which
  session updated it.
- **Cross-references**: use slug or `adr_id`, never raw paths (so renaming
  doesn't break links).

## Index

(Updated each time a new file is added.)

### Sessions
| date | slug | type | summary |
|---|---|---|---|
| 2026-05-31 | session1_a1_a3_b1                | analysis | A1 diagnosis + A3 bootstrap + B1 s25 reimpl |
| 2026-06-01 | session2_cluster_scaffold        | infra    | 44 files / 6789 lines of cluster/ + bundle scaffold |
| 2026-06-01 | session3_refactor                | infra    | collapse bundle/, add IO dirs, rename phd_*  |
| 2026-06-01 | session4_trial_round1_round2_prep | debugging | trial 1-4 outputs + diagnosis + compute-node SBATCH |
| 2026-06-02 | session5_b2_1_2_3                 | theory   | WLC MC + P_z(z) + K2D(l) all three steps green |
| 2026-06-02 | session6_b2_4_5                   | theory   | B2.4 ratio test beats Xu 8-14×; B2.5 anchor-cone surcharge +3.8 kBT for rigid |

### Decisions
| adr_id | slug | status | summary |
|---|---|---|---|
| 001 | lc_12nm_ecto_convention             | accepted | Lc = 12 nm (ecto only) for WLC theory pending senior confirmation |
| 002 | phys_env_local_only_on_cluster      | accepted | Don't require phys env on cluster; use system base python |
| 003 | hard_gate_kernel_first              | accepted | B2.3 uses hard cutoff kernel; soft Boltzmann is a future swap |
| 004 | z_negative_truncation               | accepted | Drop WLC samples with z < 0 (unphysical chain-through-membrane) |
| 005 | double_loop_io_dirs                 | accepted | cluster/{trial/,}outputs|results/ for round-trip with user + senior |
| 006 | purpose_banner_runtime_print        | accepted | All user-facing scripts print PURPOSE banner on entry |

### Calibration
| topic | status | summary |
|---|---|---|
| b2_vs_measured_xi_rl       | partially-resolved | B2.4 absolute 1.3-1.9× over, ratio test rigid:flex = 0.39 vs measured 0.30 (Xu 1.00, 229% off) |
| b2_vs_pptx_re              | open | WLC √⟨R²⟩ under-predicts senior PPT Re by 9-21% |
| closure_methods_consensus  | open | 5 methods within 0.22 kBT consensus on flex-rigid; semi/flex disputed by L_c |
| fconf_three_way            | open | B2.5 reveals anchor-cone surcharge +3.8/+1.2/-0.04 kBT (rigid/semi/flex) that MS misses |

---
type: decision
status: accepted
adr_id: 005
date: 2026-06-01
summary: cluster/{trial/,}outputs/ for raw data, cluster/{trial/,}results/ for Claude analysis — enables round-trip protocol with user (trial) and senior (full data)
agent_read_when:
  - adding new files to cluster/outputs or cluster/results
  - documenting a new round of trial outputs or senior responses
  - explaining the file-naming convention to a collaborator
alternatives_considered:
  - "one bidirectional dir per actor (no inputs/outputs split)"
  - "separate top-level dirs (e.g. inbox/ outbox/)"
  - "git branches per round"
expected_revision_trigger: protocol scales to ≥ 5 rounds and dated subdirs become unmanageable
related_sessions: [session3_refactor]
related_calibration: []
---

# ADR 005 — Double-loop IO dirs in cluster/

## Context

After session 2, the cluster/ tree had no obvious place for:
- User's trial outputs (.out files from running trial scripts on cluster-A)
- Claude's diagnoses of those outputs + script patches
- Senior's distilled tarballs (when she runs the bundle on her server)
- Claude's analysis of senior's outputs

Without a structured location, the workflow was ad-hoc and prone to
"wait, where do I put this?".

## Decision

Four IO loop directories with a strict round protocol:

```
cluster/
├── outputs/            ← senior pushes raw / distilled here
│   └── <YYYY-MM-DD>_round<N>/
├── results/            → Claude writes analysis here
│   └── <YYYY-MM-DD>_round<N>_analysis.md
└── trial/
    ├── outputs/        ← user pushes raw .out here
    │   └── <YYYY-MM-DD>_round<N>/
    └── results/        → Claude writes diagnosis here
        └── <YYYY-MM-DD>_round<N>_diagnosis.md
```

Each round closes with a `<date>_round<N>_verdict.md` declaring the loop
done OR triggering round N+1.

## Rationale

- Mirrors the natural data flow: raw data IN, processed analysis OUT.
- Two independent loops (user-side trial, senior-side §0 bundle) need
  separate dirs because the cadence and content differ.
- Dated round subdirs preserve history without git branch overhead.
- Each dir gets its own README.md documenting the round protocol.

## Consequences

- Every cluster/-related session log MUST reference which round it
  worked on, by path.
- `cluster/outputs/` is partially gitignored:
  - small distilled files (TSV, npz, md) tracked
  - large raw outputs (extracted/, slab/, logs/, *_pilot/) gitignored
- The 4 READMEs document the round-N protocol so collaborators don't
  have to read this ADR.

## Revision plan

If the protocol scales to ≥ 5 active rounds simultaneously and dated
dirs become a forest:
- Add `cluster/{outputs,results}/CHANGELOG.md` index pointing to the
  active round.
- Consider archiving old rounds into `cluster/outputs/_archive/`.

## Files affected

- `cluster/outputs/README.md`
- `cluster/results/README.md`
- `cluster/trial/outputs/README.md`
- `cluster/trial/results/README.md`
- `cluster/README.md` (top-level workflow doc references the loop)
- `cluster/.gitignore` (selective ignores)

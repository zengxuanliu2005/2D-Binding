# cluster/trial/results/ — Claude writes diagnosis + script-patch plans here

## Purpose

For each round of user trial-script outputs in
`cluster/trial/outputs/<date>_round<N>/`, Claude reads them and writes
a diagnosis here, plus any `cluster/scripts/*` patches needed to fix
what the trial uncovered.

## Convention

Each round of diagnosis produces one or more files keyed by date and
round number:

```
cluster/trial/results/
├── 2026-06-02_round1_diagnosis.md   # what was found, what needs fixing
├── 2026-06-02_round1_patch.diff     # (optional) the script changes themselves
├── 2026-06-02_round1_next_actions.md # what user should do next
└── 2026-06-04_round2_verdict.md     # round 2 was last; pipeline green
```

The `*_diagnosis.md` template:

```markdown
# Round <N> diagnosis (<date>)

## Inputs read
- cluster/trial/outputs/<date>_round<N>/01_env_check.out
- cluster/trial/outputs/<date>_round<N>/02_paths_check.out
- ...

## What I found
- <bullet per concrete issue, with line refs into the .out files>

## What needs fixing in cluster/scripts/
- File: cluster/scripts/<name>.py:<line>
  Change: <description or patch>
- ...

## What's already correct
- <things that the trial confirmed work as expected>

## Next round
- User pulls, reruns: bash cluster/trial/04_extract_pilot.sh
- Expected: ✓✓✓ PASSED
```

## Round termination

The round is closed when Claude commits both:

1. The diagnosis + patch in this folder
2. The actual script fixes in `cluster/scripts/`

Trial pipeline is "validated" when a `<date>_round<N>_verdict.md` here
says all 4 trial scripts pass on cluster-A with no required changes.
At that point we ship the bundle to senior (see `cluster/outputs/`
README for the senior-side double-loop).

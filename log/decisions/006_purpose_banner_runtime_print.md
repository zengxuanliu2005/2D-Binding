---
type: decision
status: accepted
adr_id: 006
date: 2026-06-01
summary: All user-facing scripts (shell, Python entry points, SLURM templates) print a PURPOSE banner on entry, with numbered progress sections and OK/WARN/FAIL helpers
agent_read_when:
  - writing a new user-facing script (anything in cluster/ or scripts/ with main())
  - extending an existing script and need to match the banner pattern
  - asking why the trial scripts print so much
alternatives_considered:
  - "docstrings only (Python convention)"
  - "banner only in README, scripts stay silent"
  - "banner + structured progress at runtime (recommended)"
expected_revision_trigger: banners become excessive for non-interactive automation contexts (CI etc.)
related_sessions: [session2_cluster_scaffold, session3_refactor]
related_calibration: []
---

# ADR 006 — Banner + PURPOSE + progress + OK/WARN/FAIL at runtime

## Context

When the user (or a senior, or a future agent) runs a script on cluster,
they should see what's running and what it does WITHOUT needing to read
the source. Bare scripts that print only their results are hostile to
operators who haven't memorised what each one does.

Additionally, when something goes wrong, the runtime output should
clearly mark which step failed (OK / WARN / FAIL) so a remote diagnosis
can be done from logs alone.

## Decision

Every user-facing script (CLI Python with main(), Shell scripts, SLURM
templates) follows this template:

```
╔════════════════════════════════════════════════════════════════════╗
║  <script-name> — <one-line role>                                  ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
<3-5 line explanation of what this script does, why, expected wall time>

▶  Step 1/N — <description>
   ✓ <ok line>
   ⚠ <warn line, non-fatal>
   ✗ <fail line>

▶  Step 2/N — ...

▶  Summary
   ✓✓✓ ALL CHECKS PASSED.  Next: <command>
   ✗✗✗ AT LEAST ONE CHECK FAILED.  Common fixes: ...
```

## Rationale

- The scriptops experience matters as much as the code correctness.
- Numbered Step N/M lets remote operators say "it failed at step 3" and
  Claude can immediately jump to the right place.
- OK/WARN/FAIL colour-tagged output (using ASCII ✓⚠✗) is parseable by
  both humans and downstream agents.
- The pattern works equally well in shell, Python, and SBATCH context.

## Consequences

- 18 user-facing scripts (4 trial + 4 SLURM + 5 cluster scripts + 3
  analysis wrappers + 1 bundle orchestrator + 1 compute_node_check SBATCH)
  follow this pattern.
- A `_BANNER = """..."""` constant + `def _print_purpose():` is the
  standard pattern in Python scripts.
- Shell scripts use `hr()`, `section()`, `ok()`, `warn()`, `fail()`
  helper functions defined at the top.

## Revision plan

If the pattern becomes excessive in automated contexts:
- Add `--quiet` flag to suppress the banner (already supported in some
  Python scripts).
- For SLURM jobs, banners are appropriate even in non-interactive runs
  because the log file is the only diagnosis source.

## Files affected

Pattern applied to (at least):
- `cluster/trial/01_env_check.sh` ... `04_extract_pilot.sh`
- `cluster/trial/slurm/compute_node_check.slurm`
- `cluster/env_setup/check_env.sh`
- `cluster/slurm/{_base,single_pilot,array_extract,array_slab_md}.slurm`
- `cluster/scripts/{explore_replicas.sh, extract_one_replica.py,
   merge_chain_coords.py, nvt-md-constrained-h.py, analyze_slab_traj.py}`
- `cluster/analysis/{run_section0_full.sh, run_slab_full.sh}`
- `cluster/run_analysis.sh`
- `scripts/{closure_four_term, closure_wlc_three_term,
   raw_tether_partition_k2d, diagnose_bound_vs_unbound,
   reconcile_methods}.py`

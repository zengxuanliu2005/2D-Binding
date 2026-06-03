---
purpose: "Log of cluster bundle releases authorised for the off-site collaborator (Loop 1 → Loop 2 transitions)"
audience: user (which SHA was released when) + Claude (provenance for incoming off-site full-data results)
status: current
---

# cluster/RELEASES.md — bundle releases authorised for off-site full-data run

Each row records that the trial loop converged at a given git SHA and the
bundle was authorised for off-site rsync. When her distilled results return,
the analysis in `cluster/results/<date>_round<N>_analysis.md` should reference
the release row here so we can recover exactly which script versions she ran.

The off-site collaborator does NOT receive a tarball — she rsyncs cluster/
directly from the shared cluster-A path. The user is responsible for keeping
cluster-A in sync with this released SHA via cyberduck (cluster-A has no git).

## Releases

| release date | git SHA | git ref | trial verdict source | notes |
|---|---|---|---|---|
| 2026-06-03 | `ff90300` + Session 9 patches | main | 2026-06-03_pilot_fullrun_verdict.md | Trial verdict from ff90300; Session 9 added MD_PARENT auto-detect + per-system symlinks + system_inputs path fallback (see log/sessions/2026-06-03_session9_pilot_fullrun_cp_workflow.md). The off-site collaborator rsyncs the cluster/ on cluster-A which reflects HEAD at her access time. |

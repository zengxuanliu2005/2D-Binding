---
purpose: 'Convention: senior''s distilled tarball unpacks into <YYYY-MM-DD>/ subdir
  here'
audience: user (after senior sends data) + Claude
status: current
---

# cluster/outputs/ — senior's distilled results land here

## Purpose

Senior runs `bash cluster/run_analysis.sh` on her server (where her
full MD data lives). It produces `distilled/` with ~5 MB of analysis
tables and bootstrap data. She sends `distilled/` back via
WeChat/email; the user untars it here.

## Convention

Each round of senior-side results goes into a dated subdirectory:

```
cluster/outputs/
└── 2026-06-05_round1/
    ├── inventory.tsv
    ├── closure_four_term.{md,npz}
    ├── closure_wlc_three_term.{md,npz}
    ├── raw_tether_partition.{md,npz}
    ├── diagnose_bias.txt
    ├── method_reconciliation.md
    ├── method_reconciliation.png
    └── run_log.txt
```

This folder is mostly small files; we commit them to git so the
analysis Claude writes in `cluster/results/` can reference exact
provenance.

## How to populate

```bash
# After senior sends back distilled.tgz via WeChat/email
mkdir -p cluster/outputs/$(date -I)_round1
tar xzf ~/Downloads/distilled.tgz -C cluster/outputs/$(date -I)_round1/ --strip-components 1
git add cluster/outputs/$(date -I)_round1/
git commit -m "outputs: senior round 1 distilled results"
git push
```

## Round termination

A round is closed when:

1. Senior's raw outputs are in `cluster/outputs/<date>_round<N>/`
2. Claude's analysis is in `cluster/results/<date>_round<N>_analysis.md`
3. Either: a follow-up question is sent to senior (Round N+1), or a
   `<date>_round<N>_verdict.md` declares §0 closed.

§0 data-volume hypothesis is "closed" when:
- ✓ All 3 senior ΔΔF values match her PPT s25 numbers within bootstrap σ
  → "you had less data" hypothesis confirmed; essay §4.5/§5.4
    rewrites as "closed by full data"
- ✗ Senior's numbers still match s001 results within noise
  → A1 diagnosis was right; bias is intrinsic; we need Workstream C
    (constrained-h slab MD) to fix §4.5/§5.4

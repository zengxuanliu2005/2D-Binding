---
purpose: "Convention: off-site distilled results land in <YYYY-MM-DD>_round<N>/ subdirs here (cp'd by the off-site collaborator into this shared dir; downloaded to laptop via cyberduck)"
audience: user (manages laptop ↔ cluster-A sync) + Claude (reads round dirs for Loop 2 analysis)
status: current
---

# cluster/outputs/ — the off-site distilled results land here

## Purpose

The off-site collaborator runs `bash cluster/run_analysis.sh` (or the
SBATCH wrapper) on her cluster. It produces `distilled/` with ~5 MB of
analysis tables and bootstrap data. She **does not transfer files** —
she has shared filesystem access to cluster-A, so she just `cp`s the
distilled directory into this folder under a dated round subdir.

The user then cyberduck-downloads the round dir to the laptop and
commits/pushes it.

## Convention

Each round of off-site-run-side results goes into a dated subdirectory:

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

The off-site collaborator runs (on her cluster, after the SLURM job
finishes):

```bash
ROUND_DIR=/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/outputs/$(date -I)_round1
mkdir -p $ROUND_DIR
cp -R $DEST/cluster/outputs/distilled/* $ROUND_DIR/
# Then WeChat-pings Zengxuan: "distilled is in $ROUND_DIR"
```

Then the user (on laptop) cyberduck-downloads the round dir and commits:

```bash
# cyberduck DOWNLOAD /mnt/.../cluster/outputs/<date>_round1/ → local cluster/outputs/
cd /Users/liuzengxuan/VSCode/2D-Binding
git add cluster/outputs/$(date -I)_round1/
git commit -m "outputs: round 1 distilled results from off-site full-data run"
git push origin main
```

## Round termination

A round is closed when:

1. The raw outputs are in `cluster/outputs/<date>_round<N>/`
2. Claude's analysis is in `cluster/results/<date>_round<N>_analysis.md`
3. Either: a follow-up question is sent to off-site collaborator (Round N+1), or a
   `<date>_round<N>_verdict.md` declares §0 closed.

§0 data-volume hypothesis is "closed" when:
- ✓ All 3 off-site collaborator ΔΔF values match her PPT s25 numbers within bootstrap σ
  → "you had less data" hypothesis confirmed; essay §4.5/§5.4
    rewrites as "closed by full data"
- ✗ The numbers still match s001 results within noise
  → A1 diagnosis was right; bias is intrinsic; we need Workstream C
    (constrained-h slab MD) to fix §4.5/§5.4

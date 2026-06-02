---
purpose: Schema off-site collaborator should expect run_analysis.sh to write under cluster/outputs/distilled/
audience: off-site collaborator + user (after bundle return)
status: current
---

# Expected output layout

After `bash run_full_analysis.sh` finishes, this directory should contain
`distilled/` with the following files. Total size ~5 MB, all safe to email.

```
distilled/
├── inventory.tsv
│       Columns: system, n_replicas, total_frames, total_bound_R, total_bound_L
│       Used to sanity-check that we found the right data on the off-site compute server.
│
├── closure_four_term.md                  ~10 kB
├── closure_four_term.npz                 ~200 kB    [bootstrap arrays per term]
│       Output of `python closure_four_term.py --bootstrap --n-bootstrap 200 --n-jobs 8`
│       run on the FULL merged data (not s001 only).
│       Key tables:
│           - Per-system F_t / F_c / F_bond / F_rot
│           - Cross-system ΔΔF (point + σ) for the 3 pairs
│       This is the table to diff vs PPT s25 (3.64 / 2.47 / −1.18).
│
├── closure_wlc_three_term.md              ~10 kB
├── closure_wlc_three_term.npz             ~200 kB
│       Output of `python closure_wlc_three_term.py --bootstrap --n-bootstrap 200 --n-jobs 8`
│       Marko-Siggia WLC closure with L_c = 12 nm. The PPT s25 numbers
│       are the comparison point.
│
├── raw_tether_partition.md         ~5 kB
├── raw_tether_partition.npz        ~500 kB    [bootstrap arrays]
│       Output of `python raw_tether_partition_k2d.py --bootstrap --n-bootstrap 200 --n-jobs 8`
│       Rigid absolute K2D — we expect 9844 nm² on s001, target 12705.
│       If the off-site full-data run gives ~12705, the "data volume" hypothesis wins.
│
├── diagnose_bias.md                ~5 kB
│       Output of `python diagnose_bound_vs_unbound.py`
│       bound vs unbound R chain geometry (z reach, term tilt) per system.
│       s001 showed Δz=−0.26 nm / Δtilt=+7° for rigid; if full data shrinks
│       these to noise, that confirms data-volume explanation.
│
├── reconcile_methods.md            ~10 kB
│       5-method ΔΔF reconciliation table.
│
└── run_log.txt                     stdout/stderr from the whole pipeline
        If anything went wrong, the trace is here.
```

## What we'll do with these

Zengxuan + Claude will diff them against the s001-only results currently in
the repo's `results/` directory:

| metric | s001 | the off-site full | verdict if equal | verdict if off-site collaborator matches PPT |
|---|---|---|---|---|
| Four-term ΔΔF flex-rigid | +3.99 | ? | data-vol explanation rejected | confirmed |
| closure_wlc_three_term ΔΔF flex-rigid | +5.23 | ? | rejected | confirmed |
| raw_tether rigid K2D (nm²) | 9844 | ? | rejected | confirmed |
| diagnose bound R Δz (nm) | −0.26 | ? | bias is real | bias is statistical noise |

Either outcome is useful — it tells us whether to write essay §4.5 / §5.4
as a real physical limitation (needs constrained-h MD to fix) or a
statistical artefact (closes automatically with more data).

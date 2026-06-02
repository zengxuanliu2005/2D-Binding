---
purpose: 'Top-level cluster/ guide: how to use this tree as both senior-bundle and
  cluster-A workspace'
audience: senior (after tarball) + user (on cluster-A) + Claude
status: current
---

# cluster/ — what to ship to senior + what to run on cluster-A

This folder is **both** the validation harness we run on cluster-A
AND the tarball we ship to senior.

```
                  ┌──────────────────────────────────────────┐
                  │  cluster/                                │
                  │  ├── trial/      ← user runs this on     │
                  │  │                  cluster-A             │
                  │  └── (everything else) ← senior runs     │
                  │                          this on her server│
                  └──────────────────────────────────────────┘
```

## Top-level layout

```
cluster/
├── README.md                       ← you are here
├── README_for_senior_zh.md         ← what senior reads first
├── requirements.txt
├── run_analysis.sh                 ← senior's main entry point
├── env_setup/
│   └── check_env.sh
├── slurm/
│   ├── _base.slurm
│   ├── single_pilot.slurm
│   ├── array_extract.slurm
│   └── array_slab_md.slurm
├── scripts/                        ← all analysis modules + utilities
│   ├── (utility)    topology.py io_xyz.py bonds.py features.py bat.py
│   │                extract_complex.py xi_rl_candidates.py
│   ├── (extract)    extract_chain_coords.py extract_one_replica.py
│   │                extract_parallel.py merge_chain_coords.py
│   │                explore_replicas.sh
│   ├── (renamed)    system_inputs.py  free_energy_terms.py
│   │                closure_four_term.py  closure_wlc_three_term.py
│   ├── (analysis)   raw_tether_partition_k2d.py  reconcile_methods.py
│   │                diagnose_bound_vs_unbound.py
│   └── (slab MD)    nvt-md-constrained-h.py  analyze_slab_traj.py
├── analysis/                       ← orchestrator shell wrappers
│   ├── run_section0_full.sh
│   ├── run_slab_full.sh
│   └── expected_output_layout.md
├── corrections/README.md
├── outputs/                        ← senior's raw outputs land here
│   └── README.md                     (synced back from her server)
├── results/                        ← Claude's senior-side analysis
│   └── README.md
└── trial/                          ← user's validation harness
    ├── README.md
    ├── 01_env_check.sh ~ 04_extract_pilot.sh
    ├── outputs/                    ← user pastes trial .out here
    │   └── README.md
    └── results/                    ← Claude's trial-side diagnosis
        └── README.md
```

## Two double-loops (user-side + senior-side)

### Loop A — user runs trial on cluster-A, Claude fixes scripts

```
User                                            Claude (laptop)
─────                                           ─────────────
1. ssh master, git pull
2. bash cluster/trial/01..04.sh
3. cluster/trial/outputs/<date>_round<N>/
   ← .out files
4. git add + commit + push   ──────────────►   git pull
                                                 5. read trial/outputs/
                                                 6. write trial/results/<date>_round<N>_diagnosis.md
                                                 7. patch cluster/scripts/*
                                                 8. git commit + push
9. git pull                  ◄──────────────
10. rerun trial 03/04
... repeat until verdict.md says PASS
```

### Loop B — senior runs cluster/ on her server, Claude analyzes

```
User                            Senior                              Claude
─────                           ──────                              ──────
1. tar czf cluster.tgz                                              
   (excluding trial/)                                                
2. WeChat / email ──────────►   3. unpack on her server             
                                4. bash cluster/run_analysis.sh    
                                5. send distilled.tgz back ────────► (via user)
                                                                      6. user unpacks to
                                                                         cluster/outputs/<date>_round<N>/
7. git add + commit + push  ───────────────────────────────────────► git pull
                                                                      8. read cluster/outputs/
                                                                      9. write cluster/results/<date>_round<N>_analysis.md
                                                                      10. write verdict.md if §0 closed
                                                                      
                                                                      OR
                                                                      
                                                                      11. write next question for senior
12. user forwards question to senior ───────────────────────────────►
... repeat
```

## How to use

### As user, on cluster-A (Loop A)

```bash
ssh master
cd /mnt/nfs/ugstu/liuzx/2D-Binding
git pull
bash cluster/trial/01_env_check.sh    > cluster/trial/outputs/$(date -I)_round1/01_env_check.out 2>&1
# (repeat for 02-04, then git commit + push)
```

### As user, to ship to senior (after trial pass)

```bash
tar czf cluster-for-senior.tgz --exclude=cluster/trial cluster/
# send via WeChat / email
```

### As senior

See `cluster/README_for_senior_zh.md` (中文).

## Naming convention

All file names follow purpose-based naming. There is no `phd_*` prefix
(historical references to senior's PPT — removed). Renamed files:

| old | new |
|---|---|
| `phd_inputs.py` | `system_inputs.py` |
| `phd_formula.py` | `free_energy_terms.py` |
| `phd_closure.py` | `closure_four_term.py` |
| `phd_closure_s25.py` | `closure_wlc_three_term.py` |
| `diagnose_rigid_sample_bias.py` | `diagnose_bound_vs_unbound.py` |

## Pilot discipline

Every script supports `--pilot` (smaller input, < 60s, asserts a sanity
invariant). Always pilot before production:

1. Locally with `--pilot` if data deps allow
2. On cluster with `cluster/slurm/single_pilot.slurm` to validate template
3. Then production array

## TODOs awaiting cluster-A trial results

Filled in by Round 1 of Loop A above:

- [ ] confirm cluster path to MD output replicas (currently assumed `/mnt/nfs/ugstu/liuzx/2D-Binding-MD/`)
- [ ] confirm conda env `phys` exists with pygamd installed
- [ ] confirm pygamd API for z-tether harmonic constraint
- [ ] confirm SLURM wall time for MD jobs
- [ ] decide array-task → (system, h) mapping for `array_slab_md.slurm`

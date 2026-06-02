---
purpose: "Top-level cluster/ guide: navigation, structure, and how the two double-loops work"
audience: user (on laptop or cluster-A) + off-site collaborator (after receiving tarball) + Claude (next session)
status: current
---

# cluster/ — full-data analysis bundle + validation harness

This folder serves three roles in one tree:

1. **Validation harness** (`cluster/trial/`) — user runs trial scripts on cluster-A.
2. **Full-data analysis bundle** (everything except `trial/`, `outputs/`, `results/`) — what we tar up and send to the off-site full-data run.
3. **Double-loop IO area** (`cluster/outputs/` ← inbound data, `cluster/results/` → Claude's analysis) — per ADR 005.

## Top-level layout

```
cluster/
├── README.md                          ← you are here
├── HOWTO_run_full_data_zh.md          ← Chinese walkthrough for running the bundle
├── run_config.sh                      ← single config file the runner edits
├── run_analysis.sh                    ← bash fallback orchestrator
├── release_bundle.sh                  ← LOCAL: packs cluster/ → tarball (after trial verdict ✓)
├── RELEASES.md                        ← log of all bundle releases (created on first release)
├── requirements.txt                   ← pip deps for the analysis stack
│
├── env_setup/                         ← see env_setup/README.md
│   └── check_env.sh                     login-node env verification
├── slurm/                             ← see slurm/README.md
│   ├── _base.slurm                      template only
│   ├── single_pilot.slurm
│   ├── array_extract.slurm
│   ├── array_slab_md.slurm
│   └── full_analysis.slurm              PRIMARY user entry — SBATCH wrapper
├── scripts/                           ← see scripts/README.md
│   ├── (extract pipeline) 6 files
│   ├── (closure framework) 5 files
│   ├── (ab initio K2D) 3 files
│   ├── (diagnostics) 1 file
│   ├── (MD) 1 file
│   └── (utilities) 5 files
├── analysis/                          ← see analysis/README.md
│   ├── run_section0_full.sh
│   ├── run_slab_full.sh
│   └── expected_output_layout.md
├── corrections/                       ← see corrections/README.md
│   └── README.md
│
├── outputs/                           ← see outputs/README.md
│   └── README.md                        Loop 2 inbound: distilled tarball lands here
├── results/                           ← see results/README.md
│   └── README.md                        Loop 2 outbound: Claude writes <date>_round<N>_analysis.md here
│
└── trial/                             ← see trial/README.md
    ├── README.md
    ├── 01_env_check.sh                  bash on login node
    ├── 02_paths_check.sh                bash on login node
    ├── 03_pygamd_probe.sh               bash on login node
    ├── 04_extract_pilot.sh              bash on login node
    ├── 05_compute_node_check.slurm      sbatch on compute node
    ├── outputs/                         user pastes .out files per round
    │   └── README.md
    └── results/                         Claude writes <date>_round<N>_diagnosis.md + verdict here
        └── README.md
```

## Two double-loops

### Loop 1 (validation) — user runs trial on cluster-A, Claude fixes scripts

Per `cluster/trial/README.md`. Round-by-round:

1. User: ssh cluster-A → `bash cluster/trial/01..04_*.sh` → output lands in `cluster/trial/outputs/<date>_round<N>/`
2. User: `sbatch cluster/trial/05_compute_node_check.slurm` → output lands in `cluster/trial/outputs/<date>_round<N>/compute/`
3. User: `git push` the outputs
4. Claude: reads outputs → writes `cluster/trial/results/<date>_round<N>_diagnosis.md` + script patches
5. Loop until verdict.md says PASSED

**Loop 1 closure**: when verdict ✓ exists, run `bash cluster/release_bundle.sh` on the laptop to pack the bundle.

### Loop 2 (full data) — off-site collaborator runs bundle, Claude analyzes returns

Per ADR 005 + ADR 007 playbook:

1. User: sends `cluster-bundle-<date>-<sha>.tgz` to off-site collaborator (WeChat/email)
2. Off-site: unpacks → edits `cluster/run_config.sh` (~6 lines) → `sbatch cluster/slurm/full_analysis.slurm`
3. Off-site: `tar czf distilled.tgz cluster/outputs/distilled/` → sends back
4. User: unpacks to `cluster/outputs/<date>_round<N>/` → `git push`
5. Claude: writes `cluster/results/<date>_round<N>_analysis.md` (MUST include B-revision impact section per ADR 007)
6. Loop until verdict says §0 hypothesis CONFIRMED or REJECTED

## Quick-reference commands

```bash
# As user on cluster-A — run trial rounds
ssh master && cd /mnt/nfs/ugstu/liuzx/2D-Binding && git pull
mkdir -p cluster/trial/outputs/$(date -I)_round1
bash cluster/trial/01_env_check.sh    > cluster/trial/outputs/$(date -I)_round1/01_env_check.out 2>&1
bash cluster/trial/02_paths_check.sh  > cluster/trial/outputs/$(date -I)_round1/02_paths_check.out 2>&1
bash cluster/trial/03_pygamd_probe.sh > cluster/trial/outputs/$(date -I)_round1/03_pygamd_probe.out 2>&1
bash cluster/trial/04_extract_pilot.sh > cluster/trial/outputs/$(date -I)_round1/04_extract_pilot.out 2>&1

mkdir -p cluster/trial/outputs/$(date -I)_round2/compute
sbatch -o cluster/trial/outputs/$(date -I)_round2/compute/%J.out \
       -e cluster/trial/outputs/$(date -I)_round2/compute/%J.err \
       cluster/trial/05_compute_node_check.slurm

# As user on laptop — release the bundle (after trial verdict ✓)
bash cluster/release_bundle.sh
# → produces cluster-bundle-<date>-<sha>.tgz; logs in cluster/RELEASES.md

# As off-site collaborator (after receiving tarball)
vim cluster/run_config.sh           # edit MD_PARENT etc.
sbatch cluster/slurm/full_analysis.slurm
tar czf distilled.tgz cluster/outputs/distilled/  # send this back
```

## Trial round status

| date | round | node type | outputs | result |
|---|---|---|---|---|
| 2026-06-01 | round1 | login | `cluster/trial/outputs/2026-06-01_round1/` | 4 issues found → patched in commits 2845d02, 1a4fcff |
| 2026-06-02 | round1 | login | `cluster/trial/outputs/2026-06-02_round1/` | ✓✓✓ all 4 PASSED |
| 2026-06-02 | round2 | compute (SBATCH job 4744 on n01) | `cluster/trial/outputs/2026-06-02_round2/compute/` | ✓✓✓ COMPUTE-NODE CHECKS PASSED — trial validated |

Trial verdict: **PASSED 2026-06-02** (see `cluster/trial/results/2026-06-02_round2_verdict.md`). Bundle release is authorised.

## Naming convention

All files use purpose-based names. No person references in any active file. The historical `phd_*` prefix (Session 3 refactor, commit 293c28d) and other person-derived file names (Session 8 cleanup) were removed in favour of functional names:

| historical name | current name |
|---|---|
| `phd_inputs.py` | `system_inputs.py` |
| `phd_formula.py` | `free_energy_terms.py` |
| `phd_closure.py` | `closure_four_term.py` |
| `phd_closure_s25.py` | `closure_wlc_three_term.py` |
| `diagnose_rigid_sample_bias.py` | `diagnose_bound_vs_unbound.py` |
| (historical config name) | `run_config.sh` |
| (historical HOWTO name) | `HOWTO_run_full_data_zh.md` |
| (historical bundle dir) | (removed; `cluster/` IS the bundle) |

## Pilot discipline

Every script supports `--pilot` (smaller input, < 60s, asserts a sanity
invariant). Always pilot before production:

1. Locally with `--pilot` if data deps allow.
2. On cluster with `cluster/slurm/single_pilot.slurm` to validate template.
3. Then production array.

## Related docs

- `cluster/HOWTO_run_full_data_zh.md` — off-site collaborator's walkthrough (中文)
- `cluster/trial/README.md` — trial pipeline detail
- `cluster/scripts/README.md`, `cluster/slurm/README.md`, `cluster/env_setup/README.md`, `cluster/analysis/README.md` — per-subfolder indexes
- `log/decisions/005_double_loop_io_dirs.md` — ADR for the IO convention
- `log/decisions/007_loop2_b_revision_playbook.md` — ADR for Loop 2 → B revision protocol

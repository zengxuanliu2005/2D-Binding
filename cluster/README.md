---
purpose: "Top-level cluster/ guide: navigation, structure, and how the two double-loops work"
audience: user (on laptop or cluster-A) + off-site collaborator (rsyncs from cluster-A) + Claude (next session)
status: current
---

# cluster/ — full-data analysis bundle + validation harness

This folder serves three roles in one tree:

1. **Validation harness** (`cluster/trial/`) — user runs trial scripts on cluster-A.
2. **Full-data analysis bundle** (everything except `trial/`, `outputs/`, `results/`) — what the off-site collaborator rsyncs from cluster-A. Released via `release_bundle.sh`.
3. **Double-loop IO area** (`cluster/outputs/` ← inbound data, `cluster/results/` → Claude's analysis) — per ADR 005.

## Data access topology

```
                          Local laptop (Zengxuan)
                                  │
                                  │ git push / pull (only laptop ↔ GitHub)
                                  │
                                  │ cyberduck UPLOAD cluster/ (no git on cluster-A)
                                  │ cyberduck DOWNLOAD trial outputs + Loop 2 round dirs
                                  ▼
                  cluster-A: master, /mnt/nfs/ugstu/liuzx/2D-Binding/
                          shared between user and off-site collaborator
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
        cluster/trial/      cluster/outputs/      cluster/scripts/
        (user runs here     (Loop 2 inbound:      cluster/slurm/
         to validate the    distilled cp'd        cluster/run_*.sh
         env + pipeline)    here by off-site)     etc. — the bundle
                                                       │
                                                       │ off-site collaborator
                                                       │ rsyncs to her own
                                                       │ <md_root>/2D-Binding-fullrun/
                                                       ▼
                          Off-site cluster (collaborator's home cluster)
                                  │
                          full-data MD already at <md_root>/<system>/
                          sbatch full_analysis.slurm → distilled output
                                  │
                                  │ cp distilled/ back to
                                  │ /mnt/nfs/ugstu/liuzx/.../cluster/outputs/<date>_round1/
                                  ▼
                          (cluster-A — shared dir)
                                  │
                                  │ cyberduck DOWNLOAD round dir
                                  ▼
                          Local laptop → git commit → Loop 2 analysis
```

**Key constraints**:

- **Cluster-A has no git**. Sync laptop ↔ cluster-A is via cyberduck (SFTP). After every laptop commit, user must cyberduck-upload `cluster/` to refresh cluster-A (script defaults are zero-edit so the upload is straight overwrite).
- **The off-site collaborator's MD data never leaves her cluster**. Only the ~5 MB distilled outputs come back via the shared cluster-A directory.
- **One shared filesystem, two roles**. The off-site collaborator and the user both have ssh + read/write access to `/mnt/nfs/ugstu/liuzx/`. The user owns the `cluster/` tree there (releases via cyberduck); the off-site collaborator drops her distilled results into `cluster/outputs/<date>_round<N>/`.

This replaces the original (Session 1-era) cluster-A vs cluster-B + WeChat email model.

## Top-level layout

```
cluster/
├── README.md                          ← you are here
├── HOWTO_run_full_data_zh.md          ← Chinese walkthrough for running the bundle
├── run_config.sh                      ← single config file the runner edits
├── run_analysis.sh                    ← bash fallback orchestrator
├── release_bundle.sh                  ← LOCAL: authorises release after trial verdict ✓ (logs in RELEASES.md, prints cyberduck/rsync templates — does NOT tar)
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
│   └── README.md                        Loop 2 inbound: off-site distilled cp'd into <date>_round<N>/
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

**Loop 1 closure**: when verdict ✓ exists, run `bash cluster/release_bundle.sh` on the laptop. It records the released git SHA in `cluster/RELEASES.md` and prints (a) a cyberduck-upload reminder (cluster-A has no git, so the user must cyberduck the laptop's cluster/ to cluster-A to refresh it to this SHA) and (b) the rsync + WeChat templates to send the off-site collaborator. It does NOT produce a tarball.

### Loop 2 (full data) — off-site collaborator runs bundle, Claude analyzes returns

Per ADR 005 + ADR 007 playbook:

1. User: refreshes cluster-A via cyberduck so it reflects the released SHA, then WeChat-pings the off-site collaborator with the rsync template.
2. Off-site: rsyncs `cluster/` from `/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/` to her own work dir (excluding `trial/`, `outputs/`, `results/`); auto-detect usually means no `run_config.sh` edit; `sbatch cluster/slurm/full_analysis.slurm`.
3. Off-site: `cp -R distilled/*` to `/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/outputs/<date>_round<N>/` and WeChat-pings the user.
4. User: cyberduck-downloads the round dir to laptop, `git push`.
5. Claude: writes `cluster/results/<date>_round<N>_analysis.md` (MUST include B-revision impact section per ADR 007).
6. Loop until verdict says §0 hypothesis CONFIRMED or REJECTED.

## Quick-reference commands

```bash
# As user on cluster-A — run trial rounds (cyberduck-upload cluster/ first; no git on cluster-A)
ssh master && cd /mnt/nfs/ugstu/liuzx/2D-Binding
mkdir -p cluster/trial/outputs/$(date -I)_round1
bash cluster/trial/01_env_check.sh    > cluster/trial/outputs/$(date -I)_round1/01_env_check.out 2>&1
bash cluster/trial/02_paths_check.sh  > cluster/trial/outputs/$(date -I)_round1/02_paths_check.out 2>&1
bash cluster/trial/03_pygamd_probe.sh > cluster/trial/outputs/$(date -I)_round1/03_pygamd_probe.out 2>&1
bash cluster/trial/04_extract_pilot.sh > cluster/trial/outputs/$(date -I)_round1/04_extract_pilot.out 2>&1

mkdir -p cluster/trial/outputs/$(date -I)_round2/compute
sbatch -o cluster/trial/outputs/$(date -I)_round2/compute/%J.out \
       -e cluster/trial/outputs/$(date -I)_round2/compute/%J.err \
       cluster/trial/05_compute_node_check.slurm
# → cyberduck-download the round dirs back to laptop and git commit/push

# As user on laptop — authorise release (after trial verdict ✓)
bash cluster/release_bundle.sh
# → appends row to cluster/RELEASES.md; prints cyberduck reminder + rsync/WeChat templates

# As off-site collaborator — see cluster/HOWTO_run_full_data_zh.md
# Summary:
#   rsync (excluding trial/outputs/results) → sbatch full_analysis.slurm
#   → cp distilled/ to /mnt/nfs/ugstu/liuzx/.../outputs/<date>_round1/
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

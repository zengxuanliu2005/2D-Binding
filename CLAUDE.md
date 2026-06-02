---
type: onboarding
project: 2D-Binding
status: accepted
date: 2026-06-02
summary: "Coarse-grained MD study of how adhesion-protein flexibility (rigid/semi/flex) sets the 2D binding constant K2D. Open question: explain ~35× K2D spread purely as an entropy difference. Active workstreams A/B/C/D; current focus is B2 (lp-parametrized theory) + cluster trial round 2."
agent_read_when:
  - new agent landing in the repo for the first time
  - need to know unit conventions, git discipline, or environment
  - looking for the right folder to write a new artifact
agent_skip_when:
  - already familiar with the project and continuing a specific workstream
  - working purely in derivation/ or log/ (those have their own onboarding)
navigation_map:
  - { path: log/,         purpose: session memory + ADRs + calibration tables,                  read_for: "rationale, history, decisions" }
  - { path: derivation/,  purpose: theory derivations (B2 WLC chain → K2D(l) → ξ_RL → F_conf),  read_for: "why a formula is what it is" }
  - { path: scripts/,     purpose: local analysis modules (laptop, s001 single-replica),         read_for: "running local analyses" }
  - { path: cluster/,     purpose: pipelines that ship to cluster-A or senior; trial validation, read_for: "cluster work, senior bundle, trial outputs/results" }
  - { path: results/,     purpose: numerical outputs (md + npz + figures),                       read_for: "current measured / predicted numbers" }
  - { path: writeup/,     purpose: stage essay (English), upcoming Chinese essay/slides/poster, read_for: "academic deliverables" }
  - { path: ref/,         purpose: reference papers + ref/nvt-md.py force-field source of truth, read_for: "literature, MD force field" }
  - { path: PLAN.md,      purpose: legacy phase tracker (now mostly in user-dir plan file),     read_for: "high-level phase summary" }
  - { path: JOURNEY.md,   purpose: historical chronology of attempts (incl. 3 that didn't close),read_for: "what we tried and rejected" }
---

# CLAUDE.md — 2D-Binding project onboarding

> **First time here?** Read frontmatter above + the "Where to go next" section.
> Everything detailed is one folder away.

## Where to go next (decision tree)

| Your task | Read first |
|---|---|
| **I'm continuing a stalled session** | most recent `log/sessions/<file>.md` |
| **I need to know why we chose X** | `log/decisions/<adr-id>_<slug>.md` |
| **I need current prediction vs measurement** | `log/calibration/<topic>.md` |
| **I'm developing B2 theory** | `derivation/0N_<topic>/00_intent.md` then 01_setup |
| **I'm working on cluster pipelines** | `cluster/README.md` |
| **I'm interpreting trial round outputs** | `cluster/trial/results/<date>_round<N>_diagnosis.md` |
| **I'm writing essay v2 / slides / poster** | `writeup/drafts/stage_essay.md` (don't add frontmatter; academic deliverable) |

The plan file (in `~/.claude/plans/` user dir, referenced by the Plan tool) holds
strategy + open questions. CLAUDE.md is the static onboarding.

## Project at a glance

CG molecular dynamics study of CD47-SIRPα-like receptor-ligand pairs anchored
on apposed lipid membranes. Three flexibility classes via ecto-domain angle
stiffness:

| name | ecto stiffness K (ε) | persistence length lp (nm) | K2D,max (nm²) |
|---|---:|---:|---:|
| K100 ("rigid") | 100  | 84.6 | 12705 |
| K10  ("semi")  |  10  |  8.18 |  875 |
| K01  ("flex")  |   0.1|  1.14 |  362 |

Open scientific question: **can the 35× K2D ratio be explained purely as
entropy?** Current consensus from 5 methods says yes, within 0.22 kBT
inverse-variance-weighted (see `log/calibration/closure_methods_consensus.md`).

## Unit system — MUST NOT get wrong

- **Length**: σ = 1 nm. (2500 proteins/µm² ⇔ 20σ spacing ⇒ 400 nm²/protein.)
- **Energy**: kBT = 1.1 ε. Convert ε → kBT by dividing by 1.1.
- **Bond r₀**: **1.0 σ for protein-protein bonds** (HARM K=100 in ref/nvt-md.py);
  0.95 σ only for lipid FENE bonds. The closure framework uses b = 1.0 σ.
- **Binding well**: depth −14.76 ε ≈ −13.4 kBT; angular gate θ₀ = 10°, K = 15/rad².
- **Thermostat**: Langevin (Bussi-Parrinello), T = 1.1 ε/kB, dt = 0.01.

## Data conventions

- `outputs/` is git-ignored (read-only input). Don't write there.
- Trajectories `traj.xyz` are 2-4 GB each — never load whole into memory; use
  `scripts/io_xyz.py::iter_frames` for streaming.
- Bead numbering: chain[3] = anchor head, chain[12] = binding bead. Ecto =
  chain[3:13]. See `scripts/system_inputs.py`.
- `*_distributed_*.tsv` files are raw per-sample lists, NOT histograms.
- Distances in σ (= nm), angles in degrees.

## Environment & network

- **Local laptop**: conda env `phys` (Python 3.11 + numpy/scipy/pandas/matplotlib/scikit-learn).
- **Cluster-A**: uses system base env at `/opt/miniconda3/bin/python` —
  do NOT require `phys` (see ADR 002).
- Network on laptop requires Clash Verge proxy:
  ```bash
  export http_proxy=http://127.0.0.1:7897
  export https_proxy=http://127.0.0.1:7897
  export all_proxy=socks5://127.0.0.1:7897
  ```

## Git discipline

- Commit after every meaningful step with a specific message
  (`feat: ...`, `diag: ...`, `refactor: ...`, `B2.N: ...`, `log: ...`).
- Never `--force` push, never rewrite shared history.
- `outputs/` and `cluster/outputs/` gitignored (large MD outputs and raw cluster results).
- Push at milestones. Remote `origin/main` exists.
- See ADR 005 for the cluster/ IO loop convention (where to write what).

## Session-end report

After every session:

1. Write a brief chat handoff (1-3 sentences: key decision / result).
2. Pointer "see `log/sessions/<date>_<slug>.md` for full".
3. Detailed Done/Changed/Findings/Decisions/Open/Next goes in the session log
   file (with YAML frontmatter per `log/README.md` schema).

This is the convention as of session 6a. Older sessions used inline chat
handoffs which are now backfilled into log/sessions/.

## Cluster reference (compact)

- **cluster-A**: `master`, repo path `/mnt/nfs/ugstu/liuzx/2D-Binding-main`.
  conda at `/opt/miniconda3`, sbatch present, `gpu*` partition with 8 idle nodes.
- **cluster-B**: senior's server, NOT accessible to us. Senior runs
  bundle on it and emails back distilled tarball.
- **Workstream C** (constrained-h slab MD): blocked on cu_gala install
  on cluster-A. § 0 bundle path is the alternative.

## Reference papers

`ref/`: Hu 2013 (PNAS), Xu 2015 (JCP), Weikl 2016 (Cell Adh & Migr),
Hou 2025 (JCTC). The senior's PPT (`2D-binding-MD.pdf`) is in repo root.

## Anti-patterns (do not repeat)

- Do NOT fit analytical polymer models per flexibility class (Gaussian works
  only for flex, Marko-Siggia only for moderate stretch — past attempts).
  The current B2 framework (discrete WLC MC) spans all 3 classes by construction.
- Do NOT tune terms to hit a target. The S1-S23 closure passes by construction
  on s001; the L_c sensitivity is exposed by B1 reimpl deliberately to test
  the senior's framework.
- Do NOT introduce `phd_*` filenames — renamed to purpose-based names in
  session 3 (see ADR for the rename rationale embedded in
  `log/sessions/session3_refactor.md`).

## Key file pointers

- B2 theory entry: `derivation/01_wlc_endpoint_distribution/00_intent.md`
- B2 code: `scripts/k2d_l_wlc_theory.py`
- 5-method consensus: `scripts/reconcile_methods.py`
- Cluster trial entry: `cluster/trial/README.md`
- Senior-facing bundle docs: `cluster/README_for_senior_zh.md`

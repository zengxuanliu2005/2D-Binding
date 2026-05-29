# 2D-Binding — flexibility & the 2D binding constant of membrane adhesion proteins

Coarse-grained molecular dynamics study of how the **flexibility** of membrane-
anchored adhesion proteins (CD47–SIRPα-like) sets their **2D binding constant**
`K2D`. The scientific goal: explain the ~35× spread in the maximum binding
constant `K2D,max` between rigid and flexible proteins from the
polymer-tether phase space that remains available for membrane bridging.
The current best route estimates one joint endpoint/orientation binding
probability directly from raw trajectories, avoiding double counting between
stretching, capture-volume, and rotational factors.

> **Companion docs:**
>
> - `JOURNEY.md` — narrative of what was tried, what worked, what's open. Start here if you're picking the project up.
> - `CLAUDE.md` — operational onboarding for Claude Code (units, conventions, rules).
> - `PLAN.md` — the live task tracker (phases, status, acceptance criteria).
> - `results/raw_tether_partition.md` — current raw-data partition-function prototype.
> - `results/phd_closure.md` — four-term baseline closure.

## Status at a glance

- ✅ Model built & simulated (Cooke membrane + anchored bead-spring R/L + directional bond).
- ✅ Master curve fitted; `K2D,max` extracted: rigid ≈ 12705, semi ≈ 875, flexible ≈ 362 nm².
- ✅ **Current main candidate: raw tether partition estimate.** It reads
  `outputs/<system>/s001/traj.xyz` directly, samples unbound R/L tether
  endpoints, applies the RB-LB capture and angle kernel once as a joint gate,
  scans membrane separation `h`, and uses `max_h K2D_eff(h)` ratios. This
  avoids treating `F_c`, `F_bond`, and `F_rot` as independent marginal terms.

  | pair | raw soft | target | gap | closed |
  |---|---:|---:|---:|---:|
  | flex − rigid | +3.339 kBT | +3.56 | −0.221 | 94 % |
  | semi − rigid | +2.440 kBT | +2.68 | −0.240 | 91 % |
  | semi − flex  | −0.899 kBT | −0.90 | +0.001 | 100 % |

  The hard-gate sanity check gives similar gaps (max 0.217 kBT). Full
  write-up: `results/raw_tether_partition.md`. Story figures:
  `results/figures/raw_tether_mechanism.png`,
  `results/figures/raw_vs_phd_closure.png`, and
  `results/figures/raw_tether_pipeline.png`.

- ✅ **Four-term baseline also closes, but is now treated as an interpretable
  approximation.** The PhD's S1–S23 framework
  (`F_t + F_c + F_bond + F_rot`) gives all three K2D,max log-ratios within
  0.4 kBT with correct signs:

  | pair | predicted | target | closed |
  |---|---|---|---|
  | flex − rigid | +3.96 kBT | +3.56 | 111 % |
  | semi − rigid | +2.69 kBT | +2.68 | **100 %** |
  | semi − flex  | −1.27 kBT | −0.90 | 141 % |

  Headline figure: `results/figures/closure_phd.png`. Full curated
  write-up: `results/phd_closure.md`. Reproduce locally with
  `python scripts/phd_closure.py && python scripts/plot_phd_closure.py`.
- ⬜ Bootstrap / multi-seed uncertainty on the raw partition estimate, especially
  the flexible-system tail probability.
- ⬜ Write-up, slide deck, and poster not yet started.

For the full chronology of attempts (including the three that didn't close,
which are kept on disk for the record) see `JOURNEY.md`. The four-term
baseline lives at tag `phase2-phd-closure-attempt`; the raw partition prototype
lives on branch `analysis/raw-tether-k2d`; the multi-replica SBATCH pipeline
(packaged but not run) lives on branch `analysis/cluster-pipeline`.

## The systems

Three flexibility classes, identical otherwise (same membrane, same protocol),
differing only in ecto-domain bending stiffness `K`:

| folder                          | K    | flexibility |
| ------------------------------- | ---- | ----------- |
| `outputs/15_120x120_K100_EPS05` | 100  | rigid       |
| `outputs/15_120x120_K10_EPS05`  | 10   | semi-rigid  |
| `outputs/22_120x120_K01_EPS05`  | 0.1  | flexible    |

Only replica `s001` of each is in the local repo (storage limit); the cluster
holds more under `/mnt/nfs/ugstu/liuzx`.

> **Note:** the K01 (flexible) folder was processed ~2 years ago and carries an
> older set of analysis outputs than K10/K100. Harmonizing the observables across
> all three (by re-extracting from the trajectories) is the first data task — see
> `CLAUDE.md` → "Data-consistency warning".

## Repo layout

```
outputs/<system>/s001/   per-system MD outputs + extracted observables (read-only)
analysis/                MD post-processing scripts (membrane-distance one is current)
ref/                     reference papers (PDF), nvt-md.py, parameter sheet
scripts/                 new analysis code for the entropy work
results/                 computed numbers, tables, figures
CLAUDE.md  PLAN.md        onboarding + task tracker
2D-binding-MD.pptx/.pdf   working presentation
```

Raw MD files (`*.xyz *.dcd *.cpt *.psf` and large `*.dat`) are git-ignored;
trajectories are 2–4 GB each and must be streamed, never loaded whole.

## Setup

```bash
# proxy (Clash Verge) — needed for network access
export http_proxy=http://127.0.0.1:7897
export https_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897

conda activate phys                 # always use this env; do not create a new one
pip install -r requirements.txt     # only if something is missing, into phys
```

## Working with Claude Code

Launch `claude` from the repo root so it loads `CLAUDE.md`. Conventions enforced
there: report all energies in **kBT**; commit every meaningful step (branches for
experiments, nothing destructive — see Git discipline); and end every task with a
structured handoff report (Done / Changed files / Findings / Decisions / Open
questions / Next steps / How to reproduce).

## Key physics reference

Master curve: `K2D = K2D,max · [1 + (ξ⊥/ξ_RL)²]^(−1/2)`
(ξ⊥ = membrane roughness, ξ_RL = complex separation fluctuation).
Theory baseline in `ref/`: Hu et al. PNAS 2013, Xu et al. JChemPhys 2015,
Numata 2012 (entropy via information theory).

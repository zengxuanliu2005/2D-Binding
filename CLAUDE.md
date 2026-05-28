# CLAUDE.md — 2D-Binding (membrane receptor–ligand adhesion)

> Project onboarding for Claude Code. Keep this concise and operational. Live task tracker lives in **PLAN.md**.

## What this project is

Coarse-grained molecular dynamics study of how adhesion-protein **flexibility** sets the 2D binding constant `K2D` for membrane-anchored receptor–ligand pairs (CD47–SIRPα-like). MD engine: **GALA / pygamd** (GPU). The open scientific question: explain the ~35× spread in `K2D,max` across rigid / semi-rigid / flexible proteins **purely as an entropy difference**.

## Current focus

The blocker is the **entropy decomposition**. The four terms (translational + rotational + conformational + end-volume) must sum to the measured free-energy gaps — the log-ratios of `K2D,max`, in units of kBT:

| pair         | target ΔF (kBT) |
| ------------ | --------------- |
| flex – rigid | 3.56            |
| semi – rigid | 2.68            |
| semi – flex  | 0.90            |

Earlier attempts double-count and don't close (one overshoots at 5.2, the revised one undershoots at 3.0 and flips the semi/flex order). **Do NOT tune terms to hit the target.** Fix the decomposition so it closes by construction — see PLAN.md Phase 2.

## Unit system — get this right; it propagates into every entropy number

- **Length:** σ = 1 nm.  (2500 proteins/µm² ⇔ 20σ spacing ⇒ 400 nm²/protein ⇒ σ = 1 nm.)
- **Energy:** kBT = 1.1 ε.  Convert any ε-based energy to kBT by **dividing by 1.1**.
- **Bead spacing** (bond `r0`): 0.95 σ ≈ 0.95 nm.
- **Binding well depth:** −14.76 ε ≈ **−13.4 kBT**.  Angular gate: θ0 = 10°, K = 15 /rad².
- Thermostat: Langevin (Bussi–Parrinello), T = 1.1 ε/kB, dt = 0.01.

## Repo layout (LOCAL repo as downloaded — this is where Claude Code runs)

Only `s001` of each system is downloaded (Mac storage limit; cluster has more replicas under /mnt/nfs/ugstu/liuzx). Trajectories are 2-4 GB each.

```
outputs/   (GIT-IGNORED — read-only input; write nothing here)
  15_120x120_K100_EPS05/s001/   RIGID    (ecto K=100)
  15_120x120_K10_EPS05/s001/    SEMI     (K=10)
  22_120x120_K01_EPS05/s001/    FLEXIBLE (K=0.1)
    s001/  MD outputs per system:
      traj.xyz (2-4 GB), mol.psf, state.cpt   <- raw MD (read-only; never load whole traj)
      *_distributed_*.tsv                     <- extracted observables (per-sample lists)
      binding_vector_final_*_vectors.tsv      <- 3D binding-vector orientation (K10/K100 only)
      bindsites_rxryrz_distribution.tsv       <- 3D binding-site positions (K10/K100 only)
      EC_angle_distributed_*.tsv              <- ecto-domain angle (K10/K100 only)
      result_Re*, result_*_complex.dat, roughness*.tsv, num_bonds_*.dat
analysis/   post-processing scripts — CURRENTLY ONLY the membrane-distance script
            (vertical_distance_to_membrane_complex.py); the generators for
            binding_vector / bindsites / EC_angle / angles / Re are NOT here yet.
ref/        reference papers (PDF) + nvt-md.py (force-field source of truth)
            + 其中一个体系的模拟参数.png (parameter sheet)
2D-binding-MD.pptx / .pdf   working presentation
scripts/    (CREATE) new analysis code for the entropy work
results/    (CREATE) computed numbers, tables, figures
```

## Flexibility mapping (resolved)

**K100 = rigid · K10 = semi-rigid · K01 (K=0.1) = flexible.** All three share the same membrane condition (EPS05, 120×120), so differences are protein flexibility only. Set by the ecto-domain angle stiffness in `nvt-md.py` (`*E-*E-*E` angles).

## Data-consistency warning — HARMONIZE BEFORE COMPARING

The simulation method is IDENTICAL across K01/K10/K100 (same nvt-md.py, only the ecto stiffness K differs), so the systems are physically comparable. The mismatch is only in analysis outputs: K01 was processed ~2 yrs ago with fewer extractors.

- K100 & K10 (newer): `binding_vector_*`, `bindsites_rxryrz`, `bindsites_angle`, `EC_angle_*`, `result_Re.tsv` + `result_*_complex.dat`, `roughness_l`.
- K01 (older): `phi_angle_*`, `result_Re_distributed_*`; MISSING the above. Harmonization plan (PhD-confirmed: EVERYTHING is derivable from `traj.xyz`): Claude Code should WRITE its own extractors from `traj.xyz` + `mol.psf` rather than wait for her scripts — but validate before trusting:

1. Write an extractor for each needed observable (binding_vector, bindsites_rxryrz, bindsites_angle, EC_angle, Re, etc.), using bead-type conventions from `nvt-md.py` + `mol.psf`.
2. **VALIDATE against existing files:** run the extractor on K10 and K100 and confirm it reproduces the PhD's existing `*.tsv` outputs for those systems. If it matches, the extractor is correct and conventions are right.
3. Then run the SAME extractor on all three systems → identical provenance by construction. The PhD's K10/K100 files are the ground-truth check, not a dependency. (She can send a reference script if a convention is ambiguous.) The membrane-distance script (`vertical_distance_to_membrane_complex.py`, in `analysis/`) is confirmed current/unchanged — reuse it, don't rewrite. Watch: Re is stored differently — K10/K100 in `result_Re_complex.dat`, K01 in `result_Re_distributed_*.tsv`; reconcile the mapping before any Re-based entropy.

## Data file conventions

- `*_distributed_*.tsv` are **raw per-sample lists** (one value per line), NOT histograms. `_bind` = sampled while a bond/complex exists; `_unbind` = unbound. Build distributions and entropies from these directly.
- Distances in σ (= nm); angles in degrees.
- `roughness.tsv` columns: `#bonds  roughness  sum_l  count`.
- Bound samples are far fewer than unbound — weight error bars accordingly.

## Environment / how to run

- Work happens on the cluster (`master`, repo under `/mnt/nfs/ugstu/liuzx`).
- **Always use the conda env `phys`:** `conda activate phys` before running anything. Don't create a new venv. If a package is missing, install it into `phys` (`conda install ...` or `pip install ...` with `phys` active); `requirements.txt` lists the analysis packages needed.
- Analysis is Python: numpy, scipy, pandas, matplotlib (+ scikit-learn for KDE).
- The MD itself (GALA/pygamd) needs a GPU and is **NOT** rerun here. Treat `outputs/` as fixed input; do not launch `nvt-md.py` or the `*.slurm` jobs.

## Network (Clash Verge proxy) — REQUIRED for connectivity

The machine routes traffic through Clash Verge. Export these in the shell **before launching `claude`** (otherwise auth/API calls and `pip`/downloads fail):

```bash
export http_proxy=http://127.0.0.1:7897
export https_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
```

If a network command fails, check the proxy is set (`echo $https_proxy`) and that Clash Verge is running on port 7897.

## Conventions & gotchas

- Report all free-energy/entropy numbers in **kBT** (divide ε by 1.1).
- For cross-flexibility comparison, pull every distribution from the **same reference condition** — don't mix the 15×15 planar runs with the 120×120 fluctuating runs.
- **Conformational entropy: do NOT fit analytical polymer models per flexibility** (Gaussian, Marko–Siggia, etc. each only work in one regime — this is why prior attempts failed). Instead estimate configurational entropy DIRECTLY from the simulated chain coordinates with a method that spans rigid→flexible: quasi-harmonic / covariance (Schlitter, Andricioaei–Karplus) cross-checked against a nonparametric kNN estimator (Kraskov et al.), combined via the mutual-information decomposition (Numata 2012, in `ref/`). Compute the TOTAL bound-vs-unbound configurational entropy, then let the MI chain rule partition it into translational/rotational/conformational/bonding so terms sum by construction. Needs per-frame internal coordinates (from `traj.xyz`, anchor- aligned, overall translation+rotation removed), not just R_e.
- Watch double-counting between anchor angle (rotational), θ binding-vector (end-volume), and conformation — the MI terms above absorb this explicitly.
- Never commit large binaries (`*.xyz *.dcd *.cpt *.psf`) — see `.gitignore`.
- Use the K2D framework from `ref/` (Hu PNAS-2013, Xu JCP-2015) rather than reconstructing formulas from scratch.

## Git discipline — MANDATORY, everything must be reversible

Git is the safety net for this project. The human reviews progress through git history, so keep it clean and complete.

- This is a git repo. **Commit after every meaningful step** (a working extractor, a validated result, a figure, a doc update) with a clear, specific message (e.g. `feat: binding-vector extractor, validated vs K10/K100`), not `update`.
- **Use branches for anything exploratory or alternative.** Different entropy estimators, trial decompositions, risky refactors → each on its own branch (e.g. `entropy/quasi-harmonic`, `entropy/knn`). Merge only what's validated.
- **Every choice must be redoable/reversible.** Never `git push --force`, never rewrite shared history, never hard-delete results — supersede them in a new commit so the old state stays recoverable. Prefer additive changes.
- Tag milestones (`git tag phase1-done`) so the human can return to known-good points.
- Commit code, docs, small `results/` tables, and figures. NEVER commit large binaries (`*.xyz *.dcd *.cpt *.psf *.dat` trajectories) — see `.gitignore`.
- **`outputs/` is git-ignored (read-only input).** Write EVERYTHING you generate — harmonized observables, intermediate data, tables, figures — into `results/` (tracked) or `scripts/`. NEVER write generated files into `outputs/`; they would be untracked and lost to git history.
- A remote `origin/main` exists. **Push at milestones** (`git push`) so work is backed up off-machine. Never force-push; never rewrite pushed history.
- If unsure whether an action is reversible, commit first, then act.

## End-of-task handoff report — ALWAYS produce this

At the end of EVERY task/prompt, before stopping, output a structured report so the human can relay it and decide next steps. Use exactly these headings:

- **Done:** what was accomplished this run (bullet list).
- **Changed files:** files created/edited + git commits/branches made (with hashes).
- **Key findings / numbers:** results, with units (kBT, nm), and any surprises.
- **Decisions made:** choices taken and why (e.g. estimator picked, convention used).
- **Open questions / blockers:** anything needing the human or the PhD.
- **Next steps:** the concrete proposed next 1-3 actions.
- **How to reproduce:** exact command(s) to re-run what was just done. Keep it concise and scannable. This report is the primary interface to the human.

## Cluster / heavy compute (instructions pending)

The human has SSH access to the group cluster; the PhD will send SLURM job- submission instructions later. Until then, do all analysis LOCALLY on the downloaded `s001` data. If a computation is too heavy for local (e.g. full-traj entropy over many frames), FLAG it in the handoff report rather than running it — it may be submitted to a calc node once instructions arrive. Do not invent cluster commands.

## Key numbers to reproduce / verify

- `K2D,max`: rigid ≈ 12705, semi ≈ 875, flexible ≈ 362 nm².
- Master curve: `K2D = K2D,max · [1 + (ξ⊥/ξ_RL)²]^(−1/2)`.

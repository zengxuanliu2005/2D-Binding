# PLAN.md — 2D-Binding work tracker

Status keys: `[x]` done · `[~]` in progress · `[ ]` todo
Goal of the project: (1) a theory/decomposition that reproduces the measured
`K2D,max` ratios, (2) a write-up, (3) a slide deck, (4) a poster.

---

## Phase 0 — Setup

- [x] Identify model & units (σ = 1 nm, kBT = 1.1 ε, well depth 13.4 kBT)
- [x] Reference papers collected in `ref/`
- [x] System matrix resolved: K100=rigid, K10=semi, K01=flexible (all EPS05)
- [x] Downloaded s001 of each system locally (no replicas — storage limit)
- [ ] Recon: inventory observables per system; confirm which generator scripts
      exist in analysis/ (only membrane-distance one is local so far)
- [ ] **Harmonize observables:** CC writes extractors from traj.xyz, VALIDATES
      them by reproducing the PhD's existing K10/K100 .tsv files, then runs the
      same extractor on all three systems (identical provenance). Reuse the
      existing membrane-distance script (confirmed current).
- [ ] `conda activate phys` (verify analysis packages present; install into phys
      from `requirements.txt` if missing); create `scripts/` and `results/` dirs
- Note: no replicas locally → error bars via block bootstrap over frames

## Phase 1 — Lock the targets

- [x] `K2D,max` values recorded (12705 / 875 / 362 nm²)
- [ ] Re-verify the master-curve fit `K2D = K2D,max·[1+(ξ⊥/ξ_RL)²]^(−1/2)`
      and extract ξ_RL per flexibility class
- [ ] Freeze ΔF targets: 3.56 / 2.68 / 0.90 kBT
- **Acceptance:** fitted curve overlays the simulated K2D vs ξ⊥ points; ξ_RL
  values match the deck within error.

## Phase 2 — Conformational entropy + decomposition (THE BLOCKER)

Key insight: analytical polymer models fail across flexibility regimes. Estimate
configurational entropy DIRECTLY from simulation coordinates instead.

- [ ] Extract anchor-aligned chain internal coordinates per frame from `traj.xyz`
      (remove overall translation + rotation) for all three flexibility classes,
      bound and unbound
- [ ] Compute conformational entropy with TWO estimators and cross-check:
      (a) quasi-harmonic/covariance (Schlitter / Andricioaei–Karplus),
      (b) nonparametric kNN (Kraskov et al.)
- [ ] Compute the TOTAL bound-vs-unbound configurational entropy; partition via
      the mutual-information chain rule (Numata 2012) into translational /
      rotational / conformational / bonding — so terms sum by construction
      (this also removes the double-counting)
- **Acceptance:** ONE conformational-entropy method gives sensible, monotonic
  values across K100/K10/K01; Σ(terms) reproduces 3.56 / 2.68 / 0.90 within error
  with the correct semi/flex ordering.

## Phase 3 — Validate

- [ ] Bootstrap error bars on each entropy term
- [ ] Sensitivity: bin width, Gaussian vs KDE entropy estimators
- **Acceptance:** conclusions stable across estimators; error bars reported.

## Phase 4 — Deliverables

- [ ] Write-up: methods + results + decomposition table/figure
- [ ] Finish the slide deck (replace the inconsistent decomposition slides)
- [ ] Poster: one-page distillation of the deck
- **Acceptance:** each artifact reviewed against the verified numbers.

---

## Open questions / decisions log

- [x] System matrix: K100=rigid, K10=semi, K01=flexible (ecto angle stiffness)
- [ ] Reference condition for the decomposition — confirm which run set is used
      consistently across all terms (all currently 120×120 EPS05)
- [ ] Confirm the "15" vs "22" prefix meaning (protein count / system size?)
- [ ] Conformational-entropy estimator: quasi-harmonic vs kNN — record which is
      adopted as primary and which as cross-check

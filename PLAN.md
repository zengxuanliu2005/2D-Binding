# PLAN.md — 2D-Binding work tracker

Status keys: `[x]` done · `[~]` in progress · `[ ]` todo
Goal of the project: (1) a theory/decomposition that reproduces the measured
`K2D,max` ratios, (2) a write-up, (3) a slide deck, (4) a poster.

For the chronology and physical reasoning behind every approach we tried,
see `JOURNEY.md`. For the closure that works, see `results/phd_closure.md`.

---

## Phase 0 — Setup

- [x] Identify model & units (σ = 1 nm, kBT = 1.1 ε, well depth 13.4 kBT)
- [x] Reference papers collected in `ref/`
- [x] System matrix resolved: K100=rigid, K10=semi, K01=flexible (all EPS05)
- [x] Downloaded s001 of each system locally (no replicas — storage limit)
- [x] Recon: inventory observables per system → `results/observables_inventory.md`
- [x] **Harmonised observables** — six legacy `.tsv` files reproduced
      byte-for-byte against K10/K100 ground truth, then applied to K01.
      Code: `scripts/extract_complex.py`,
      `scripts/extract_bindsites_ecangle.py`. Validation:
      `scripts/validate_against_legacy.py`. Outputs:
      `results/extracted/<sys>/`.
- [x] `conda activate phys` confirmed; `scripts/` and `results/` populated.

## Phase 1 — Lock the targets

- [x] `K2D,max` values recorded (12705 / 875 / 362 nm²); log-ratio targets
      3.56 / 2.68 / 0.90 kBT.
- [x] K2D sanity check from simulation: K100 reaches ~96 % of K2D,max under
      per-frame averaging, ordering rigid > semi > flex preserved. Code:
      `scripts/k2d_sanity.py` → `results/k2d_sanity.md`.
- [~] Master-curve fit `K2D = K2D,max·[1+(ξ⊥/ξ_RL)²]^(−1/2)` and ξ_RL
      extraction per system — *taken as given from the PhD's slides 5–8*,
      not refit by us. Validating from raw simulation would need MD at
      multiple roughnesses (cluster).

## Phase 2 — Decomposition (CLOSED — was the blocker)

The closure budget is closed within 1 kBT acceptance via the PhD's S1–S23
four-term framework. **Semi − rigid lands at exactly 100 %.**

- [x] Extract per-chain coordinates from `traj.xyz` —
      `scripts/extract_chain_coords.py` → `results/chain_coords/<sys>/chain_coords.npz`
- [x] Numata MI chain-rule attempt — *did not close* (max 32 %). Code on
      disk at `scripts/mi_decomposition.py` /
      `scripts/decomposition_full.py`; outputs at
      `results/mi_decomposition.md`, `results/full_decomposition.md`. Kept
      as historical record of which framework is wrong for this problem
      (the chain-rule MI captures coupling but the K2D ratio is dominated
      by absolute phase-volume differences). See `JOURNEY.md` §5 for the
      details.
- [x] **PhD's S1–S23 four-term framework — this is the closure that works.**
      Code: `scripts/phd_formula.py`, `scripts/phd_inputs.py`,
      `scripts/phd_closure.py`, `scripts/plot_phd_closure.py`.
      Result:

      | pair | predicted | target | gap | closed |
      |---|---|---|---|---|
      | flex − rigid | +3.96 | +3.56 | +0.40 | 111 % |
      | semi − rigid | +2.69 | +2.68 | +0.01 | **100 %** |
      | semi − flex  | −1.27 | −0.90 | −0.37 | 141 % |

      Three explicit corrections to her writeup were required:
      drop `n_b` from inside `F_bond`'s log; apply `F_c` once per pair
      (not twice for R + L); compute `F_rot` via histogram on S² /
      S² × S² (not Schlitter on the in-plane disk). See
      `results/phd_closure.md` for the curated write-up.

- **Acceptance met:** signs correct, all gaps within 1 kBT, semi−rigid
  exact.

## Phase 3 — Validate

- [ ] **Bootstrap error bars on each of the four ΔF terms.** Resample
      frames with replacement, recompute, report σ. ~5 min of local compute,
      maybe 100 lines of code in a new `scripts/phd_closure_bootstrap.py`.
      **Required for the write-up.**
- [ ] (Optional) Bin-sensitivity sweep on `F_rot`'s histogram —
      `(n_bins_marg, n_bins_joint)` over (8, 4) … (20, 6). The
      ΔΔF_rot shifts by up to 0.5 kBT across that range, which sets the
      uncertainty on flex − rigid and semi − flex.
- [ ] (Optional) Parametric replacement for the F_rot histogram —
      Bingham distribution on S² or normalising flow. Would tighten the
      0.4 kBT residual analytically. Bias-variance trade-off only; not
      required for the closure to stand. See `JOURNEY.md` §9.2.
- **Acceptance:** closure numbers reported as point ± σ rather than point
  estimates; the closure conclusion is stable across estimator choices.

## Phase 4 — Deliverables

- [ ] Write-up: methods + results + decomposition table/figure. Headline
      figure is `results/figures/closure_phd.png`. The qualitative
      evidence figure is `results/figures/e2e_distributions.png` (chain
      stretching cost visible directly in the bound vs unbound R_ee
      shift for K01).
- [ ] Finish the slide deck (replace the inconsistent decomposition
      slides 21 / 24 with the closure that works).
- [ ] Poster: one-page distillation of the deck.
- **Acceptance:** each artifact reviewed against the verified numbers in
  `results/phd_closure.md`.

## Phase 5 (optional) — Multi-replica run on the cluster

The s001-only result passes acceptance. A multi-replica run would tighten
F_rot's histogram. Packaging is on branch `analysis/cluster-pipeline`
(SBATCH-ready in PhD's cluster style). **The PhD declined to run it.**
Available if the decision reverses.

- Cluster handoff doc: `cluster/README.md` on
  `analysis/cluster-pipeline`.
- Acceptance if rerun: semi − rigid stays at ≥ 95 %; the other two pairs
  tighten toward 100 %.

---

## Open questions / decisions log

- [x] System matrix: K100=rigid, K10=semi, K01=flexible. Per project
      memory `memory/project_flexibility_mapping.md`, both R and L use
      the same K per system (matching CLAUDE.md's "*E-*E-*E angles" phrasing);
      `ref/nvt-md.py` shows receptor K=100 / ligand K=10 for K10 but the actual
      K10 production data has R and L equally flexible.
- [x] Reference condition: all closure terms use bound-state vs unbound-state
      averages from the same `chain_coords.npz`. R_e is over unbound R and L,
      D is over bound R and L (ligand z flipped). No mixing of run conditions.
- [x] "15" / "22" prefix = R-L pair count per box (15 pairs in K100/K10,
      22 in K01). Confirmed in
      `memory/project_flexibility_mapping.md` and `results/k2d_sanity.md`.
- [x] Conformational-entropy estimator: not relevant in the closure-that-works
      path. The Schlitter and kNN tracks (sessions 2.5, 3, 4, 5) gave at most
      32 % closure. The PhD's S1–S23 framework uses analytical formulas for
      F_t / F_c / F_bond and a histogram on S² / S² × S² for F_rot — see
      `scripts/phd_formula.py`.
- [ ] **(Open)** receptor/ligand K asymmetry in the actual K10 production
      run — `ref/nvt-md.py` shows receptor K=100 / ligand K=10, but the
      simulation data shows R and L equally flexible. Worth confirming
      which value is correct for the write-up.
- [ ] **(Open)** persistence-length assumption in S5 (Debye-function R_e)
      — our F_c uses simulation-measured R_e directly, so this assumption
      doesn't enter the closure. But if the write-up wants to *connect*
      to the analytical worm-like-chain limit, it needs a chosen l_p
      per system.

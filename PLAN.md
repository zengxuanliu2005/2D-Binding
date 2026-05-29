# PLAN.md — 2D-Binding work tracker

Status keys: `[x]` done · `[~]` in progress · `[ ]` todo
Goal of the project: (1) a theory/estimator that reproduces the measured
`K2D,max` ratios without double-counting tether phase space, (2) a write-up,
(3) a slide deck, (4) a poster.

For the chronology and physical reasoning behind every approach we tried,
see `JOURNEY.md`. For the current raw-data candidate, see
`results/raw_tether_partition.md`. For the four-term baseline, see
`results/phd_closure.md`.

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

## Phase 2 — Decomposition / partition estimate (CLOSED for s001 prototype)

The four-term budget closes within 1 kBT, but it risks double-counting because
stretching, capture volume, and rotation are overlapping marginals. The current
main candidate is therefore the raw tether partition estimate: one joint
endpoint/orientation binding gate, streamed directly from raw `traj.xyz`.

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
- [x] **PhD's S1–S23 four-term framework — baseline closure.**
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

- [x] **Raw tether partition-function prototype — current main candidate.**
      Code: `scripts/raw_tether_partition_k2d.py`; result:
      `results/raw_tether_partition.md`; figures:
      `scripts/plot_raw_tether_story.py` →
      `results/figures/raw_tether_mechanism.png`,
      `results/figures/raw_vs_phd_closure.png`,
      `results/figures/raw_tether_pipeline.png`.
      It streams bead 3/11/12 from `outputs/<system>/s001/traj.xyz`,
      excludes chains bound in the same raw frame, samples unbound R/L
      endpoint pairs, scans membrane separation `h`, and applies RB-LB
      capture plus angular compatibility as one joint gate.

      | pair | raw soft | target | gap | closed |
      |---|---:|---:|---:|---:|
      | flex − rigid | +3.339 | +3.56 | −0.221 | 94 % |
      | semi − rigid | +2.440 | +2.68 | −0.240 | 91 % |
      | semi − flex  | −0.899 | −0.90 | +0.001 | 100 % |

      The hard-gate sanity check gives a similar maximum gap
      (0.217 kBT), while z-reach alone closes only 10–13 %. This supports
      the polymer-tether partition-function route and shows that endpoint
      height alone is not the mechanism.

- **Acceptance met for s001 prototype:** signs correct, all raw-partition gaps
  within 0.24 kBT, and the four-term baseline remains a useful interpretive
  comparison.

## Phase 3 — Validate

- [ ] **Bootstrap error bars on the raw tether partition estimate.** Resample
      raw frames / unbound R-L pairs and recompute `max_h K2D_eff(h)` ratios.
      Report point ± σ for soft kernel and hard gate. This is the highest
      priority validation for the write-up.
- [ ] **Tail-sampling convergence check for the flexible system.** Sweep random
      pair count and bond-vector samples per pair. The K01 extended tail is the
      likely remaining uncertainty.
- [ ] **Multi-seed / multi-replica confirmation if data become available.**
      The local repo has only `s001`; cluster replicas would test whether the
      0.24 kBT max gap is stable.
- [ ] (Optional baseline) Bootstrap the PhD four-term closure and sweep
      `F_rot` histogram bins. This is now secondary, useful mainly for comparing
      the old decomposition to the raw joint-partition estimator.
- **Acceptance:** raw partition numbers reported as point ± σ; signs and
  `≤ 0.3 kBT` max gap remain stable across resampling choices.

## Phase 4 — Deliverables

- [ ] Write-up: methods + results + raw partition table/figure. Headline
      figures are `results/figures/raw_tether_mechanism.png`,
      `results/figures/raw_vs_phd_closure.png`, and
      `results/figures/raw_tether_pipeline.png`. Keep
      `results/figures/closure_phd.png` as the four-term baseline figure.
- [ ] Finish the slide deck (replace the inconsistent decomposition
      slides 21 / 24 with the raw joint-partition picture and the baseline
      comparison).
- [ ] Poster: one-page distillation of the deck.
- **Acceptance:** each artifact reviewed against the verified numbers in
  `results/raw_tether_partition.md`, with the baseline numbers checked against
  `results/phd_closure.md`.

## Phase 5 (optional) — Multi-replica run on the cluster

The s001-only raw partition result passes prototype acceptance. A multi-replica
run would tighten the endpoint/angle tail probabilities and also improve the
old `F_rot` histogram baseline. Packaging is on branch
`analysis/cluster-pipeline` (SBATCH-ready in PhD's cluster style). **The PhD
declined to run it.** Available if the decision reverses.

- Cluster handoff doc: `cluster/README.md` on
  `analysis/cluster-pipeline`.
- Acceptance if rerun: raw-partition signs stay correct and max gap remains
  near the current 0.24 kBT scale.

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
- [x] Raw joint-partition route: current preferred interpretation. It treats
      endpoint reach, RB-LB capture, and binding-angle compatibility as one
      probability kernel, so the same phase-space restriction is not counted
      again as separate `F_c`, `F_bond`, and `F_rot` terms.
- [ ] **(Open)** receptor/ligand K asymmetry in the actual K10 production
      run — `ref/nvt-md.py` shows receptor K=100 / ligand K=10, but the
      simulation data shows R and L equally flexible. Worth confirming
      which value is correct for the write-up.
- [ ] **(Open)** persistence-length assumption in S5 (Debye-function R_e)
      — our F_c uses simulation-measured R_e directly, so this assumption
      doesn't enter the closure. But if the write-up wants to *connect*
      to the analytical worm-like-chain limit, it needs a chosen l_p
      per system.

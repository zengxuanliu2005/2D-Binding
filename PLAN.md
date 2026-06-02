---
type: plan
status: legacy
date: 2026-06-02
summary: Legacy phase tracker. The active strategy + open question list lives in the user-dir plan file (loaded by Plan tool). This file is kept for the phase 0-5 history.
agent_read_when:
  - need a 1-page summary of phases 0-5 historical structure
  - looking for "what was done before session 1"
agent_skip_when:
  - need current task status (use log/sessions/ instead)
  - need active strategy (the plan tool's user-dir file is canonical)
canonical_plan: ~/.claude/plans/open-question-cluster-jiggly-hamster.md
---

# PLAN.md — Legacy phase tracker

> The active plan + strategy is in the user-dir plan file. This file is the
> historical phase summary kept for reference.

Status keys: `[x]` done · `[~]` in progress · `[ ]` todo

---

## Phase 0 — Setup [DONE pre-session 1]

- [x] Identify model & units (σ = 1 nm, kBT = 1.1 ε, well depth 13.4 kBT)
- [x] Reference papers collected in `ref/`
- [x] System matrix resolved: K100=rigid, K10=semi, K01=flex (all EPS05)
- [x] Downloaded s001 of each system locally
- [x] Harmonised observables — 6 legacy `.tsv` files reproduced byte-for-byte
      against K10/K100, applied to K01. See
      `scripts/extract_complex.py`, `scripts/extract_bindsites_ecangle.py`,
      `scripts/validate_against_legacy.py`.

## Phase 1 — Lock the targets [DONE pre-session 1]

- [x] K2D,max baseline numbers (12705 / 875 / 362 nm²) confirmed against
      the source PPT slide 9. ΔΔF targets +3.56 / +2.68 / -0.90 kBT.

## Phase 2 — Four-term S1-S23 closure [DONE pre-session 1]

- [x] Four-term closure: F_t + F_c + F_bond + F_rot per the the source PPT
      slides S1-S23. Reproduces target ΔΔF within 0.4 kBT.
- [x] Code: `scripts/closure_four_term.py` (renamed from `phd_closure.py` in
      session 3) driven by `scripts/free_energy_terms.py` (renamed) and
      `scripts/system_inputs.py` (renamed). Output at
      `results/closure_four_term.{md,npz}`.
- [x] Headline figure: `results/figures/closure_four_term.png`.

## Phase 3 — Validate [DONE session 1]

- [x] **Bootstrap error bars on the raw tether partition estimate** —
      n=200 frame-level resampling. Report point ± σ. See
      `results/raw_tether_partition.md`.
- [x] **Bootstrap on the four-term closure** — σ_sum ≈ 0.03 kBT confirms
      14σ / 13σ systematic gap on flex-rigid + semi-flex (known end-volume
      × rotation double-counting).
- [x] **5-method consensus** — `scripts/reconcile_methods.py`. See
      `log/calibration/closure_methods_consensus.md` for current numbers.

## Phase 4 — Deliverables [IN PROGRESS]

- [~] Write-up (stage_essay.md draft exists; v2 pending B2 + cluster results).
- [ ] Slide deck (Chinese, aligned with off-site collaborator PPT structure).
- [ ] Poster (A0).
- [ ] Re-do all figures with academic-publication style (D1 in plan).

## Phase 5 — Multi-replica + theory [B2 DONE, cluster IN PROGRESS]

- [x] **B2 lp-parametrized WLC theory** — all 5 steps done:
      - B2.1 P(R; lp, Lc) discrete WLC MC (session 5, commit 6cb511f)
      - B2.2 P_z(z; lp, Lc, k_a) membrane-anchored z marginal (session 5, commit 8b6b540)
      - B2.3 K2D(l) hard-gate convolution (session 5, commit bf20668)
      - B2.4 ξ_RL = σ_K2D + Xu 2015 ratio test (session 6b, commit 02ab226)
            — B2 beats Xu by 8-14× on rigid:flex / rigid:semi ratios
      - B2.5 F_conf via -ln P_z(D_bound) (session 6b, commit 5a06ed4)
            — anchor-cone surcharge Δ = +3.79 / +1.21 / -0.04 kBT monotone in lp
- [x] Cluster trial validation — login + compute both ✓ on 2026-06-02 (verdict file: `cluster/trial/results/2026-06-02_round2_verdict.md`); release authorised
- [ ] Full-data analysis bundle round-trip — pending `bash cluster/release_bundle.sh` + send to off-site collaborator + wait for distilled return
- [ ] Constrained-h slab MD (Workstream C; blocked on cu_gala install)

## Phase 6 — Documentation + delivery [IN PROGRESS]

- [x] **Session 6a — meta plumbing** (commit 9ed3dc2): log/ bootstrap, CLAUDE.md restructure with navigation map, Tier 1/2 YAML frontmatter on 45 md files.
- [x] **Session 6b — B2.4 + B2.5** (commits 02ab226, 5a06ed4).
- [x] **Session 6c — cluster-prep + audit** (commits e860152, 196ecf4, d72b35e): `analyze_slab_traj.py` real K2D math; legacy results md → Tier 2 FM; b2_chain_completeness snapshot.
- [x] **Session 7 — double-loop protocol** (commits 72b01dc, c52e107, 6621b56): SBATCH wrapper + `release_bundle.sh` + ADR 007 Loop 2 playbook.
- [x] **Session 8 — repo-wide cleanup** (commits TBD): person references removed from all active files; compute_node_check promoted to Step 5; round 1+2 diagnosis + verdict; 4 new index READMEs; comprehensive README audit.
- [ ] **Workstream D** (figures + essay v2 + slides + poster) — see user-dir plan Session 9+.

---

## Open questions

See active plan + `log/decisions/` for current open decisions.
Resolved decisions are checked off in the relevant ADR (status: accepted).

Historical open Qs:

- [ ] Receptor/ligand K asymmetry in K10 production data — ref/nvt-md.py
      shows receptor K=100 / ligand K=10, but observation shows R and L
      equally flexible. Worth confirming for the write-up.
- [ ] Lc convention (ecto vs full chain) for B2 derivation. See ADR 001.

---

## Where to go for current state

- **Active strategy**: user-dir plan file (Plan tool canonical).
- **Recent session work**: `log/sessions/<date>_<slug>.md` (6 sessions through 6b).
- **Current numbers**: `log/calibration/*.md` (4 running tables).
- **Theory derivations**: `derivation/01..05/` (B2 chain complete).
- **B2 outputs**: `results/derivation_b2/*.{npz,md}` (5 npz, 2 result-md).
- **Cluster status**: `cluster/trial/results/<latest>.md`.
- **Latest commits**: `git log -10 --oneline` — bf20668 (B2.3) → 02ab226 (B2.4)
  → 5a06ed4 (B2.5).

---
type: plan
status: active
date: 2026-06-03
summary: "Active session plan. Lean by design: this file holds ONLY the next session's goals/process/expected outcomes/correction plan + async triggers. History → JOURNEY.md + log/sessions/. Conventions → CLAUDE.md."
agent_read_when:
  - landing on the repo and want to know "what is the next concrete thing to do"
  - finished a session and need to pick up the next one
  - need the correction protocol if pilot / off-site / theory hits an unexpected state
agent_skip_when:
  - need historical session detail (read log/sessions/<date>_*.md)
  - need conventions / unit system / git discipline (read CLAUDE.md)
  - need theory / derivation step (read derivation/0N_<topic>/)
  - need to know which session a commit came from (read JOURNEY.md §14)
---

# PLAN.md — active session focus

## Where we are right now

- **Last shipped**: Session 9 (2026-06-03, head `f823153`). Pilot full-data ✓ on cluster-A; off-site release authorised; `cluster/RELEASES.md` first row recorded; WeChat template ready for off-site collaborator.
- **Waiting on**: off-site collaborator's distilled tarball cp'd into `cluster/outputs/<date>_round1/` → Loop 2 analysis.
- **Active workstream**: D (deliverables). Session 10 = D1 figure framework + 3 B2 headline figures + 14 legacy figures rerun.
- **Async pending**: Session 6d (Loop 2 protocol triggered by off-site data return), can run in parallel with Session 10+.

## Pointers (where everything else lives)

- **Project at a glance, unit system, conventions, navigation map** → `CLAUDE.md`
- **Per-session detailed handoffs** → `log/sessions/<date>_<slug>.md` (Session 1-9 all recorded)
- **Chronological history of every approach we tried** → `JOURNEY.md` (§14 covers Sessions 6a-9)
- **Theory derivation steps (B2.1 → B2.5)** → `derivation/01..05/`
- **Loop 2 decision tree (off-site data → B revision)** → `log/decisions/007_loop2_b_revision_playbook.md`
- **Running calibration tables (predictions vs measurements)** → `log/calibration/*.md`
- **Immutable ADRs** → `log/decisions/001..007`
- **Cluster workflow / off-site bundle / data topology** → `cluster/README.md`
- **WeChat reply drafts for the off-site collaborator** → `cluster/WECHAT_TEMPLATES_zh.md`
- **Off-site collaborator HOWTO (中文)** → `cluster/HOWTO_run_full_data_zh.md`

---

## Session 10 [NEXT] — D1 figure framework + B2 headline figures (~3-4 hrs)

### Goal

Build the academic figure framework (`scripts/figure_style.py`) and use it to produce 3 new B2 headline figures + regenerate the 14 legacy figures with consistent style. Output: a figure set ready to drop into stage_essay.md v2 (Session 11).

### Plan

**D1.1 — `scripts/figure_style.py` framework (~1 hr)**

| Component | Spec |
|---|---|
| rcParams | label=11pt, tick=9pt, title=12pt, legend=9pt, axes lw=0.8, plot lw=1.5, sans-serif |
| Palette | Okabe-Ito 8-color (colorblind-safe); `okabe_ito(i)` helper |
| Academic-name dict | `closure_phd` → "Four-term decomposition (Eqs. S1–S23)"; `raw partition` → "Ab initio binding-kernel integration"; `s25 reimpl` → "Three-term WLC closure (this work, L_c = 12 nm)" |
| LaTeX axis-label helpers | `axis_label("xi_perp")` → `$\xi_\perp$ (nm)`; same for `K2D`, `ddF`, `lp`, `Lc` |
| `apply_style()` | applies rcParams + palette in one call |
| `savefig_paper(fig, name)` | saves 600 dpi PNG + PDF to `results/figures/`; old version → `results/figures/_archive/<date>/` |
| `--audit results/figures/` | scans all PNG/PDF: rejects any "PhD's" / "ours" / "our" wording (returns nonzero if found) |
| `--pilot` | applies framework to ONE existing figure (recommend `method_reconciliation.png`); saves to `results/scratch/pilot_figures/`; assert no audit failure |

**D1.2 — 3 new B2 headline figures (~1 hr)**

| Figure | Source data | Content |
|---|---|---|
| `results/figures/derivation_b2_ratio_test.{png,pdf}` | `results/derivation_b2/xi_rl_lp_prediction.npz` | Bar chart of 3 ratios (rigid:flex, rigid:semi, semi:flex) × 3 sources (B2, Xu 2015, measured) with bootstrap σ error bars |
| `results/figures/derivation_b2_anchor_cone_surcharge.{png,pdf}` | `results/derivation_b2/fconf_b2_selfconsistency.npz` | Bar chart of Δ_anchor (B2 − MS) for the 3 systems, showing monotone +3.79 / +1.21 / -0.04 kBT in lp |
| `results/figures/derivation_b2_pz_per_system.{png,pdf}` | `results/derivation_b2/wlc_z_marginal.npz` | 3-panel P_z(z) histogram per system with D_bound vertical markers + F_conf^(B2) value annotated |

Each figure has companion `scripts/plot_<name>.py` that calls `figure_style.apply_style()` + `savefig_paper()`.

**D1.3 — 14 legacy figures regenerated (~1.5 hrs)**

Batch script: for each existing `scripts/plot_*.py`, add `from figure_style import apply_style, savefig_paper` at top, replace direct `plt.rcParams` calls with `apply_style()`, replace `plt.savefig` with `savefig_paper`. Run each in sequence; audit at end. Archive old PNGs.

### Expected outcomes

- `scripts/figure_style.py` exists with the 7 components above; `python scripts/figure_style.py --pilot` exits 0
- 3 new B2 figures exist at `results/figures/derivation_b2_*.{png,pdf}`
- 14 legacy figures regenerated (same names) with new style; archives in `results/figures/_archive/2026-06-XX/`
- `python scripts/figure_style.py --audit results/figures/` exits 0 (no "PhD's" / "ours" wording)
- All YAML frontmatter still parses
- 1-2 commits: (1) `feat: figure_style framework + B2 headline figures`, (2) `figures: regenerate 14 legacy figures with academic style`
- `log/sessions/2026-06-XX_session10_d1_figures.md` written + pushed

### Correction triggers / 纠偏 plan

| If this happens | Then |
|---|---|
| `figure_style.py --pilot` produces visually-jarring chart on the sample figure | iterate `apply_style()` rcParams before batch-regenerating; better to debug 1 figure than 14 |
| `--audit` finds residual "PhD's" / "ours" in axis labels | add to academic-name dict + rerun plot script; do NOT manually edit PNG |
| A legacy `plot_*.py` script can't be retrofitted cleanly | flag in `log/sessions/...` followups; fall back to keeping old figure for that one rather than block Session 10 |
| One of the B2 npz files lacks expected fields | check `derivation/0X/03_result.md` for the npz schema; if mismatch, fix the figure script (do NOT regenerate the npz — that's a B2 theory rerun, separate work) |
| Cluster Round 1 distilled returns mid-Session 10 | pause D1, switch to Session 6d (Loop 2 analysis per ADR 007); D1 can resume after |
| Session 10 spills over 4 hrs | split D1.3 (14 legacy figures) into Session 10b; ship D1.1 + D1.2 alone in Session 10 commit |

### What Session 10 explicitly does NOT do

- ❌ Touch essay text (D2a is Session 11)
- ❌ Modify B2 theory or rerun any analysis npz (would be a separate session)
- ❌ Touch the off-site bundle (Session 9 is the latest release)
- ❌ Loop 2 analysis (Session 6d-async, separate path)

---

## Upcoming session outlines (one-liners)

- **Session 11** — D2a: `writeup/drafts/stage_essay.md` v2 (English). §4.5 + §5.4 + §4.6 + §5.3 + §A. Uses D1 figures.
- **Session 12** — D2b (中文 stage_essay_zh.md) + D3 (slides_zh.md via Marp → PDF+PPTX) + D4 (poster.md A0).
- **Session 6d [ASYNC]** — fires when off-site distilled returns to `cluster/outputs/<date>_round1/`. Protocol = ADR 007 (decision tree S1-S8). Write `cluster/results/<date>_round1_analysis.md` with B-revision impact section + flip relevant `log/calibration/*.md` rows + new `log/sessions/<date>_6d_*.md`. Can run in parallel with Sessions 10-12.

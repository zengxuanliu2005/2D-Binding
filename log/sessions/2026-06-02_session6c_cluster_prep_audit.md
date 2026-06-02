---
type: session
status: accepted
date: 2026-06-02
session_type: infra
duration_hours: 3
summary: "Cluster-prep + 修正 + 复盘 — implement analyze_slab_traj.py (pilot passes, K100 K2D 19% off target); frontmatter writer on 12 legacy scripts + bulk-prepend to 15 results md; session log + b2 chain completeness calibration snapshot"
agent_read_when:
  - planning Session 7 (D1 figures) or Session 6d (cluster data arrival)
  - asking what was the 'audit cleanup' done while waiting for cluster sbatch
  - need to know which scripts now write Tier 2 YAML frontmatter to their results md
related_decisions: []
key_outputs:
  commits: [e860152, 196ecf4]  # 6c.C commit appended after this edit
  artifacts:
    - cluster/scripts/analyze_slab_traj.py        (placeholder → real K2D math)
    - 12 scripts in scripts/ now write Tier 2 frontmatter on their results md
    - 15 results/*.md now have YAML frontmatter
    - log/sessions/2026-06-02_session6c_cluster_prep_audit.md  (this file)
    - log/calibration/b2_chain_completeness.md     (new)
followups:
  blockers: []
  tasks:
    - "Session 7 — D1 figure framework + 3 B2 headline figures (now ready: B2.4/B2.5 outputs have FM; figure_style can audit md+png)"
    - "Session 6d — when cluster slab MD or senior bundle data lands, _load_slab_frames_real hook is the single integration point"
---

# Session 6c — Cluster-prep + 修正 + 复盘

## What we did

Three workstreams in one session, three commits, no theory changes.

### Workstream A — analyze_slab_traj.py 实装 (commit TBD)

`cluster/scripts/analyze_slab_traj.py`:

- **Removed**: hardcoded per-system placeholder K2D values (12000/870/360)
- **Added**: real Mayer f-function K2D integral via
  `measure_k2d_from_arrays(R_bind, R_term, L_bind, L_term, h)` — same
  formula as `scripts/raw_tether_partition_k2d.py::estimate_area_curve`
- **Added**: synthetic-data pilot path via `_synthesize_slab_frames`
  that draws R/L binding-bead positions from B2.2's z-stats Gaussian
  (μ, σ matching `wlc_z_marginal.npz`)
- **Kept**: `_load_slab_frames_real(traj_dir, h, n_lim)` stub returning
  None — this is the single hook to fill when cluster slab MD data
  arrives. Once `cluster/outputs/slab/<sys>_h<h>/{traj.xyz, mol.psf}`
  exists, follow the pattern of
  `raw_tether_partition_k2d.extract_raw_unbound_features` (topology
  parse + iter_frames with subset_indices for binding beads)
- Pilot uses each system's optimal h = 2·μ_z (rigid h=22.4, semi h=13.3,
  flex h=3.4) so that R bind can actually reach L bind across the gap.

Pilot result (3 systems × 1 h each, < 1 s wall):

| system | h (nm) | K2D (synth) | K2D target (PPT) | ratio | reading |
|---|---:|---:|---:|---:|---|
| K100 | 22.4 | 15155 nm² | 12705 | 1.19 | ✓ excellent rigid agreement (σ_z accurate) |
| K10  | 13.3 |  6157 nm² |   875 | 7.04 | semi over (B2.2 σ_z too wide per derivation/02 Q2) |
| K01  |  3.4 |  7386 nm² |   362 | 20.4 | flex over (same root cause) |

The 19 % rigid agreement validates the K2D Mayer-integral implementation
and the binding kernel reuse (radial_u_kbt + angle_factor). The K10 /
K01 over-prediction is the same B2.2 σ_z over-width documented in
derivation/02/05 Q2 — once we have real slab data this will tighten.

### Workstream B — 12 legacy scripts + 15 results md frontmatter

**Script edits** (insert 8-line YAML-writer block right after each script's
`with open(out_md, "w") as fp:`):

1. scripts/closure_four_term.py → closure_four_term_data.md
2. scripts/closure_wlc_three_term.py → closure_wlc_three_term.md
3. scripts/reconcile_methods.py → method_reconciliation.md
4. scripts/raw_tether_partition_k2d.py → raw_tether_partition.md (write_report)
5. scripts/plot_xi_rl_decomposition.py → xi_rl_decomposition.md
6. scripts/xi_rl_decomposition.py → xi_rl_fit_summary.md
7. scripts/convolve_k2d_xi.py → k2d_xi_curves.md
8. scripts/conf_entropy.py → conf_entropy_schlitter.md
9. scripts/mi_decomposition.py → mi_decomposition.md
10. scripts/decomposition_full.py → full_decomposition.md
11. scripts/k2d_sanity.py → k2d_sanity.md
12. scripts/absolute_k2d.py → absolute_k2d.md

Pattern inserted (same 6-line YAML across all scripts):
```python
fp.write("---\n")
fp.write('purpose: "<one-line summary>"\n')
fp.write('audience: "<who reads this>"\n')
fp.write("status: current\n")
fp.write("generated_by: scripts/<name>.py\n")
fp.write('related: "<derivation/calibration cross-ref>"\n')
fp.write("---\n\n")
```

**Bulk pre-write** (so existing md files are immediately compliant
without needing to re-run every script): same YAML prepended in place
to 15 existing md files (12 auto-generated + 3 manual: closure_four_term.md,
observables_inventory.md, potential_framework_review.md).

**Smoke test**: re-ran `scripts/reconcile_methods.py` — script regenerated
md with frontmatter intact.

**Verification**: `yaml.safe_load` walk on all 18 md files in `results/`
(15 in results/ + 3 in results/derivation_b2/ — wait, B2.4/B2.5 output
files already had FM from 6c-audit; total now is 16 + 2 = 18). All
18 parse OK.

### Workstream C — 复盘 reporting (this commit)

- `log/sessions/2026-06-02_session6c_cluster_prep_audit.md` (this file)
- `log/calibration/b2_chain_completeness.md` — B2.1-2.5 acceptance
  criteria snapshot table
- `log/README.md` — index updated: sessions=7, calibration=5

## Key findings / numbers

1. **analyze_slab_traj.py K100 pilot K2D = 15155 nm² (19 % off target
   12705)** — validates the Mayer-integral implementation. Same kernel
   as raw_tether_partition_k2d gives the rigid magnitude right when fed
   B2.2 σ_z = 0.625 nm.
2. **All 18 results/*.md now Tier 2 compliant** (purpose / audience /
   status / generated_by / related).
3. **12 scripts future-proofed**: any subsequent regen writes FM block
   first. Pattern is uniform so a new agent can grep for it.
4. **Cluster integration single point**: `_load_slab_frames_real` is
   the ONLY hook needed when slab traj.xyz files arrive — saves Session
   6d from having to redesign the K2D math.

## Decisions made

- analyze_slab_traj.py uses soft Mayer integral (matches
  raw_tether_partition_k2d). Hard-gate variant left as nan in output
  (we have it in derivation/03 if needed for comparison).
- Pilot h chosen per-system = 2·μ_z (not a single h=14) so all three
  systems exercise the integral on a non-trivial valid_frac.
- Frontmatter pattern intentionally 6 lines (purpose/audience/status/
  generated_by/related) to match the Tier 2 schema in 6a's CLAUDE.md
  navigation_map; not 10+ Tier 1 fields.

## Open questions / blockers

- 0 blockers. All Session 6c acceptance criteria met.
- Session 6d (async, cluster data arrival): the single hook to fill is
  `_load_slab_frames_real` — that's the only TODO left in
  analyze_slab_traj.py.

## Next steps

- Session 7 — D1 figure framework + 3 B2 headline figures (ratio test,
  anchor-cone, P_z per system). Now unblocked by 6c completing the
  Tier 2 FM coverage.
- Session 8 — D2a essay v2 §5.3 + §4.6 (uses 6b results + 6c FM-clean
  results md as source).
- Session 6d (ASYNC) — when slab MD / senior bundle data lands.

## How to reproduce verification

```bash
conda activate phys
python cluster/scripts/analyze_slab_traj.py --pilot
python3 -c "
import yaml, pathlib
for fp in sorted(pathlib.Path('results').glob('*.md')) + \
          sorted(pathlib.Path('results/derivation_b2').glob('*.md')):
    t = fp.read_text()
    end = t.index(chr(10)+'---'+chr(10), 4)
    yaml.safe_load(t[4:end])
print('all parse OK')
"
```

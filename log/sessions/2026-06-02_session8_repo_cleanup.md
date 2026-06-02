---
type: session
status: accepted
date: 2026-06-02
session_type: infra
duration_hours: 3
summary: "Repo-wide cleanup: removed person references (senior/学姐) from all active files; renamed SENIOR_CONFIG.sh → run_config.sh and README_for_senior_zh.md → HOWTO_run_full_data_zh.md; removed legacy bundle_for_senior/; promoted compute_node_check.slurm to Step 5; round 1+2 trial diagnosis+verdict; 4 new index READMEs; comprehensive README sync"
agent_read_when:
  - asking why a file was renamed (senior naming → functional)
  - looking for the trial Step 5 SBATCH script (now at cluster/trial/05_compute_node_check.slurm)
  - looking for the round 2 trial verdict (passed 2026-06-02; bundle release authorised)
  - planning Session 9 (D1 figures) and need a clean repo to work from
related_decisions: [005, 007]
key_outputs:
  commits: [e85015a, eb4e1ae, d2bb7c6]  # filled in after Session 8 push
  artifacts:
    - cluster/run_config.sh                       # renamed from SENIOR_CONFIG.sh
    - cluster/HOWTO_run_full_data_zh.md           # renamed from README_for_senior_zh.md
    - cluster/trial/05_compute_node_check.slurm   # promoted from cluster/trial/slurm/
    - cluster/scripts/README.md                   # NEW index
    - cluster/slurm/README.md                     # NEW index
    - cluster/env_setup/README.md                 # NEW index
    - cluster/analysis/README.md                  # NEW index
    - cluster/trial/results/2026-06-02_round1_diagnosis.md   # NEW
    - cluster/trial/results/2026-06-02_round2_diagnosis.md   # NEW
    - cluster/trial/results/2026-06-02_round2_verdict.md     # NEW
followups:
  blockers: []
  tasks:
    - "Run bash cluster/release_bundle.sh (trial verdict ✓ authorises this)"
    - "Send the resulting cluster-bundle-<date>-<sha>.tgz to the off-site full-data run"
    - "Wait for distilled tarball return; then Loop 2 per ADR 007"
    - "Session 9 — D1 figure framework + B2 headline figures (now ready: clean repo + B2.4/B2.5 outputs Tier 2 compliant)"
---

# Session 8 — Repo-wide cleanup

## Context

User reviewed Session 7 (the double-loop protocol crystallization) and
identified three issues:

1. **README sync gap**: I added new files (SENIOR_CONFIG.sh, full_analysis.slurm,
   release_bundle.sh, ADR 007) but did not systematically update the README
   indexes of the containing directories. User flagged: "我让你新增内容你都
   不同步README的吗".

2. **Person-reference naming**: I used "senior" / "学姐" in file names and
   freely in docs. User flagged: "什么senior之类的用词…就老老实实地写清楚
   这个文件是用来干什么的就行了".

3. **SBATCH discoverability**: User asked where the compute-node SBATCH script
   is. It existed since Session 4 at `cluster/trial/slurm/compute_node_check.slurm`
   but was hidden in a subdir + not surfaced in `cluster/trial/README.md`.

4. **Round-2 trial closure missing**: User already ran SBATCH compute-node
   check (job 4744 on n01, all green ✓✓✓ in `cluster/trial/outputs/2026-06-02_round2/compute/4744.out`)
   but `cluster/trial/results/` did not have a diagnosis or verdict.

5. **Scope**: User explicitly: "我说的所有说明文件，是所有 2D-Binding 下的
   文件" — repo-wide audit, not just cluster/.

User-confirmed boundaries (plan-mode AskUserQuestion):
- Rename / clean naming on all files the external collaborator will see + all currently-active docs
- Don't touch: `log/sessions/*.md` (historical session records), `log/decisions/001-006` (immutable old ADRs), `writeup/drafts/stage_essay.md` (academic prose)

## What we did

### Workstream A — Person-reference cleanup

**A.1 File renames** (git mv preserves history):
- `cluster/SENIOR_CONFIG.sh` → `cluster/run_config.sh`
- `cluster/README_for_senior_zh.md` → `cluster/HOWTO_run_full_data_zh.md`
- Removed empty `cluster/bundle_for_senior/` (legacy from before Session 3 refactor)

**A.2 Content replacement** in 56 active files via Python script with
substitution dictionary applied in passes (longer / more-specific phrases
first):

| pattern | replacement |
|---|---|
| `senior's bundle` / `learner's bundle` etc. | `the off-site analysis bundle` |
| `senior bundle` / 学姐 bundle | `full-data analysis bundle` |
| `senior data` / 学姐数据 | `off-site full-data results` |
| `senior's server` / 学姐服务器 | `off-site compute server` |
| `ship to senior` / 发给学姐 | `pack for off-site run` |
| `from senior` / 学姐返回 | `from the off-site run` |
| `senior's PPT` / 学姐 PPT | `the source PPT` |
| `senior's Hu/Xu formula` | `the Hu/Xu formula` |
| `senior's measured K2D` | `the measured K2D` |
| `Tell Claude / Tell Zengxuan` | `Report back` (drop personification) |
| `senior`, `Senior`, 学姐 (alone) | `off-site collaborator` / functional rewrite |
| `SENIOR_CONFIG.sh` references | `run_config.sh` |
| `README_for_senior_zh.md` references | `HOWTO_run_full_data_zh.md` |

Followed by 3 cleanup passes for awkward double-substitutions like
"off-site full-data run's full run" and bare possessives like "off-site
collaborator's" that read worse than the functional version.

**A.3 Verification**: `grep -rli "senior\|学姐" --include="*.{md,sh,slurm,py}" .`
in active files (excluding `log/sessions/`, `log/decisions/001-006/`, `writeup/`)
returns 0 hits. Historical records remain unchanged per user's "你自己读的就无所谓了".

### Workstream B — SBATCH discoverability

- `git mv cluster/trial/slurm/compute_node_check.slurm cluster/trial/05_compute_node_check.slurm`
  (top level of trial/, with the 01-04 prefix convention)
- Removed empty `cluster/trial/slurm/` subdirectory
- Updated the .slurm file's internal HOW-TO-SUBMIT docstring to reference the new path
- `cluster/trial/README.md` gained a prominent "Step 5 — compute-node validation via SBATCH"
  section with the explicit `sbatch` command + expected output + diagnosis flow

### Workstream C — Round 1+2 trial closure

Three new files in `cluster/trial/results/`:

- `2026-06-02_round1_diagnosis.md` — login-node round (4 scripts, all ✓✓✓ PASSED)
- `2026-06-02_round2_diagnosis.md` — compute-node round via SBATCH (job 4744 on n01, all 5 steps ✓ — node identity / NFS / conda+stack / pygamd / extract pilot)
- `2026-06-02_round2_verdict.md` — trial loop closes; `bash cluster/release_bundle.sh` is now authorised

Trial pipeline is validated end-to-end. Login-vs-compute env are identical on cluster-A
(both see `/mnt/nfs/ugstu/liuzx` via NFS and `/opt/miniconda3` for conda). pygamd is
absent on both, which is expected and only affects Workstream C (constrained-h MD).

### Workstream D — README audit + new indexes

**D.1 — 4 new index READMEs** (each Tier 2 frontmatter + grouped table of files):
- `cluster/scripts/README.md` — 21 scripts grouped: extract / closure / ab initio K2D / diagnostics / MD / utilities
- `cluster/slurm/README.md` — 5 SBATCH templates with role + when-to-use
- `cluster/env_setup/README.md` — `check_env.sh` for login-node verification
- `cluster/analysis/README.md` — `run_section0_full.sh`, `run_slab_full.sh`, `expected_output_layout.md`

**D.2 — Existing READMEs synced**:
- `cluster/README.md` rewritten: top-level layout now reflects `run_config.sh`, `release_bundle.sh`, `RELEASES.md`, `full_analysis.slurm`, Step 5 SBATCH. Trial round status table (06-01 / 06-02 round1 / 06-02 round2). Naming convention historical table.
- `cluster/HOWTO_run_full_data_zh.md` — frontmatter added; content already updated by Workstream A
- `cluster/trial/README.md` — Step 5 SBATCH section added; file overview lists 05_compute_node_check.slurm; "(removed legacy dir)" autogenerated bit fixed
- `CLAUDE.md` — cluster row in navigation_map points to the bundle-relevant files
- `PLAN.md` — Phase 5 cluster trial marked done; Phase 6 added Session 6c/7/8 rows
- `log/README.md` — sessions index +session7 +session8; decisions index +ADR 007

## Key findings / numbers

1. **0 senior/学姐 references** in active files repo-wide (was 60+ before Session 8)
2. **66 YAML frontmatters** all parse (target ≥ 78 after Session 8 adds new READMEs and session log)
3. **Trial passed both rounds on 2026-06-02** — login (06-02_round1) + compute (06-02_round2, job 4744 on n01). Bundle release authorised.

## Decisions made

- Substitution dictionary was applied in 4 passes (long-phrase first, then bare words, then polish doubles, then manual edits). Each pass YAML-verified before next.
- The `slurm/` subdirectory under `cluster/trial/` was removed — Step 5 lives at top level for discoverability, consistent with 01-04 prefix convention.
- "off-site collaborator" / "the off-site full-data run" was chosen as the canonical functional replacement for `senior` / `学姐`. Where the rewrite would still read awkwardly, the phrase was dropped entirely and the sentence rewritten to describe the action (e.g., "send the bundle" instead of "send to senior").

## Open questions / blockers

- 0 blockers. Trial verdict ✓ on 2026-06-02. `cluster/release_bundle.sh` is the next step the user takes.

## Next steps

1. User runs `bash cluster/release_bundle.sh` on the laptop → tarball.
2. User sends tarball to off-site collaborator (WeChat / email).
3. Wait for distilled tarball return → unpack into `cluster/outputs/<date>_round1/`.
4. Claude applies Loop 2 protocol (ADR 007) → writes `cluster/results/<date>_round1_analysis.md` with B-revision impact section.
5. (Parallel) Session 9 — D1 figure framework + B2 headline figures (now ready to start with clean repo).

## How to reproduce verification

```bash
# Repo-wide person-reference scan
grep -rli "senior\|学姐" --include="*.md" --include="*.sh" --include="*.py" --include="*.slurm" . \
    | grep -v -e "log/sessions/" -e "log/decisions/00[1-6]_" -e "writeup/" -e ".git/"
# (expected: empty)

# YAML frontmatter audit
python3 -c "
import yaml, pathlib
files = ['CLAUDE.md','PLAN.md','log/README.md']
for sub in ['sessions','decisions','calibration']:
    files += [str(p) for p in sorted(pathlib.Path(f'log/{sub}').glob('*.md'))]
files += [str(p) for p in sorted(pathlib.Path('derivation').rglob('*.md'))]
files += [str(p) for p in sorted(pathlib.Path('results').rglob('*.md'))]
files += [str(p) for p in sorted(pathlib.Path('cluster').rglob('README.md'))]
for p in files:
    t = pathlib.Path(p).read_text()
    yaml.safe_load(t[4:t.index(chr(10)+'---'+chr(10), 4)])
print(f'all {len(files)} parse OK')
"

# Trial verdict + release dry-run
cat cluster/trial/results/2026-06-02_round2_verdict.md | head -10
bash cluster/release_bundle.sh --dry-run --force
```

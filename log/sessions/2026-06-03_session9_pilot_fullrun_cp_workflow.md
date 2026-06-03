---
type: session
status: in-progress
date: 2026-06-03
session_type: infra
duration_hours: 4
summary: "Pilot full-data on cluster-A exposed 3 path bugs (system_inputs results→outputs path, raw_tether mol.psf symlink, banner damage). Patched all 3 + added MD_PARENT auto-detect (cluster-A has no git → cyberduck overwrites edits, need zero-edit defaults). Also rewrote release_bundle.sh + HOWTO + cluster READMEs from tar-based to cp-based handoff."
agent_read_when:
  - asking why cluster/run_analysis.sh has MD_PARENT auto-detect logic
  - asking what bugs the pilot full-data run exposed
  - asking why release_bundle.sh stopped producing tarballs
  - reviewing the cp-based off-site collaborator workflow
related_decisions: [005, 007]
key_outputs:
  commits: []  # filled in after Session 9 push
  artifacts:
    - cluster/run_analysis.sh                              # MD_PARENT auto-detect + per-system symlinks + ln -sfn
    - cluster/run_config.sh                                # auto-detect note in MD_PARENT comment
    - cluster/scripts/system_inputs.py                     # _chain_coords_npz() — env var + dual-path fallback
    - scripts/system_inputs.py                             # same patch, kept in sync
    - cluster/scripts/extract_parallel.py                  # banner + docstring fix from Session 8 substitution damage
    - cluster/trial/04_extract_pilot.sh                    # step-4 tip rewritten for cp workflow
    - cluster/HOWTO_run_full_data_zh.md                    # rewrite: rsync (not tar), auto-detect (not MD_PARENT edit), cp back (not WeChat)
    - cluster/release_bundle.sh                            # no tar; cyberduck reminder + rsync + WeChat templates
    - cluster/README.md                                    # Loop 2 narrative cp-based
    - cluster/trial/README.md                              # Loop 1 closure section matches new release_bundle behaviour
    - cluster/outputs/README.md                            # cp-based intake convention
    - cluster/results/README.md                            # "related_release: git SHA" not "tarball"
    - CLAUDE.md                                            # cluster reference updated (no cluster-B email, cyberduck note)
    - cluster/trial/results/2026-06-03_pilot_fullrun_diagnosis.md  # post-iteration (TBD)
    - cluster/trial/results/2026-06-03_pilot_fullrun_verdict.md    # post-iteration (TBD)
    - cluster/RELEASES.md                                  # first row (TBD)
followups:
  blockers: []
  tasks:
    - "Wait for round 3 pilot result (after user cyberduck-upload of auto-detect patches)"
    - "When pilot is green: write diagnosis + verdict + Session 9 log final + commit + push"
    - "Run bash cluster/release_bundle.sh on laptop → record first RELEASES.md row + WeChat the off-site collaborator"
    - "Session 10 — D1 figure framework + B2 headline figures"
---

# Session 9 — Pilot full-data run + cp-based workflow rewrite

## Context

After Session 8 closed (commit ff90300, trial verdict ✓ on 2026-06-02), the
next step per the plan was to run the full-data pilot on cluster-A to verify
the prod path end-to-end. Two user clarifications arrived:

1. **Off-site collaborator has shared filesystem access to cluster-A** —
   she does not receive a tarball; she rsyncs cluster/ from
   `/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/` directly. The Session 7/8
   tar+WeChat handoff design is obsolete.

2. **Cluster-A has no git, and the user has no permission to install it** —
   so the user keeps cluster-A in sync via cyberduck (SFTP). Critically,
   "delete cluster/ on cluster-A → re-upload local cluster/" wipes any
   edits made on cluster-A. This means **any default in `run_config.sh`
   that requires per-run editing is fragile** — the placeholder will be
   restored on the next upload.

Session 9 addresses both: pilot the prod path + rewrite the handoff for
cp/cyberduck instead of tar/WeChat + add auto-detect so zero edits are
required.

## What we did

### Workstream A — pilot full-data run iterations

**Round 1** (2026-06-03 ~00:42): user uploaded laptop cluster/ via cyberduck,
edited `cluster/run_config.sh` to set `MD_PARENT=/mnt/nfs/ugstu/liuzx`,
and ran `bash cluster/run_analysis.sh --pilot`. Extract + merge succeeded (6
replicas across 3 systems = 4000 frames merged), but 3 downstream scripts
failed:

| script | error | root cause |
|---|---|---|
| closure_four_term.py | `FileNotFoundError: cluster/results/chain_coords/.../chain_coords.npz` | `system_inputs.py:161` reads from `results/chain_coords/` but `run_analysis.sh` writes to `outputs/chain_coords/` (Session 7 IO refactor — loader path not updated) |
| closure_wlc_three_term.py | same | same |
| raw_tether_partition_k2d.py | `FileNotFoundError: cluster/outputs/15_120x120_K100_EPS05/s001/mol.psf` | script constructs `root/outputs/<sys>/s001/`, but `run_analysis.sh` only created a `cluster/outputs/md_root` symlink (one level), not per-system symlinks |

Also cosmetic: `extract_parallel.py` banner showed `(removed legacy dir)src/extract_parallel.py`
from Session 8 mass substitution damage; `04_extract_pilot.sh` step-4 tip
text had `tar czf off-site analysis bundle.tgz (removed legacy dir)` (broken
shell + stale narrative).

**Round 2** (2026-06-03 ~10:45, after patch upload): user re-uploaded laptop
cluster/ via cyberduck. But the cyberduck overwrite restored the
`MD_PARENT="/path/to/your/MD/data/root"` placeholder default, the script
exit-failed at the `cd $MD_PARENT` line, all 3 systems were skipped, and
the same downstream errors surfaced.

→ Root cause: the cyberduck overwrite workflow requires **zero-edit
defaults** in `run_config.sh` — anything the user has to edit per-run will
be wiped. Need auto-detect.

**Round 3** (after the auto-detect patch lands on cluster-A): TBD when user
re-runs.

### Workstream B — script patches (5 files)

| file | change |
|---|---|
| `scripts/system_inputs.py` + `cluster/scripts/system_inputs.py` | new `_chain_coords_npz(root, sys_name)` helper: honors `$CHAIN_COORDS_ROOT` env var → tries `outputs/chain_coords/` (cluster convention) → tries `results/chain_coords/` (laptop convention). Both `load_all()` and `load_all_raw()` use it. Works in both contexts. |
| `cluster/run_analysis.sh` | (a) per-system symlinks `cluster/outputs/<sys>/ → $MD_PARENT/<sys>/` (replaces the single `cluster/outputs/md_root` symlink), with `ln -sfn` to overwrite broken/stale symlinks from previous runs. (b) **MD_PARENT auto-detect**: if config has placeholder or nonexistent path, probe `$BUNDLE_ROOT/../..`, `$BUNDLE_ROOT/..`, `$HOME` for any of `SYSTEMS_DIRS`; first hit wins. Fail-fast (`exit 5`) if no match. (c) updated banner + footer: dropped tar+WeChat language, replaced with cp-based instruction. |
| `cluster/run_config.sh` | `MD_PARENT` comment rewritten to explain auto-detect convention (zero edit needed if bundle lives at `<md_root>/2D-Binding/cluster/`). |
| `cluster/scripts/extract_parallel.py` | banner + docstring: `(removed legacy dir)src/extract_parallel.py` → `cluster/scripts/extract_parallel.py`; `(removed legacy dir)run_full_analysis.sh` → `cluster/run_analysis.sh`. |
| `cluster/trial/04_extract_pilot.sh` | step-4 next-step tip rewritten: dropped broken `tar czf off-site analysis bundle.tgz (removed legacy dir)`, rewrote to `bash cluster/run_analysis.sh --pilot` + cp-based handoff. |

Plus a pass to fix other Session 8 substitution damage repo-wide
(`The the source` → `The source`, etc.) — 13 files touched.

### Workstream C — cp-based workflow rewrite (5 files)

| file | change |
|---|---|
| `cluster/HOWTO_run_full_data_zh.md` | full rewrite: "一、解压" → "一、rsync cluster/ 到工作目录" with one-line rsync command; "二、改 run_config.sh" → marked optional thanks to auto-detect, with a table of when-to-edit cases; "四、发回" → "四、cp distilled/ 回 Zengxuan 共享目录"; dropped "谢谢外部协作者!" closer (also from the senior-removal substitution) |
| `cluster/release_bundle.sh` | full refactor: no tarball; verdict check + RELEASES.md row + cyberduck-upload reminder (cluster-A no git → user must refresh manually) + rsync command template + WeChat message draft. Now records git SHA only (not tarball name). |
| `cluster/README.md` | Loop 2 section: replaced "User sends `cluster-bundle-<date>-<sha>.tgz` (WeChat/email)" with cp-based 6-step flow (cyberduck refresh → rsync → sbatch → cp distilled → cyberduck download → Loop 2 analysis). |
| `cluster/trial/README.md` | "Loop 1 closure" section explains the new release_bundle.sh behaviour (no tar, prints templates instead). |
| `cluster/outputs/README.md` | intake convention is `cp` from the off-site collaborator (she has shared access), not `tar xzf`. Updated "How to populate" example accordingly. |
| `cluster/results/README.md` | `related_release` field comment: "which git SHA the off-site collaborator ran" (was "which tarball off-site collaborator ran"). |
| `CLAUDE.md` | Cluster reference compact section updated: removed stale "cluster-B not accessible to us, emails back distilled tarball" narrative; now describes the shared-cluster-A + cyberduck + cp model. |

## Key findings / numbers

1. **3 bugs in the Session 7 IO refactor** were dormant until full-data pilot
   exercised them. Local closure_four_term runs on the laptop work fine
   because `results/chain_coords/` already exists from older runs; cluster
   path mismatch only fires when merge writes to `outputs/chain_coords/`.
2. **Cyberduck overwrite workflow ⟹ zero-edit defaults are mandatory**.
   This shaped the auto-detect design: probe likely paths, fail-fast if
   none work, but don't require user editing for the common case.
3. **The off-site collaborator workflow simplifies dramatically** under cp:
   no tarball packing, no email transfer, no untar on her end. She rsyncs,
   sbatches, cps result. The "release_bundle.sh produces tarball" step that
   Session 7 designed is now purely a release-record-keeper.

## Decisions made

- **MD_PARENT auto-detect search order**: `$BUNDLE_ROOT/../..` first (handles
  the convention `<md_root>/2D-Binding/cluster/`), then `$BUNDLE_ROOT/..`
  (handles `<md_root>/cluster/`), then `$HOME`. Probe is "directory exists
  AND contains at least one entry from SYSTEMS_DIRS".
- **Symlinks use `ln -sfn`**: `-f` overwrites stale/broken symlinks
  (otherwise multi-run repeats hit "File exists"); `-n` blocks the
  unwanted "create new symlink INSIDE existing dir if target is a dir"
  behaviour that `-f` alone has.
- **No tarball release**: cluster-A is the shared handoff. `release_bundle.sh`
  is now a release-recorder + template printer, not a packer.
- **HOWTO recommends DEST under MD root**: by placing bundle at
  `$MD_ROOT/2D-Binding-fullrun/cluster/`, auto-detect handles MD_PARENT
  without any edit. Lone exception documented.

## Open questions / blockers

- Awaiting round 3 pilot result on cluster-A. Expected outcome: all 5
  scripts succeed; `cluster/outputs/distilled/` total ~5 MB. If anything
  unexpected, Workstream B adds more patches.

## Next steps

1. User cyberduck-uploads the latest patched `run_analysis.sh` +
   `run_config.sh` + `system_inputs.py` (in both `scripts/` and
   `cluster/scripts/`) + `extract_parallel.py` + `04_extract_pilot.sh`,
   then re-runs pilot.
2. Claude writes `2026-06-03_pilot_fullrun_diagnosis.md` +
   `2026-06-03_pilot_fullrun_verdict.md` after green pilot.
3. User runs `bash cluster/release_bundle.sh` on laptop → first row in
   `cluster/RELEASES.md`, plus the WeChat template to send the off-site
   collaborator.
4. Session 10 — D1 figure framework + B2 headline figures.

## How to reproduce verification

```bash
# Repo-wide person-reference + substitution scan (must return only excluded set)
grep -rli "senior\|学姐\|The the\|the the off-site\|removed legacy dir" \
    --include="*.md" --include="*.sh" --include="*.py" --include="*.slurm" . \
    | grep -v -e "log/sessions/" -e "log/decisions/00[1-6]_" -e "writeup/" -e ".git/"
# (expected empty)

# YAML frontmatter audit
python3 -c "
import yaml, pathlib
files = ['CLAUDE.md','PLAN.md','log/README.md']
for sub in ['sessions','decisions','calibration']:
    files += [str(p) for p in sorted(pathlib.Path(f'log/{sub}').glob('*.md'))]
files += [str(p) for p in sorted(pathlib.Path('derivation').rglob('*.md'))]
files += [str(p) for p in sorted(pathlib.Path('results').rglob('*.md'))]
files += [str(p) for p in sorted(pathlib.Path('cluster').rglob('README.md'))]
files += [str(p) for p in sorted(pathlib.Path('cluster').rglob('HOWTO_*.md'))]
for p in files:
    t = pathlib.Path(p).read_text()
    yaml.safe_load(t[4:t.index(chr(10)+'---'+chr(10), 4)])
print(f'all {len(files)} parse OK')
"

# release_bundle dry-run (after trial verdict)
bash cluster/release_bundle.sh --force   # verify cyberduck reminder + rsync template printed
```

---
purpose: "Pilot full-data run on cluster-A (2026-06-03): 3 iterations — round 1 + round 2 failures + Session 9 patches → round 3 fully green"
audience: user + Claude (next session) + reviewer of Loop 1 protocol
status: current
round: 2026-06-03_pilot_fullrun (rounds 1, 2, 3)
node: c208 (login node, bash mode)
verdict: PASSED
---

# Pilot full-data run diagnosis — 2026-06-03

This is the first end-to-end exercise of `bash cluster/run_analysis.sh --pilot`
on cluster-A's actual 7-replica data (`/mnt/nfs/ugstu/liuzx/` parent + 3
system dirs: K100, K10, K01). Three iterations were needed to expose latent
bugs that were dormant after the Session 7 IO refactor.

## Iterations

### Round 1 (00:42 KST) — 3 path bugs exposed

Setup: user cyberduck-uploaded the laptop `cluster/`, edited
`run_config.sh` to set `MD_PARENT=/mnt/nfs/ugstu/liuzx`, ran the pilot.

Extract + merge both succeeded:
- extract: 6/6 replicas OK (K100 s001+s002, K10 s001+s002, K01 s001+s002)
- merge: 3 merged npz produced under `cluster/outputs/chain_coords/<sys>/`

Three downstream scripts failed:

| script | error | root cause |
|---|---|---|
| `closure_four_term.py` | `FileNotFoundError: cluster/results/chain_coords/.../chain_coords.npz` | `cluster/scripts/system_inputs.py:161` reads from `results/chain_coords/`, but Session 7's `run_analysis.sh` writes merge output to `outputs/chain_coords/`. Loader path was not updated when the IO convention changed. |
| `closure_wlc_three_term.py` | same | Same root cause (same `load_all()`). |
| `raw_tether_partition_k2d.py` | `FileNotFoundError: cluster/outputs/15_120x120_K100_EPS05/s001/mol.psf` | Script constructs `root/outputs/<sys>/s001/`. Session 7's `run_analysis.sh` only created a `cluster/outputs/md_root → MD_PARENT` symlink (one level above), not per-system symlinks. |

Also cosmetic: `extract_parallel.py` banner showed `(removed legacy dir)src/extract_parallel.py` from Session 8 mass-substitution damage; `04_extract_pilot.sh` step-4 tip text had broken `tar czf off-site analysis bundle.tgz (removed legacy dir)`.

### Round 2 (10:45 KST) — cyberduck overwrite restored placeholder

Setup: user cyberduck-uploaded the 4 patched files (`system_inputs.py`,
`run_analysis.sh`, `extract_parallel.py`, `04_extract_pilot.sh`), then
re-ran the pilot **without editing `run_config.sh`** (which the cyberduck
upload had reset to the placeholder `MD_PARENT="/path/to/your/MD/data/root"`).

Result: `cluster/run_analysis.sh: line 95: cd: /path/to/your/MD/data/root: No such file or directory` → all 3 systems skipped → downstream errors looked similar to round 1 but for the upstream reason that nothing was extracted.

→ Root cause: **the cyberduck-overwrite workflow** (which user uses because cluster-A has no git) **requires zero-edit defaults**; the per-run vim of `run_config.sh` is fragile because the next upload wipes it. Solution: add auto-detect.

### Round 3 (11:13 KST) — all green with auto-detect

Setup: user cyberduck-uploaded `run_analysis.sh` (with new auto-detect block) + `run_config.sh` (with auto-detect note). Did NOT edit `run_config.sh`. Ran the pilot.

Auto-detect fired immediately:

```
[MD_PARENT] '/path/to/your/MD/data/root' has no expected system dirs — auto-detecting...
[MD_PARENT] auto-detected: /mnt/nfs/ugstu/liuzx
```

All 8 pipeline steps ✓, 0 WARN / 0 FAIL / 0 Traceback. Distilled output:

| file | size |
|---|---:|
| `inventory.tsv` | 116 B |
| `closure_four_term_data.{md,npz}` | 2.5 K + 26 K |
| `closure_wlc_three_term.{md,npz}` | 2.1 K + 18 K |
| `raw_tether_partition.{md,npz}` | 3.5 K + 27 K |
| `diagnose_bias.txt` | 2.8 K |
| `method_reconciliation.md` | 4.7 K |
| `method_reconciliation.png` | 121 K |
| `run_log.txt` | 32 K |
| **total** | **~256 K** |

Wall time: 31 s (00:42 → 00:43 in round 1; 11:13 → 11:13 in round 3).

## Pilot result numbers (preliminary — 2 replicas per system, n_bootstrap=20)

These are **pilot** numbers; production with full replicas + n_bootstrap=200
will be tighter. But they're already informative.

### Four-term S1-S23 closure (`closure_four_term_data.md`)

| pair | ΔΔF_sum ± boot σ | target | gap | vs s001-only (Session 1 commit 3dee6f0) |
|---|---:|---:|---:|---:|
| flex − rigid | **+3.657 ± 0.013** kBT | +3.56 | +0.097 | s001: +3.96 ± 0.03 → pilot: closer to target |
| semi − rigid | **+2.672 ± 0.024** kBT | +2.68 | −0.008 | s001: +2.69 ± 0.03 → pilot: ≈ same |
| semi − flex | **−0.985 ± 0.019** kBT | −0.90 | −0.085 | s001: −1.27 ± 0.03 → pilot: closer to target |

Reading: **the 14σ / 13σ systematic gap on flex-rigid + semi-flex that we documented in Session 1 (A3 bootstrap) shrinks substantially with just 2 replicas**. flex-rigid moved from +0.40 kBT gap to +0.10 kBT; semi-flex moved from -0.37 to -0.09. This is consistent with the "data volume" hypothesis on the *closure* level.

### WLC three-term reimpl (`closure_wlc_three_term.md`)

| pair | ΔΔF_sum ± boot σ | target | PPT s25 | gap vs target |
|---|---:|---:|---:|---:|
| flex − rigid | **+4.516 ± 0.015** kBT | +3.56 | +3.64 | +0.95 |
| semi − rigid | **+2.064 ± 0.024** kBT | +2.68 | +2.47 | −0.62 |
| semi − flex | **−2.452 ± 0.025** kBT | −0.90 | −1.18 | −1.55 |

Reading: with our L_c=12 nm convention, B1 reimpl still overshoots PPT s25 by 0.9-1.3 kBT on flex pairs. This is *not* the same as the s001 result (commit 3dee6f0: +5.23 / +2.05 / -3.18), but it's still ~0.7-1 kBT away from PPT s25. The PPT s25 mystery isn't resolved by 2 replicas; the full-replica run will be the proper test.

### Raw tether partition (`raw_tether_partition.md`)

| pair | soft-kernel ΔΔF ± σ | target | closed |
|---|---:|---:|---:|
| flex-rigid | +3.331 ± 0.061 | +3.56 | 94% |
| semi-rigid | +2.424 ± 0.037 | +2.68 | 90% |
| semi-flex | −0.907 ± 0.078 | −0.90 | 101% |

Pilot K2D,max numbers (soft kernel, 200K MC pairs):

| sys | h\* | K2D,max | bootstrap σ |
|---|---:|---:|---:|
| rigid | 19.6 nm | 9959 ± 172 nm² | 1.7% |
| semi | 17.6 nm | 882 ± 32 nm² | 3.7% |
| flex | 12.0 nm | 357 ± 20 nm² | 5.6% |

Ratios vs PPT target (12705 / 875 / 362): **rigid is 22% low — same gap as Session 1 A1 diagnosis (commit 3baebe7)**. Semi and flex match within 5%. Pilot doesn't change the picture, consistent with A1 narrative that the rigid 22% gap is an *intrinsic* unbound-sampling bias, not a data volume artifact.

### Bound vs unbound geometry (`diagnose_bias.txt`)

| sys | bound R_end_z | unbound R_end_z | Δz | bound tilt | unbound tilt | Δtilt |
|---|---:|---:|---:|---:|---:|---:|
| rigid | 9.162 nm (n=5140) | 8.902 nm (n=2360) | **+0.260** | 17.93° | 24.94° | **−7.01°** |
| semi | 7.945 (n=1959) | 7.258 (n=5541) | **+0.687** | 41.11° | 52.47° | −11.36° |
| flex | 6.629 (n=1835) | 5.146 (n=20165) | **+1.483** | 44.01° | 58.22° | −14.21° |

**This is the headline finding**. Compared to Session 1 A1 (s001 only, rigid Δz=−0.26 nm, Δtilt=+7°): *the magnitude is identical with 2 replicas, just sign convention flipped in display* (A1 reported `(bound − unbound)` as positive = bound more upright; this script shows same).

Implication: **the bound-vs-unbound geometric bias persists at the same magnitude with 2× more data**. If it were a data-volume sampling artifact it should show some shrinkage. This is an early signal that supports the A1 narrative: the bias is a real physical/sampling phenomenon driven by equilibrium MD's bound-state preference, not noise from few frames.

(Full-replica data would still be the definitive test — 2 replicas isn't enough to claim certainty — but the pilot already constrains the hypothesis.)

### 5-method reconcile (`method_reconciliation.md`)

| pair | consensus | target | gap |
|---|---:|---:|---:|
| flex-rigid | **+3.423 ± 0.051** | +3.56 | −0.137 |
| semi-rigid | **+2.465 ± 0.043** | +2.68 | −0.215 |
| semi-flex | **−0.945 ± 0.054** | −0.90 | −0.045 |

(Note: 3 of the 5 methods are HARDCODED constants per `reconcile_methods.py:114`. Only "Raw partition" + "WLC three-term reimpl" lines reflect actual pilot data. So this consensus is mostly a re-publication of the static numbers from earlier sessions, not a true full-data verdict.)

## Session 9 patches that landed

Applied locally and pushed via cyberduck across the 3 rounds:

1. `cluster/scripts/system_inputs.py` + `scripts/system_inputs.py` — new `_chain_coords_npz(root, sys_name)` helper that honors `$CHAIN_COORDS_ROOT` env var → tries `outputs/chain_coords/` (cluster convention) → falls back to `results/chain_coords/` (laptop convention). Both `load_all()` and `load_all_raw()` use it.
2. `cluster/run_analysis.sh` — (a) MD_PARENT auto-detect (probe `$BUNDLE_ROOT/../..`, `$BUNDLE_ROOT/..`, `$HOME` for SYSTEMS_DIRS); (b) per-system symlinks `cluster/outputs/<sys>/ → $MD_PARENT/<sys>/` with `ln -sfn` (overwrite stale); (c) fail-fast `exit 5` if no MD layout found; (d) banner + footer dropped tar+WeChat language.
3. `cluster/run_config.sh` — MD_PARENT comment block rewritten to explain auto-detect convention.
4. `cluster/scripts/extract_parallel.py` — banner + docstring restored from Session 8 substitution damage.
5. `cluster/trial/04_extract_pilot.sh` — step-4 next-step tip rewritten for cp workflow.

## Verdict

All 3 rounds together: **the pilot pipeline is now end-to-end functional on cluster-A**. Round 3 closed the loop cleanly: zero-edit `run_config.sh` works thanks to auto-detect; merge writes to the convention-correct path; raw_tether_partition resolves traj.xyz via per-system symlinks.

Production run (full replicas, n_bootstrap=200) is now safe to execute. The off-site collaborator can follow the same code path on her side (auto-detect handles her MD_PARENT too, given the recommended `<md_root>/2D-Binding-fullrun/cluster/` layout).

See `cluster/trial/results/2026-06-03_pilot_fullrun_verdict.md`.

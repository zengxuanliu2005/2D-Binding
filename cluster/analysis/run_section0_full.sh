#!/bin/bash
###############################################################################
#  cluster/analysis/run_section0_full.sh — §0 full pipeline on cluster
#
#  Purpose (also printed when run)
#  --------------------------------
#  Orchestrates §0 data-volume test from start to finish on cluster-A:
#    1. env_setup/check_env.sh         — env readiness
#    2. scripts/explore_replicas.sh    — inventory replicas per system
#    3. slurm/array_extract.slurm × 3  — pilot extract (1 sys × 2 reps) then
#                                         production array per system
#    4. scripts/merge_chain_coords.py  — concat → merged npz per system
#
#  After this finishes, rsync cluster/results/section0/merged_chain_coords/
#  back to laptop and run phd_closure / phd_closure_s25 / raw_tether against
#  the merged data to test the "data volume" hypothesis.
#
#  Failure tolerance: each step exits non-zero on failure; subsequent steps
#  are skipped.
#
###############################################################################
set -e

hr() { printf '\n%s\n' "──────────────────────────────────────────────────────────────────────"; }
section() { hr; printf '▶  %s\n' "$1"; hr; }
ok()    { printf '   ✓  %s\n' "$*"; }

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  §0 full pipeline — data volume test on cluster-A                 ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
End-to-end §0: inventory replicas → pilot extract → production array
→ merge per system. Output ends in cluster/results/section0/.

Total wall time : ~30-45 min depending on replica count.
Steps           : 4 (see below).
BAN

section 'Step 1/4 — env check'
bash cluster/env_setup/check_env.sh
ok 'env ready'

section 'Step 2/4 — inventory replicas'
bash cluster/scripts/explore_replicas.sh
cat cluster/results/section0/inventory.tsv
ok 'inventory written'

section 'Step 3/4 — pilot extract (1 sys × 2 reps)'
PILOT_JOB=$(SYS=15_120x120_K100_EPS05 sbatch --parsable --array=1-2 \
    cluster/slurm/array_extract.slurm)
echo "   pilot job id: $PILOT_JOB"
echo "   waiting for pilot to finish ..."
while squeue -h -j "$PILOT_JOB" 2>/dev/null | grep -q .; do
    sleep 30
done
ok 'pilot finished'
ls -la cluster/outputs/extracted/15_120x120_K100_EPS05/ | head | sed 's/^/     /'

section 'Step 4a/4 — production extract (per system)'
for SYS in 15_120x120_K100_EPS05 15_120x120_K10_EPS05 22_120x120_K01_EPS05; do
    N=$(awk -F'\t' -v s="$SYS" '$1==s {print $2}' cluster/results/section0/inventory.tsv)
    if [[ -z "$N" || "$N" -le 0 ]]; then
        echo "   skip $SYS (n=$N)"
        continue
    fi
    echo "   submitting $SYS  array=1-$N"
    SYS="$SYS" sbatch --array="1-$N" cluster/slurm/array_extract.slurm
done

section 'Step 4b/4 — wait + merge'
echo "   waiting for all extract jobs ..."
while squeue -h -u "$USER" -n extract 2>/dev/null | grep -q .; do
    sleep 60
done
ok 'all extract jobs finished'
python cluster/scripts/merge_chain_coords.py --n-jobs 3
ok 'merge complete'

section 'Done — next step'
cat <<'EOF'
   ✓✓✓  §0 pipeline finished.

   Sync the merged npz back to your laptop:
     rsync -av master:/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/results/section0/merged_chain_coords/ \
         results/chain_coords_full/

   Then locally:
     for s in phd_closure phd_closure_s25 raw_tether_partition_k2d; do
         python scripts/$s.py --bootstrap --n-bootstrap 200 --n-jobs 8 \
             --inputs-root results/chain_coords_full
     done
     python scripts/diagnose_rigid_sample_bias.py

   Compare numbers vs current results/ — if they converge to PPT s25 or
   target K2D, the "data volume" hypothesis is confirmed.
EOF

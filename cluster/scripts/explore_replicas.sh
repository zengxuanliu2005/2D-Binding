#!/bin/bash
###############################################################################
#  cluster/scripts/explore_replicas.sh — inventory replicas per system
###############################################################################
#
#  Run this once on cluster-A from the repo root. It writes
#  cluster/results/section0/inventory.tsv with one row per system:
#
#      system_dir_name   n_replicas   total_size   first_replica_example
#
#  The output drives the SLURM array range for cluster/slurm/array_extract.slurm
#  (e.g. `--array=1-N` where N comes from this inventory).
#
###############################################################################
set -u

hr() { printf '\n%s\n' "──────────────────────────────────────────────────────────────────────"; }
section() { hr; printf '▶  %s\n' "$1"; hr; }
ok()    { printf '   ✓  %s\n' "$*"; }
warn()  { printf '   ⚠  %s\n' "$*"; }

cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  cluster/scripts/explore_replicas.sh — replica inventory          ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Count how many continuation replicas (s001, s002, ...) exist per system
on cluster-A. Writes:

    cluster/results/section0/inventory.tsv

Use the n_replicas column to set --array=1-N for array_extract.slurm.

Override the MD root by exporting MD_BASE before running, e.g.:
    MD_BASE=/path/to/your/data bash cluster/scripts/explore_replicas.sh

Default MD_BASE is /mnt/nfs/ugstu/liuzx/2D-Binding-MD (tell Claude if wrong).

BAN

BASE="${MD_BASE:-/mnt/nfs/ugstu/liuzx/2D-Binding-MD}"
SYSTEMS=(15_120x120_K100_EPS05 15_120x120_K10_EPS05 22_120x120_K01_EPS05)

OUT=cluster/results/section0/inventory.tsv
mkdir -p "$(dirname "$OUT")"
printf 'system\tn_replicas\ttotal_size\tfirst_replica_example\n' > "$OUT"

section "Scanning $BASE"
if [[ ! -d "$BASE" ]]; then
    warn "MD_BASE=$BASE does not exist on this host."
    warn "Set MD_BASE env var and retry, e.g.:"
    warn "  MD_BASE=/mnt/nfs/ugstu/liuzx bash cluster/scripts/explore_replicas.sh"
    exit 2
fi

for SYS in "${SYSTEMS[@]}"; do
    DIR="$BASE/$SYS"
    if [[ ! -d "$DIR" ]]; then
        warn "$SYS not found at $DIR"
        printf '%s\t0\t-\t(missing)\n' "$SYS" >> "$OUT"
        continue
    fi
    N=$(ls -1d "$DIR"/s[0-9][0-9][0-9] 2>/dev/null | wc -l | tr -d ' ')
    SIZE=$(du -sh "$DIR" 2>/dev/null | cut -f1)
    FIRST=$(ls -1d "$DIR"/s[0-9][0-9][0-9] 2>/dev/null | head -1 | xargs -I{} basename {} 2>/dev/null)
    [[ -z "$FIRST" ]] && FIRST="(none)"
    ok "$SYS  n=$N  size=$SIZE  first=$FIRST"
    printf '%s\t%s\t%s\t%s\n' "$SYS" "$N" "$SIZE" "$FIRST" >> "$OUT"
done

section "Wrote $OUT"
echo
column -t -s $'\t' "$OUT"
echo
section "Next: submit one array job per system"
for SYS in "${SYSTEMS[@]}"; do
    N=$(awk -F'\t' -v s="$SYS" '$1==s {print $2}' "$OUT")
    if [[ -n "$N" && "$N" -gt 0 ]]; then
        echo "  SYS=$SYS sbatch --array=1-$N cluster/slurm/array_extract.slurm"
    fi
done

#!/bin/bash
###############################################################################
#  bundle_for_senior/run_full_analysis.sh — full-data rerun of A1/A3/B1
#
#  Self-contained orchestrator senior runs on her server. Walks her MD data
#  (parent dir), extracts chain_coords per replica, merges per system,
#  runs 4 analyses, packs distilled outputs into distilled/ for return.
#
#  Usage:
#      bash run_full_analysis.sh           # production (all replicas)
#      bash run_full_analysis.sh --pilot   # 2 replicas / system, ~5 min
#
#  Env overrides (optional):
#      MD_PARENT  : where her MD data lives relative to bundle (default ..)
#      N_JOBS     : parallel workers (default 8)
#      N_BOOTSTRAP: bootstrap iterations (default 200; pilot uses 20)
###############################################################################
set -uo pipefail

cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  bundle_for_senior — full-data rerun of A1/A3/B1                  ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Walks ../*/s### (your MD replicas), extracts chain_coords per replica,
merges them per system, then runs:

  1. closure_four_term.py --bootstrap         (S1-S23 4-term decomposition)
  2. closure_wlc_three_term.py --bootstrap     (3-term WLC closure)
  3. raw_tether_partition_k2d.py        (ab initio K2D)
  4. diagnose_bound_vs_unbound.py      (bound vs unbound geometry)
  5. reconcile_methods.py               (5-method ΔΔF consensus)

All outputs go to distilled/ (≈ 5 MB total). Send distilled/ back via
WeChat / email to Zengxuan.

BAN

# Config — override via env var if your naming differs
SYSTEMS_DIRS=(
    "15_120x120_K100_EPS05"
    "15_120x120_K10_EPS05"
    "22_120x120_K01_EPS05"
)
MD_PARENT="${MD_PARENT:-..}"
N_JOBS="${N_JOBS:-8}"
N_BOOTSTRAP="${N_BOOTSTRAP:-200}"

# Pilot mode
PILOT=""
if [[ "${1:-}" == "--pilot" ]]; then
    PILOT="--pilot"
    N_BOOTSTRAP=20
    echo "[PILOT] Pilot mode: 2 replicas per system, n_bootstrap=$N_BOOTSTRAP"
fi

# Setup
BUNDLE_ROOT="$(cd "$(dirname "$0")" && pwd)"
EXTRACTED_DIR="$BUNDLE_ROOT/extracted"
MERGED_DIR="$BUNDLE_ROOT/results/chain_coords"
DISTILLED="$BUNDLE_ROOT/distilled"
LOG="$DISTILLED/run_log.txt"
mkdir -p "$EXTRACTED_DIR" "$MERGED_DIR" "$DISTILLED"

# closure_four_term uses merged chain_coords (covers all replicas).
# raw_tether_partition_k2d and diagnose_bound_vs_unbound read raw traj.xyz
# directly from `<bundle_root>/outputs/<system>/s001/` — point that at the
# real MD parent dir so they find senior's first-replica data.
if [[ ! -e "$BUNDLE_ROOT/outputs" ]]; then
    ln -s "$(cd "$MD_PARENT" && pwd)" "$BUNDLE_ROOT/outputs"
fi

# Tee everything to log
exec > >(tee -a "$LOG") 2>&1
echo "=== run_full_analysis.sh — start $(date -Iseconds) ==="
echo "BUNDLE_ROOT=$BUNDLE_ROOT  MD_PARENT=$MD_PARENT  N_JOBS=$N_JOBS  PILOT=$PILOT"

# Inventory — write inventory + a flat (system, replica_dir) list for extract.
# Using flat list instead of associative array → bash 3.2 compatible (macOS).
echo
echo "--- inventory ---"
INVENTORY="$DISTILLED/inventory.tsv"
echo -e "system\tn_replicas_total\tn_replicas_used" > "$INVENTORY"
REPLICA_LIST="$(mktemp)"
for SYS in "${SYSTEMS_DIRS[@]}"; do
    SYS_DIR="$MD_PARENT/$SYS"
    if [[ ! -d "$SYS_DIR" ]]; then
        echo "  WARN: $SYS_DIR not found, skipping"
        echo -e "${SYS}\t0\t0" >> "$INVENTORY"
        continue
    fi
    N_ALL=$(ls -1d "$SYS_DIR"/s[0-9][0-9][0-9] 2>/dev/null | wc -l | tr -d ' ')
    REPS=$(ls -1d "$SYS_DIR"/s[0-9][0-9][0-9] 2>/dev/null | sort)
    if [[ -n "$PILOT" ]]; then
        REPS=$(echo "$REPS" | head -2)
    fi
    N_USED=$(echo "$REPS" | grep -c .)
    echo "  $SYS: $N_ALL replicas total, using $N_USED"
    echo -e "${SYS}\t${N_ALL}\t${N_USED}" >> "$INVENTORY"
    echo "$REPS" | while read REP_DIR; do
        [[ -z "$REP_DIR" ]] && continue
        echo -e "${SYS}\t${REP_DIR}" >> "$REPLICA_LIST"
    done
done

# Extract chain_coords for every (system, replica) — parallel via xargs -P
echo
echo "--- extract ($N_JOBS workers in parallel) ---"
EXTRACT_TASKS="$(mktemp)"
while IFS=$'\t' read -r SYS REP_DIR; do
    REP=$(basename "$REP_DIR")
    OUT_DIR="$EXTRACTED_DIR/$SYS/$REP"
    [[ -f "$OUT_DIR/chain_coords.npz" ]] && continue
    printf '%s\t%s\t%s\n' "$SYS" "$REP_DIR" "$OUT_DIR" >> "$EXTRACT_TASKS"
done < "$REPLICA_LIST"
rm -f "$REPLICA_LIST"
N_TASKS=$(wc -l < "$EXTRACT_TASKS" | tr -d ' ')
echo "  $N_TASKS replicas to extract"
if [[ "$N_TASKS" -gt 0 ]]; then
    N_JOBS="$N_JOBS" python -u "$BUNDLE_ROOT/src/extract_parallel.py" \
        < "$EXTRACT_TASKS" || { echo "ERROR: extract phase failed"; exit 2; }
fi
rm -f "$EXTRACT_TASKS"

# Merge per-system
echo
echo "--- merge per-system ---"
cd "$BUNDLE_ROOT/src"
python -u merge_chain_coords.py \
    --input-root "$EXTRACTED_DIR" \
    --output-root "$MERGED_DIR" \
    --n-jobs 3 \
    $PILOT || { echo "ERROR: merge failed"; exit 3; }
cd "$BUNDLE_ROOT"

# Analyses
echo
echo "--- closure_four_term (S1-S23 four-term) ---"
cd "$BUNDLE_ROOT/src"
python -u closure_four_term.py --bootstrap --n-bootstrap "$N_BOOTSTRAP" --n-jobs "$N_JOBS" \
    || echo "WARN: closure_four_term failed"
cd "$BUNDLE_ROOT"

echo
echo "--- closure_wlc_three_term (3-term WLC) ---"
cd "$BUNDLE_ROOT/src"
python -u closure_wlc_three_term.py --bootstrap --n-bootstrap "$N_BOOTSTRAP" --n-jobs "$N_JOBS" \
    || echo "WARN: closure_wlc_three_term failed"
cd "$BUNDLE_ROOT"

echo
echo "--- raw_tether_partition (absolute K2D) ---"
cd "$BUNDLE_ROOT/src"
python -u raw_tether_partition_k2d.py --bootstrap --n-bootstrap "$N_BOOTSTRAP" --n-jobs "$N_JOBS" \
    || echo "WARN: raw_tether_partition failed"
cd "$BUNDLE_ROOT"

echo
echo "--- diagnose bound vs unbound bias ---"
cd "$BUNDLE_ROOT/src"
python -u diagnose_bound_vs_unbound.py > "$DISTILLED/diagnose_bias.txt" 2>&1 \
    || echo "WARN: diagnose failed"
cd "$BUNDLE_ROOT"

echo
echo "--- reconcile methods (5-method consensus) ---"
cd "$BUNDLE_ROOT/src"
python -u reconcile_methods.py || echo "WARN: reconcile failed"
cd "$BUNDLE_ROOT"

# Distill
echo
echo "--- distill outputs ---"
for f in \
    "$BUNDLE_ROOT/results/closure_four_term.npz" \
    "$BUNDLE_ROOT/results/closure_four_term_data.md" \
    "$BUNDLE_ROOT/results/closure_wlc_three_term.npz" \
    "$BUNDLE_ROOT/results/closure_wlc_three_term.md" \
    "$BUNDLE_ROOT/results/raw_tether_partition.npz" \
    "$BUNDLE_ROOT/results/raw_tether_partition.md" \
    "$BUNDLE_ROOT/results/method_reconciliation.md" \
    "$BUNDLE_ROOT/results/figures/method_reconciliation.png"; do
    if [[ -f "$f" ]]; then
        cp "$f" "$DISTILLED/"
        echo "  + $(basename "$f")"
    fi
done

echo
echo "=== run_full_analysis.sh DONE $(date -Iseconds) ==="
echo "Total distilled output size:"
du -sh "$DISTILLED"
echo
echo "Please zip distilled/ and send back to Zengxuan:"
echo "  tar czf distilled_for_zengxuan.tgz distilled/"

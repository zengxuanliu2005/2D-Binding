#!/bin/bash
###############################################################################
#  cluster/run_analysis.sh — full-data rerun of A1/A3/B1
#
#  BASH FALLBACK entry point. If your server has SLURM, prefer
#  `sbatch cluster/slurm/full_analysis.slurm` (PRIMARY) — same orchestrator,
#  but resource-managed.
#
#  Self-contained orchestrator. Walks the off-site MD data (parent dir defined
#  in cluster/run_config.sh), extracts chain_coords per replica, merges
#  per system, runs 4 analyses + reconcile_methods, packs distilled outputs
#  to ~5 MB tarball ready to email back.
#
#  Usage:
#      bash cluster/run_analysis.sh           # production (all replicas)
#      bash cluster/run_analysis.sh --pilot   # 2 replicas / system, ~5 min
#
#  Config: cluster/run_config.sh (single source of truth, sourced below).
#  Env overrides still respected (config values use ${VAR:-default} pattern).
###############################################################################
set -uo pipefail

# Locate self — BUNDLE_ROOT is cluster/ (the dir containing this script)
BUNDLE_ROOT="$(cd "$(dirname "$0")" && pwd)"

# SBATCH preflight hint
if command -v sbatch >/dev/null 2>&1 && [[ -z "${SLURM_JOB_ID:-}" ]]; then
    echo
    echo "ℹ  SLURM detected. For better resource management, consider:"
    echo "     sbatch $BUNDLE_ROOT/slurm/full_analysis.slurm"
    echo "   Continuing with bash mode in 3 s (Ctrl-C to abort) ..."
    sleep 3
fi

cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  cluster/run_analysis.sh — full-data rerun of A1/A3/B1            ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Walks the off-site MD data, extracts chain_coords per replica, merges per
system, then runs:

  1. closure_four_term.py --bootstrap         (S1-S23 4-term decomposition)
  2. closure_wlc_three_term.py --bootstrap     (3-term WLC closure)
  3. raw_tether_partition_k2d.py        (ab initio K2D)
  4. diagnose_bound_vs_unbound.py      (bound vs unbound geometry)
  5. reconcile_methods.py               (5-method ΔΔF consensus)

All outputs go to distilled/ (≈ 5 MB total). Send distilled/ back via
WeChat / email to Zengxuan.

BAN

# Source single-source config (run_config.sh sits next to this script)
if [[ -f "$BUNDLE_ROOT/run_config.sh" ]]; then
    # shellcheck disable=SC1091
    source "$BUNDLE_ROOT/run_config.sh"
    echo "[config sourced from cluster/run_config.sh]"
else
    echo "WARN: run_config.sh not found at $BUNDLE_ROOT/; using built-in defaults"
    SYSTEMS_DIRS=(
        "15_120x120_K100_EPS05"
        "15_120x120_K10_EPS05"
        "22_120x120_K01_EPS05"
    )
    MD_PARENT="${MD_PARENT:-..}"
    N_JOBS="${N_JOBS:-8}"
    N_BOOTSTRAP="${N_BOOTSTRAP:-200}"
fi

# Pilot mode
PILOT=""
if [[ "${1:-}" == "--pilot" ]]; then
    PILOT="--pilot"
    N_BOOTSTRAP=20
    echo "[PILOT] Pilot mode: 2 replicas per system, n_bootstrap=$N_BOOTSTRAP"
fi

# Setup — work dirs under cluster/outputs/ per ADR 005 double-loop convention
EXTRACTED_DIR="$BUNDLE_ROOT/outputs/extracted"
MERGED_DIR="$BUNDLE_ROOT/outputs/chain_coords"
DISTILLED="$BUNDLE_ROOT/outputs/distilled"
LOG="$DISTILLED/run_log.txt"
mkdir -p "$EXTRACTED_DIR" "$MERGED_DIR" "$DISTILLED"

# raw_tether_partition_k2d and diagnose_bound_vs_unbound read raw traj.xyz
# directly from `<bundle_root>/outputs/<system>/s001/` — point that at the
# real MD parent dir so they find the off-site first-replica data.
if [[ ! -e "$BUNDLE_ROOT/outputs/md_root" ]]; then
    ln -s "$(cd "$MD_PARENT" && pwd)" "$BUNDLE_ROOT/outputs/md_root"
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
    N_JOBS="$N_JOBS" python -u "$BUNDLE_ROOT/scripts/extract_parallel.py" \
        < "$EXTRACT_TASKS" || { echo "ERROR: extract phase failed"; exit 2; }
fi
rm -f "$EXTRACT_TASKS"

# Merge per-system
echo
echo "--- merge per-system ---"
cd "$BUNDLE_ROOT/scripts"
python -u merge_chain_coords.py \
    --input-root "$EXTRACTED_DIR" \
    --output-root "$MERGED_DIR" \
    --n-jobs 3 \
    $PILOT || { echo "ERROR: merge failed"; exit 3; }
cd "$BUNDLE_ROOT"

# Analyses
echo
echo "--- closure_four_term (S1-S23 four-term) ---"
cd "$BUNDLE_ROOT/scripts"
python -u closure_four_term.py --bootstrap --n-bootstrap "$N_BOOTSTRAP" --n-jobs "$N_JOBS" \
    || echo "WARN: closure_four_term failed"
cd "$BUNDLE_ROOT"

echo
echo "--- closure_wlc_three_term (3-term WLC) ---"
cd "$BUNDLE_ROOT/scripts"
python -u closure_wlc_three_term.py --bootstrap --n-bootstrap "$N_BOOTSTRAP" --n-jobs "$N_JOBS" \
    || echo "WARN: closure_wlc_three_term failed"
cd "$BUNDLE_ROOT"

echo
echo "--- raw_tether_partition (absolute K2D) ---"
cd "$BUNDLE_ROOT/scripts"
python -u raw_tether_partition_k2d.py --bootstrap --n-bootstrap "$N_BOOTSTRAP" --n-jobs "$N_JOBS" \
    || echo "WARN: raw_tether_partition failed"
cd "$BUNDLE_ROOT"

echo
echo "--- diagnose bound vs unbound bias ---"
cd "$BUNDLE_ROOT/scripts"
python -u diagnose_bound_vs_unbound.py > "$DISTILLED/diagnose_bias.txt" 2>&1 \
    || echo "WARN: diagnose failed"
cd "$BUNDLE_ROOT"

echo
echo "--- reconcile methods (5-method consensus) ---"
cd "$BUNDLE_ROOT/scripts"
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

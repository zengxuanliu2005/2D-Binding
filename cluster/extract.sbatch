#!/bin/bash
#SBATCH --job-name=2dbind-extract
#SBATCH --output=cluster/logs/extract_%A_%a.out
#SBATCH --error=cluster/logs/extract_%A_%a.err
#SBATCH --array=1-10                                # adjust to your replica range
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#
# Extract per-replica chain_coords.npz from a single trajectory file.
#
# SLURM array index ($SLURM_ARRAY_TASK_ID) selects the replica number,
# e.g. 1 -> s001, 2 -> s002.  The systems are looped over inside the
# script (each task does all three systems for its replica).
#
# Usage:
#     sbatch cluster/extract.sbatch
#
# Before submitting:
#   - edit  SBATCH --array=1-N        to match the number of replicas you have
#   - edit  TRAJ_ROOT                 if your replicas don't live under
#                                     /mnt/nfs/ugstu/liuzx
#   - edit  OUT_ROOT                  if you want the per-replica output
#                                     somewhere other than $PWD/chain_coords/
#
# Outputs land at
#     $OUT_ROOT/<system>/s$REPLICA/chain_coords.npz
# one per (system, replica) tuple.  Combine them with closure.sbatch.

set -euo pipefail

# -------- configurable --------
TRAJ_ROOT="${TRAJ_ROOT:-/mnt/nfs/ugstu/liuzx}"
OUT_ROOT="${OUT_ROOT:-$PWD/chain_coords}"
REPLICA=$(printf "s%03d" "$SLURM_ARRAY_TASK_ID")
SYSTEMS=(
    "15_120x120_K100_EPS05"
    "15_120x120_K10_EPS05"
    "22_120x120_K01_EPS05"
)
# ------------------------------

mkdir -p cluster/logs

# activate phys env (adjust to your cluster's conda init if different)
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate phys

cd "$SLURM_SUBMIT_DIR"

for SYS in "${SYSTEMS[@]}"; do
    SRC="${TRAJ_ROOT}/${SYS}/${REPLICA}"
    if [[ ! -d "$SRC" ]]; then
        echo "[skip] $SRC does not exist (replica missing for $SYS)"
        continue
    fi
    if [[ ! -f "$SRC/traj.xyz" ]]; then
        echo "[skip] $SRC/traj.xyz missing"
        continue
    fi
    OUT_DIR="${OUT_ROOT}/${SYS}/${REPLICA}"
    echo "[run] $SYS / $REPLICA -> $OUT_DIR/chain_coords.npz"
    python scripts/extract_chain_coords.py "$SRC" --out "$OUT_DIR"
done

echo "[done] extract task ${SLURM_ARRAY_TASK_ID} (${REPLICA}) finished"

#!/bin/bash
# Extract chain_coords.npz from every (system, replica) trajectory.
#
# Loops over the three K-systems and every s*** replica directory under
# each. For each replica it runs scripts/extract_chain_coords.py to read
# the 2-4 GB trajectory once and write a small (~few MB) npz containing
# the 13-bead chain positions, the per-frame bound state, and metadata.
#
# Already-done replicas are skipped (the matching chain_coords.npz exists
# in the per-replica output dir), matching the PhD's auto-job idiom of
# "do the work only if the output isn't there yet."
#
# Run from inside the `cluster/` directory, OR set REPO_ROOT explicitly.
# All paths after the configurable block can be overridden via env var
# before submission.

set -euo pipefail

# ----------------- configurable ---------------------------------
# Root directory containing the system folders. On the cluster this is
# the parent of 15_120x120_K100_EPS05/, 15_120x120_K10_EPS05/, and
# 22_120x120_K01_EPS05/ — likely /mnt/nfs/ugstu/liuzx or its 2d_binding_MD
# subdirectory. EDIT before submitting if your path differs.
TRAJ_ROOT="${TRAJ_ROOT:-/mnt/nfs/ugstu/liuzx/2d_binding_MD}"

# Where the per-replica chain_coords.npz files go. Default is a sibling
# directory next to where this script was submitted from (typically the
# `analysis/` working dir). chain_coords/<system>/<sNNN>/chain_coords.npz
OUT_ROOT="${OUT_ROOT:-$PWD/chain_coords}"

# Root of the repo containing scripts/extract_chain_coords.py.
# Defaults to the parent of THIS file's directory (assumes this script
# lives at <repo>/cluster/extract_all.sh).
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

SYSTEMS=(
    "15_120x120_K100_EPS05"
    "15_120x120_K10_EPS05"
    "22_120x120_K01_EPS05"
)
# -----------------------------------------------------------------

# Activate the phys conda env (CLAUDE.md says always use it).
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate phys

echo "[extract_all] TRAJ_ROOT=$TRAJ_ROOT"
echo "[extract_all] OUT_ROOT=$OUT_ROOT"
echo "[extract_all] REPO_ROOT=$REPO_ROOT"

n_done=0
n_skipped=0
n_missing_traj=0
n_missing_bond=0
for sys in "${SYSTEMS[@]}"; do
    SYS_DIR="${TRAJ_ROOT}/${sys}"
    if [[ ! -d "$SYS_DIR" ]]; then
        echo "[skip system] $SYS_DIR not found"
        continue
    fi
    # iterate replica directories s*** in chronological order
    for s in "$SYS_DIR"/s*; do
        [[ -d "$s" ]] || continue
        REPLICA=$(basename "$s")
        OUT_DIR="${OUT_ROOT}/${sys}/${REPLICA}"
        # incremental: don't redo what's done
        if [[ -f "$OUT_DIR/chain_coords.npz" ]]; then
            n_skipped=$((n_skipped+1))
            continue
        fi
        if [[ ! -f "$s/traj.xyz" ]]; then
            echo "[no traj] $sys/$REPLICA"
            n_missing_traj=$((n_missing_traj+1))
            continue
        fi
        if [[ ! -f "$s/num_bonds_for_xyz_frames.dat" ]]; then
            echo "[no bond] $sys/$REPLICA — num_bonds_for_xyz_frames.dat missing; skipping"
            n_missing_bond=$((n_missing_bond+1))
            continue
        fi
        echo "[run]      $sys/$REPLICA -> $OUT_DIR/chain_coords.npz"
        python "$REPO_ROOT/scripts/extract_chain_coords.py" "$s" --out "$OUT_DIR"
        n_done=$((n_done+1))
    done
done

echo "[extract_all done] $n_done extracted, $n_skipped already done, "\
"$n_missing_traj missing traj.xyz, $n_missing_bond missing num_bonds file"

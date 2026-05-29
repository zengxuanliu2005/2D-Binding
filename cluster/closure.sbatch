#!/bin/bash
#SBATCH --job-name=2dbind-closure
#SBATCH --output=cluster/logs/closure_%j.out
#SBATCH --error=cluster/logs/closure_%j.err
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#
# After all extract.sbatch array tasks have finished, combine the
# per-replica chain_coords.npz files (one merged npz per system) and
# run the PhD's S1-S23 four-term closure on the merged data.
#
# Usage:
#     sbatch cluster/closure.sbatch
#
# Before submitting:
#   - edit  CHAIN_COORDS_IN    if you used a non-default OUT_ROOT in extract
#   - by default it picks up everything under chain_coords/<sys>/s*/
#
# Outputs land in
#     results/chain_coords/<sys>/chain_coords.npz       (merged, per system)
#     results/phd_closure.npz, .md, _data.md            (closure tables)
#     results/figures/closure_phd.png                   (bar chart)
#
# Then copy the three merged chain_coords npz files (one per system) back
# to your laptop and replace results/chain_coords/<sys>/chain_coords.npz.
# I'll re-run the closure locally to update the markdown + figure on main.

set -euo pipefail

# -------- configurable --------
CHAIN_COORDS_IN="${CHAIN_COORDS_IN:-$PWD/chain_coords}"
SYSTEMS=(
    "15_120x120_K100_EPS05"
    "15_120x120_K10_EPS05"
    "22_120x120_K01_EPS05"
)
# ------------------------------

mkdir -p cluster/logs

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate phys

cd "$SLURM_SUBMIT_DIR"

# --- step 1: combine per-replica npz per system ---
for SYS in "${SYSTEMS[@]}"; do
    INPUTS=( "${CHAIN_COORDS_IN}/${SYS}"/s*/chain_coords.npz )
    if [[ ${#INPUTS[@]} -eq 0 ]] || [[ ! -e "${INPUTS[0]}" ]]; then
        echo "[err] no chain_coords.npz found under ${CHAIN_COORDS_IN}/${SYS}/"
        echo "       did extract.sbatch finish? Did you set CHAIN_COORDS_IN correctly?"
        exit 1
    fi
    OUT="results/chain_coords/${SYS}/chain_coords.npz"
    echo "[combine] ${SYS}: ${#INPUTS[@]} replicas -> ${OUT}"
    python scripts/combine_chain_coords.py "${INPUTS[@]}" --out "$OUT"
done

# --- step 2: closure on the merged data ---
echo "[closure]"
python scripts/phd_inputs.py
python scripts/phd_closure.py
python scripts/plot_phd_closure.py

echo "[done] closure.sbatch finished — see results/phd_closure.md"

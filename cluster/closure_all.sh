#!/bin/bash
# Combine per-replica chain_coords.npz files and run the four-term ΔF
# closure on the merged data. Run this AFTER extract_all.sh has finished
# for all systems.
#
# Inputs: the per-replica npz files produced by extract_all.sh, located
# under $CHAIN_COORDS_IN/<system>/s*/chain_coords.npz.
#
# Outputs:
#   $CHAIN_COORDS_IN/<system>/merged/chain_coords.npz   (per-system merged)
#   results/phd_closure.{md,npz,_data.md}               (closure tables)
#   results/figures/closure_phd.png                     (closure figure)
#
# Send the three merged chain_coords.npz files back to me (a few MB
# each); I'll plug them into the repo locally and update the closure on
# main.

set -euo pipefail

# ----------------- configurable ---------------------------------
CHAIN_COORDS_IN="${CHAIN_COORDS_IN:-$PWD/chain_coords}"
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
RESULTS_ROOT="${RESULTS_ROOT:-$REPO_ROOT}"
SYSTEMS=(
    "15_120x120_K100_EPS05"
    "15_120x120_K10_EPS05"
    "22_120x120_K01_EPS05"
)
# -----------------------------------------------------------------

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate phys

echo "[closure_all] CHAIN_COORDS_IN=$CHAIN_COORDS_IN"
echo "[closure_all] REPO_ROOT=$REPO_ROOT"
echo "[closure_all] RESULTS_ROOT=$RESULTS_ROOT"

# --- step 1: combine per-replica npz per system ---
for sys in "${SYSTEMS[@]}"; do
    # glob for per-replica npz; sort for reproducibility
    INPUTS=( "${CHAIN_COORDS_IN}/${sys}"/s*/chain_coords.npz )
    if [[ ${#INPUTS[@]} -eq 0 ]] || [[ ! -e "${INPUTS[0]}" ]]; then
        echo "[err] no per-replica chain_coords.npz under "\
"${CHAIN_COORDS_IN}/${sys}/ — did extract_all.sh finish? Did you set "\
"CHAIN_COORDS_IN to match its OUT_ROOT?"
        exit 1
    fi
    # write the merged file where the repo expects to find it
    OUT="${RESULTS_ROOT}/results/chain_coords/${sys}/chain_coords.npz"
    echo "[combine]  ${sys}: ${#INPUTS[@]} replicas -> ${OUT}"
    python "$REPO_ROOT/scripts/combine_chain_coords.py" "${INPUTS[@]}" --out "$OUT"
done

# --- step 2: closure on the merged data ---
cd "$REPO_ROOT"
echo "[inputs]"
python scripts/phd_inputs.py
echo "[closure]"
python scripts/phd_closure.py
echo "[plot]"
python scripts/plot_phd_closure.py

echo "[closure_all done]  See results/phd_closure.md for the table and "\
"results/figures/closure_phd.png for the figure."

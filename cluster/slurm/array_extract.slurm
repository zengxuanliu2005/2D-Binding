#!/bin/bash
###############################################################################
#  cluster/slurm/array_extract.slurm — array job to extract chain_coords
#
#  PURPOSE
#  -------
#  Runs cluster/scripts/extract_one_replica.py once per (system, replica) for
#  ONE system at a time. Submit once per system; --array=1-N where N is the
#  replica count returned by explore_replicas.sh inventory.tsv.
#
#  Outputs land at:
#      cluster/outputs/extracted/<SYS>/s<task_id>/chain_coords.npz
#
#  Use cases
#  ---------
#    (a) Pilot mode — verify the template runs at all:
#          SYS=15_120x120_K100_EPS05 sbatch --array=1-2 \\
#              cluster/slurm/array_extract.slurm
#    (b) Production per system (use inventory N):
#          SYS=15_120x120_K100_EPS05 sbatch --array=1-100 \\
#              cluster/slurm/array_extract.slurm
#
#  Then merge with cluster/scripts/merge_chain_coords.py.
###############################################################################

#SBATCH -J extract
#SBATCH -o cluster/outputs/logs/extract_%A_%a.log
#SBATCH -e cluster/outputs/logs/extract_%A_%a.err
#SBATCH -p gpu
#SBATCH -w n01
#SBATCH -N 1
#SBATCH -c 1

set -e
: "${SYS:?Export SYS first. e.g. SYS=15_120x120_K100_EPS05 sbatch ...}"

echo "==========================================================="
echo "  extract array job  ${SLURM_ARRAY_JOB_ID:-?}_${SLURM_ARRAY_TASK_ID:-?}"
echo "  system = $SYS"
echo "  start  : $(date -Iseconds)"
echo "==========================================================="

# auto-discover conda (cluster-A is /opt/miniconda3, laptops are ~/miniconda3)
for _prefix in /opt/miniconda3 ~/miniconda3 /opt/anaconda3 ~/anaconda3; do
    if [[ -f "$_prefix/etc/profile.d/conda.sh" ]]; then
        source "$_prefix/etc/profile.d/conda.sh"
        break
    fi
done
cd "${SLURM_SUBMIT_DIR:-$(pwd)}"
mkdir -p cluster/outputs/logs "cluster/outputs/extracted/$SYS"

REPLICA=$(printf "s%03d" "$SLURM_ARRAY_TASK_ID")
echo "▶  extracting $SYS / $REPLICA"
python cluster/scripts/extract_one_replica.py \
    --system "$SYS" \
    --replica "$REPLICA" \
    --out "cluster/outputs/extracted/$SYS/$REPLICA/chain_coords.npz" \
    --quiet

echo "==========================================================="
echo "  done $SYS/$REPLICA at $(date -Iseconds)"
echo "==========================================================="

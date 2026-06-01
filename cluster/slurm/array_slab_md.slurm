#!/bin/bash
###############################################################################
#  cluster/slurm/array_slab_md.slurm — 18-task constrained-h MD array
#
#  PURPOSE
#  -------
#  Runs constrained-h MD for every (system, h) combination on cluster-A:
#
#      task index 1- 6 : K100 × (8, 10, 12, 14, 16, 18) σ
#      task index 7-12 : K10  × same
#      task index 13-18: K01  × same
#
#  Only launch AFTER single_pilot.slurm has passed (so we know the template
#  and the cu_gala wiring in nvt-md-constrained-h.py are correct).
#
#  Expected wall time per task: depends on system, typically several hours
#  on a shared GPU. Total queue time can be days unless the cluster is idle.
#
#  Submit:
#      sbatch cluster/slurm/array_slab_md.slurm
#
#  Then analyze:
#      python cluster/scripts/analyze_slab_traj.py --n-jobs 8
###############################################################################

#SBATCH -J slab
#SBATCH -o cluster/outputs/logs/slab_%A_%a.log
#SBATCH -e cluster/outputs/logs/slab_%A_%a.err
#SBATCH -p gpu
#SBATCH -w n01
#SBATCH -N 1
#SBATCH -c 1
#SBATCH --array=1-18

set -e
echo "==========================================================="
echo "  slab MD task ${SLURM_ARRAY_TASK_ID}  of array ${SLURM_ARRAY_JOB_ID}"
echo "  start $(date -Iseconds)"
echo "==========================================================="

source ~/miniconda3/etc/profile.d/conda.sh
conda activate phys
cd "${SLURM_SUBMIT_DIR:-$(pwd)}"
mkdir -p cluster/outputs/logs

SYSTEMS=(K100 K10 K01)
HS=(8 10 12 14 16 18)
N_H=${#HS[@]}

I=$((SLURM_ARRAY_TASK_ID - 1))
SYS_IDX=$((I / N_H))
H_IDX=$((I % N_H))
SYS=${SYSTEMS[$SYS_IDX]}
H=${HS[$H_IDX]}

OUT=cluster/outputs/slab/${SYS}_h${H}
mkdir -p "$OUT"
echo "▶  task=$SLURM_ARRAY_TASK_ID  system=$SYS  h=${H}σ  out=$OUT"

python cluster/scripts/nvt-md-constrained-h.py \
    --system "$SYS" \
    --h "${H}.0" \
    --n-frames 500 \
    --seed $((20260601 + SLURM_ARRAY_TASK_ID)) \
    --out-dir "$OUT" \
    --quiet

echo "==========================================================="
echo "  done $SYS h=${H}σ at $(date -Iseconds)"
echo "==========================================================="

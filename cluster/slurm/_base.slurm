#!/bin/bash
###############################################################################
#  cluster/slurm/_base.slurm — base SBATCH template for cluster-A
#
#  PURPOSE
#  -------
#  Mirrors analysis/analysis.slurm (confirmed by senior 2026-06-01):
#    partition gpu, node n01, 1 node × 1 CPU, log %J.log, err %J.err.
#
#  This file is a TEMPLATE — do not submit directly. Copy it then override
#  -J (job name) and the command line at the bottom.
#
#  Why these defaults
#  ------------------
#    -p gpu   : the only partition senior confirmed runs MD jobs
#    -w n01   : the GPU node senior uses; -N 1 -c 1 matches her template
#    -o/-e    : %J expands to slurm job id (deterministic per job)
#    No -t   : senior said default wall time is enough — uncomment only
#              if you see jobs killed for time
###############################################################################

#SBATCH -J 2d_base                    # OVERRIDE: job name
#SBATCH -o %J.log                     # stdout (%J = job id)
#SBATCH -e %J.err                     # stderr
#SBATCH -p gpu                        # partition
#SBATCH -w n01                        # node (drop -w if you see collisions)
#SBATCH -N 1                          # 1 node (DO NOT CHANGE per senior)
#SBATCH -c 1                          # 1 CPU per task
# #SBATCH -t 24:00:00                 # uncomment if default is too short

set -e
echo "==========================================================="
echo "  SLURM job ${SLURM_JOB_ID:-?}  on  $(hostname)"
echo "  start  : $(date -Iseconds)"
echo "  partition=${SLURM_JOB_PARTITION:-?}  node=${SLURM_JOB_NODELIST:-?}"
echo "==========================================================="

# auto-discover conda (cluster-A is /opt/miniconda3, laptops are ~/miniconda3)
for _prefix in /opt/miniconda3 ~/miniconda3 /opt/anaconda3 ~/anaconda3; do
    if [[ -f "$_prefix/etc/profile.d/conda.sh" ]]; then
        source "$_prefix/etc/profile.d/conda.sh"
        break
    fi
done
conda activate phys

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

echo "ERROR: _base.slurm is a TEMPLATE. Copy and replace this echo with"
echo "       your actual command (and override -J at the top)."
exit 1

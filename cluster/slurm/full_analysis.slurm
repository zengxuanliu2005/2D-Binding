#!/bin/bash
###############################################################################
#  cluster/slurm/full_analysis.slurm — SBATCH wrapper for full-data analysis run
#
#  PRIMARY entry point for the full-data analysis bundle. Wraps the existing
#  cluster/run_analysis.sh orchestrator inside a SLURM-managed job so the
#  the full-data analysis workflow is exactly:
#
#      vim cluster/run_config.sh      # edit MD_PARENT etc.
#      sbatch cluster/slurm/full_analysis.slurm
#
#  All knobs (partition, time, memory, parallelism) come from
#  cluster/run_config.sh. The #SBATCH directives below are sane defaults;
#  if your cluster needs different headers, edit SLURM_* in run_config.sh
#  and re-submit (the wrapper re-reads the config inside the job).
###############################################################################

#SBATCH -J 2d_full_analysis
#SBATCH -o cluster/outputs/slurm-%j.log
#SBATCH -e cluster/outputs/slurm-%j.err
#SBATCH -p gpu
#SBATCH -N 1
#SBATCH -c 8
#SBATCH --mem=32G
#SBATCH -t 24:00:00
# NOTE: If your cluster requires a specific node, add `#SBATCH -w n01` (or
# override SLURM_NODE in run_config.sh and resubmit).

set -uo pipefail

cat <<'BAN'
╔════════════════════════════════════════════════════════════════════╗
║  cluster/slurm/full_analysis.slurm — the off-site full-data analysis  ║
╚════════════════════════════════════════════════════════════════════╝
PURPOSE
─────────
SLURM-wrapped run of cluster/run_analysis.sh. Walks the off-site MD data,
extracts chain_coords per replica, merges per system, runs 4 analyses
+ reconcile_methods, distills outputs to ~5 MB tarball ready for return.

CONFIG sourced from cluster/run_config.sh — edit there, not here.
BAN

# Job preamble
echo "==========================================================="
echo "  SLURM job ${SLURM_JOB_ID:-?}   $(hostname)   $(date -Iseconds)"
echo "  partition=${SLURM_JOB_PARTITION:-?}  node=${SLURM_JOB_NODELIST:-?}"
echo "  cpus=${SLURM_CPUS_ON_NODE:-?}  mem=${SLURM_MEM_PER_NODE:-?}M"
echo "==========================================================="

# Locate config relative to submit dir
SUBMIT_DIR="${SLURM_SUBMIT_DIR:-$(pwd)}"
cd "$SUBMIT_DIR"

if [[ ! -f cluster/run_config.sh ]]; then
    echo "ERROR: cluster/run_config.sh not found at $SUBMIT_DIR/cluster/"
    echo "       Submit from the bundle root (the dir containing cluster/)."
    exit 2
fi

# Source config (defines MD_PARENT, SYSTEMS_DIRS[], N_JOBS, N_BOOTSTRAP, PY_ENVS[], etc.)
# shellcheck disable=SC1091
source cluster/run_config.sh
echo
echo "[config]  MD_PARENT=$MD_PARENT"
echo "[config]  SYSTEMS_DIRS=(${SYSTEMS_DIRS[*]})"
echo "[config]  N_JOBS=$N_JOBS  N_BOOTSTRAP=$N_BOOTSTRAP"

# Validate MD_PARENT
if [[ ! -d "$MD_PARENT" ]]; then
    echo "ERROR: MD_PARENT ($MD_PARENT) is not a directory."
    echo "       Edit cluster/run_config.sh and resubmit."
    exit 3
fi

# Python env: try each PY_ENVS in order
echo
echo "--- python env ---"
ACTIVATED=""
for _prefix in /opt/miniconda3 ~/miniconda3 /opt/anaconda3 ~/anaconda3; do
    if [[ -f "$_prefix/etc/profile.d/conda.sh" ]]; then
        # shellcheck disable=SC1090
        source "$_prefix/etc/profile.d/conda.sh"
        echo "  conda root: $_prefix"
        break
    fi
done
for ENV in "${PY_ENVS[@]}"; do
    if conda activate "$ENV" 2>/dev/null; then
        # Verify required packages
        if python -c "import numpy, scipy, pandas, matplotlib" 2>/dev/null; then
            echo "  activated env: $ENV  ($(python -c 'import sys; print(sys.executable)'))"
            ACTIVATED="$ENV"
            break
        fi
        conda deactivate 2>/dev/null || true
    fi
done
if [[ -z "$ACTIVATED" ]]; then
    echo "  WARN: none of [${PY_ENVS[*]}] worked; using system python"
    which python
    python -c "import numpy, scipy, pandas, matplotlib" || {
        echo "ERROR: required packages (numpy/scipy/pandas/matplotlib) not available."
        echo "       Edit PY_ENVS in cluster/run_config.sh or pip install --user."
        exit 4
    }
fi

# Hand off to bash orchestrator. It also sources run_config.sh internally,
# but the env vars from this shell already propagate.
echo
echo "--- handing off to cluster/run_analysis.sh ---"
export MD_PARENT N_JOBS N_BOOTSTRAP
bash cluster/run_analysis.sh "$@"
RC=$?

echo
echo "==========================================================="
echo "  SLURM job ${SLURM_JOB_ID:-?} DONE  $(date -Iseconds)  rc=$RC"
echo "==========================================================="
exit $RC

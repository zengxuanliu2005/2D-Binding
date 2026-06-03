#!/bin/bash
###############################################################################
#  cluster/run_config.sh — single-source config file for the full-data run
#
#  THIS IS THE ONLY FILE YOU EDIT. Both SBATCH wrapper
#  (cluster/slurm/full_analysis.slurm) and bash fallback (cluster/run_analysis.sh)
#  source this file. Change values below, then sbatch or bash — nothing else
#  needs editing.
#
#  USAGE
#  -----
#    1. vim cluster/run_config.sh    (edit MD_PARENT + SYSTEMS_DIRS if naming differs)
#    2. sbatch cluster/slurm/full_analysis.slurm    (PRIMARY — uses SLURM)
#       OR
#       bash cluster/run_analysis.sh                 (FALLBACK — if no SLURM)
#    3. After it finishes (1-2 h wall):
#       tar czf distilled.tgz cluster/outputs/distilled/
#       send distilled.tgz back to Zengxuan
###############################################################################

# ─── MD data location ────────────────────────────────────────────────────────
# Parent directory containing the 3 system folders (15_120x120_K100_EPS05/ etc.)
#
# AUTO-DETECT: if you leave the default below unchanged, run_analysis.sh /
# full_analysis.slurm will probe $BUNDLE_ROOT/../.. (and $BUNDLE_ROOT/..,
# $HOME) for any of the SYSTEMS_DIRS and use the first one that matches.
# This means if your bundle lives at <md_root>/2D-Binding/cluster/ with the
# per-system data dirs at <md_root>/<system>/, you do NOT need to edit this
# field — auto-detect handles it.
#
# Set MD_PARENT explicitly only if your layout differs. Example:
#   MD_PARENT="/scratch/jane/MD"   (data at /scratch/jane/MD/15_120x120_K100_EPS05/...)
MD_PARENT="${MD_PARENT:-/path/to/your/MD/data/root}"

# ─── Required: system directory names ────────────────────────────────────────
# Adjust if your naming convention differs from the defaults below.
# Each entry corresponds to one of the 3 flexibility classes.
SYSTEMS_DIRS=(
    "15_120x120_K100_EPS05"      # rigid (K=100)
    "15_120x120_K10_EPS05"       # semi  (K=10)
    "22_120x120_K01_EPS05"       # flex  (K=0.1)
)

# ─── Performance ─────────────────────────────────────────────────────────────
# Parallel workers for extract + bootstrap loops.
# Recommend 8 on a 16-core node, 16 on a 32-core node.
N_JOBS="${N_JOBS:-8}"

# Bootstrap iterations for ΔΔF + K2D σ. 200 is the project default.
# Pilot mode (--pilot flag) overrides this to 20.
N_BOOTSTRAP="${N_BOOTSTRAP:-200}"

# ─── SLURM (only used by cluster/slurm/full_analysis.slurm) ──────────────────
# Adjust to match your cluster's partition and node availability.
SLURM_PARTITION="${SLURM_PARTITION:-gpu}"          # partition name
SLURM_NODE="${SLURM_NODE:-n01}"                     # specific node (or empty to disable -w)
SLURM_TIME="${SLURM_TIME:-24:00:00}"                # wall time
SLURM_MEM="${SLURM_MEM:-32G}"                       # memory per job
SLURM_CPUS="${SLURM_CPUS:-8}"                       # CPUs per task (≥ N_JOBS)

# ─── Python environment ──────────────────────────────────────────────────────
# Tried in order. First one with numpy/scipy/pandas/matplotlib wins.
# 'phys' is the project-recommended env; 'base' is the system default.
PY_ENVS=("${PY_ENVS[@]:-phys base}")

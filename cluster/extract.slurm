#!/bin/bash
#SBATCH -J 2dbind_extract     # job name
#SBATCH -o %J.log             # stdout/log
#SBATCH -e %J.err             # stderr
#SBATCH -p gpu                # partition (same as PhD's analysis.slurm)
#SBATCH -w n01                # specific node (matches her template; edit if n01 unavailable)
#SBATCH -N 1                  # number of cluster nodes !!!DONOT touch this line
#SBATCH -c 1                  # number of cpu cores

# Wrapper. The actual loop over (system, replica) lives in
# extract_all.sh — see that script for the configurable knobs
# (TRAJ_ROOT, OUT_ROOT, REPO_ROOT).

./extract_all.sh

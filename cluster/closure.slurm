#!/bin/bash
#SBATCH -J 2dbind_closure     # job name
#SBATCH -o %J.log             # stdout/log
#SBATCH -e %J.err             # stderr
#SBATCH -p gpu                # partition
#SBATCH -w n01                # specific node
#SBATCH -N 1                  # number of cluster nodes !!!DONOT touch this line
#SBATCH -c 1                  # number of cpu cores

# Wrapper. The actual combine + closure pipeline lives in closure_all.sh.

./closure_all.sh

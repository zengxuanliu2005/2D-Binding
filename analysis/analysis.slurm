#!/bin/bash
#SBATCH -J 11_100       # job name
#SBATCH -o %J.log      # log file of the job, the job number (%j) and compute node (%N)
#SBATCH -e %J.err      # error file
#SBATCH -p gpu       # partition
#SBATCH -w n01
#SBATCH -N 1           # number of cluster nodes !!!DONOT touch this line
#SBATCH -c 1           # number of cpu cores

./get_vertical_distance_to_membrane_complex.sh
#./get_kinetics.sh

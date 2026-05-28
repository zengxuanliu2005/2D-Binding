#!/bin/bash
runs=(22_120x120_K01_EPS05)
BOXLZ=50
TIMESTEP="0.01"

#directory of the shell script
cwd=$(cd `dirname $0`; pwd)
#father directory
dir=$(dirname "$cwd")

#loop over the runs
for run in ${runs[@]}; do
  N=${run%$"_"*"_"*"_"*}
  ((NPRO= N * 2))
  L=${run%$"x"*}; L=${L#*"_"}
  ((AREA=L * L))
  E=${run#*"EPS"}
  K=${run#*"K"};K=${K%"_EPS"*}
  echo "analyzing data from "$run
  # extract phi
  for s in $dir/$run/s0*; do
   if [ -d "$s" ]; then
    # extract phi
     #rm $s/complex_distance_bind.tsv
     #rm $s/theta_angle_distributed_unbind.tsv
     if [ ! -f "$s/complex_distance_to_membrane_distributed_bind.tsv" ]; then
      FREQ_XYZ=`grep trajectory $s/sys.log | grep -o '[0-9]*'` # get FREQ_XYZ from sys.log
      PRO_XYZ=`grep 'production steps:' $s/sys.log | grep -o '[0-9]*'`
      NLIP=`grep "lipids" $s/sys.log | cut -d " " -f 5`
      ((NLIPS=NLIP * 3))
      ((NFRA=PRO_XYZ / FREQ_XYZ))
      printf "%-6i %-6i %-6i %-6i\n" $L $NFRA $NLIPS $NPRO >> __k2d.txt
      python $cwd/vertical_distance_to_membrane_complex.py $L $NPRO $NFRA $NLIPS $s/traj.xyz $s/num_bonds_for_xyz_frames.dat $s/complex_distance_to_membrane_distributed_bind.tsv
    fi
    touch -r $s/traj.xyz $s
   fi
  done
done

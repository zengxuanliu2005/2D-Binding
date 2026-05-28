#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@File    ：vertical_distance_to_membrane.py
@IDE     ：PyCharm
@Author  ：hourh
@Date    ：2023/11/11 09:39
'''
import sys
import numpy as np

# Parse input arguments
Lx = int(sys.argv[1])
Ly = Lx
Lz = 50
num_protein = int(sys.argv[2])
frame_count = int(sys.argv[3])
N_lipids = int(sys.argv[4])
fin1 = sys.argv[5]  # traj.xyz
fin2 = sys.argv[6]  # num_bonds_for_xyz_frames.tsv
fout_complex_heights = sys.argv[7]  # Complex heights output

# Initialize arrays to hold distances (z coordinates of S for R and L)
dis = np.zeros((frame_count, num_protein))

def apply_min_img(r):
    return min(r, abs(r - Lz))

S_xyz = []
with open(fin1, 'r') as f:
    mlines = 0
    nframes = 0
    for line in f:
        word = line.split()
        mlines += 1
        if mlines == 1:
            nlines_frame = int(word[0]) + 2
        if line.startswith("S "):
            S_xyz.append(float(word[3]))
        if mlines == nlines_frame:
            for i in range(num_protein):  # Assuming H_xyz and S_xyz have paired coordinates
                sxyz = np.array(S_xyz)
                z_coord = sxyz[i * 2 + 1]
                dis[nframes][i] = z_coord  # Or another array if needed
            mlines = 0
            nframes += 1
            S_xyz = []
#print(dis)  # For debugging: Print the z-coordinates for the first frame

# Read bond information
RLn_index = [[] for _ in range(frame_count)]
with open(fin2, 'r') as f:
    num_lines = 0
    for line in f:
        word = line.split()
        curr_bonds = int(word[0])
        for idx in range(curr_bonds):
            R = int((int(word[idx * 6 + 5]) - N_lipids) / 13)  # Even index for R
            L = int((int(word[idx * 6 + 6]) - N_lipids) / 13)  # Odd index for L
            RLn_index[num_lines].append([R, L])  # Store R-L pair
        num_lines += 1
        #print(RLn_index)  # For debugging: Print bond pairs for each frame

# Initialize storage for complex heights
complex_heights = []

# Calculate complex heights for each frame
for i in range(len(RLn_index)):  # Loop over frames
    for j in range(len(RLn_index[i])):  # Loop over each pair in the frame
        R_idx = RLn_index[i][j][0]  # Get R index (even)
        L_idx = RLn_index[i][j][1]  # Get L index (odd)
        # Calculate the difference in z-coordinates (R - L)
        complex_height = np.abs(dis[i, R_idx] - dis[i, L_idx])
        complex_height1 = apply_min_img(complex_height)
        complex_heights.append(complex_height1)
        #print(f"Frame {i}, R_idx {R_idx}, L_idx {L_idx}, Height {complex_height:.4f}")

# Output complex heights
with open(fout_complex_heights, 'w') as f:
    for height in complex_heights:
        f.write(f"{height:.4f}\n")

#!/bin/bash
###############################################################################
#  cluster/slurm/single_pilot.slurm — pilot constrained-h MD
#
#  PURPOSE
#  -------
#  A single sbatch job that runs ONE constrained-h MD (K10, h=14, 50 frames)
#  on cluster-A. Used to validate:
#
#    (a) the SBATCH template works (partition / node / activate / cd)
#    (b) cluster/scripts/nvt-md-constrained-h.py runs end-to-end and
#        produces pilot_summary.json with bond_count_total=0 and
#        ⟨z_membrane⟩ ≈ h_target
#    (c) cluster/scripts/analyze_slab_traj.py --pilot can read the output
#
#  Only run AFTER cluster/trial/03_pygamd_probe.sh passed and Claude has
#  wired the cu_gala import / harmonic class into nvt-md-constrained-h.py.
#
#  Expected wall time: ~5-10 min on GPU (50 frames × 10k MD steps = 500k steps).
#
#  Submit:
#      sbatch cluster/slurm/single_pilot.slurm
###############################################################################

#SBATCH -J slab_pilot
#SBATCH -o cluster/outputs/logs/pilot_%J.log
#SBATCH -e cluster/outputs/logs/pilot_%J.err
#SBATCH -p gpu
#SBATCH -w n01
#SBATCH -N 1
#SBATCH -c 1

set -e
echo "==========================================================="
echo "  PILOT constrained-h MD"
echo "  Goal: validate template + cu_gala wiring + summary writer"
echo "  job ${SLURM_JOB_ID:-?}  start $(date -Iseconds)"
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
mkdir -p cluster/outputs/logs cluster/outputs/slab_pilot

echo
echo "▶  running nvt-md-constrained-h.py --pilot ..."
python cluster/scripts/nvt-md-constrained-h.py \
    --pilot \
    --system K10 \
    --h 14.0 \
    --n-frames 50 \
    --seed 20260601 \
    --out-dir cluster/outputs/slab_pilot/K10_h14

echo
echo "▶  running sanity assertions on pilot_summary.json ..."
python - <<'PY'
import json, pathlib, sys
out = pathlib.Path("cluster/outputs/slab_pilot/K10_h14/pilot_summary.json")
if not out.exists():
    print(f"   ✗  {out} missing", file=sys.stderr); sys.exit(1)
d = json.loads(out.read_text())
print(json.dumps(d, indent=2))
assert d["bond_count_total"] == 0, f"   ✗  bond count not zero ({d['bond_count_total']})"
assert abs(d["mean_z_membrane"] - 14.0) < 0.5, \
    f"   ✗  ⟨z⟩={d['mean_z_membrane']} not near h=14"
assert d["n_frames_written"] >= 40, "   ✗  too few frames written"
print(f"   ✓  PILOT OK: bond_count=0, ⟨z⟩={d['mean_z_membrane']:.3f} σ, "
      f"n_frames={d['n_frames_written']}")
PY
echo
echo "==========================================================="
echo "  PILOT done  $(date -Iseconds)"
echo "  Next: bash cluster/analysis/run_slab_full.sh"
echo "==========================================================="

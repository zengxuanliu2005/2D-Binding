#!/bin/bash
###############################################################################
#  cluster/analysis/run_slab_full.sh — Workstream C slab MD pipeline
#
#  Purpose (also printed when run)
#  --------------------------------
#  Only run this if §0 (run_section0_full.sh) did NOT close the K2D gaps —
#  i.e. the "data volume" explanation failed and we need real slab MD.
#
#    1. Pilot one constrained-h MD (K10, h=14, 50 frames)
#    2. Verify ⟨z_membrane⟩ ≈ h and bond_count = 0
#    3. Launch the 18-task production array (3 systems × 6 h values)
#    4. Wait for all to finish, then analyze → K2D(l) grid
#
#  Prerequisites: cluster/trial/03_pygamd_probe.sh PASSED, and
#  cluster/scripts/nvt-md-constrained-h.py has its cu_gala TODOs filled in
#  by Claude using the probe output.
#
###############################################################################
set -e

hr() { printf '\n%s\n' "──────────────────────────────────────────────────────────────────────"; }
section() { hr; printf '▶  %s\n' "$1"; hr; }

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  Workstream C — constrained-h slab MD pipeline                    ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Only run if §0 didn't close the K2D gaps. Runs:
  1. pilot constrained-h MD (1 system, 1 h)
  2. validate z-tether holds and binding stays off
  3. production array (3 × 6 = 18 jobs)
  4. analyze → K2D(l) grid → cluster/results/slab/K2D_l_grid.npz

Total wall time : depends on cluster GPU queue (potentially many hours).
BAN

section 'Step 1/4 — pilot MD (K10, h=14, ~50 frames)'
PILOT_JOB=$(sbatch --parsable cluster/slurm/single_pilot.slurm)
echo "   pilot job id: $PILOT_JOB"
while squeue -h -j "$PILOT_JOB" 2>/dev/null | grep -q .; do
    sleep 30
done
echo "   pilot finished, validating ..."

python - <<'PY'
import json, sys
from pathlib import Path
p = Path("cluster/outputs/slab_pilot/K10_h14/pilot_summary.json")
if not p.exists():
    print(f"   ✗  {p} missing — pilot did not produce summary")
    sys.exit(1)
d = json.loads(p.read_text())
print(json.dumps(d, indent=2))
if d.get("bond_count_total", 1) != 0:
    print("   ✗  R-L binding NOT disabled — check nvt-md-constrained-h.py")
    sys.exit(2)
if abs(d.get("mean_z_membrane", -1) - d["h_target"]) > 0.5:
    print("   ✗  z-tether NOT effective — ⟨z⟩ drifted from target")
    sys.exit(3)
print("   ✓  pilot sanity PASSED")
PY

python cluster/scripts/analyze_slab_traj.py --pilot

section 'Step 2/4 — production array (18 jobs)'
ARRAY_JOB=$(sbatch --parsable cluster/slurm/array_slab_md.slurm)
echo "   array job id: $ARRAY_JOB"
echo "   waiting (may take many GPU-hours) ..."
while squeue -h -j "$ARRAY_JOB" 2>/dev/null | grep -q .; do
    sleep 300
done

section 'Step 3/4 — analyze K2D(l) grid'
python cluster/scripts/analyze_slab_traj.py --n-jobs 8

section 'Step 4/4 — done'
cat <<'EOF'
   ✓✓✓  Slab MD pipeline complete.

   Sync result back:
     rsync -av master:/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/results/slab/ \
         results/slab/

   Then locally update stage_essay.md §4.5 + §5.4 using the slab K2D(l)
   measurements (see plan §C.4 acceptance criteria).
EOF

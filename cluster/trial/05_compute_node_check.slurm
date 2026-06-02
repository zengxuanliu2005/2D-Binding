#!/bin/bash
###############################################################################
#  cluster/trial/slurm/compute_node_check.slurm
#  Validates the COMPUTE node's environment (different from login node!)
###############################################################################
#
#  WHY THIS IS NECESSARY
#  ---------------------
#  Login-node `bash cluster/trial/01..04.sh` already passed (or was close to
#  passing) for the login-node env. But the actual production workloads
#  (`array_extract.slurm`, `array_slab_md.slurm`) run on COMPUTE nodes, which
#  on this cluster can differ from the login node in:
#
#    - whether `/opt/miniconda3` or `~/miniconda3` is reachable
#    - whether NFS-mounted user $HOME and /mnt/nfs/ugstu/liuzx are mounted
#    - whether the conda base env (which provides numpy/scipy/...) is the
#      same on compute as it is on login (it should be if /opt/miniconda3
#      is shared, but worth confirming)
#    - whether `cu_gala` / `poetry` is installed in the compute env (this is
#      where it actually matters for Workstream C — login node MD jobs would
#      never run there anyway)
#
#  This SBATCH script re-runs the same checks as trial 01 + 03 + 04 but on a
#  compute node, so we can compare login vs compute and patch anything that
#  diverges.
#
#  HOW TO SUBMIT
#  -------------
#      cd /mnt/nfs/ugstu/liuzx/2D-Binding-main
#      mkdir -p cluster/trial/outputs/$(date -I)_round2/compute
#      # SBATCH -o needs to be set at submit time because cwd-relative path:
#      sbatch -o cluster/trial/outputs/$(date -I)_round2/compute/%J.out \
#             -e cluster/trial/outputs/$(date -I)_round2/compute/%J.err \
#             cluster/trial/slurm/compute_node_check.slurm
#
#      # wait for it to finish, then move the latest output file into
#      # the round dir (or just keep where it is — naming with %J is fine)
#
###############################################################################

#SBATCH -J trial_compute_check
#SBATCH -p gpu
#SBATCH -N 1
#SBATCH -c 1
#SBATCH -o trial_compute_check.%J.out
#SBATCH -e trial_compute_check.%J.err

set -u

hr() { printf '\n%s\n' "──────────────────────────────────────────────────────────────────────"; }
section() { hr; printf '▶  %s\n' "$1"; hr; }
ok()    { printf '   ✓  %s\n' "$*"; }
warn()  { printf '   ⚠  %s\n' "$*"; }
fail()  { printf '   ✗  %s\n' "$*"; FAILED=1; }
FAILED=0

cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  TRIAL Round 2 — compute-node environment validation              ║
║  Runs on a SLURM-allocated compute node, NOT the login node       ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Same checks as login-node trial 01 + 03 + 04, but on a compute node.
Compute nodes can differ from login in conda paths, NFS visibility,
and what's installed in `phys` / `base`. If any of these diverge we
need to know BEFORE running the production extract array.

What this script does (5 steps, ~2-3 min total wall time):
  1. Report hostname + node identity (so we know which node we hit)
  2. NFS visibility check (/mnt/nfs/ugstu/liuzx + $HOME)
  3. Source conda + verify analysis stack imports in active env
  4. Try every pygamd/cu_gala/poetry import path
  5. Run `extract_one_replica.py --pilot` on K100 s001
       — sanity check that the bundle pipeline works on this node

BAN

# ── step 1: identity ─────────────────────────────────────────────────────────
section 'Step 1/5 — compute node identity'
echo "   SLURM_JOB_ID    : ${SLURM_JOB_ID:-?}"
echo "   SLURM_NODELIST  : ${SLURM_NODELIST:-?}"
echo "   hostname        : $(hostname)"
echo "   whoami          : $(whoami)"
echo "   pwd             : $(pwd)"
echo "   SLURM_SUBMIT_DIR: ${SLURM_SUBMIT_DIR:-?}"
echo "   date            : $(date -Iseconds)"
cd "${SLURM_SUBMIT_DIR:-$(pwd)}" || true

# ── step 2: NFS mounts ───────────────────────────────────────────────────────
section 'Step 2/5 — NFS visibility'
if [[ -d /mnt/nfs/ugstu/liuzx ]]; then
    ok "/mnt/nfs/ugstu/liuzx is mounted on $(hostname)"
    echo "   disk free:"
    df -h /mnt/nfs/ugstu/liuzx 2>&1 | sed 's/^/     /'
else
    fail "/mnt/nfs/ugstu/liuzx NOT mounted on this compute node!"
fi
if [[ -d "$HOME" ]]; then
    ok "\$HOME = $HOME exists"
    if [[ -f "$HOME/.condarc" ]]; then
        echo "   ~/.condarc contents:"
        cat "$HOME/.condarc" | sed 's/^/     /'
    fi
else
    warn "\$HOME = $HOME does not exist? Conda envs under ~/.conda/envs/ won't be visible."
fi

# ── step 3: conda + analysis stack ──────────────────────────────────────────
section 'Step 3/5 — conda + analysis stack on compute node'
CONDA_SH=""
for prefix in /opt/miniconda3 ~/miniconda3 /opt/anaconda3 ~/anaconda3; do
    if [[ -f "$prefix/etc/profile.d/conda.sh" ]]; then
        CONDA_SH="$prefix/etc/profile.d/conda.sh"
        ok "conda.sh at: $CONDA_SH"
        break
    fi
done
if [[ -z "$CONDA_SH" ]]; then
    fail "could not find conda.sh on this compute node — production jobs will fail"
else
    # shellcheck disable=SC1090
    source "$CONDA_SH"
    echo
    echo "   conda env list (as seen from compute node):"
    conda env list 2>&1 | sed 's/^/     /'
    echo
    ok "using compute-node python = $(which python)"
    python --version 2>&1
    echo
    echo "   importing analysis stack ..."
    python - <<'PY' 2>&1 | sed 's/^/     /'
import importlib, sys
all_ok = True
for mod in ("numpy", "scipy", "pandas", "matplotlib", "sklearn"):
    try:
        m = importlib.import_module(mod)
        print(f"  OK  {mod:<12} {getattr(m, '__version__', '?')}")
    except ImportError as e:
        print(f"  FAIL  {mod}: {e}")
        all_ok = False
sys.exit(0 if all_ok else 1)
PY
    if [[ $? -eq 0 ]]; then
        ok "analysis stack imports on compute node"
    else
        fail "analysis packages missing on compute node — install with: pip install numpy scipy pandas matplotlib scikit-learn"
    fi
fi

# ── step 4: pygamd probe on compute node ────────────────────────────────────
section 'Step 4/5 — pygamd / cu_gala on compute node'
echo "   trying common imports (relevant for Workstream C only) ..."
for spec in \
    "import pygamd" \
    "from poetry import cu_gala" \
    "from poetry import gala" \
    "import gala" \
    "from gala import cu_gala" \
    "import cu_gala"; do
    out=$(python -c "$spec; print('OK')" 2>&1 | tr '\n' ' ' | head -c 200)
    if echo "$out" | grep -q '^OK'; then
        ok "[$spec]  →  $out"
    fi
done
python - <<'PY' 2>&1 | sed 's/^/     /'
import importlib
found = False
for spec in ("pygamd", "poetry.cu_gala", "poetry.gala", "gala", "cu_gala"):
    try:
        m = importlib.import_module(spec)
        print(f"  ✓ {spec} importable on compute node — version {getattr(m, '__version__', '?')}")
        print(f"    location: {getattr(m, '__file__', '?')}")
        found = True
    except ImportError:
        pass
if not found:
    print("  ✗ no pygamd-like module on compute node either (consistent with login)")
PY

# ── step 5: extract pilot on compute node ───────────────────────────────────
section 'Step 5/5 — extract pilot on K100 s001 (compute node)'
K100_DIR=$(find /mnt/nfs/ugstu/liuzx -maxdepth 4 -type d \
              \( -name '*K100*' -o -name '*K_100*' \) 2>/dev/null | head -1)
if [[ -z "$K100_DIR" ]]; then
    fail "cannot find K100 dir from compute node — NFS/path differs"
else
    MD_BASE=$(dirname "$K100_DIR")
    K100_NAME=$(basename "$K100_DIR")
    ok "K100 dir : $K100_DIR"
    ok "MD_BASE  : $MD_BASE"

    OUT_DIR=cluster/outputs/extracted/trial_round2_compute_${SLURM_JOB_ID:-pilot}
    mkdir -p "$OUT_DIR"
    echo
    echo "▶  running extract_one_replica.py --pilot on K100 s001 ..."
    python -u cluster/scripts/extract_one_replica.py \
        --system "$K100_NAME" --replica s001 \
        --md-base "$MD_BASE" \
        --out "$OUT_DIR/K100_s001.npz" \
        --pilot --quiet
    RC=$?
    if [[ "$RC" -eq 0 ]]; then
        ok "extract succeeded on compute node"
        python - "$OUT_DIR/K100_s001.npz" <<'PY' 2>&1 | sed 's/^/     /'
import sys
from pathlib import Path
import numpy as np
p = Path(sys.argv[1])
d = np.load(p)
print(f"  file: {p} ({p.stat().st_size/1e6:.2f} MB)")
print(f"  n_frames = {int(d['n_frames'])}")
print(f"  n_R/n_L  = {int(d['n_R'])}/{int(d['n_L'])}")
print(f"  bound R / frame = {d['bound_R'].sum(axis=1).mean():.2f}")
PY
    else
        fail "extract failed on compute node (RC=$RC)"
    fi
fi

# ── summary ──────────────────────────────────────────────────────────────────
section 'Summary'
if [[ "$FAILED" -eq 0 ]]; then
    cat <<EOF
   ✓✓✓  COMPUTE-NODE CHECKS PASSED on $(hostname).

   Means:
     • /mnt/nfs/ugstu/liuzx visible from compute node
     • phys env (or equivalent) reachable + analysis stack importable
     • extract_one_replica.py runs end-to-end here

   → Production array jobs (cluster/slurm/array_extract.slurm) will work.

   Next steps:
     • If trial 01 (login-node Round 2) also passed → ship to senior
     • And/or run bash cluster/run_analysis.sh on user's own 7 replicas
EOF
else
    cat <<'EOF'
   ✗   At least one compute-node check failed (see above).

   Common divergences when login ≠ compute:
     • phys at ~/.conda/envs/phys but $HOME not NFS-mounted on compute node
       → install env at /opt/miniconda3/envs/phys instead (system-wide)
     • /mnt/nfs/ugstu/liuzx mounted on login but not compute node
       → tell admin to mount it everywhere
     • cu_gala installed in some other env not yet discovered
       → ask senior for the exact env / module she uses to run MD

   Send this log + the login-node Round 2 log to Claude — patch will follow.
EOF
    exit 1
fi

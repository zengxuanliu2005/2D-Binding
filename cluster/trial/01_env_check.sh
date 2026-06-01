#!/bin/bash
###############################################################################
#  TRIAL 01 — environment sanity check on cluster-A
###############################################################################
#
#  Purpose
#  -------
#  Before we ship the §0 data-volume test (bundle_for_senior) or submit any
#  constrained-h MD jobs, we need to know:
#
#    (a) Which conda installation lives on cluster-A (miniconda vs anaconda)
#        and where its profile.d/conda.sh is — this fixes the activation line
#        in every SLURM template.
#    (b) Whether the `phys` env already exists with the analysis stack
#        (numpy/scipy/pandas/matplotlib/scikit-learn). If yes, we use it; if
#        no, we install it (via cluster/env_setup/install_phys.sh).
#    (c) What SLURM looks like — sbatch version, visible partitions, and your
#        current queue — so we know -p gpu actually exists and there isn't a
#        long backlog blocking us.
#
#  Expected wall time : < 30 seconds.
#  Failure tolerance  : everything below MUST pass. If anything errors, fix
#                       that first before proceeding to 02/03/04 — those
#                       scripts assume a working phys env.
#
#  What to look for in the output
#  ------------------------------
#  ✓ A line "OK  phys env activated, python=…" near the bottom
#  ✓ All 5 analysis pkgs show "OK <version>"
#  ✓ sbatch responds and `gpu` partition is in `sinfo` output
#
#  What to send back
#  -----------------
#  The entire stdout/stderr of this script — paste into REPORT_BACK.md §01.
#
###############################################################################
set -u

# ── helpers ───────────────────────────────────────────────────────────────────
hr() { printf '\n%s\n' "──────────────────────────────────────────────────────────────────────"; }
section() { hr; printf '▶  %s\n' "$1"; hr; }
ok()    { printf '   ✓  %s\n' "$*"; }
warn()  { printf '   ⚠  %s\n' "$*"; }
fail()  { printf '   ✗  %s\n' "$*"; FAILED=1; }
FAILED=0

# ── banner ────────────────────────────────────────────────────────────────────
cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  TRIAL 01 / 04  —  environment sanity check                       ║
║  Goal: confirm conda + phys env + SLURM are usable on cluster-A.   ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Before we ship the §0 data-volume bundle to senior or submit any
constrained-h MD jobs, we need to know:

  (a) Which conda installation lives on cluster-A (miniconda vs anaconda)
      and where its profile.d/conda.sh is — this fixes the `source ...`
      line in every SLURM template.
  (b) Whether the `phys` env already exists with the analysis stack
      (numpy/scipy/pandas/matplotlib/scikit-learn). If yes, we use it;
      if no, we install it (via cluster/env_setup/install_phys.sh).
  (c) What SLURM looks like — sbatch version, visible partitions, and
      your current queue — so we know -p gpu actually exists and there
      isn't a long backlog blocking us.

Expected wall time : < 30 seconds.
Everything below MUST pass before scripts 02/03/04 will work.
What to send back  : the entire stdout of this script.
BAN
printf 'Host : %s\n' "$(hostname)"
printf 'User : %s\n' "$(whoami)"
printf 'Date : %s\n' "$(date -Iseconds)"
printf 'PWD  : %s\n' "$(pwd)"

# ── step 1: shell + bare python ───────────────────────────────────────────────
section 'Step 1/5 — basic shell & python on PATH'
echo "   bash : $(bash --version | head -1)"
PY_PATH="$(which python 2>/dev/null || echo NONE)"
echo "   python on PATH : $PY_PATH"
if [[ "$PY_PATH" != "NONE" ]]; then
    echo "   python --version : $(python --version 2>&1)"
fi

# ── step 2: locate conda ──────────────────────────────────────────────────────
section 'Step 2/5 — locate conda installation'
CONDA_BIN="$(which conda 2>/dev/null || echo NONE)"
if [[ "$CONDA_BIN" == "NONE" ]]; then
    fail "conda not on PATH. Will search common install prefixes anyway."
else
    ok "conda found at: $CONDA_BIN"
    echo "   conda --version : $(conda --version 2>&1)"
fi

CONDA_SH=""
for prefix in ~/miniconda3 ~/anaconda3 /opt/miniconda3 /opt/anaconda3 /usr/local/miniconda3; do
    if [[ -f "$prefix/etc/profile.d/conda.sh" ]]; then
        CONDA_SH="$prefix/etc/profile.d/conda.sh"
        ok "found profile.d at: $CONDA_SH"
        echo "   → SLURM templates should use: source $CONDA_SH"
        break
    fi
done
if [[ -z "$CONDA_SH" ]]; then
    fail "could not find conda.sh under ~/miniconda3, ~/anaconda3, /opt/*."
    warn "tell Claude the actual path so cluster/slurm/*.slurm can be fixed."
fi

# ── step 3: list envs ─────────────────────────────────────────────────────────
section 'Step 3/5 — list conda envs'
conda env list 2>&1
if conda env list 2>/dev/null | grep -q '^phys '; then
    ok "phys env exists"
else
    warn "phys env NOT FOUND. After this script, run:"
    warn "   bash cluster/env_setup/install_phys.sh"
    warn "  (or have senior install it for you)"
fi

# ── step 4: activate phys + import analysis stack ─────────────────────────────
section 'Step 4/5 — activate phys & verify analysis packages'
if [[ -n "$CONDA_SH" ]]; then
    # shellcheck disable=SC1090
    source "$CONDA_SH"
fi
if conda activate phys 2>/dev/null; then
    ok "phys activated, python = $(which python)"
    echo "   python --version : $(python --version 2>&1)"
    echo
    echo "   importing analysis stack ..."
    python - <<'PY' 2>&1
import importlib, sys
mods = ("numpy", "scipy", "pandas", "matplotlib", "sklearn")
all_ok = True
for mod in mods:
    try:
        m = importlib.import_module(mod)
        print(f"     OK  {mod:<12} {getattr(m, '__version__', '?')}")
    except ImportError as e:
        print(f"     FAIL  {mod}: {e}")
        all_ok = False
sys.exit(0 if all_ok else 1)
PY
    if [[ $? -eq 0 ]]; then
        ok "all 5 analysis packages OK"
    else
        fail "some analysis packages missing — install before §0 bundle works"
    fi
else
    fail "could not activate phys env — fix this before anything else"
fi

# ── step 5: SLURM ─────────────────────────────────────────────────────────────
section 'Step 5/5 — SLURM scheduler check'
if command -v sbatch >/dev/null 2>&1; then
    ok "sbatch on PATH at: $(which sbatch)"
    echo "   sbatch --version : $(sbatch --version 2>&1 | head -1)"
    echo
    echo "   visible partitions (looking for 'gpu'):"
    sinfo -h -o "     %P   nodes=%D   state=%t" 2>&1 | head -10
    if sinfo -h -o "%P" 2>/dev/null | grep -qx 'gpu'; then
        ok "'gpu' partition exists — matches senior's analysis/analysis.slurm"
    else
        warn "no 'gpu' partition? cluster/slurm/_base.slurm needs adjusting"
    fi
    echo
    echo "   your current queue:"
    squeue -u "$USER" 2>&1 | head -5 || true
else
    fail "sbatch not on PATH — can't submit any cluster jobs"
fi

# ── summary ───────────────────────────────────────────────────────────────────
section 'Summary'
if [[ "$FAILED" -eq 0 ]]; then
    cat <<'EOF'
   ✓✓✓  ALL CHECKS PASSED.  Proceed to 02_paths_check.sh.

   Tell Claude:
     • the CONDA_SH path printed in Step 2 (the source line for SLURM)
     • whether phys exists, and what's in conda env list
     • whether sbatch responds and `gpu` is a partition
EOF
else
    cat <<'EOF'
   ✗✗✗  AT LEAST ONE CHECK FAILED — fix before continuing.

   Common fixes:
     • phys missing → bash cluster/env_setup/install_phys.sh
     • conda.sh not in a standard prefix → tell Claude the actual path
     • sbatch missing → ssh to a compute node? or wrong cluster?

   Send the full output to Claude regardless.
EOF
    exit 1
fi

#!/bin/bash
###############################################################################
#  TRIAL 01 — environment sanity check on cluster-A
###############################################################################
#
#  Purpose
#  -------
#  Before we ship the §0 data-volume bundle to senior or submit any
#  constrained-h MD jobs on cluster-A, we need to know:
#
#    (a) Which conda installation lives on cluster-A and where its
#        profile.d/conda.sh is — for sourcing from SLURM templates.
#    (b) Whether the analysis stack (numpy/scipy/pandas/matplotlib/
#        scikit-learn) is importable from the python on PATH. We do
#        NOT require a `phys` env on the server — `phys` is Zengxuan's
#        local laptop env; on the server we use whatever python is
#        active (usually base).
#    (c) What SLURM looks like — sbatch version, visible partitions,
#        current queue — so we know -p gpu actually exists.
#
#  Expected wall time : < 30 seconds.
#  Failure tolerance  : if (a)+(c) pass and (b) only misses numpy/scipy,
#                       run `pip install numpy scipy pandas matplotlib
#                       scikit-learn` and rerun.
#
#  What to look for in the output
#  ------------------------------
#  ✓ "using cluster python = /opt/miniconda3/bin/python"
#  ✓ All 5 analysis pkgs show "OK <version>"
#  ✓ sbatch responds and `gpu*` or `gpu` partition is in `sinfo` output
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
║  Goal: confirm conda + analysis stack + SLURM are usable.         ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Before we ship the §0 data-volume bundle to senior or submit any
constrained-h MD jobs, we need to know:

  (a) Which conda installation lives on cluster-A (so SLURM templates
      can source its profile.d/conda.sh).
  (b) Whether numpy/scipy/pandas/matplotlib/scikit-learn import in the
      python that's on PATH. NOTE: we do NOT require a `phys` conda env
      on the server — that's Zengxuan's local dev env. On the server
      we use whatever python is active (usually `base`).
  (c) What SLURM looks like — sbatch + partitions + queue — so we know
      `-p gpu` works.

Expected wall time : < 30 seconds.
What to send back  : the entire stdout of this script.
BAN
printf 'Host : %s\n' "$(hostname)"
printf 'User : %s\n' "$(whoami)"
printf 'Date : %s\n' "$(date -Iseconds)"
printf 'PWD  : %s\n' "$(pwd)"

# ── step 1: shell + bare python ───────────────────────────────────────────────
section 'Step 1/4 — basic shell & python on PATH'
echo "   bash : $(bash --version | head -1)"
PY_PATH="$(which python 2>/dev/null || echo NONE)"
echo "   python on PATH : $PY_PATH"
if [[ "$PY_PATH" != "NONE" ]]; then
    echo "   python --version : $(python --version 2>&1)"
fi

# ── step 2: locate conda ──────────────────────────────────────────────────────
section 'Step 2/4 — locate conda installation'
CONDA_BIN="$(which conda 2>/dev/null || echo NONE)"
if [[ "$CONDA_BIN" == "NONE" ]]; then
    fail "conda not on PATH. Will search common install prefixes anyway."
else
    ok "conda found at: $CONDA_BIN"
    echo "   conda --version : $(conda --version 2>&1)"
fi

CONDA_SH=""
for prefix in /opt/miniconda3 ~/miniconda3 /opt/anaconda3 ~/anaconda3 /usr/local/miniconda3; do
    if [[ -f "$prefix/etc/profile.d/conda.sh" ]]; then
        CONDA_SH="$prefix/etc/profile.d/conda.sh"
        ok "found profile.d at: $CONDA_SH"
        echo "   → SLURM templates should use: source $CONDA_SH"
        break
    fi
done
if [[ -z "$CONDA_SH" ]]; then
    fail "could not find conda.sh under /opt/miniconda3, ~/miniconda3, /opt/anaconda3 ..."
    warn "tell Claude the actual path so cluster/slurm/*.slurm can be fixed."
fi

# ── step 3: verify analysis stack imports ────────────────────────────────────
section 'Step 3/4 — verify analysis packages on PATH python'
if [[ -n "$CONDA_SH" ]]; then
    # shellcheck disable=SC1090
    source "$CONDA_SH"
fi
ok "using cluster python = $(which python)"
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
    ok "all 5 analysis packages OK in the active env"
else
    fail "some analysis packages missing — install with: pip install numpy scipy pandas matplotlib scikit-learn"
fi

# ── step 4: SLURM ─────────────────────────────────────────────────────────────
section 'Step 4/4 — SLURM scheduler check'
if command -v sbatch >/dev/null 2>&1; then
    ok "sbatch on PATH at: $(which sbatch)"
    echo "   sbatch --version : $(sbatch --version 2>&1 | head -1)"
    echo
    echo "   visible partitions (looking for 'gpu'):"
    sinfo -h -o "     %P   nodes=%D   state=%t" 2>&1 | head -10
    # 'gpu*' has a trailing star (marks the default partition); accept either.
    if sinfo -h -o "%P" 2>/dev/null | grep -qE '^gpu\*?$'; then
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
     • whether analysis packages all imported in Step 3
     • whether sbatch responds and `gpu` is a partition
EOF
else
    cat <<'EOF'
   ✗✗✗  AT LEAST ONE CHECK FAILED — fix before continuing.

   Common fixes:
     • analysis package missing → pip install numpy scipy pandas matplotlib scikit-learn
     • conda.sh not in /opt/miniconda3 or ~/miniconda3 → tell Claude actual path
     • sbatch missing → ssh to a compute node? or wrong cluster?

   Send the full output to Claude regardless.
EOF
    exit 1
fi

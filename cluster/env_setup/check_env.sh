#!/bin/bash
###############################################################################
#  cluster/env_setup/check_env.sh — environment readiness probe (server-side)
#
#  Wraps the checks needed before §0 bundle or Workstream C MD can run on
#  cluster-A. Reused by run_section0_full.sh / run_slab_full.sh as a gate.
#
#  NOTE: we do NOT try to activate `phys` here. `phys` is Zengxuan's local
#  laptop env name; on cluster-A we use whatever python is on PATH (the
#  system `base` env from /opt/miniconda3). All we need is that the analysis
#  stack imports.
#
###############################################################################
set -u

hr() { printf '\n%s\n' "──────────────────────────────────────────────────────────────────────"; }
section() { hr; printf '▶  %s\n' "$1"; hr; }
ok()    { printf '   ✓  %s\n' "$*"; }
warn()  { printf '   ⚠  %s\n' "$*"; }
fail()  { printf '   ✗  %s\n' "$*"; FAILED=1; }
FAILED=0

cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  cluster/env_setup/check_env.sh — environment readiness probe     ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Confirms cluster-A has what we need to run §0 bundle + Workstream C MD:
  (a) conda installation reachable (just for sourcing profile.d)
  (b) numpy / scipy / pandas / matplotlib / scikit-learn importable
      in whatever python is on PATH
  (c) pygamd / cu_gala importable (only Workstream C needs it; optional)
  (d) sbatch on PATH + free disk on /mnt/nfs/ugstu/liuzx

We deliberately do NOT activate a `phys` env — that's Zengxuan's local
env, not relevant on the server.

BAN

# ── step 1: conda + sourceability ───────────────────────────────────────────
section 'Step 1/4 — conda installation'
if ! command -v conda >/dev/null 2>&1; then
    fail "conda not on PATH. Trying common prefixes anyway."
fi
ok "conda found at $(which conda 2>/dev/null) ($(conda --version 2>&1))"

CONDA_SH=""
for prefix in /opt/miniconda3 ~/miniconda3 /opt/anaconda3 ~/anaconda3; do
    if [[ -f "$prefix/etc/profile.d/conda.sh" ]]; then
        CONDA_SH="$prefix/etc/profile.d/conda.sh"
        # shellcheck disable=SC1090
        source "$CONDA_SH"
        ok "sourced $CONDA_SH"
        break
    fi
done
[[ -z "$CONDA_SH" ]] && warn "no conda.sh found; will continue with current python on PATH"

# ── step 2: python + analysis stack ─────────────────────────────────────────
section 'Step 2/4 — python + analysis packages'
echo "   using python = $(which python) ($(python --version 2>&1))"
python - <<'PY' 2>&1
import importlib, sys
ok = True
for mod in ("numpy", "scipy", "pandas", "matplotlib", "sklearn"):
    try:
        m = importlib.import_module(mod)
        print(f"   ✓  {mod:<12} {getattr(m, '__version__', '?')}")
    except ImportError as e:
        print(f"   ✗  {mod}: {e}")
        ok = False
sys.exit(0 if ok else 3)
PY
if [[ $? -ne 0 ]]; then
    fail "analysis stack incomplete. Install with: pip install numpy scipy pandas matplotlib scikit-learn"
fi

# pygamd / cu_gala is optional — only Workstream C needs it
echo
python - <<'PY' 2>&1
try:
    import pygamd
    print(f"   ✓  pygamd       {getattr(pygamd, '__version__', '?')}  (constrained-h MD enabled)")
except ImportError:
    try:
        from poetry import cu_gala
        print("   ✓  cu_gala via poetry  (constrained-h MD enabled)")
    except ImportError:
        print("   ⚠  pygamd / cu_gala MISSING  — §0 still works, Workstream C blocked")
PY

# ── step 3: SLURM ───────────────────────────────────────────────────────────
section 'Step 3/4 — SLURM scheduler'
if command -v sbatch >/dev/null 2>&1; then
    ok "sbatch at $(which sbatch) ($(sbatch --version 2>&1 | head -1))"
    echo "   partitions visible:"
    sinfo -h -o "     %P  nodes=%D  state=%t" 2>&1 | head -5
else
    fail "sbatch not on PATH"
fi

# ── step 4: NFS workspace ───────────────────────────────────────────────────
section 'Step 4/4 — NFS workspace'
if [[ -d /mnt/nfs/ugstu/liuzx ]]; then
    ok "/mnt/nfs/ugstu/liuzx mounted"
    df -h /mnt/nfs/ugstu/liuzx | sed 's/^/     /'
else
    warn "/mnt/nfs/ugstu/liuzx not mounted on this node"
fi

# ── summary ─────────────────────────────────────────────────────────────────
section 'Summary'
if [[ "$FAILED" -eq 0 ]]; then
    echo "   ✓✓✓  Server environment is ready."
else
    echo "   ✗   Fix the FAIL items above before submitting jobs."
    exit 1
fi

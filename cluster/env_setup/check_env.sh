#!/bin/bash
###############################################################################
#  cluster/env_setup/check_env.sh — environment readiness probe
#
#  Wraps the same checks as cluster/trial/01_env_check.sh, callable from
#  other scripts (run_section0_full.sh, run_slab_full.sh, etc) as a
#  one-stop "is this env usable?" gate.
#
#  If you're just starting on cluster-A, prefer running the trial scripts
#  in order (01 → 02 → 03 → 04) — they give you richer output.
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
  (a) conda + the `phys` env activate-able
  (b) numpy / scipy / pandas / matplotlib / scikit-learn importable
  (c) pygamd importable (only needed for C; optional otherwise)
  (d) sbatch on PATH + free disk on /mnt/nfs/ugstu/liuzx

If anything fails here, fix it before submitting any cluster jobs.

BAN
printf 'Host : %s\n' "$(hostname)"
printf 'Date : %s\n' "$(date -Iseconds)"

# ── step 1: conda envs ──────────────────────────────────────────────────────
section 'Step 1/4 — conda + envs'
if ! command -v conda >/dev/null 2>&1; then
    fail "conda not on PATH. Try: source ~/miniconda3/etc/profile.d/conda.sh"
    exit 1
fi
ok "conda found at $(which conda) ($(conda --version 2>&1))"
echo
conda env list

# ── step 2: activate phys ───────────────────────────────────────────────────
section 'Step 2/4 — activate phys env'
for prefix in ~/miniconda3 ~/anaconda3 /opt/miniconda3 /opt/anaconda3; do
    if [[ -f "$prefix/etc/profile.d/conda.sh" ]]; then
        # shellcheck disable=SC1090
        source "$prefix/etc/profile.d/conda.sh"
        break
    fi
done
if conda activate phys 2>/dev/null; then
    ok "phys active, python = $(which python) ($(python --version 2>&1))"
else
    fail "phys env not found. Run bash cluster/env_setup/install_phys.sh"
    exit 2
fi

# ── step 3: analysis stack + pygamd ─────────────────────────────────────────
section 'Step 3/4 — Python packages'
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
# pygamd optional — only Workstream C needs it
try:
    import pygamd
    print(f"   ✓  pygamd       {getattr(pygamd, '__version__', '?')}  (constrained-h MD enabled)")
except ImportError:
    try:
        from poetry import cu_gala
        print("   ✓  cu_gala via poetry  (constrained-h MD enabled)")
    except ImportError as e:
        print(f"   ⚠  pygamd / cu_gala MISSING  ({e})  — §0 still works, C blocked")
sys.exit(0 if ok else 3)
PY

# ── step 4: SLURM + disk ────────────────────────────────────────────────────
section 'Step 4/4 — SLURM + disk'
if command -v sbatch >/dev/null 2>&1; then
    ok "sbatch at $(which sbatch) ($(sbatch --version 2>&1 | head -1))"
    echo "   partitions visible:"
    sinfo -h -o "     %P  nodes=%D  state=%t" 2>&1 | head -5
else
    fail "sbatch not on PATH"
fi

if [[ -d /mnt/nfs/ugstu/liuzx ]]; then
    echo "   disk free on /mnt/nfs/ugstu/liuzx:"
    df -h /mnt/nfs/ugstu/liuzx | sed 's/^/     /'
else
    warn "/mnt/nfs/ugstu/liuzx not mounted"
fi

# ── summary ─────────────────────────────────────────────────────────────────
section 'Summary'
if [[ "$FAILED" -eq 0 ]]; then
    echo "   ✓✓✓  Environment is ready. You can now run §0 bundle and/or C MD."
else
    echo "   ✗   Fix the FAIL items above before submitting jobs."
    exit 1
fi

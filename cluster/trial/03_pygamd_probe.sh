#!/bin/bash
###############################################################################
#  TRIAL 03 — probe pygamd / cu_gala for constrained-h MD wiring
###############################################################################
#
#  Purpose
#  -------
#  The constrained-h slab MD (Workstream C) needs two specific things from
#  pygamd that we don't yet know how to call:
#
#    (a) a HARMONIC z-tether that pins each membrane's z center-of-mass at
#        ±h/2 — needed to enforce a fixed membrane gap during the MD run.
#    (b) a way to set the R-L binding ε to 0 in the nonbonded table — so
#        the slab simulation generates pure-unbound R/L chain statistics.
#
#  ref/nvt-md.py shows that the production simulations use cu_gala via
#  `from poetry import cu_gala`. We need to discover, on cluster-A:
#
#    1. Which import statement actually works on this cluster
#    2. The fully-qualified class name of the harmonic / external-force class
#    3. The pygamd / cu_gala version (for reproducibility)
#
#  This script tries every reasonable import path and prints the public
#  symbols in candidate force/constraint modules. Claude then picks the
#  right call to wire into cluster/scripts/nvt-md-constrained-h.py.
#
#  Expected wall time : < 1 minute.
#  Failure tolerance  : if pygamd is missing entirely, Workstream C is
#                       blocked until it's installed. The §0 bundle-for-
#                       off-site collaborator path does NOT need pygamd, so 01/02/04 can
#                       still proceed even if 03 fails.
#
#  What to send back
#  -----------------
#  Entire stdout. Especially the "matches '<keyword>'" lines under each
#  candidate module — those are the constraint/force class names.
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
║  TRIAL 03 / 04  —  pygamd / cu_gala probe                         ║
║  Goal: find the right import + the harmonic-constraint class name ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
The constrained-h slab MD (Workstream C) needs two specific things from
pygamd that we don't yet know how to call:

  (a) a HARMONIC z-tether that pins each membrane's z center-of-mass at
      ±h/2 — to enforce a fixed membrane gap during the MD run.
  (b) a way to set the R-L binding ε to 0 in the nonbonded table — so
      the slab simulation generates pure-unbound R/L chain statistics.

ref/nvt-md.py uses cu_gala via `from poetry import cu_gala`. We need to
discover, on cluster-A:

  1. Which import statement actually works
  2. The fully-qualified class name of the harmonic / external-force class
  3. The pygamd / cu_gala version (for reproducibility)

This script tries every reasonable import path and prints public symbols
in candidate force/constraint modules. Claude then picks the right call
to wire into cluster/scripts/nvt-md-constrained-h.py.

Expected wall time : < 1 minute.
Failure tolerance  : if pygamd is missing entirely, Workstream C is
                     blocked until install. The §0 bundle path doesn't
                     need pygamd, so 04 can still proceed.
What to send back  : entire stdout. Especially the "matches '<keyword>'"
                     lines under each candidate module — those are the
                     constraint/force class names.
BAN
printf 'Host : %s\n' "$(hostname)"
printf 'Date : %s\n' "$(date -Iseconds)"

# ── activate phys (silently if it succeeds) ───────────────────────────────────
for prefix in ~/miniconda3 ~/anaconda3 /opt/miniconda3 /opt/anaconda3; do
    if [[ -f "$prefix/etc/profile.d/conda.sh" ]]; then
        # shellcheck disable=SC1090
        source "$prefix/etc/profile.d/conda.sh"
        break
    fi
done
if ! conda activate phys 2>/dev/null; then
    warn "could not activate phys env — using system python."
    warn "(Re-run after 01 passes if you can.)"
fi
echo "   using python: $(which python)"
echo "   python --version: $(python --version 2>&1)"

# ── step 1: try every reasonable import path ─────────────────────────────────
section 'Step 1/3 — which import statement works?'
echo "   Trying common imports. Each line shows the result."
echo
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
    else
        printf '     [%s]  →  %s\n' "$spec" "$out"
    fi
done

# ── step 2: inspect ref/nvt-md.py — what does our production code actually use ─
section 'Step 2/3 — what ref/nvt-md.py imports (production anchor)'
if [[ -f ref/nvt-md.py ]]; then
    echo "   First 15 lines of import statements in ref/nvt-md.py:"
    grep -nE "^(import|from )" ref/nvt-md.py | head -15 | sed 's/^/     /'
else
    warn "ref/nvt-md.py not found at $(pwd)/ref/nvt-md.py."
    warn "Are you in the repo root? cd to /mnt/nfs/ugstu/liuzx/2D-Binding"
fi

# ── step 3: discover the harmonic/external-force class ───────────────────────
section 'Step 3/3 — search candidate modules for harmonic constraint classes'
echo "   This is what lets us hold the membrane at fixed z. Looking for any"
echo "   class whose name contains: Harmonic, External, Plane, Tether, Confine,"
echo "   Restraint, Wall, or Constraint."
echo

python - <<'PY' 2>&1
import importlib
import sys

# Try to find ANY pygamd-like top-level module
top_modules = []
for spec in ("pygamd", "poetry.cu_gala", "poetry.gala", "gala", "cu_gala"):
    try:
        m = importlib.import_module(spec)
        top_modules.append((spec, m))
        print(f"   top-level {spec} imported: {getattr(m, '__file__', '?')}")
        print(f"     version: {getattr(m, '__version__', '?')}")
    except Exception as e:
        print(f"   {spec}: NOT importable ({type(e).__name__})")

if not top_modules:
    print("\n   ✗  NO pygamd-like module is importable in this env.")
    print("      The constrained-h MD path (Workstream C) is blocked until")
    print("      someone installs pygamd. The §0 bundle does not need pygamd,")
    print("      so 04_extract_pilot can still pass.")
    sys.exit(1)

KEYWORDS = ("Harmonic", "External", "Plane", "Tether", "Confine",
             "Restraint", "Wall", "Constraint", "Force", "Z_")
print()
print("   public symbols matching constraint/force keywords:")
for spec, m in top_modules:
    print(f"\n   ── {spec} ──")
    public = [x for x in dir(m) if not x.startswith("_")]
    print(f"     ({len(public)} public symbols total)")
    for kw in KEYWORDS:
        hits = [x for x in public if kw.lower() in x.lower()]
        if hits:
            print(f"     matches '{kw}': {hits}")

# Also probe known submodule names
print()
print("   probing potential force / constraint sub-modules:")
for spec, _ in top_modules:
    for sub in ("force", "constraint", "potential", "bond", "external"):
        mod_path = f"{spec}.{sub}"
        try:
            sm = importlib.import_module(mod_path)
            pub = [x for x in dir(sm) if not x.startswith("_")]
            print(f"     {mod_path}: {len(pub)} symbols, sample: {pub[:8]}")
        except ImportError:
            pass
PY

# ── summary ──────────────────────────────────────────────────────────────────
section 'Summary'
cat <<'EOF'
   Look at the output above and report:

     1. Which import line printed OK (Step 1)
     2. Whether ref/nvt-md.py was found and what its imports look like (Step 2)
     3. The class name (and module path) for harmonic z-tether (Step 3) —
        e.g. "cu_gala.HarmonicConstraint" or "pygamd.force.PlanePotential"

   With that info Claude will fill in the TODO lines in
   cluster/scripts/nvt-md-constrained-h.py and we can submit a real
   constrained-h pilot via cluster/slurm/single_pilot.slurm.

   If everything failed: pygamd isn't installed here. Tell off-site collaborator so she
   can confirm install path. The §0 bundle path (which doesn't need pygamd)
   is still your fastest answer to the data-volume question.

   Next : bash cluster/trial/04_extract_pilot.sh
EOF

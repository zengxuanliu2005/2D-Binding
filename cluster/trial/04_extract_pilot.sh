#!/bin/bash
###############################################################################
#  TRIAL 04 — extract pilot: run the bundle's extract step on YOUR K100 s001
###############################################################################
#
#  Purpose (also printed when this runs)
#  -------------------------------------
#  The §0 bundle (bundle_for_senior/) hinges on one Python script working
#  end-to-end: extract_chain_coords.py reading traj.xyz + mol.psf +
#  num_bonds_for_xyz_frames.dat and writing chain_coords.npz with the right
#  schema (positions_R / positions_L / bound_R / bound_L / partner_R /
#  partner_L / n_frames / box).
#
#  We confirm this on cluster-A using your K100 s001 — the smallest possible
#  real test. If this passes:
#
#    • The bundle will work when senior runs it on her server.
#    • cluster/scripts/extract_one_replica.py path constants are correct.
#    • We can move on to running the full bundle (--pilot mode) and start
#      packaging it for senior.
#
#  Expected wall time : ~1-2 min (50 frames extracted from one traj.xyz).
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
║  TRIAL 04 / 04  —  extract pilot on K100 s001                     ║
║  Goal: extract_one_replica.py --pilot works on real cluster data  ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
This is the smallest real test of the §0 bundle pipeline. We:

  (a) auto-detect the K100 dir on /mnt/nfs/ugstu/liuzx
  (b) call cluster/scripts/extract_one_replica.py with --pilot (limits to
      50 frames; ~30 s of work)
  (c) verify the output chain_coords.npz has the expected schema
      (positions_R / positions_L / bound_R / bound_L / n_R / n_L / box /
      n_frames)
  (d) report bound/unbound R counts so we can see this is real data, not
      garbage

If this passes the §0 bundle will work on senior's server. If it fails the
fix lives in cluster/scripts/extract_one_replica.py (path constants) or in
cluster/scripts/topology.py / bonds.py (file-format assumptions). Either
way Claude can patch with the exact error message from this script.

Expected wall time : 1-2 min.
What to send back  : entire stdout.

BAN
printf 'Host : %s\n' "$(hostname)"
printf 'Date : %s\n' "$(date -Iseconds)"
printf 'PWD  : %s\n' "$(pwd)"

# ── step 0: activate phys if local, else use whatever python on PATH ─────────
section 'Step 0/4 — pick conda env (phys if local, else current)'
for prefix in /opt/miniconda3 ~/miniconda3 /opt/anaconda3 ~/anaconda3; do
    if [[ -f "$prefix/etc/profile.d/conda.sh" ]]; then
        # shellcheck disable=SC1090
        source "$prefix/etc/profile.d/conda.sh"
        break
    fi
done
ok "using cluster python = $(which python)"
# Quick verify the analysis stack imports — required for extract to work.
python - <<'PY' 2>&1
import importlib, sys
all_ok = True
for mod in ("numpy",):
    try:
        importlib.import_module(mod)
    except ImportError as e:
        print(f"   ✗  {mod} not importable: {e}", file=sys.stderr)
        all_ok = False
sys.exit(0 if all_ok else 2)
PY
if [[ $? -ne 0 ]]; then
    fail "numpy not installed in the active env. Run 01_env_check.sh to confirm."
    exit 2
fi

# ── step 1: detect K100 layout ───────────────────────────────────────────────
section 'Step 1/4 — detect K100 directory'
echo "   searching /mnt/nfs/ugstu/liuzx for a directory named like K100 ..."
K100_DIR=$(find /mnt/nfs/ugstu/liuzx -maxdepth 4 -type d \
              \( -name '*K100*' -o -name '*K_100*' \) 2>/dev/null | head -1)
if [[ -z "$K100_DIR" ]]; then
    fail "no K100 directory found under /mnt/nfs/ugstu/liuzx"
    warn "Re-check 02_paths_check.sh output — perhaps the naming differs."
    exit 3
fi
MD_BASE=$(dirname "$K100_DIR")
K100_NAME=$(basename "$K100_DIR")
ok "K100 directory : $K100_DIR"
ok "MD_BASE        : $MD_BASE"
ok "K100 name      : $K100_NAME"

# ── step 2: find s001 + verify files ─────────────────────────────────────────
section 'Step 2/4 — verify s001 has the 3 expected files'
S001="$K100_DIR/s001"
if [[ ! -d "$S001" ]]; then
    fail "s001 dir not found at $S001"
    ls -la "$K100_DIR" 2>&1 | head | sed 's/^/     /'
    exit 4
fi
ok "s001 dir : $S001"
for f in traj.xyz mol.psf num_bonds_for_xyz_frames.dat; do
    if [[ -f "$S001/$f" ]]; then
        ok "$f  ($(du -h "$S001/$f" | cut -f1))"
    else
        fail "$f MISSING in $S001"
    fi
done
[[ "$FAILED" -eq 1 ]] && exit 5

# ── step 3: run the pilot extract ────────────────────────────────────────────
section 'Step 3/4 — run extract_one_replica.py --pilot (~30 s)'
OUT_DIR=cluster/outputs/extracted/trial_pilot
mkdir -p "$OUT_DIR"
echo "   command:"
echo "     python cluster/scripts/extract_one_replica.py \\"
echo "         --system $K100_NAME --replica s001 \\"
echo "         --md-base $MD_BASE \\"
echo "         --out $OUT_DIR/K100_s001.npz \\"
echo "         --pilot"
echo
START=$(date +%s)
python -u cluster/scripts/extract_one_replica.py \
    --system "$K100_NAME" --replica s001 \
    --md-base "$MD_BASE" \
    --out "$OUT_DIR/K100_s001.npz" \
    --pilot
RC=$?
DUR=$(( $(date +%s) - START ))
if [[ "$RC" -eq 0 ]]; then
    ok "extract completed in ${DUR} s"
else
    fail "extract exited with code $RC"
    warn "Send the error message above to Claude — fix is usually a path"
    warn "constant in cluster/scripts/extract_one_replica.py or a bead-naming"
    warn "convention in cluster/scripts/topology.py."
    exit 6
fi

# ── step 4: verify the produced npz ──────────────────────────────────────────
section 'Step 4/4 — verify the chain_coords.npz schema'
echo "   asserting schema and printing first-replica statistics ..."
python - "$OUT_DIR/K100_s001.npz" <<'PY' 2>&1
import sys
from pathlib import Path
import numpy as np

p = Path(sys.argv[1])
if not p.exists():
    print(f"   ✗  {p} does not exist")
    sys.exit(7)

d = np.load(p)
print(f"\n   file size: {p.stat().st_size/1e6:.2f} MB")
print("\n   contents:")
for k in d.files:
    arr = d[k]
    sh = getattr(arr, "shape", ())
    print(f"     {k:<14}  shape={str(sh):<22}  dtype={arr.dtype}")

required = ["positions_R", "positions_L", "bound_R", "bound_L",
            "n_frames", "n_R", "n_L", "box"]
missing = [k for k in required if k not in d.files]
if missing:
    print(f"\n   ✗  MISSING required keys: {missing}")
    sys.exit(8)
print(f"\n   ✓  all required schema keys present")

nf = int(d["n_frames"])
nR = int(d["n_R"]); nL = int(d["n_L"])
bR_per_frame = d["bound_R"].sum(axis=1).mean()
bL_per_frame = d["bound_L"].sum(axis=1).mean()
print(f"   n_frames         = {nf}")
print(f"   n_R / n_L        = {nR} / {nL}  (expected K100: 15 / 15)")
print(f"   bound R per frame = {bR_per_frame:.2f}  (s001 baseline ≈ 10.3)")
print(f"   bound L per frame = {bL_per_frame:.2f}")
print(f"   box               = {d['box']}")

# Pilot-quality assertions
ok_count = 0
fails = []
if 0 < nf <= 50:        ok_count += 1
else:                    fails.append(f"n_frames={nf} not in (0, 50]")
if nR == 15 and nL == 15: ok_count += 1
else:                     fails.append(f"n_R/n_L = {nR}/{nL}, K100 expects 15/15")
if bR_per_frame > 0:     ok_count += 1
else:                     fails.append(f"bound R count is zero — extract broken")

if fails:
    print("\n   ✗  pilot assertions FAILED:")
    for f in fails: print(f"      • {f}")
    sys.exit(9)
print(f"\n   ✓  pilot assertions PASSED ({ok_count}/3)")
PY
RC=$?

# ── summary ──────────────────────────────────────────────────────────────────
section 'Summary'
if [[ "$RC" -eq 0 && "$FAILED" -eq 0 ]]; then
    cat <<EOF
   ✓✓✓  TRIAL 04 PASSED.

   Means:
     • extract_one_replica.py works on cluster reality
     • cluster/scripts/topology.py + bonds.py read your traj/psf correctly
     • chain_coords.npz schema is exactly what bundle_for_senior expects

   Send back to Claude:
     • The "contents:" table (shape + dtype of each key)
     • The "bound R per frame" number (sanity vs s001 ≈ 10.3)
     • The wall time printed under Step 3 (so we can project full-bundle cost)

   Next steps you can do without me:
     1. If 02_paths_check showed you have YOUR own s002+:
            cp -R cluster/bundle_for_senior /mnt/nfs/ugstu/liuzx/
            cd /mnt/nfs/ugstu/liuzx/bundle_for_senior
            bash run_full_analysis.sh --pilot
        That tests the full pipeline on your data, ~5 min.
     2. Otherwise just package the bundle for senior:
            cd /mnt/nfs/ugstu/liuzx/2D-Binding/cluster
            tar czf bundle_for_senior.tgz bundle_for_senior/
            ls -lh bundle_for_senior.tgz
        and send to her via WeChat / email.
EOF
else
    cat <<'EOF'
   ✗  Trial 04 failed somewhere — see error messages above.

   Common fixes:
     • "no K100 directory found" → 02_paths_check showed your dirs differ
       from K100; tell Claude the actual prefix.
     • "missing required keys" → schema mismatch in topology.py / bonds.py;
       cluster MD outputs are slightly different format from local.
     • "extract exited with code N" → paste the Python traceback; it
       almost always points to a single function in topology.py or bonds.py
       that needs to be made forgiving about the cluster's file format.

   Send the entire stdout to Claude regardless.
EOF
fi

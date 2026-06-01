#!/bin/bash
###############################################################################
#  TRIAL 02 — locate MD data and count replicas on cluster-A
###############################################################################
#
#  Purpose
#  -------
#  The local repo has copies of three systems' s001 directories under
#  outputs/. The cluster-A NFS workspace (/mnt/nfs/ugstu/liuzx) is where the
#  real production data lives — and it may have continuation replicas s002,
#  s003, ... that we don't yet have. This script:
#
#    (a) confirms the NFS mount and disk free
#    (b) finds the three system directories (K100 / K10 / K01)
#    (c) counts replicas per system — KEY QUESTION: do YOU have s002+?
#         If yes, we can run a mini §0 data-volume test on YOUR data,
#         independent of waiting for senior.
#    (d) sanity-checks one s001 has the expected files (traj.xyz, mol.psf,
#         num_bonds_for_xyz_frames.dat) so downstream extract works.
#
#  Expected wall time : < 30 seconds.
#  Failure tolerance  : if NFS isn't mounted you can't do anything else; if
#                       directory names differ from what cluster/scripts/*
#                       assume, we'll patch those constants based on the
#                       output here.
#
#  What to send back
#  -----------------
#  Entire stdout/stderr. Most important: the inventory table near the bottom.
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
║  TRIAL 02 / 04  —  MD data inventory                              ║
║  Goal: find K100/K10/K01 directories, count replicas, verify files║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
The local repo has copies of three systems' s001 only. The cluster-A NFS
workspace (/mnt/nfs/ugstu/liuzx) is where the real production data lives,
and may have continuation replicas s002, s003, ... we don't have locally.
This script:

  (a) confirms the NFS mount and disk free
  (b) finds the three system directories (K100 / K10 / K01) on cluster
  (c) counts replicas per system → KEY QUESTION: do YOU have s002+?
        If yes, we can run a mini §0 data-volume test on YOUR data,
        independent of waiting for senior's bundle reply.
  (d) sanity-checks one s001 has the expected files (traj.xyz, mol.psf,
        num_bonds_for_xyz_frames.dat) so downstream extract works.

Expected wall time : < 30 seconds.
What to send back  : the inventory table near the bottom + the file
                     name list under "sanity-check files in one s001".
BAN
printf 'Host : %s\n' "$(hostname)"
printf 'Date : %s\n' "$(date -Iseconds)"

# ── step 1: home + workspace ─────────────────────────────────────────────────
section 'Step 1/4 — home & workspace'
echo "   HOME : $HOME"
echo "   PWD  : $(pwd)"
echo
echo "   ls -la \$HOME (first 20 entries) :"
ls -la "$HOME" 2>&1 | head -20

# ── step 2: NFS workspace ────────────────────────────────────────────────────
section 'Step 2/4 — NFS workspace /mnt/nfs/ugstu/liuzx'
if [[ -d /mnt/nfs/ugstu/liuzx ]]; then
    ok "/mnt/nfs/ugstu/liuzx is mounted"
    echo
    echo "   contents (top-level, first 30):"
    ls -la /mnt/nfs/ugstu/liuzx 2>&1 | head -30
    echo
    echo "   disk free:"
    df -h /mnt/nfs/ugstu/liuzx 2>&1
else
    fail "/mnt/nfs/ugstu/liuzx not mounted on $(hostname). Wrong cluster node?"
    warn "We can still proceed if your MD data lives elsewhere — see Step 3."
fi

# ── step 3: find system directories ─────────────────────────────────────────
section 'Step 3/4 — locate K100 / K10 / K01 system directories'
echo "   searching depth ≤ 3 under /mnt/nfs/ugstu/liuzx for directories named"
echo "   like a 2D-Binding system (contains 120x120 / EPS05 / K100 / K10 / K01):"
echo
HITS=$(find /mnt/nfs/ugstu/liuzx -maxdepth 3 -type d 2>/dev/null \
       | grep -iE '120x120|EPS05|K100|K10|K01|2D-Binding|2D_Binding')
if [[ -z "$HITS" ]]; then
    fail "no system directories found under /mnt/nfs/ugstu/liuzx"
    warn "Tell Claude where your MD outputs actually live so paths can be fixed."
else
    echo "$HITS" | head -30 | sed 's/^/     /'
    N_HITS=$(echo "$HITS" | wc -l | tr -d ' ')
    ok "found $N_HITS candidate directories"
fi

# ── step 4: replicas per system ─────────────────────────────────────────────
section 'Step 4/4 — count replicas per system'
echo "   listing every s### directory under /mnt/nfs/ugstu/liuzx,"
echo "   grouped by the parent directory that matches a system pattern:"
echo
INVENTORY_RAW=$(find /mnt/nfs/ugstu/liuzx -maxdepth 4 -type d -name 's[0-9][0-9][0-9]' 2>/dev/null)
N_REP_TOTAL=$(echo "$INVENTORY_RAW" | grep -c .)
echo "   total s### directories found: $N_REP_TOTAL"
echo
echo "   per-system count (system name = parent dir matching K100/K10/K01/etc):"
echo
echo "$INVENTORY_RAW" | awk -F/ '
    {
        sys="(other)"
        for(i=NF-1;i>=1;i--) {
            if($i ~ /120x120|EPS05|K100|K10|K01/) { sys=$i; break }
        }
        count[sys]++
    }
    END {
        for(s in count) printf "     %-40s  %d replicas\n", s, count[s]
    }
' | sort -k2 -rn

if [[ "$N_REP_TOTAL" -le 3 ]]; then
    warn "≤3 replicas total — you probably only have s001 per system."
    warn "  → §0 data-volume test depends entirely on senior's bundle run."
elif [[ "$N_REP_TOTAL" -ge 6 ]]; then
    ok "$N_REP_TOTAL replicas — you have continuation data!"
    ok "  → we can run a mini §0 test on YOUR data without waiting for senior."
fi

# sanity check: pick the first s001 we find and look for expected files
echo
echo "   sanity-check files in one s001 (whichever shows up first):"
S001_DIR=$(find /mnt/nfs/ugstu/liuzx -maxdepth 4 -type d -name 's001' 2>/dev/null | head -1)
if [[ -n "$S001_DIR" ]]; then
    echo "     example replica: $S001_DIR"
    ls -la "$S001_DIR" 2>&1 | head -15 | sed 's/^/       /'
    echo
    for f in traj.xyz mol.psf num_bonds_for_xyz_frames.dat; do
        if [[ -f "$S001_DIR/$f" ]]; then
            sz=$(du -h "$S001_DIR/$f" | cut -f1)
            ok "$f exists ($sz)"
        else
            fail "$f MISSING in $S001_DIR — extract will not work"
        fi
    done
else
    fail "no s001 directory found anywhere — fundamental layout mismatch"
fi

# ── summary ──────────────────────────────────────────────────────────────────
section 'Summary'
if [[ "$FAILED" -eq 0 ]]; then
    cat <<EOF
   ✓✓✓  Inventory complete.

   Tell Claude:
     • Total replica count: $N_REP_TOTAL
     • Per-system breakdown (the table above)
     • The exact directory names for the 3 systems (the matching lines)
     • One example replica path (so MD_BASE in extract_one_replica.py can be locked)

   Next : bash cluster/trial/03_pygamd_probe.sh
EOF
else
    cat <<'EOF'
   ✗  Some checks failed. Most likely fixes:

     • NFS not mounted on this node → try another login node
     • Directory names differ from K100/K10/K01 — tell Claude the actual names
     • Missing file in s001 (traj.xyz / mol.psf / num_bonds_for_xyz_frames.dat)
       → likely a different naming convention; tell Claude what's there instead

   Send the full output to Claude regardless.
EOF
    exit 1
fi

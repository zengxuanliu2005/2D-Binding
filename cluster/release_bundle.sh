#!/bin/bash
###############################################################################
#  cluster/release_bundle.sh — authorize Loop 1 → Loop 2 release (cp-based)
#
#  Run LOCALLY from the repo root AFTER trial loop converges (i.e., after
#  cluster/trial/results/<date>_round<N>_verdict.md says "all green").
#
#  This script does NOT produce a tarball. The off-site collaborator
#  rsyncs cluster/ directly from cluster-A (she has shared-filesystem
#  access). What this script does:
#    1. Verify the trial verdict file exists (or --force to override)
#    2. Capture git SHA + date and append a row to cluster/RELEASES.md
#    3. Print the cyberduck-upload reminder (cluster-A has no git, so
#       the user must cyberduck-upload the latest cluster/ to keep
#       cluster-A in sync with this released SHA)
#    4. Print copy-paste templates: rsync command + WeChat message
#
#  Usage:
#      bash cluster/release_bundle.sh                # production
#      bash cluster/release_bundle.sh --force        # skip verdict check
###############################################################################
set -euo pipefail

FORCE=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=1 ;;
        --dry-run) echo "  --dry-run is no longer meaningful (no tar to dry-run); skipping flag"; ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
    shift
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

cat <<'BAN'
╔════════════════════════════════════════════════════════════════════╗
║  cluster/release_bundle.sh — authorize Loop 1 → Loop 2 release    ║
╚════════════════════════════════════════════════════════════════════╝
PURPOSE
─────────
Records that the trial loop has converged and the bundle is ready for
the off-site collaborator. Cluster-A is the shared handoff point; she
rsyncs cluster/ directly. No tarball, no WeChat file transfer.
BAN

# ─── Step 1: verify trial verdict exists ─────────────────────────────────────
echo
echo "--- step 1: check trial verdict ---"
LATEST_VERDICT=$(ls -t cluster/trial/results/*_verdict.md 2>/dev/null | head -1 || true)
if [[ -z "$LATEST_VERDICT" ]]; then
    if [[ "$FORCE" -eq 1 ]]; then
        echo "  ⚠ no trial verdict found, but --force given — proceeding"
        LATEST_VERDICT="(none, --force)"
    else
        echo "  ✗ no cluster/trial/results/*_verdict.md found"
        echo "    Run the trial loop to convergence first, OR use --force to override."
        echo "    See cluster/trial/README.md for the trial protocol."
        exit 2
    fi
else
    echo "  ✓ latest verdict: $LATEST_VERDICT"
fi

# ─── Step 2: gather metadata ─────────────────────────────────────────────────
echo
echo "--- step 2: gather metadata ---"
RELEASE_DATE=$(date -I)
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
echo "  date     : $RELEASE_DATE"
echo "  git SHA  : $GIT_SHA"
echo "  git ref  : $GIT_BRANCH"

# Check working tree is clean (warn if not)
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    echo "  ⚠ working tree has uncommitted changes — release will reflect ON-DISK state"
    echo "     (consider committing first so RELEASES.md links a clean SHA)"
fi

# ─── Step 3: log in RELEASES.md ──────────────────────────────────────────────
echo
echo "--- step 3: log in cluster/RELEASES.md ---"
RELEASES_MD="cluster/RELEASES.md"
if [[ ! -f "$RELEASES_MD" ]]; then
    cat > "$RELEASES_MD" <<'EOF'
---
purpose: "Log of cluster bundle releases authorised for the off-site collaborator (Loop 1 → Loop 2 transitions)"
audience: user (which SHA was released when) + Claude (provenance for incoming off-site full-data results)
status: current
---

# cluster/RELEASES.md — bundle releases authorised for off-site full-data run

Each row records that the trial loop converged at a given git SHA and the
bundle was authorised for off-site rsync. When her distilled results return,
the analysis in `cluster/results/<date>_round<N>_analysis.md` should reference
the release row here so we can recover exactly which script versions she ran.

The off-site collaborator does NOT receive a tarball — she rsyncs cluster/
directly from the shared cluster-A path. The user is responsible for keeping
cluster-A in sync with this released SHA via cyberduck (cluster-A has no git).

## Releases

| release date | git SHA | git ref | trial verdict source | notes |
|---|---|---|---|---|
EOF
fi

VERDICT_DISPLAY="${LATEST_VERDICT#cluster/trial/results/}"
echo "| $RELEASE_DATE | \`$GIT_SHA\` | $GIT_BRANCH | $VERDICT_DISPLAY | |" >> "$RELEASES_MD"
echo "  ✓ appended row to $RELEASES_MD"

# ─── Step 4: print cyberduck-upload reminder ─────────────────────────────────
echo
echo "==========================================================="
echo "  ⚠  cyberduck-upload reminder (cluster-A has no git)"
echo "==========================================================="
cat <<'EOF'
  Before the off-site collaborator rsyncs, you MUST refresh cluster-A
  with this released SHA. Use cyberduck:

    1. ssh master  &&  rm -rf /mnt/nfs/ugstu/liuzx/2D-Binding/cluster
       (deletes the stale cluster/ on cluster-A, so the upload doesn't
        merge with old files)

    2. In cyberduck, connect to cluster-A and navigate to
         /mnt/nfs/ugstu/liuzx/2D-Binding/
       Drag local /Users/.../2D-Binding/cluster/ into that directory.
       cyberduck will create /mnt/nfs/ugstu/liuzx/2D-Binding/cluster/
       with ~46 files. ~1-3 min.

  Skip this only if cluster-A already reflects the released SHA.
EOF

# ─── Step 5: print rsync template (for off-site collaborator) ────────────────
echo
echo "==========================================================="
echo "  Off-site rsync template (paste into your WeChat message)"
echo "==========================================================="
cat <<'EOF'

```bash
# Run on the off-site cluster
SOURCE=/mnt/nfs/ugstu/liuzx/2D-Binding/cluster
MD_ROOT=/your/MD/data/root                # absolute path to your MD data
DEST=$MD_ROOT/2D-Binding-fullrun/cluster
mkdir -p $DEST
rsync -av \
    --exclude='trial' --exclude='outputs' --exclude='results' \
    --exclude='.DS_Store' --exclude='.git*' \
    $SOURCE/ $DEST/

# Then submit:
cd $DEST/..
sbatch cluster/slurm/full_analysis.slurm

# After ~30 min, cp distilled back to the shared dir:
ROUND=/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/outputs/$(date -I)_round1
mkdir -p $ROUND
cp -R $DEST/cluster/outputs/distilled/* $ROUND/
# Ping Zengxuan on WeChat: distilled is in $ROUND
```

See cluster/HOWTO_run_full_data_zh.md for the full Chinese walkthrough.

EOF

# ─── Step 6: print WeChat draft ──────────────────────────────────────────────
echo "==========================================================="
echo "  WeChat draft (for you to send the off-site collaborator)"
echo "==========================================================="
cat <<EOF

[你好！]

2D-Binding 全量数据复跑包已经放在共享目录里 (git SHA $GIT_SHA, $RELEASE_DATE)：

  /mnt/nfs/ugstu/liuzx/2D-Binding/cluster/

详细步骤看 cluster/HOWTO_run_full_data_zh.md (中文)，简版：

  1. rsync 这个 cluster/ 到你 MD 数据根目录下的工作目录 (exclude trial/outputs/results)
  2. sbatch cluster/slurm/full_analysis.slurm  (大约 30 min)
  3. cp cluster/outputs/distilled/ 到 /mnt/nfs/ugstu/liuzx/2D-Binding/cluster/outputs/<date>_round1/
  4. 微信告诉我 distilled 在哪个 round 目录里

EOF

# ─── Step 7: final summary ───────────────────────────────────────────────────
echo "==========================================================="
echo "  ✓ Release authorised (SHA $GIT_SHA)"
echo "==========================================================="
echo "Next actions for you:"
echo "  1. (cyberduck-upload reminder above) refresh cluster-A with this SHA"
echo "  2. git add cluster/RELEASES.md && git commit -m \"release: $RELEASE_DATE\""
echo "  3. WeChat the off-site collaborator (template above)"
echo "  4. Wait for distilled cp into cluster/outputs/<date>_round1/"
echo "  5. Apply Loop 2 protocol (log/decisions/007): write"
echo "     cluster/results/<date>_round1_analysis.md including B-revision impact"
echo

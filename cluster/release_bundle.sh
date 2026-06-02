#!/bin/bash
###############################################################################
#  cluster/release_bundle.sh — pack cluster/ for off-site full-data run, close Loop 1
#
#  Run LOCALLY from the repo root AFTER trial loop converges (i.e., after
#  cluster/trial/results/<date>_round<N>_verdict.md says "all green").
#
#  Packs cluster/ into a tarball ready to send for off-site run via WeChat/email,
#  excluding the Loop 1 / Loop 2 working directories that off-site collaborator doesn't
#  need (trial/, outputs/, results/).
#
#  Usage:
#      bash cluster/release_bundle.sh                # production release
#      bash cluster/release_bundle.sh --dry-run      # show what would be packed
#      bash cluster/release_bundle.sh --force        # skip trial-verdict check
#
#  Logs each release in cluster/RELEASES.md so the user can track which git
#  SHA the off-site collaborator actually got.
###############################################################################
set -euo pipefail

DRY_RUN=0
FORCE=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --force) FORCE=1 ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
    shift
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

cat <<'BAN'
╔════════════════════════════════════════════════════════════════════╗
║  cluster/release_bundle.sh — Loop 1 → Loop 2 transition           ║
╚════════════════════════════════════════════════════════════════════╝
PURPOSE
─────────
Packs cluster/ into a tarball off-site collaborator can unpack on her server. Excludes
the validation / round-tripping infrastructure she doesn't need.
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
TARBALL="cluster-bundle-${RELEASE_DATE}-${GIT_SHA}.tgz"
echo "  date     : $RELEASE_DATE"
echo "  git SHA  : $GIT_SHA"
echo "  git ref  : $GIT_BRANCH"
echo "  tarball  : $TARBALL"

# Check working tree is clean (warn if not)
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    echo "  ⚠ working tree has uncommitted changes — bundle will reflect ON-DISK state"
    echo "     (consider committing first so RELEASES.md links a clean SHA)"
fi

# ─── Step 3: build exclude list ──────────────────────────────────────────────
echo
echo "--- step 3: build exclude list ---"
EXCLUDES=(
    "cluster/trial"                  # validation harness; not for off-site full-data run
    "cluster/outputs"                # Loop 2 data; off-site collaborator writes her own
    "cluster/results"                # Loop 2 analysis; we write
    "cluster/off-site analysis bundle"      # legacy directory (refactored away)
    "cluster/.gitignore"             # not needed in tarball
    "cluster/release_bundle.sh"      # we release; off-site collaborator doesn't
    ".DS_Store"                      # macOS metadata
)
for E in "${EXCLUDES[@]}"; do
    echo "  exclude: $E"
done

# ─── Step 4: pack tarball ────────────────────────────────────────────────────
echo
echo "--- step 4: pack ---"
TAR_EXCLUDE_ARGS=()
for E in "${EXCLUDES[@]}"; do
    TAR_EXCLUDE_ARGS+=(--exclude="$E")
done

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  (dry-run) files that would be packed:"
    tar czf /dev/null "${TAR_EXCLUDE_ARGS[@]}" --verbose cluster/ 2>&1 | head -40
    echo "  ..."
    N_FILES=$(tar czf /dev/null "${TAR_EXCLUDE_ARGS[@]}" --verbose cluster/ 2>&1 | wc -l | tr -d ' ')
    echo "  total: $N_FILES files"
    echo
    echo "  (dry-run) tarball NOT created. Run without --dry-run to actually pack."
    exit 0
fi

tar czf "$TARBALL" "${TAR_EXCLUDE_ARGS[@]}" cluster/
SIZE=$(du -h "$TARBALL" | cut -f1)
echo "  ✓ packed $TARBALL ($SIZE)"

# ─── Step 5: log in RELEASES.md ──────────────────────────────────────────────
echo
echo "--- step 5: log in cluster/RELEASES.md ---"
RELEASES_MD="cluster/RELEASES.md"
if [[ ! -f "$RELEASES_MD" ]]; then
    cat > "$RELEASES_MD" <<EOF
---
purpose: "Log of cluster bundle releases sent to off-site collaborator (Loop 1 → Loop 2 transitions)"
audience: user (sent which version when) + Claude (provenance for incoming off-site full-data results)
status: current
---

# cluster/RELEASES.md — bundle releases sent to off-site collaborator

Each row is a tarball sent to off-site collaborator. Maps tarball → git SHA + trial verdict
that authorized this release. When her distilled results return, the analysis
in \`cluster/results/<date>_round<N>_analysis.md\` should reference the
release row here so we can recover exactly which script versions she ran.

## Releases

| release date | tarball | git SHA | git ref | trial verdict source | size | notes |
|---|---|---|---|---|---|---|
EOF
fi

VERDICT_DISPLAY="${LATEST_VERDICT#cluster/trial/results/}"
echo "| $RELEASE_DATE | \`$TARBALL\` | \`$GIT_SHA\` | $GIT_BRANCH | $VERDICT_DISPLAY | $SIZE | |" >> "$RELEASES_MD"
echo "  ✓ appended row to $RELEASES_MD"

# ─── Step 6: print next steps ────────────────────────────────────────────────
echo
echo "==========================================================="
echo "  ✓ Release complete"
echo "==========================================================="
echo "Next steps:"
echo "  1. Send $TARBALL via WeChat / email"
echo "  2. (optional) git add cluster/RELEASES.md && git commit -m \"release: $RELEASE_DATE bundle to off-site collaborator\""
echo "  3. Wait for off-site full-data run to return cluster-distilled.tgz (~1-2 h on her end)"
echo "  4. When received: mkdir cluster/outputs/\$(date -I)_round1 &&"
echo "     tar xzf cluster-distilled.tgz -C cluster/outputs/\$(date -I)_round1/ --strip-components 1"
echo "  5. Apply Loop 2 protocol (log/decisions/007): write"
echo "     cluster/results/\$(date -I)_round1_analysis.md including B-revision impact"
echo

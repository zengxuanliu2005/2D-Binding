#!/bin/bash
###############################################################################
#  cluster/env_setup/install_phys.sh — create or update the `phys` conda env
###############################################################################
#
#  PURPOSE (also printed at runtime)
#  ----------------------------------
#  cluster/env_setup/check_env.sh just told you `phys` is missing. This
#  script creates it from cluster/../requirements.txt (or the equivalent
#  in repo root) plus the standard analysis stack.
#
#  pygamd is NOT installed by this script — it usually needs a custom
#  channel / build that the cluster admin (or senior) has set up. Ask
#  senior how she got pygamd, then either:
#    pip install pygamd                # vanilla
#    pip install --index-url <URL> pygamd
#    or follow her install notes
#
#  After this script finishes, re-run check_env.sh to confirm.
#
###############################################################################
set -e

hr() { printf '\n%s\n' "──────────────────────────────────────────────────────────────────────"; }
section() { hr; printf '▶  %s\n' "$1"; hr; }

cat <<'BAN'

╔════════════════════════════════════════════════════════════════════╗
║  cluster/env_setup/install_phys.sh — install/update phys env      ║
╚════════════════════════════════════════════════════════════════════╝

PURPOSE
─────────
Create or update the `phys` conda env with the analysis stack
(numpy/scipy/pandas/matplotlib/scikit-learn). DOES NOT install pygamd —
see comment block at top of this file.

BAN

REQ_TXT="$(dirname "$0")/../../requirements.txt"
if [[ ! -f "$REQ_TXT" ]]; then
    echo "   ⚠  requirements.txt not found at $REQ_TXT — will install minimal set"
    REQ_TXT=""
fi

section 'Step 1/2 — locate conda + activate'
for prefix in ~/miniconda3 ~/anaconda3 /opt/miniconda3 /opt/anaconda3; do
    if [[ -f "$prefix/etc/profile.d/conda.sh" ]]; then
        # shellcheck disable=SC1090
        source "$prefix/etc/profile.d/conda.sh"
        break
    fi
done

section 'Step 2/2 — create or update phys env'
if conda env list | grep -q '^phys '; then
    echo "   phys already exists — updating packages"
    conda activate phys
    if [[ -n "$REQ_TXT" ]]; then
        pip install --upgrade -r "$REQ_TXT"
    else
        pip install --upgrade numpy scipy pandas matplotlib scikit-learn
    fi
else
    echo "   creating phys with python 3.11 + analysis stack"
    conda create -y -n phys python=3.11 numpy scipy pandas matplotlib scikit-learn
    conda activate phys
    [[ -n "$REQ_TXT" ]] && pip install -r "$REQ_TXT"
fi

section 'Done'
cat <<'EOF'
   ✓  phys env ready. Now run:
       bash cluster/env_setup/check_env.sh

   If you need pygamd (for constrained-h MD):
     1. Ask senior for her install command
     2. With phys active, run that command
     3. python -c "import pygamd; print(pygamd.__version__)"
EOF

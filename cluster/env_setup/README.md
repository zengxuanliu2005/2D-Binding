---
purpose: "Index of cluster/env_setup/: one bash script to verify the login-node Python env"
audience: anyone first ssh-ing to a new cluster or compute server
status: current
---

# cluster/env_setup/ — login-node environment verification

| file | purpose |
|---|---|
| `check_env.sh` | bash; verifies that conda is reachable + the analysis stack (numpy/scipy/pandas/matplotlib/scikit-learn) imports in the active Python env. Reports the conda.sh path so it can be hard-coded into SLURM templates. Does NOT require a `phys` conda env — uses whatever Python is on PATH (per ADR 002). |

## Usage

```bash
bash cluster/env_setup/check_env.sh
```

Expected tail:

```
✓ conda env list reachable
✓ analysis stack imports OK
✓ sbatch on PATH at: /usr/bin/sbatch
```

## Adjacent verification (NOT in this directory)

The compute-node equivalent — same checks but inside an SBATCH-allocated
compute-node job — is `cluster/trial/05_compute_node_check.slurm`. Run
that BEFORE submitting any production array job, so login-vs-compute
environment divergences (if any) are caught early.

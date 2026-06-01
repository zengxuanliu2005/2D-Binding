"""Parallel extract — drive extract_chain_coords.run() over many replicas.

PURPOSE
=======
Reads (system, replica_dir, out_dir) rows from stdin (tab-separated).
Runs `extract_chain_coords.run()` for each in a ProcessPoolExecutor with
n_jobs workers. Idempotent: skips rows whose out_dir/chain_coords.npz
already exists.

Replaces an xargs-based extract loop that hit "command line too long" for
any non-trivial replica list.

CONTEXT
=======
Called by bundle_for_senior/run_full_analysis.sh. Each row in stdin is one
replica to extract; the script fans those out to N_JOBS workers.

ENV
===
    N_JOBS : parallel workers (default 8). Set to match cluster CPU count.
"""
from __future__ import annotations
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_chain_coords import run as extract_run  # noqa: E402


def _do_one(task: tuple[str, str, str]) -> tuple[str, str, bool, str]:
    system, replica_dir, out_dir = task
    out_path = Path(out_dir) / "chain_coords.npz"
    if out_path.exists():
        return system, replica_dir, True, "exists"
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    try:
        extract_run(Path(replica_dir), Path(out_dir), max_frames=None,
                     progress=False)
        return system, replica_dir, True, "ok"
    except Exception as e:
        return system, replica_dir, False, f"{type(e).__name__}: {e}"


def main() -> int:
    n_jobs = int(os.environ.get("N_JOBS", "8"))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    tasks: list[tuple[str, str, str]] = []
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            print(f"WARN: skipping malformed line: {line}", file=sys.stderr)
            continue
        tasks.append((parts[0], parts[1], parts[2]))

    if not tasks:
        print("No tasks to run.")
        return 0

    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║  bundle_for_senior/src/extract_parallel.py                        ║
║  Parallel extract of chain_coords across replicas                  ║
╚════════════════════════════════════════════════════════════════════╝
   tasks  : {len(tasks)}
   n_jobs : {n_jobs}
""")
    n_ok = 0
    n_skip = 0
    n_fail = 0
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        for system, rep, ok, status in ex.map(_do_one, tasks):
            tag = "OK" if ok and status == "ok" else ("SKIP" if ok else "FAIL")
            print(f"  {tag:<4}  {system}  {Path(rep).name}  ({status})", flush=True)
            if status == "exists":
                n_skip += 1
            elif ok:
                n_ok += 1
            else:
                n_fail += 1
    print(f"\nExtract: {n_ok} ok, {n_skip} already done, {n_fail} failed")
    return 0 if n_fail == 0 else 4


if __name__ == "__main__":
    sys.exit(main())

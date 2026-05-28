"""Byte-compare extractor output in `results/extracted/<sys>/` against the
PhD's legacy files in `outputs/<sys>/s001/`.

Skips systems whose legacy file is missing (e.g. K01 lacks
`result_Re_complex.dat` and `binding_vector_*` because they were never
generated under the older analysis pipeline).
"""
from __future__ import annotations
import filecmp
import sys
from pathlib import Path

SYSTEMS = [
    "15_120x120_K100_EPS05",
    "15_120x120_K10_EPS05",
    "22_120x120_K01_EPS05",
]

FILES = [
    "result_Re_complex.dat",
    "binding_vector_final_bound_vectors.tsv",
    "binding_vector_final_unbound_vectors.tsv",
    "bindsites_rxryrz_distribution.tsv",
    "bindsites_angle_distribution.tsv",
    "EC_angle_distributed_bind.tsv",
    "EC_angle_distributed_unbind.tsv",
]

# Files where legacy uses a row ordering for cross-pair bonds we couldn't
# reverse-engineer; the multiset of values is identical, so we also check
# value-set equality and report it separately.
VALUE_SET_OK_FILES = {
    "EC_angle_distributed_bind.tsv",
}


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    rc = 0
    for sys_name in SYSTEMS:
        legacy_dir = root / "outputs" / sys_name / "s001"
        ext_dir = root / "results" / "extracted" / sys_name
        print(f"\n[{sys_name}]")
        for fname in FILES:
            legacy = legacy_dir / fname
            mine = ext_dir / fname
            if not legacy.exists():
                print(f"  {fname:50s}  legacy: MISSING (expected for K01)")
                continue
            if not mine.exists():
                print(f"  {fname:50s}  mine: MISSING")
                rc = 1
                continue
            if filecmp.cmp(mine, legacy, shallow=False):
                print(f"  {fname:50s}  IDENTICAL")
                continue
            # Try value-set comparison (sorted) — useful for files where row
            # ordering for cross-pair bonds is the only difference.
            with open(mine) as f:
                mine_sorted = sorted(f.readlines())
            with open(legacy) as f:
                legacy_sorted = sorted(f.readlines())
            if mine_sorted == legacy_sorted and fname in VALUE_SET_OK_FILES:
                print(f"  {fname:50s}  value-set IDENTICAL (row order differs)")
                continue
            print(f"  {fname:50s}  DIFFERS")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())

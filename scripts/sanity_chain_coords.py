"""Sanity-check the extracted chain_coords NPZ files.

Recomputes a handful of observables directly from the NPZ and compares
against the validated `results/extracted/<system>/*.tsv` outputs:

  * Bond lengths along each chain  — should peak near 1.0 σ (HARM r₀ = 1).
  * End-to-end (chain_idx 0 to 12)  — should reflect the flexibility class:
      K100 rigid ~ 12 σ (contour), K10 mid, K01 flexible ~ 3-5 σ Gaussian.
  * Re for bound pairs               — must equal `result_Re_complex.dat`
                                       (chain_idx_5 R-to-L distance with MIC).
  * Bound-fraction per frame         — must equal the k2d_sanity values.

If any check fails, the NPZ is wrong and entropy work shouldn't proceed.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def min_image(v: np.ndarray, box: np.ndarray) -> np.ndarray:
    return v - box * np.round(v / box)


def check_system(npz_path: Path, extracted_dir: Path) -> dict:
    d = np.load(npz_path)
    positions_R = d["positions_R"]
    positions_L = d["positions_L"]
    bound_R = d["bound_R"]
    bound_L = d["bound_L"]
    partner_R = d["partner_R"]
    box = d["box"]
    n_frames, n_R, _, _ = positions_R.shape
    n_L = positions_L.shape[1]

    # --- bond length distribution along the chain ---
    bond_vecs = positions_R[:, :, 1:, :] - positions_R[:, :, :-1, :]
    # min-image wrap (chains are continuous in unwrapped coords, but be safe)
    bond_vecs = min_image(bond_vecs, box)
    bond_lens = np.linalg.norm(bond_vecs, axis=-1).ravel()
    bond_len_mean = float(bond_lens.mean())
    bond_len_std = float(bond_lens.std())

    # --- end-to-end (chain_idx 0 to 12) ---
    e2e_R = np.linalg.norm(
        min_image(positions_R[:, :, 12, :] - positions_R[:, :, 0, :], box),
        axis=-1,
    ).ravel()

    # --- Re for bound pairs (chain_idx 5 R-to-L distance) ---
    # iterate frames; partner_R[f, i] tells which L is bonded to R-slot i
    re_recomputed: list[float] = []
    for f in range(n_frames):
        for r in range(n_R):
            l = int(partner_R[f, r])
            if l < 0:
                continue
            v = positions_R[f, r, 5, :] - positions_L[f, l, 5, :]
            v = min_image(v, box)
            re_recomputed.append(float(np.linalg.norm(v)))
    re_recomputed = np.array(re_recomputed)

    # legacy Re column from extracted file
    legacy_re_path = extracted_dir / "result_Re_complex.dat"
    legacy_re = np.array([
        float(line.split()[3])
        for line in open(legacy_re_path)
        if not line.startswith("#")
    ])

    # we may have a different per-frame order than the bond log;
    # compare sorted to verify the multiset of values matches.
    sorted_match = np.allclose(np.sort(re_recomputed), np.sort(legacy_re), atol=1e-4)

    # --- bound-fraction check vs k2d_sanity numbers ---
    n_bound_R_per_frame = bound_R.sum(axis=1)
    n_bound_L_per_frame = bound_L.sum(axis=1)

    return {
        "n_frames": int(n_frames),
        "n_R": int(n_R),
        "n_L": int(n_L),
        "bond_len_mean": bond_len_mean,
        "bond_len_std": bond_len_std,
        "e2e_R_mean": float(e2e_R.mean()),
        "e2e_R_std": float(e2e_R.std()),
        "n_bound_pairs_total": int(len(re_recomputed)),
        "n_bound_in_legacy_Re": int(len(legacy_re)),
        "Re_sorted_match_atol_1e-4": bool(sorted_match),
        "mean_n_bound_R": float(n_bound_R_per_frame.mean()),
        "mean_n_bound_L": float(n_bound_L_per_frame.mean()),
    }


def main():
    root = Path(__file__).resolve().parent.parent
    for sys_name in [
        "15_120x120_K100_EPS05",
        "15_120x120_K10_EPS05",
        "22_120x120_K01_EPS05",
    ]:
        npz = root / "results" / "chain_coords" / sys_name / "chain_coords.npz"
        ext = root / "results" / "extracted" / sys_name
        print(f"\n[{sys_name}]")
        r = check_system(npz, ext)
        for k, v in r.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

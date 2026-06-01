"""Parse `mol.psf` to recover bead-type identity and the R/L pair structure.

`mol.psf` and `traj.xyz` do not carry the simulation's real bead types
(`H/T/T1` for lipids and `RH/RT/RE/RB` / `LH/LT/LE/LB` for proteins). The
information is recovered here from the !NBOND list of `mol.psf`:

1. Read !NATOM and !NBOND.
2. Split atoms into connected components (= molecules).
3. Classify each component by size + degree profile:
     - 3 atoms, mutually bonded triangle           -> lipid (H, T, T1)
     - 13 atoms, linear path                       -> protein (one ecto chain)
4. Walk each linear protein from the low-index endpoint and assign bead
   types in the canonical chain order:
       chain_idx  : 0  1  2  3   4   5   6   7   8   9  10  11  12
       receptor   : RT RT RT RH  RE  RE  RE  RE  RE  RE  RE  RE  RB
       ligand     : LT LT LT LH  LE  LE  LE  LE  LE  LE  LE  LE  LB
   The outermost RT/LT (chain idx 0) is the membrane-embedded end; RB/LB
   (chain idx 12) is the binding bead.

Pair convention (verified against `analysis/vertical_distance_to_membrane_complex.py`):
proteins are stored interleaved — component 0 = receptor 0, component 1 =
ligand 0, component 2 = receptor 1, etc. The "protein index" used by the
PhD's legacy output files is `(atom_index - N_lipid_atoms) / 13` — even =
receptor, odd = ligand.

The bead at chain index 5 (the second RE/LE bead from the head) is the
"reference" bead used by the legacy `result_Re_complex.dat` (Re = distance
between chain_idx_5 of R and L) and by `binding_vector_final_*_vectors.tsv`
(binding_vector = pos(chain_idx_5) - pos(RB) of the receptor).
"""

from __future__ import annotations
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

CHAIN_LEN = 13
RH_CHAIN_IDX = 3          # receptor head / anchor junction
REF_CHAIN_IDX = 5         # legacy reference bead (see module docstring)
RB_CHAIN_IDX = 12         # binding bead

R_TYPES = ["RT", "RT", "RT", "RH", "RE", "RE", "RE", "RE", "RE", "RE", "RE", "RE", "RB"]
L_TYPES = ["LT", "LT", "LT", "LH", "LE", "LE", "LE", "LE", "LE", "LE", "LE", "LE", "LB"]


@dataclass
class Topology:
    n_atoms: int
    bead_type: list[str]           # per atom
    molecule_id: list[int]         # per atom
    molecule_kind: list[str]       # per molecule: 'lipid' | 'receptor' | 'ligand'
    lipid_atoms: list[list[int]] = field(default_factory=list)
    # interleaved protein storage: receptor i and ligand i are paired
    receptor_chain: list[list[int]] = field(default_factory=list)
    ligand_chain: list[list[int]] = field(default_factory=list)

    @property
    def n_lipids(self) -> int:     return len(self.lipid_atoms)
    @property
    def n_receptors(self) -> int:  return len(self.receptor_chain)
    @property
    def n_ligands(self) -> int:    return len(self.ligand_chain)
    @property
    def n_pairs(self) -> int:      return len(self.receptor_chain)

    # convenience indices for the extractors
    def rh(self, i: int) -> int:   return self.receptor_chain[i][RH_CHAIN_IDX]
    def rb(self, i: int) -> int:   return self.receptor_chain[i][RB_CHAIN_IDX]
    def rref(self, i: int) -> int: return self.receptor_chain[i][REF_CHAIN_IDX]
    def lh(self, i: int) -> int:   return self.ligand_chain[i][RH_CHAIN_IDX]
    def lb(self, i: int) -> int:   return self.ligand_chain[i][RB_CHAIN_IDX]
    def lref(self, i: int) -> int: return self.ligand_chain[i][REF_CHAIN_IDX]

    def protein_index(self, kind: str, i: int) -> int:
        """Return the legacy protein index (atom-based): receptor i -> 2i,
        ligand i -> 2i+1."""
        if kind == "receptor":
            return 2 * i
        if kind == "ligand":
            return 2 * i + 1
        raise ValueError(kind)


def parse_psf(psf_path: Path) -> tuple[int, list[tuple[int, int]]]:
    """Return (n_atoms, 1-indexed bond list)."""
    with open(psf_path) as f:
        lines = f.readlines()
    n_atoms = None
    n_bonds = None
    bonds: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "!NATOM" in line:
            n_atoms = int(line.split()[0])
            i += 1 + n_atoms
            continue
        if "!NBOND" in line:
            n_bonds = int(line.split()[0])
            i += 1
            while len(bonds) < n_bonds and i < len(lines):
                toks = lines[i].split()
                for k in range(0, len(toks), 2):
                    if k + 1 < len(toks):
                        bonds.append((int(toks[k]), int(toks[k + 1])))
                i += 1
            break
        i += 1
    if n_atoms is None or n_bonds is None:
        raise RuntimeError(f"could not parse NATOM/NBOND from {psf_path}")
    if len(bonds) != n_bonds:
        raise RuntimeError(f"parsed {len(bonds)} bonds, header claims {n_bonds}")
    return n_atoms, bonds


def _connected_components(n_atoms: int, adj: dict[int, list[int]]) -> list[list[int]]:
    seen = [False] * n_atoms
    components: list[list[int]] = []
    for start in range(n_atoms):
        if seen[start]:
            continue
        stack = [start]
        seen[start] = True
        comp = []
        while stack:
            v = stack.pop()
            comp.append(v)
            for u in adj[v]:
                if not seen[u]:
                    seen[u] = True
                    stack.append(u)
        components.append(sorted(comp))
    return components


def _walk_linear_chain(comp: list[int], adj: dict[int, list[int]]) -> list[int] | None:
    """If `comp` is a linear path, return atom indices walked from the
    lowest-index endpoint to the highest. Otherwise None."""
    ends = [a for a in comp if len(adj[a]) == 1]
    if len(ends) != 2:
        return None
    start, end = min(ends), max(ends)
    ordered = [start]
    prev = -1
    cur = start
    while cur != end:
        nxt = [u for u in adj[cur] if u != prev]
        if len(nxt) != 1:
            return None
        prev, cur = cur, nxt[0]
        ordered.append(cur)
    if len(ordered) != len(comp):
        return None
    return ordered


def build_topology(psf_path: Path) -> Topology:
    n_atoms, bonds = parse_psf(psf_path)
    adj: dict[int, list[int]] = defaultdict(list)
    for a, b in bonds:
        adj[a - 1].append(b - 1)
        adj[b - 1].append(a - 1)

    components = _connected_components(n_atoms, adj)

    bead_type = ["?"] * n_atoms
    molecule_id = [-1] * n_atoms
    molecule_kind: list[str] = []
    lipid_atoms: list[list[int]] = []
    protein_chains_in_order: list[list[int]] = []   # by component order

    for comp in components:
        if len(comp) == 3:
            a, b, c = comp
            if b in adj[a] and c in adj[a] and c in adj[b]:
                mid = len(molecule_kind)
                bead_type[a], bead_type[b], bead_type[c] = "H", "T", "T1"
                molecule_id[a] = molecule_id[b] = molecule_id[c] = mid
                lipid_atoms.append([a, b, c])
                molecule_kind.append("lipid")
                continue
        if len(comp) == CHAIN_LEN:
            ordered = _walk_linear_chain(comp, adj)
            if ordered is not None:
                protein_chains_in_order.append(ordered)
                continue
        raise RuntimeError(
            f"unrecognised molecule of size {len(comp)} starting at atom {comp[0]}"
        )

    # interleave: even-indexed component (among proteins) = receptor, odd = ligand
    if len(protein_chains_in_order) % 2 != 0:
        raise RuntimeError(
            f"odd protein count ({len(protein_chains_in_order)}) — cannot pair R/L"
        )
    receptor_chain: list[list[int]] = []
    ligand_chain: list[list[int]] = []
    for k, chain in enumerate(protein_chains_in_order):
        if k % 2 == 0:
            mid = len(molecule_kind)
            for atom, t in zip(chain, R_TYPES):
                bead_type[atom] = t
                molecule_id[atom] = mid
            receptor_chain.append(chain)
            molecule_kind.append("receptor")
        else:
            mid = len(molecule_kind)
            for atom, t in zip(chain, L_TYPES):
                bead_type[atom] = t
                molecule_id[atom] = mid
            ligand_chain.append(chain)
            molecule_kind.append("ligand")

    return Topology(
        n_atoms=n_atoms,
        bead_type=bead_type,
        molecule_id=molecule_id,
        molecule_kind=molecule_kind,
        lipid_atoms=lipid_atoms,
        receptor_chain=receptor_chain,
        ligand_chain=ligand_chain,
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <path/to/mol.psf>", file=sys.stderr)
        return 2
    topo = build_topology(Path(argv[1]))
    print(f"n_atoms        = {topo.n_atoms}")
    print(f"n_lipids       = {topo.n_lipids}")
    print(f"n_R-L pairs    = {topo.n_pairs}")
    if topo.n_pairs:
        print(f"receptor 0: atoms {topo.receptor_chain[0][0]}..{topo.receptor_chain[0][-1]}")
        print(f"  RH={topo.rh(0)}  ref(chain_idx 5)={topo.rref(0)}  RB={topo.rb(0)}")
        print(f"ligand 0:   atoms {topo.ligand_chain[0][0]}..{topo.ligand_chain[0][-1]}")
        print(f"  LH={topo.lh(0)}  ref(chain_idx 5)={topo.lref(0)}  LB={topo.lb(0)}")
        # sanity: protein indices in the legacy (atom-based) numbering
        print(f"legacy protein_index: receptor 0 -> {topo.protein_index('receptor', 0)}, "
              f"ligand 0 -> {topo.protein_index('ligand', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

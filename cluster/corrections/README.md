# corrections/ — patches to upstream MD setup

Every file we ship here must be paired with a `.diff` showing the *minimum*
deviation from the upstream version in `ref/`. This makes it easy to:

- audit "what did we change physically?"
- merge upstream fixes (rare, but the principle stands)
- explain the modification in the essay's methods section

## Conventions

For each derived MD script in `cluster/scripts/`, we produce:

- `<script>.diff` — `diff -u ../../ref/<original>.py <script>.py`
- One paragraph in this README per diff, explaining the *physical* reason

## Current entries

### `nvt-md-constrained-h.diff` (TODO, depends on cluster pygamd API)

Two physical changes vs `ref/nvt-md.py`:

1. **z-tether harmonic constraint on membrane CoMs.** Holds each leaflet's
   center-of-mass z coordinate at ±h/2 with stiffness k_z = 100 ε/σ². Without
   this, the equilibrium fluctuation in membrane separation re-introduces
   the unbound-sampling bias diagnosed in §4.5 of stage_essay.

2. **R-L binding interaction disabled.** Sets the LJ ε between binding beads
   (RB / LB pair) to 0 in the nonbonded table. This produces "pure unbound"
   chain statistics at fixed h — the unique signal we need for K2D(l) and
   chain-response analysis.

Other force-field terms (FENE bonds, angle potentials, lipid LJ) are
unchanged from `ref/nvt-md.py`.

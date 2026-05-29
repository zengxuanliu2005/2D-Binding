# JOURNEY.md — what was tried, what worked, what's open

This file is a chronological walkthrough of every approach we tried to
close the K2D,max log-ratio budget (3.56 / 2.68 / 0.90 kBT for
flex−rigid / semi−rigid / semi−flex), the closure numbers each one
gave, why it succeeded or failed, and where the relevant code and
results live in this repo. It's written so that someone (you, or
your AI coding agent) can pick up the work cleanly without re-tracing
the dead ends.

If you just want the current result: skip to **§8 Raw tether partition
estimate (current main candidate)**. For the earlier four-term baseline,
see **§7 The PhD's S1–S23 four-term decomposition**.

---

## 0. The question

The simulation gives K2D,max = 12 705 / 875 / 362 nm² for rigid /
semi / flex. Log-ratios:

    ln(K2D,rigid / K2D,flex)  = 3.56 kBT     (flex − rigid)
    ln(K2D,rigid / K2D,semi)  = 2.68 kBT     (semi − rigid)
    ln(K2D,semi  / K2D,flex)  = 0.89 kBT     (sign: semi has lower ΔF than flex)

The scientific goal is to explain these three numbers from first
principles — to decompose ΔF_bind into named terms (translational,
rotational, conformational, end-volume) such that the four terms,
each computable from simulation, sum to the right value across all
three pair comparisons.

Prior attempts (slides 21 and 24 of `2D-binding-MD.pdf`) gave:

* Gaussian-chain analytic: flex−rigid 5.2 kBT (146 % — overshoots)
* Marko–Siggia analytic: flex−rigid 3.0 kBT (84 % — undershoots),
  semi−rigid only 1.45 kBT (54 %), semi−flex sign-flipped

So neither prior analytic decomposition closed. Our task was to fix
that.

---

## 1. Session 0 — Reconnaissance (orientation)

Read CLAUDE.md, PLAN.md, README.md, the four reference papers in
`ref/`, `nvt-md.py`. Verified the unit system (σ = 1 nm, kBT = 1.1 ε,
binding well = −13.4 kBT, K_bind = 15 /rad², θ₀ = 10°). Inventoried
the per-system observables under `outputs/<sys>/s001/` and noted that
K01 (flex) was processed ~2 years earlier with fewer extractors, so
the analysis pipeline needed harmonising across all three systems
before any closure attempt.

* commit: `b5b3319 chore: scaffold scripts/ and results/; add observables inventory`
* file: `results/observables_inventory.md`

---

## 2. Sessions 1A & 1B — Harmonised extractors (precondition for everything that follows)

Wrote per-trajectory observable extractors from scratch and
**byte-validated** them against the PhD's existing K100 and K10 .tsv
outputs. This step was necessary because nothing downstream is
trustworthy until we know our extraction agrees with the PhD's
ground truth on the systems where she has it.

What was extracted (all five files now match the PhD's bit-for-bit):

* `result_Re_complex.dat` — per-bond Re between chain-mid bead 5 of R
  and L
* `binding_vector_final_{bound,unbound}_vectors.tsv` — per-protein
  orientation vectors
* `bindsites_rxryrz_distribution.tsv`,
  `bindsites_angle_distribution.tsv` — RB-LB vectors and binding
  angles
* `EC_angle_distributed_{bind,unbind}.tsv` — five ecto-domain
  deviations from 180°, per chain

The pipeline (`scripts/extract_complex.py`,
`scripts/extract_bindsites_ecangle.py`) discovered several
non-obvious conventions:

* Protein indexing is interleaved (R_proto = 2i, L_proto = 2i+1).
* About 25 % of bonds in K100 are cross-pair (R_i bound to L_j with
  j ≠ i).
* The legacy bond file logs angle-partner atoms (chain idx 11), not
  the binding bead (chain idx 12).
* All vector quantities need per-chain PBC unwrap.
* For ligand vectors, the z-component is flipped in the legacy file
  so both R and L vectors share the +z hemisphere.

K01 was processed through the same code path → harmonised
observables for the first time, in `results/extracted/<sys>/`.

* commits: `d1ed35c feat(extract): harmonized Re_complex + binding_vector extractor`,
  `6ec74c7 feat(extract): bindsites_rxryrz, bindsites_angle, EC_angle extractors`
* validation: `python scripts/validate_against_legacy.py`

---

## 3. Session 2 — Phase 2 foundations (K2D sanity + chain coords)

Two pieces:

**(a)** K2D sanity check (`scripts/k2d_sanity.py` →
`results/k2d_sanity.md`). Reconstructed K2D = N_bound · A / (N_R_free
· N_L_free) from `bond_state.tsv`. K100 reaches ~96 % of the published
K2D,max under per-frame averaging (52 % under ratio-of-averages);
ordering rigid > semi > flex is preserved. This validates that our
bond_state data faithfully reflects the simulation.

**(b)** Chain-coords extractor (`scripts/extract_chain_coords.py` →
`results/chain_coords/<sys>/chain_coords.npz`). One pass over each
trajectory writes a small (~few MB) npz containing the 13 bead
positions of every R and L chain per frame, the per-frame bound mask,
and partner indices. **Crucial wrinkle:** about 3 % of chains in
`traj.xyz` straddle a PBC boundary, producing an apparent 120-σ "bond"
inside a single chain; the extractor detects this and shifts trailing
beads to restore continuity. Sanity-checked by re-computing Re from
the npz and matching `result_Re_complex.dat` multisets at atol=1e-4.

A physical finding from this data: **both R and L are equally flexible
within each system.** The `ref/nvt-md.py` snapshot has receptor K=100,
ligand K=10 (so it would predict asymmetric R/L), but the actual K10
data shows R-E2E = 11.42 σ ≈ L-E2E = 11.43 σ. The K10 production run
used K=10 for both ecto domains, not just the ligand. CLAUDE.md's
phrasing "*E-*E-*E angles" (both sides) was correct; the ref/nvt-md.py
snapshot is misleading.

* commit: `c618a2a feat(phase2): K2D sanity check + per-chain unwrapped coordinate extractor`

---

## 4. Session 2.5 — Schlitter conformational entropy (first cut, single term only)

`scripts/conf_entropy.py`. Schlitter quasi-harmonic on BAT internal
coordinates (12 bonds + 11 angles + 10 torsions = 33 DOF) gives a
**per-chain** entropy difference S_bound − S_unbound. Closure (single
term, conformational only):

    flex − rigid: +0.82 kBT  (vs target +3.56, 23 % closed)
    semi − rigid: +0.45 kBT  (vs target +2.68, 17 % closed)
    semi − flex : +0.37 kBT  (vs target +0.90, 41 % closed)

Correct signs everywhere. Result confirmed CLAUDE.md's prediction that
the configurational entropy is one piece of a larger budget, not the
whole story.

* commit: `c7b2e77 feat(entropy): Schlitter quasi-harmonic conformational entropy prototype`
* tag: `phase2-conf-entropy-prototype`

---

## 5. Sessions 3, 4 & 5 — The Numata MI chain-rule decomposition (didn't close)

This was the wrong framework, but it took three sessions to figure
that out. Documenting the dead end carefully because it's instructive.

**Idea:** define five per-protein feature blocks (axis_ecto 2, ext_z
1, bonds 12, angles 11, torsions 10) and decompose the binding entropy
ΔS = S_bound(R,L joint) − S_unbound(R) − S_unbound(L) via the chain
rule

    H(axis,inner,end) = H(axis) + H(inner|axis) + H(end|axis,inner)

so the per-block ΔS sum to the total ΔS by construction. Five terms,
five entropy estimates from the same data.

**Three attempts**:

| session | estimator | flex−rigid | semi−rigid | semi−flex | signs |
|---|---|---|---|---|---|
| 3 | Schlitter throughout | +1.14 | +0.58 | −0.56 | ✓ |
| 4 (cyclic) | Schlitter + cyclic kNN for torsions | +0.11 | +0.31 | +0.20 | ✗ semi−flex |
| 5 (+ ΔU) | session-4 + chain potential ΔU added | +0.73 | +0.21 | −0.52 | ✓ |

All gave **at most 32 % closure on flex−rigid** with correct signs in
the best case. Session 4's first cut after the feature redesign
flipped the semi−flex sign, but that was a code path issue that
session 5 fixed.

**Why it didn't close (the actual scientific reason):** the chain-rule
MI computes the *coupling* between R and L's degrees of freedom when
bound, but the K2D,max ratio is dominated by the *absolute phase-space
difference* across systems. Specifically, the K01 free chain has a
much larger orientational + conformational phase space than K100 —
that *ratio* is what enters K2D,max via Z_R(K01)/Z_R(K100). The
chain-rule subtraction H_bound − H_R − H_L cancels most of this
information out because BOTH the bound and unbound K01 chain are
"floppy" with similar marginal entropy; the bound-vs-unbound
*difference* per chain is similar across systems even when the
absolute entropies differ wildly. The MI captures coupling, but the
K2D ratio asks for absolute phase volumes.

This was a category-of-quantity mistake, not an implementation bug.
Sessions 3–5 stayed on disk as the historical record of which
framework is wrong for this problem.

* commits: `56e18ba feat(entropy): Numata MI chain-rule decomposition + illustrative figures`,
  `29d9ead feat(entropy): chain potential energy + cyclic-torsion + full ΔΔF decomposition`
* outputs: `results/mi_decomposition.md`, `results/mi_decomposition_results.npz`,
  `results/full_decomposition.md`, `results/full_decomposition.npz`,
  `results/figures/closure_full.png`
* tag: `phase2-conf-entropy-prototype` (covers the Schlitter-only first cut)
* The four illustrative figures from session 3 are still in
  `results/figures/` (`axis_angle_distributions.png`,
  `e2e_distributions.png`, `binding_bead_z.png`, `closure_bars.png`)
  and remain useful — they show qualitatively where the rigid-vs-flex
  K2D difference comes from (the K01 chain's e2e shifts from ~9 σ
  unbound to ~10.5 σ bound, while K100 sits at ~12.6 σ in both
  states). That intuition is independent of the failed MI framework.

---

## 6. The reframe — partition-function ratios, not MI

After session 5 the user pushed back: "Prof Hu has analysed the
rigid case successfully — there must be a way." That reframed the
problem. Hu's PNAS 2013 and Xu's JCP 2015 don't use a chain-rule MI
*at all*; they use **partition-function ratios** for K2D, with
explicit terms for the orientation phase volume Ω, the chain spring
constants, and the membrane-separation distribution P(l). The PhD
also has a half-finished SI write-up at `ref/adhesion protein.pdf`
(Eqs. S1–S23) that decomposes ΔF directly into four named terms
matching slides 21 and 24.

Reading the SI carefully, the four terms are:

    F_t     (S1, S3)    translational      ln(σb²) − 1
    F_c     (S4)        conformational     1.5 · (D/Re)²
    F_bond  (S17–S19)   end-volume         −ln(b²/A) or −ln(b³/(A·L))
    F_rot   (S22–S23)   rotational         −ln[ω_RL / (ω_R · ω_L)]

This was the first framework that worked numerically. It remains the
baseline, but it is not the cleanest final theory because `F_c`,
`F_bond`, and `F_rot` are low-dimensional views of overlapping tether
phase space.

---

## 7. The PhD's S1–S23 four-term decomposition (baseline closure)

`scripts/phd_formula.py` + `phd_inputs.py` + `phd_closure.py`
implement S1, S4, S17–S19, S22–S23 directly. Inputs come from
`results/chain_coords/<sys>/chain_coords.npz`:

* `R_e` — free-chain end-to-end ⟨|chain[12] − chain[3]|⟩ over unbound R and L
* `D`   — bound-chain vertical reach ⟨chain[12].z − chain[3].z⟩ (ligand z flipped)
* `L`   — R_max − D, vertical range available to the binding bead
* `ω_R, ω_L, ω_RL` — solid-angle phase volumes of the chain axis on
  S² (free) and S²×S² (bound joint), histogram-estimated

**Result (commit `041cb0e` on `main`, tag `phase2-phd-closure-attempt`):**

| pair | predicted | target | gap | closed |
|---|---|---|---|---|
| flex − rigid | +3.96 | +3.56 | +0.40 | **111 %** |
| semi − rigid | +2.69 | +2.68 | +0.01 | **100 %** |
| semi − flex  | −1.27 | −0.90 | −0.37 | **141 %** |

All three signs correct. All gaps within 0.4 kBT (the plan's
acceptance threshold was 1 kBT). **Semi − rigid lands at exactly
100 %** — the strongest single piece of evidence that the framework
is right, because this is the case where the chain bending sits in
S4's Gaussian-stretch regime and Hu's analytical theory is known to
be exact.

### Three explicit corrections to the PhD's writeup that were required

These are the things her writeup either left ambiguous or got wrong;
all three were necessary to close the budget:

1. **F_bond drops the `n_b` factor inside the log.** Her S17 reads
   `f·V = −n_b · ln(n_b · v/V) + n_b`. Dividing by n_b gives a
   per-pair contribution `−ln(n_b · v/V) + 1`. Keeping `n_b` inside
   the log is circular: n_b is the equilibrium *output* (how many
   bonds form) and we're trying to *predict* K2D = n_b · A /
   (N_R · N_L). Drop it. What remains is the geometric capture
   term −ln(b²/A) for rigid (S18) and −ln(b³/(A·L)) for semi/flex
   (S19) — exactly the structure that gives S20's clean result
   ΔF_bond = ln(L/b).

2. **F_c is per-pair, not doubled.** Her S3 per-system Fc values
   (1.69 / 1.74 / 3.4 kBT for rigid / semi / flex) use single-chain
   D and R_e. The slides occasionally multiplied by 2 (one stretch
   each for R and L), which double-counts. The membrane gap is
   bridged by *the complex*, not by R alone + L alone separately
   stretched.

3. **F_rot uses the right manifold.** Her S22–S23 references
   `ω_RL / (ω_R · ω_L)` on S² but doesn't fully specify how to
   estimate ω from simulation. Earlier sessions tried Schlitter on
   the in-plane disk `(v_x, v_y)`, which lives on the wrong manifold
   (edge singularity at the unit circle). The correct approach is
   histogram differential entropy on `(cos θ, φ)` for the marginals
   (16 × 16 bins on S²) and on the 4D joint `S² × S²` for the bound
   pair (6⁴ bins). Bin sensitivity is real but bounded.

### Per-system inputs (verified against the closure)

| label | regime | n_b/frame | R_e (σ) | D (σ) | L (σ) | F_t | F_c | F_bond | F_rot |
|---|---|---|---|---|---|---|---|---|---|
| rigid | 2D | 10.28 | 9.48 | 9.15 | 2.85 | −7.87 | +1.40 |  +9.58 | −1.06 |
| semi  | 3D |  3.92 | 8.45 | 7.96 | 4.04 | −7.87 | +1.33 | +10.97 | +0.30 |
| flex  | 3D |  1.83 | 6.17 | 6.62 | 5.39 | −7.48 | +1.73 | +11.26 | +0.50 |

* commit: `70a09c5 feat(theory): PhD's S1-S23 four-term ΔF decomposition closes the budget` → merged via `041cb0e`
* outputs: `results/phd_closure.md` (curated narrative),
  `results/phd_closure_data.md` (auto-generated tables),
  `results/phd_closure.npz`, `results/figures/closure_phd.png`
* tag: `phase2-phd-closure-attempt`
* reproduce: `conda activate phys && python scripts/phd_closure.py && python scripts/plot_phd_closure.py`

---

## 8. Raw tether partition estimate (current main candidate)

The four-term closure raised a conceptual problem: `F_c`, `F_bond`, and
`F_rot` all depend on the same endpoint/orientation phase space. Adding
them as independent terms can double-count parts of the tether restriction.
The references downloaded into `ref/potential/` point to a cleaner
polymer-tether partition-function route:

    K2D_eff(h) = K0 * A * q_t(LR; h) / [q_t(L; h) * q_t(R; h)]

For this project the empirical equivalent is:

    K2D_eff(h) proportional to K0 * P_tether(capture + angle gate | h)

where the capture and angle constraints are evaluated once as a joint gate.
The microscopic `K0` cancels in cross-system ratios, so the comparison uses
`max_h K2D_eff(h)` as the `K2D,max` proxy.

`scripts/raw_tether_partition_k2d.py` implements a raw-data prototype:

* Reads `outputs/<system>/s001/traj.xyz` directly, not
  `results/chain_coords/<sys>/chain_coords.npz`.
* Streams bead 3/11/12 for every protein.
* Excludes chains bound in the same raw frame using
  `num_bonds_for_xyz_frames.dat`.
* Samples unbound R × L endpoint pairs across trial membrane separations `h`.
* Applies RB-LB radial binding and binding-angle compatibility as one
  Boltzmann kernel, with a hard-gate sanity check.

**Result (branch `analysis/raw-tether-k2d`):**

| pair | raw soft | target | gap | closed |
|---|---:|---:|---:|---:|
| flex − rigid | +3.339 | +3.56 | −0.221 | 94 % |
| semi − rigid | +2.440 | +2.68 | −0.240 | 91 % |
| semi − flex  | −0.899 | −0.90 | +0.001 | 100 % |

Hard-gate sanity check:

| pair | raw hard | target | gap | closed |
|---|---:|---:|---:|---:|
| flex − rigid | +3.392 | +3.56 | −0.168 | 95 % |
| semi − rigid | +2.463 | +2.68 | −0.217 | 92 % |
| semi − flex  | −0.929 | −0.90 | −0.029 | 103 % |

The z-reach-only variant closes only 10–13 %, so endpoint height alone
is not the mechanism. The important object is the joint probability that
the two tethered binding sites land in the radial capture region with
compatible binding angles.

This is now the preferred main line:

* It improves the maximum gap from the four-term baseline's 0.40 kBT to
  0.24 kBT for the soft kernel.
* It gives the correct signs for all three pair comparisons.
* It nearly exactly hits semi − flex, the hardest sign-sensitive contrast.
* It avoids assigning overlapping phase-space restrictions to independent
  additive terms.

The result is still an s001-only prototype. The next required validation is
bootstrap / multi-seed uncertainty, especially for the flexible-system tail
probability.

* commits: `88f250c docs: review polymer-tether binding framework`,
  `478fcab feat: raw tether partition K2D prototype`,
  `7150e5d figures: add raw tether story visuals`
* outputs: `results/raw_tether_partition.md`,
  `results/raw_tether_partition.npz`,
  `results/figures/raw_tether_mechanism.png`,
  `results/figures/raw_vs_phd_closure.png`,
  `results/figures/raw_tether_pipeline.png`
* reproduce: `conda activate phys && python scripts/raw_tether_partition_k2d.py`
* figures: `conda activate phys && python scripts/plot_raw_tether_story.py`

---

## 9. Cluster pipeline — packaged, not run

The s001-only raw partition result closes the budget within prototype
acceptance. A multi-replica run on the cluster would test whether the
endpoint/angle tail probabilities, especially for K01, stay stable across
seeds. It would also tighten the old four-term `F_rot` histogram baseline
if that comparison is kept in the write-up.

The packaging is on branch `analysis/cluster-pipeline`:

* `cluster/extract.slurm` + `cluster/extract_all.sh` — loops over
  (system, replica) tuples, runs `extract_chain_coords.py` for each
  replica found under `/mnt/nfs/ugstu/liuzx/2d_binding_MD/<sys>/s*`.
  Incremental skip-if-done, matches the PhD's auto-job idiom and
  her cluster's SBATCH style (`-J / -o %J.log / -p gpu / -w n01 /
  -N 1 / -c 1`).
* `cluster/closure.slurm` + `cluster/closure_all.sh` — combines the
  per-replica npz files via `combine_chain_coords.py` and runs the
  closure pipeline on the merged data.
* `cluster/README.md` — full documentation aimed at the PhD: physics
  → code mapping, SBATCH conventions matching her template, what to
  send back.

**The PhD declined to run this**, on the grounds that her existing
scripts already process the trajectories and the multi-replica result
wouldn't change her conclusion qualitatively. That's a defensible
position — the s001 closure already passes acceptance. The cluster
package is left intact on the branch for whoever wants to revisit.

* branch: `analysis/cluster-pipeline` (head `4d21b35`)
* not merged to main; tag `phase2-phd-closure-attempt` on main points
  at the closure as it stands

---

## 10. Methodological refinements that remain open

These are not blockers for the s001 prototype — they're captured here so the
next person doesn't reinvent them.

### 10.1 Raw partition uncertainty: flexible-tail sampling

The current raw partition estimate uses 500000 random R/L pairs per system
and 32 bond-vector samples per pair and membrane separation. That is enough
to show the method works, but the flexible system is controlled by extended
tail conformations. The next estimator step is bootstrap / convergence:
resample raw frames, sweep pair count, sweep bond-vector samples, and report
point ± σ for `max_h K2D_eff(h)` ratios.

### 10.2 Why F_rot was the limiting term in the four-term baseline

The four-term residual 0.4 kBT on flex−rigid and semi−flex sits in F_rot.
F_t cancels by construction (all three systems have ~equal protein
density). F_c uses single-chain D and R_e — direct measurements with
sub-percent precision. F_bond is closed-form `ln(L/b)` and the L
values are direct ext_z averages. F_rot is the only term that involves
an empirical density estimator (histogram on S² × S²) and shows
visible bin sensitivity when you sweep `(n_bins_marg, n_bins_joint)`
from (8, 4) to (20, 6) — ΔΔF_rot shifts by up to 0.5 kBT across that
range.

### 10.3 Parametric replacement: Bingham or normalizing flow

The natural fix is to replace the histogram with a parametric density
on S². Two candidates:

* **Bingham distribution**: `f(u) ∝ exp(u^T·A·u)`, two parameters per
  axis, analytical normaliser via confluent hypergeometric ¹F₁. For
  the bound joint use a Bingham with explicit coupling parameter.
  Bias-variance trade-off: ~1000 bin densities → 2–4 fit parameters
  per system. Closed-form ω.
* **Normalizing flow on S² / S² × S²**: more flexible parametric
  family, learns the empirical distribution exactly while keeping the
  Jacobian (hence the entropy) analytically tractable. Probably
  overkill given the closure already passes; useful as a methods-paper
  appendix.

Neither requires more MD; both run on the existing `chain_coords.npz`.
Estimated complexity: Bingham ~150 lines, flow ~300 lines + GPU
optional.

### 10.4 Why CNN is the wrong shape for this problem

Briefly considered (and discarded): CNN feeding chain coordinates →
ΔF. Three reasons it doesn't fit:

* Our chain is 13 beads — too short for convolutions to compose
  hierarchical features.
* No translation invariance to exploit — bead 0 (anchor) and bead 12
  (binding bead) are physically distinct roles.
* Output is a scalar ΔF; we have ≤ 2 000 (input, output) pairs per
  system. CNN needs orders of magnitude more.

Normalizing flows for density estimation on S² are the relevant ML
tool, not CNN.

### 10.5 The DFT analogy (worth labelling honestly)

User pointed out the four-term decomposition has the same structural
shape as DFT's `T_s + V_ext + J + E_xc` split — three analytical
terms + one hard remainder. The analogy is **structural only**: real
DFT functionals operate on 3-D electron density ρ(r), our F_rot
operates on angular distributions on S². No specific DFT functional
(LDA, GGA, B3LYP, SCAN, ...) can be evaluated on our objects. The
analogy gave us a vocabulary for describing the situation
("F_rot is our exchange-correlation term") but no transferable
implementation. Bingham / flow refinements are borrowed from
*directional statistics*, not DFT.

### 10.6 Bootstrap error bars for the baseline

The four-term baseline numbers are point estimates with no
uncertainty quantification. Resampling frames with replacement,
recomputing the four terms, and reporting σ per term is local
(~minutes) and would let the write-up state the closure as
"+3.96 ± σ kBT vs target +3.56" rather than the point estimate
"111 %". This is secondary to raw-partition bootstrapping, but useful
for a fair baseline comparison.

---

## 11. Suggested next steps (in priority order)

1. **Bootstrap / convergence for the raw tether partition estimate.**
   Resample raw frames and R/L endpoint pairs; sweep random pair count
   and bond-vector samples. Report soft-kernel and hard-gate
   `max_h K2D_eff(h)` ratios as point ± σ.

2. **Phase 4 deliverables** — write-up, slide deck, poster. The
   headline figures are `results/figures/raw_tether_mechanism.png`,
   `results/figures/raw_vs_phd_closure.png`, and
   `results/figures/raw_tether_pipeline.png`. Keep
   `results/figures/closure_phd.png` as the four-term baseline.

3. **(Optional baseline) Bingham fit for F_rot.** Would tighten the 0.4 kBT
   residual on flex−rigid and semi−flex. Not required for the closure
   to stand; useful as a "methods appendix" enhancement.

4. **(Optional) Multi-replica run.** Branch `analysis/cluster-pipeline`
   ready to submit if the decision to skip it reverses.

5. **(Optional) Revisit the receptor/ligand asymmetry question.**
   `ref/nvt-md.py` shows receptor K=100 / ligand K=10 for the K10
   system, but our K10 data shows R and L are equally flexible
   (E2E 11.42 σ for both). Worth confirming with the actual K10 run
   parameters which set the K values.

---

## 12. How to navigate this repo

| file / directory | what's in it |
|---|---|
| `README.md` | one-page status overview |
| `JOURNEY.md` | **this file** — narrative of what was tried |
| `PLAN.md` | live task tracker with phase status |
| `CLAUDE.md` | operational onboarding (units, conventions, git discipline) |
| `ref/` | reference papers (Hu 2013, Xu 2015, Numata 2012, adhesion protein.pdf, nvt-md.py) |
| `scripts/raw_tether_partition_k2d.py` | current raw-data partition estimate |
| `scripts/plot_raw_tether_story.py` | story figures for the raw partition route |
| `scripts/phd_*.py` | four-term baseline closure (S1–S23 framework) |
| `scripts/extract_*.py` | trajectory → harmonised observables |
| `scripts/{conf,mi,decomposition}_*.py` | sessions 2.5 / 3 / 4 / 5 (the closures that didn't work) |
| `results/raw_tether_partition.md` | current raw partition result |
| `results/phd_closure.md` | curated closure write-up |
| `results/figures/raw_*.png` | current story / closure comparison figures |
| `results/figures/closure_phd.png` | four-term baseline figure |
| `results/figures/e2e_distributions.png` | the qualitative-evidence figure |
| `cluster/` | multi-replica SBATCH pipeline (packaged, not run) |
| `outputs/<sys>/s001/` | per-system MD outputs (read-only; git-ignored) |
| `results/extracted/<sys>/` | harmonised observable .tsv files |
| `results/chain_coords/<sys>/chain_coords.npz` | per-system chain coordinates |

For reproducing any of the numbers in this document:

```bash
conda activate phys
python scripts/raw_tether_partition_k2d.py # raw partition table
python scripts/plot_raw_tether_story.py    # raw story figures
python scripts/phd_closure.py            # closure table
python scripts/plot_phd_closure.py       # closure_phd.png
python scripts/k2d_sanity.py             # K2D sanity vs published K2D,max
python scripts/sanity_chain_coords.py    # validate chain_coords.npz
python scripts/validate_against_legacy.py # validate extracted observables
```

The raw partition pass streams raw trajectories and samples random pairs; the
others are sub-second except the validation pass.

---

## 13. Git milestones

```
main after raw-tether merge
            │
            ├── branch: analysis/raw-tether-k2d
            │       raw tether partition prototype + story figures
            ├── tag: phase2-phd-closure-attempt  (the four-term closure)
            ├── tag: phase2-conf-entropy-prototype  (the Schlitter first cut)
            │
            └── branch: analysis/cluster-pipeline (4d21b35)
                    cluster handoff, PhD declined to run

Previous attempts (all merged into main, branches deleted):
    Numata MI chain rule         → results/mi_decomposition.md
    MI + chain potential         → results/full_decomposition.md
    Schlitter conformational     → results/conf_entropy_schlitter.md
    Harmonised observable extractors → results/extracted/
```

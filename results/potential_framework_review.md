# Potential framework review: polymer-tether binding route

Purpose: evaluate the new references in `ref/potential/` as possible
replacements or upgrades for the current `adhesion protein.pdf` four-term
decomposition. The criterion is whether a framework can predict the
`K2D,max` ratios from tether conformational phase space while reducing
double-counting between stretching, capture volume, and orientation terms.

## Bottom line

The most promising route is not to abandon the existing entropy-decomposition
idea, but to rebuild it from the polymer-tether partition-function framework
of Martin/Zhang/Wang.

Use:

```text
K2D_eff(h) = K0 * A * q_t(LR; h) / [q_t(L; h) * q_t(R; h)]
```

or its simulation-estimated equivalent:

```text
K2D_eff(h) proportional to K0 * P_tether(capture + angle gate | h)
```

Then maximize over membrane separation `h` to obtain `K2D,max`. This makes
the core variable a joint endpoint/orientation distribution, not separate
marginals. The current four terms can be retained as an interpretation of
the log of this probability, but should not be treated as independent terms
unless they are written as a conditional-probability chain.

## Paper-by-paper findings

### Martin, Zhang & Wang 2006

File:
`ref/potential/J Polym Sci B Polym Phys - 2006 - Martin - Polymer‐tethered ligand receptor interactions between surfaces.pdf`

Role: single tether on one surface binding to receptors on the other surface.
This is the cleanest statistical-mechanics precursor to our problem.

Key points:

- The central object is the tether partition function at surface separation
  `h`, with and without ligand-receptor binding.
- For a receptor configuration `sigma(r)`, the binding contribution enters as
  the free-end probability on the receptor surface:

  ```text
  Q[sigma, h, eps] = Q0(h) * [1 + (exp(beta eps) - 1)
                              * sum_r P0(r; h) sigma(r)]
  ```

- `P0(r; h)` is the end-point distribution of the free tether on the opposing
  surface. This is exactly the quantity our current `F_c`, `F_bond`, and
  parts of `F_rot` are trying to approximate indirectly.
- The paper distinguishes annealed/mobile receptors from quenched/immobile
  receptors. Our simulation is closer to the mobile/annealed case because
  receptor and ligand proteins diffuse laterally in a membrane before binding.
- Binding is controlled by two competing effects: polymer confinement at small
  membrane separations and tether stretching at large separations. The minimum
  of the interaction free energy sets the preferred separation.
- For low receptor density in the quenched case, binding is limited by receptor
  availability within tether reach. This is less central for our mobile system,
  but useful for understanding finite-density corrections.

Project implication:

- This paper gives the right mathematical shape for a new method:
  replace independent entropy terms by one probability of the binding bead
  reaching a capture region with the correct receptor availability.
- It naturally avoids double-counting because the end-point distribution enters
  once, inside `Q`, instead of being split into separate `F_c` and `F_bond`
  approximations.

### Zhang & Wang 2007

File:
`ref/potential/polymer-tethered-ligand-receptor-interactions-between-surfaces-ii.pdf`

Role: full two-surface thermodynamics with ligands and receptors on both
surfaces. This is the main replacement candidate for `adhesion protein.pdf`.

Key points:

- The paper explicitly derives an effective 2D binding constant containing
  both microscopic ligand-receptor affinity and tether conformational entropy:

  ```text
  K = K0 * A * q_t(LR) / [q_t(L) * q_t(R)]
  ```

- `K0` is the microscopic 3D binding constant of untethered binding groups.
  The `q_t` factors are tether translational/conformational partition
  functions and depend on the membrane separation.
- The effective binding energy can be written as an intrinsic binding term
  plus a tether stretching/confinement term:

  ```text
  eps_eff(h) = eps_0 + Delta eps_tether(h)
  ```

- At small separations, the effective 2D constant approaches the familiar
  `K2D ~ K3D / h` scaling. At large separations, stretching dominates and
  suppresses binding.
- The paper treats several mobility ensembles: immobile, fixed-density mobile,
  and reservoir/open. Our fixed-number membrane simulation is closest to the
  mobile fixed-density case, not the fully open reservoir case.
- The ideal Gaussian-chain model is used for analytic formulas, but the
  structure of the theory does not require Gaussian chains. We can replace
  Green's functions by empirical distributions from MD.

Project implication:

- This is the best theoretical backbone. It gives a clean alternative to
  `F_t + F_c + F_bond + F_rot`:

  ```text
  -ln K2D_eff = -ln K0 - ln A - ln q_t(LR)
                + ln q_t(L) + ln q_t(R)
  ```

- Our current PhD four terms should be reinterpreted as approximations to
  these partition-function ratios. In particular, `F_c`, `F_bond`, and
  `F_rot` are not independent physical observables; they are low-dimensional
  approximations to the same joint tether phase space.

### Jeppesen et al. 2001

File: `ref/potential/science.293.5529.465.pdf`

Role: experimental and simulation evidence that tethered binding is governed
by rare extended conformations, not by mean end-to-end length.

Key points:

- Capture distances are between the average end position and the fully
  stretched contour length.
- Binding efficiency depends strongly on rare extended conformations over the
  experimental or biological waiting time.
- The equilibrium average extension `Re` is not enough to determine binding.
- The relevant object is a tail probability or first-passage/capture
  probability of the tether end reaching the target separation.

Project implication:

- This is a direct warning against relying too heavily on
  `F_c = 1.5 * (D / Re)^2`.
- For flexible K01, the key physical quantity is likely the probability mass in
  the extended tail of the binding-bead distribution, conditioned on angle
  gates, rather than the mean `Re`.
- A new analysis should plot and integrate endpoint tail distributions for
  rigid/semi/flex, not only their means.

### Moore & Kuhl 2006

File: `ref/potential/PIIS0006349506718811.pdf`

Role: connects single-tether binding range to multiple bond formation between
surfaces.

Key points:

- In equilibrium, the single-tether binding probability is approximately a
  logistic function of binding energy minus tether stretching energy:

  ```text
  f(l) = exp[(W - U(l))/kBT] / [1 + exp[(W - U(l))/kBT]]
  ```

- This often becomes a nearly discrete binding range: bind when `l <= lB`,
  do not bind when `l > lB`.
- For multiple bonds, the number of possible bridges follows from how much
  area lies within this binding range.
- The paper focuses on curved surfaces and force spectroscopy, so the geometry
  is not identical to our planar membrane patch. The single-tether probability
  idea is still useful.

Project implication:

- This paper provides a practical reduced model:

  ```text
  P_bind(h) = < logistic[(W - U_eff(endpoint, angle, h))/kBT] >
  ```

- It can act as an intermediate model between the fully empirical
  partition-function estimate and the current analytic four-term estimate.
- It also suggests that the binding well depth and angular gate should enter
  as a probability kernel, not as a separate additive entropy term.

### Bell & Terentjev 2017

File: `ref/potential/kinetics-of-tethered-ligands-binding-to-a-surface-receptor.pdf`

Role: kinetic theory for tethered ligands reaching a target, including
entropic barriers and two-surface bridging.

Key points:

- The mean first passage time is controlled by an entropic activation factor.
  For a distant target, the barrier has the same form as a chain-stretching
  free energy.
- For two surfaces separated by a gap, the binding time depends on both lateral
  displacement and gap.
- The theory is kinetic, not an equilibrium `K2D` theory.

Project implication:

- Use this paper only as a secondary interpretation unless the project later
  needs binding rates.
- It reinforces the same physical message as Jeppesen: target-reaching
  probabilities, not average extension alone, control tethered binding.

## Mapping to the current project

Current `phd_closure` terms:

```text
F_t     = graft-density translational term
F_c     = Gaussian stretching from D / Re
F_bond  = geometric capture volume
F_rot   = orientation phase-volume loss
```

Problem:

- `F_c`, `F_bond`, and `F_rot` are all derived from overlapping aspects of the
  same underlying phase-space distribution: endpoint position, chain extension,
  orientation, and bound R/L correlation.
- Adding them as independent terms risks double-counting, especially for the
  flexible system where endpoint tail probability, vertical reach, and
  orientation are strongly coupled.

Replacement view:

```text
K2D_eff(h) / K0 = integral dX_R dX_L
                 p_R^free(X_R; h) p_L^free(X_L; h)
                 * gate_capture(X_R, X_L; h)
                 * gate_angle(X_R, X_L)
```

where `X` should include at least:

```text
endpoint position relative to anchor: r_end = chain[12] - chain[3]
ecto axis unit vector: u = r_end / |r_end|
binding bead position: chain[12]
anchor/head position: chain[3]
```

This is the empirical analog of `A*q_t(LR)/(q_t(L)*q_t(R))`. It uses the joint
distribution once, so double-counting is avoided.

## Recommended new framework

### Step 1: empirical tether partition-function estimator

For each flexibility class:

1. Load unbound receptor chains and unbound ligand chains from
   `results/chain_coords/<sys>/chain_coords.npz`.
2. Convert each chain to an anchor-frame endpoint/orientation state.
3. Randomly pair receptor and ligand states and place them at a trial membrane
   separation `h`.
4. Sample lateral offsets in the membrane plane.
5. Evaluate one binding kernel:

   ```text
   G = 1 if RB-LB distance <= b_capture and angular gates pass
       0 otherwise
   ```

   or a smooth Boltzmann kernel using the actual directional bond potential
   from `ref/nvt-md.py`.

6. Estimate:

   ```text
   P_gate(h) = mean(G)
   K2D_eff(h) = C * K0 * A * P_gate(h)
   ```

   For cross-flexibility ratios, `C*K0` cancels if the microscopic binding
   chemistry is identical across systems.

7. Sweep `h` and take:

   ```text
   K2D,max ratio = max_h P_gate_Ka(h) / max_h P_gate_Kb(h)
   DeltaDeltaF = -ln[K2D,max_a / K2D,max_b]
   ```

Sign conventions must be aligned with the existing closure table before
writing results.

### Step 2: conditional decomposition for interpretation

After the total probability is estimated, decompose it as a chain of
conditional probabilities:

```text
-ln P_gate
  = -ln P(z reachable)
    -ln P(r_parallel capture | z reachable)
    -ln P(angle gate | z, r_parallel capture)
    -ln P(residual correlation)
```

This keeps the intuitive four-term story but removes overlap. The fourth term
is then a real coupling/residual term, not a duplicated rotation entropy.

### Step 3: compare against existing baseline

The new method should be evaluated against:

```text
target log ratios: flex-rigid +3.56, semi-rigid +2.68, semi-flex -0.90 kBT
current PhD framework: +3.96, +2.69, -1.27 kBT
```

Success criteria:

- Primary: signs correct and all gaps below 1 kBT without using the
  `adhesion protein.pdf` four-term formulas.
- Strong success: flex-rigid and semi-flex residuals improve relative to the
  current about 0.4 kBT gaps.
- Scientific success even if residuals remain: the total comes from one
  well-defined joint probability, so double-counting is removed.

## Data fields needed from existing repo

Already available:

- `positions_R`, `positions_L`
- `bound_R`, `bound_L`
- `partner_R`, `partner_L`
- `box`
- bead indices:
  - `3`: anchor head
  - `12`: binding bead

Likely constants:

- capture length `b = 1.0 sigma`
- box area `A = 120 * 120 sigma^2`
- binding well depth `13.4 kBT`
- angular gate `theta0 = 10 deg`
- angular stiffness `K = 15 / rad^2`

Open choices for the prototype:

- whether to use hard gates first or the full Boltzmann directional-bond
  kernel;
- whether to use only unbound conformations for the free partition function
  or include bound conformations for estimating the bound-state kernel;
- whether to optimize over membrane separation `h` using observed bound
  separation ranges or a wider synthetic sweep.

## Recommendation

Proceed with the empirical partition-function route as the next project step.
It follows the downloaded polymer-tether literature more directly than the
current PhD SI decomposition, retains a clean entropy/free-energy story, and
solves the double-counting issue by replacing parallel additive terms with one
joint probability. The current four-term framework should remain as a useful
low-dimensional interpretation and as a numerical baseline, not as the final
theory.

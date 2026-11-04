# JPC Fit & Novelty Ledger — E1

**Binding rule:** every phase deliverable must map to a row here. If a piece of
work strengthens no row, it is scope creep — cut it. Reviewed at every phase gate.
**Target:** *Journal of Process Control* (Elsevier). Fallback: *Geothermics*
(requires reframing: application-forward, methods compressed — see §4).

## 1. What JPC publishes vs. what E1 supplies

| JPC scope element (from the journal's aims & recent EMPC/soft-sensor output) | E1 element supplying it |
|---|---|
| State/parameter estimation, soft sensing for unmeasured process variables | Hybrid kinetic-core + LightGBM-residual scaling-rate soft sensor (P4) |
| Economic MPC / RTO with hard process constraints | Robust RTO on dose + reinjection-T with per-scenario scaling-rate constraint (P4, per G7 doc) |
| Handling plant–model mismatch and uncertainty | Scenario-envelope robustness (T1 Tiwi vertices) + modifier adaptation; synthetic-plant mismatch evaluation (this build) |
| Rigorous benchmarking | Ablation triple: hybrid vs pure-ML vs pure-physics; controller vs empirical-dosing baseline — becomes Tables 1–2 |
| Novel application domains for established theory | First control-oriented treatment of geothermal silica scaling; PH liquid-dominated archetype |

**Framing law (non-negotiable):** methodology leads, geothermal follows. Title,
abstract, and contributions list are written in estimation/control language;
silica chemistry appears as "a strongly nonlinear (order ≈ 4), induction-delayed,
non-monotonically actuated constraint process" — which is, honestly, a *gift*
of a benchmark problem for EMPC, and should be sold as one.

## 2. Novelty ledger (claim → nearest prior art → the daylight)

| # | Claim | Nearest prior art | Daylight |
|---|---|---|---|
| N1 | Hybrid (physics-core + ML-residual) soft sensor for scaling **rate** | Juhri et al. 2024 SGW (T2): ML with kinetics-as-features | Residual architecture vs feature engineering; journal-tier evaluation; mismatch study; sparse-measurement regime |
| N2 | Closed-loop economic RTO of inhibitor dose + reinjection T with hard scaling-rate constraint | Thermochem/EDC pH-mod practice (T3); Kobayashi 2024 manual reinjection mgmt (T2) | Any *model-based closed loop at all* — practice is static/manual; we quantify the ×101 temperature lever they trade off by hand |
| N3 | Robustness to brine-chemistry uncertainty from a T1 endmember envelope | Marchetti 2009 modifier adaptation (generic) | Domain instantiation with a *data-grounded* uncertainty set + MA for structural kinetic mismatch |
| N4 | Quantified failure of Arrhenius extrapolation at reinjection conditions (×3.0 at 150 °C) as a modeling requirement | RR79 stated it qualitatively | Fitted, figure-ready, and consequential for anyone modeling hot brine lines |
| N4b | Out-of-sample cross-model validation: RR79 peak-rate core vs. Scott 2024 T1 decay data (P5) | neither paper cross-validates the other | Single-curve decay is cleanly **2nd order** on 2024 data (median R²=0.99, order-2 in 100% of 11 near-neutral exps, 23-80 °C), distinct from RR79's 4th-order *peak-rate* law; the RR79-core effective decay constant differs from observed by ~6× (median) — no single transcribed law reproduces independent data, which is N1's real-data justification for a learned residual |
| N5 | Non-monotonic dose response ⇒ dosing is a genuine optimization problem | Gallup 2002 (T1, lab observation) | First to carry it into an optimization formulation |

**Kill-criteria:** if during P4/P5 any row's daylight collapses (e.g., a newly
found paper does hybrid+control for scaling), stop, re-run the gap search, and
re-scope before writing — not after review.

## 3. Reviewer-objection pre-emption (standing list)

1. *"Validation is synthetic."* — Answer built-in: T1-grounded truth envelope,
   parameterized mismatch, ablations, plus van den Heuvel 2018 in-pipe data as
   the real-data anchor in P5. State the in-silico posture in §Limitations first.
2. *"Kinetics are 40+ years old."* — ANSWERED (P5): the RR79 core is validated out-of-sample against Scott et al. 2024 T1 data. Finding: 2024 single-curve decay is 2nd order (vs RR79's 4th-order peak-rate law — different observables, both reported honestly); the two solubility correlations (GA00 2000 vs Scott 2024 endpoints) mutually validate to median 1.05×. The ~6× effective-rate gap between any fixed transcribed law and independent data is exactly what the learned residual absorbs — turning the objection into the motivation.
3. *"Why not a PINN?"* — Hybrid-residual chosen for data scarcity + constraint
   interpretability; cite von Stosch taxonomy; ablation shows pure-ML failure mode.
4. *"Dose–response is assumed."* — Synthetic, Gallup-anchored, perturbed
   per-episode; controller performance reported across perturbations, not at one shape.
5. *"T3 numbers."* — Motivation only; enforced in code (`validate_target`,
   transcription gates); say so in the manuscript.

## 4. Fallback framing (Geothermics) — only if JPC desk-rejects

Invert the lead: brine-management problem first, controller as the tool;
expand PH field context (Fronda, Sugiaman, See); compress EMPC theory to a
paragraph; keep every figure. Decision point: after first JPC decision letter,
not before.

## Changelog
- 2026-07-14 — v1.0 — created at P4 build 1 (synthetic plant).
- 2026-07-14 — v1.1 — P4 build 2 strengthens N1 with two architecture
  elements born from a documented negative result: (a) v1 zero-shot
  cross-plant evaluation FAILED (hybrid lost to both baselines) because
  per-plant mismatch draws are unpredictable ex ante — evaluation redesigned
  to the soft-sensor-correct per-plant temporal protocol (Kadlec) with
  sparse daily labels; (b) LOO-credibility shrinkage λ with decision
  hysteresis: the residual is weighted by its cross-validated out-of-sample
  signal, so the hybrid degrades gracefully to the physics prior as labels
  → few (λ→0), and the transfer experiment shows the same mechanism is the
  deployment safety interlock (a transferred residual with foreign λ
  actively harms). Both are manuscript material: the negative result
  motivates the protocol; the shrinkage is a method contribution.
- 2026-07-15 — v1.2 — P4 build 4 (closed-loop Table 2, 6 plants × 45 d)
  delivers NEGATIVE RESULT #2, strengthening N2/N3: scalar bias-update MA
  achieves +109% uplift but violates the scaling constraint chronically
  (mean 3.8, max 12 days/plant) — an additive correction learned at one
  setpoint does not extrapolate across a mismatch that is multiplicative
  in k(T) and quartic in supersaturation. The hybrid-sensor-in-the-loop
  arm (state-dependent correction) achieves +47% with ~zero violations;
  vertex-robust nominal RTO gives +42% with zero. Design rule adopted from
  the result: feedback may only TIGHTEN the constraint until the sensor
  earns LOO credibility (warmup ε ≥ 0). Manuscript framing: the safety-vs-
  harvest frontier, with naive MA as the demonstrated unsafe baseline and
  the structured hybrid as the proposed safe feedback. G7's "decide MA vs
  alternatives at P5 with numbers" is hereby decided — with numbers.
- 2026-07-15 — v1.3 — Brine-dilution artifact fixed (OU mean reversion;
  stationarity now gated), both control tables rerun. FINAL Table 2
  (benign random mismatch, 6×45 d): nominal +41.7% / 0.17 viol-days;
  scalar-MA +84% / 5.33 viol-days (unsafe even in the benign regime once
  the artifact's free dilution is removed); hybrid +41.4% / 0 viol-days
  on 6/6 plants. Table 2b (single-factor ×6 stress = the P5-measured
  median cross-model gap): nominal 17.2 post-warmup viol-days (vertex
  envelope covers brine, not kinetics); scalar-MA 14.2 ≈ open-loop — the
  mechanism is now precise: an ADDITIVE bias cannot stabilize a
  MULTIPLICATIVE mismatch on a quartic constraint (small absolute error
  when hot, explosive when cold → limit cycle); hybrid(no margin) 2.17
  post-warmup — an 8× reduction, but pre-registered E3 (zero) FAILED:
  a learned constraint operated with no margin breaches on symmetric-
  error days. RESPONSE (design, not tuning): uncertainty-aware back-off
  — the RTO enforces r̂·exp(κ·σ_LOO) ≤ r_max, with σ_LOO the residual's
  own leave-one-out error. Credibility-consistent (few labels → wide σ →
  conservative; data → σ shrinks → harvest returns), benign-regime cost
  ~2% MW, and it completes G7: the sensor supplies both the correction
  and its uncertainty, and the optimizer consumes both. κ=0 retained as
  the Table 2b ablation arm; definitive κ=1 numbers pending the rerun.
- 2026-07-16 — v1.4 — DEFINITIVE two-regime results (all pre-registered
  verdicts + E3'/E5 PASS). Benign (Table 2): hybrid +33.4% / 0 viol-days
  on 6/6 (nominal +41.7%/0.17; MA +84%/5.33). Stress ×6 (Table 2b):
  hybrid(κ=1) +6.2% / 0.50 post-warmup viol-days vs κ=0 2.17 (back-off
  ablation >4×), nominal 17.2, MA 14.2. THE 2×2 IS COMPLETE: the hybrid
  with credibility shrinkage + κσ back-off is the only arm (near-)safe in
  BOTH regimes; the price of that safety is quantified (8 pp benign
  uplift; most stress-regime harvest). Adaptive lever shift observed
  under stress (optimizer substitutes dose for temperature when the
  T-lever becomes risk-expensive). κ joins the P6 sensitivity set.
- 2026-07-16 — v1.5 — P5 CLOSED (build 3: sensor architecture on real T1
  Scott curves, 21 experiments). FINDINGS: (i) wide-range batch-decay
  model error is STATE-DEPENDENCE-dominated (physics rmse_ln ~2.8 ≈ ×16
  typical; a level-only correction ~ties physics); (ii) the state
  correction is UNIDENTIFIABLE from early-clustered labels (label ln s
  spread 0.047 vs 2.61 test span; raw-affine slopes b ∈ [−230, +769],
  median rmse up to 20.5 — kept as the cautionary ablation);
  (iii) the P4 credibility mechanism TRANSFERS: LOO-selected clipped
  slope collapses to scalar when unearned (K≤3) and, at K=5, selects in
  9/21 experiments with median b = −2.50 — independently re-measuring
  the order-2 finding — and wins outright (2.59 vs physics 3.04).
  DESIGN PRINCIPLE for N1 and §Limitations: identifiability precedes
  correction — narrow-operating-window field sensing is level-dominated
  and label-covered (why the field hybrid wins in Tables 1-2); wide-range
  extrapolation demands state-spanning labels. P5 validation stack:
  solubility (endpoints 1.05×), kinetics (order-2, ×6 gap), and sensor
  architecture — all against independent T1 data.
- 2026-07-16 — v1.6 — P6 build 1 (Sobol, N=512 seeded, reproduced
  exactly on the workstation): over the DECLARED uncertainty set
  (kinetic band = measured ×6; solubility band = measured [0.90,1.37];
  scenario bands for flash, dose-response, r_max, economics), the
  drivers are: gross MW / T* / net ← logk_shift (ST 0.41/0.57/0.33) —
  kinetic model-family uncertainty dominates the economics, which IS the
  quantified case for the sensing/adaptation layer; dose* ← d_opt (ST
  0.67) — dosing policy is dose-response-knowledge-driven; feasibility
  constant at 100% — the set never strands the RTO; lever ratio (ln
  space) ← ce_scale (S1 0.44), spread 47×/405×/divergent near
  saturation, k-invariant by construction; 10% of scenarios are
  undersaturated at 150 °C. Manuscript band: gross MW at the robust
  optimum 6.0/11.7/17.6 (q05/q50/q95).
- 2026-07-16 — v1.7 — P6 CLOSED (build 2: economics bands). Every MW/PHP
  headline now carries lo/nom/hi over the declared envelope (η 0.08-0.14,
  4-7 PHP/kWh, 150-600 PHP/kg), computed by REVALUATION of committed
  trajectories with the enabling assumption GATED: decisions verified
  exactly invariant at all 8 economics corners (inhibitor cost share
  < 15% everywhere; sandbox worst 5.4%). Uplift-% and violation counts
  are envelope-invariant by construction — the safety story does not
  depend on economic assumptions. Bands live in results/economics_bands
  .csv (regenerable). P7 (manuscript) opens.
- 2026-07-23 — v1.8 — WERES CLOSURE (last open calibration). Weres/Yee/
  Tsao 1981 transcribed under the T1 protocol from the primary PDF:
  Eq. [3] flux law, [4a-c] fifth-order-to-linear trial function, [5]
  log k_OH = 3.1171 − 4296.6/T, their internal c0. Printed checksums
  reproduce: quoted St triplet 2.15/1.99/1.85 (primary variant = LSQ
  fit through the triplet) and effective Ea 2.94 ≈ printed 3.0 kcal/mol
  (analytic joint validation of both slopes). SOURCE-INTERNAL
  DISCREPANCY documented, not repaired: the typeset [4c] matches its
  own quoted triplet only at 50 °C (gives 2.150/2.068/2.000); both
  variants carried in results/weres_rmax_calibration.csv. THE NUMBER:
  r_max = 0.5 g/t/min ↔ ≈0.31 mm/yr molecular-deposition wall growth
  (lower bound on total scale) at the Table-2 operating point; 0.04–
  1.64 mm/yr across the 90–175 °C constraint-active envelope; Sobol
  r_max band spans it. §6 caveat retired in manuscript + submission
  package; gate now 94 checks / 13 modules.

# Manuscript Skeleton — E1 → Journal of Process Control

**Working title (methodology leads, geothermal follows — framing law):**
"A credibility-weighted hybrid soft sensor and uncertainty-consuming robust
RTO for a hard-constrained scaling process: design, negative results, and
out-of-sample validation on geothermal silica"

Alternates:
- "Safe economic real-time optimization under structural kinetic mismatch:
  a hybrid soft sensor with earned corrections, applied to geothermal
  silica scaling"
- "Identifiability-gated hybrid estimation and back-off RTO for
  quartic-constrained processes: the geothermal silica benchmark"

**Venue:** Journal of Process Control. Fallback: Geothermics (invert lead
per ledger §4; decision only after first JPC letter).

---

## Abstract (draft v0, ~210 words — every number is committed & regenerable)

Scaling processes couple strongly nonlinear kinetics to hard operational
constraints, and their models are structurally wrong in ways that matter:
we measure a ×6 median gap between a classical fitted rate law and
independent modern kinetic data. We present a control architecture that
treats that mismatch as a first-class object: (i) a hybrid soft sensor —
physics core plus a learned residual — whose correction is weighted by its
own leave-one-out credibility, so it degrades gracefully to the prior when
data has not earned it; and (ii) a vertex-robust economic RTO that consumes
both the sensor's correction and its uncertainty as a multiplicative
constraint back-off. On a synthetic geothermal brine-line plant grounded
entirely in primary-literature chemistry, the hybrid sensor reduces
estimation error by 40% versus physics and 48% versus pure ML under
sparse daily labels, and the closed loop is the only tested policy that is
(near-)violation-free in both a benign-mismatch regime (+33% power uplift,
0 violation days) and a ×6 adverse-kinetics stress (0.5 post-warmup
violation days versus 17.2 open-loop). Two pre-registered failures — of
zero-shot residual transfer and of scalar modifier adaptation against
multiplicative mismatch — motivate the design. All kinetic, solubility and
sensor components are validated out-of-sample against an independent 2024
experimental dataset.

---

## Contributions list (maps 1:1 to ledger N-claims)

1. **Credibility-weighted hybrid soft sensor** (N1): parallel physics+ML
   residual with LOO-shrinkage λ and decision hysteresis; provable
   graceful degradation; the same mechanism shown to be the deployment
   safety interlock (foreign-λ transfer actively harms: 0.317 vs 0.155).
2. **Uncertainty-consuming robust economic RTO** (N2, N3): Tiwi-vertex
   envelope + modifier bias + κ·σ_LOO back-off; the sensor supplies both
   correction and uncertainty; ablation κ=1 vs κ=0: 0.50 vs 2.17
   post-warmup violation days under ×6 stress.
3. **The two-regime safety–harvest frontier with negative results**
   (N2/N3): scalar bias-MA achieves +84% uplift but violates chronically
   even under benign mismatch (5.33 d) and cannot stabilize a
   multiplicative error on a quartic constraint under stress (14.2 d ≈
   open-loop 17.2 d) — mechanism identified; the hybrid is the only arm
   safe in both regimes.
4. **Out-of-sample kinetic cross-validation and the identifiability
   principle** (N4, N4b): RR79's 4th-order peak-rate law vs Scott 2024
   single-curve decay = cleanly 2nd order (median R² 0.992, 100% of 11
   exps); ×6 effective-rate gap; GA00/Scott endpoints mutually validate
   (median 1.05×); on real curves, corrections are usable only where
   labels identify them (LOO-gated slope selected 9/21 at K=5, median
   b = −2.50, wins 2.59 vs 3.04).
5. **A quantified benchmark problem for constrained EMPC** (N5 + P2):
   order-≈4 peak-rate nonlinearity, induction delay (P ∝ s⁻⁴·³, r²=0.88),
   non-monotonic actuator (Gallup-anchored), ×101 temperature lever
   (150→90 °C), ×3.0 Arrhenius overprediction at 150 °C — offered as a
   reusable in-silico benchmark, PH liquid-dominated archetype.

---

## Section map (content bullets + artifact slots; ALL artifacts exist and
regenerate from /src via the gate)

### 1. Introduction (~1.5 pp) — WRITE LAST
- Hook: hard-constrained processes with structurally-wrong models; the
  measured ×6 model-family gap as the opening fact.
- Gap vs prior art (from gap_matrix.md): prediction-only ML (Juhri T2),
  static field practice (See 2010, Remoroza 2008, Baltazar 2014 — all T2
  PH primaries), generic MA theory (Marchetti 2009/2010).
- Contributions list (above), paragraph form.

### 2. The scaling-control problem as a benchmark (~2 pp)
- **§2.1 Philippine industrial context (NEW, per author):** PH among the
  world's largest geothermal producers (fronda2020country); silica as the
  reinjection-temperature floor; documented EDC practice = the empirical
  baseline (see2010wgc, remoroza2008ph, baltazar2014grc,
  espartinez2015bacman, kobayashi2024mahanagdong); PHP economics.
- Chemistry → control language: constraint process with order-4 peak-rate
  law, induction state, non-monotonic actuator, two levers (T_rej, dose).
- **Fig. 1** = fig_temperature_lever.png (×101; captions.md tiers)
- **Fig. 2** = fig_arrhenius_overprediction.png (×3.0, Ea 9.1 kJ/mol)
- Archetype & envelope: Tiwi endmembers (Sugiaman T1), flash scenario;
  economics as declared scenario bands (T3 fencing stated here once).

### 3. Architecture (~3 pp)
- 3.1 Synthetic-truth plant (mismatch config, OU brine — cite the
  dilution-artifact fix openly; induction fit P ∝ s⁻⁴·³ r²=0.88).
- 3.2 Hybrid sensor: trailing-24h target, sparse daily labels, per-plant
  protocol (Kadlec), log1p residual, λ with hysteresis; **the v1
  zero-shot failure reported as the motivating negative result #1.**
- 3.3 Robust RTO: vertex constraint, grid solve (auditable), MA bias,
  κσ back-off; tighten-only warmup rule.

### 4. In-silico results (~3 pp)
- **Table 1** = results/table1_summary.csv (0.117/0.196/0.227; wf2
  63/41/37%) + **Fig. 3** = fig_scarcity_sweep.png (10-d hybrid beats
  60-d physics).
- Transfer boundary (results/transfer_boundary.csv): λ as interlock.
- **Table 2** = table2_summary.csv (+33.4%/0 viol; nominal +41.7%/0.17;
  MA +84%/5.33) + **Fig. 4** = fig_control_benchmark.png.
- **Table 2b** = table2b_summary.csv (17.2 / 14.2 / 2.17 / 0.50
  post-warmup; stress = the measured ×6) + **Fig. 5** =
  fig_stress_benchmark.png; **negative result #2 mechanism** (additive
  vs multiplicative-quartic → limit cycle).
- Robustness: **Fig. 6** = fig_sensitivity_sobol.png (logk drives
  MW/T*/net: ST 0.41/0.57/0.33 — "kinetic uncertainty dominates the
  economics" = the case for the sensor; dose* ← d_opt 0.67; 100%
  feasible; MW 6.0/11.7/17.6) + economics bands
  (results/economics_bands.csv; decisions gated-invariant; safety story
  economics-invariant).

### 5. Out-of-sample validation on independent data (~2.5 pp)
- Dataset: Scott 2024 supplementary (61 exps / 1275 pts; cite article +
  corrigendum; parser integrity checks replace transcription protocol).
- **Fig. 7** = fig_kinetics_validation.png: order-2 finding + Arrhenius
  Ea ≈ 22 kJ/mol; the ×6 gap; reconciliation (different observables).
- Solubility mutual validation (endpoints 0.90–1.37×, median 1.05).
- **Fig. 8** = fig_sensor_validation_scott.png: credible arm; raw-affine
  cautionary ablation (b ∈ [−230, +769]); K=5 win 2.59 vs 3.04, b −2.50;
  **identifiability precedes correction** — and why the field setting
  (narrow window, label-covered) is exactly where hybrids win.

### 6. Discussion & Limitations (~1.5 pp) — DRAFT FROM LEDGER
- In-silico closed-loop posture (real-data validation is component-wise).
- Constraint units: polymerization rate, not deposition mm/yr — Weres
  1981 closure pending; RTO structure invariant, calibration will move.
- T3 fencing (motivation only; enforced in code).
- κ chosen at 1; σ already adaptive; κ-sensitivity noted.
- Identifiability boundary as scope statement, not weakness.
- Speciation layer (high-pH) deferred; PH field-data access.

### 7. Conclusions (~0.5 pp) + Data/Code availability (gate, seeds,
  Zenodo at P9 — Scott script excluded pending permission).

**Appendices:** A. Transcription protocol + checksum validation (33/33).
B. Reproducibility: run_all_checks.py (88 checks), pinned seeds, env.

---

## P7 build order (next builds)
- Build 2: LaTeX scaffold (elsarticle), references.bib wiring, figure
  drop-in, section files.
- Build 3: Methods + Results prose (numbers from CSVs, never retyped).
- Build 4: Validation + Discussion + Intro; abstract polish; caption pass.
- Build 5: internal referee pass against ledger §3 objection list.

## Changelog
- 2026-07-16 — v0.1 — skeleton created at P7 open; all slots verified
  against committed artifacts (gate 88/88).
- 2026-07-16 — v0.2 — title approved; §2.1 Philippine industrial context
  added; author: Bien Don G. Busico, sole author, affiliation UP Diliman
  (work venue; Mapúa MCM B.S. → bio/acknowledgments); adviser
  acknowledgment-vs-coauthorship to be confirmed with adviser.
- 2026-07-16 — v0.3 — build 3 complete: §3 (architecture, 4 equations,
  both protective mechanisms + negative result #1 in prose) and §4 (all
  three tables typeset with source-CSV comments, scarcity/Sobol figures,
  negative result #2 mechanism, 2×2 statement) written in full.
- 2026-07-16 — v0.4 — build 4 complete: §1 (intro, written last), §2
  (benchmark + PH context + captions), §5 (validation, both findings +
  identifiability principle), §6 (limitations from ledger + what
  generalizes), §7 (conclusions + availability), appendices A/B. Body
  prose COMPLETE. Editorial: Table-2/2b bar figures held out of §4 —
  tables carry the content; a trajectory figure queued as the build-5
  punch-list candidate.
- 2026-07-16 — v1.0 — build 5 (polish + reviewer-2 pass, per author):
  title now carries the Philippine context ("...for silica scaling
  control in Philippine geothermal fields..."); full-body rewrite for
  natural PhD register (em-dash rhetoric removed everywhere except
  numeric-range en-dashes and table placeholders; cadence varied; tics
  thinned); sole-author/no-adviser confirmed and scaffolding updated
  (acknowledgments now thank Dr. Scott pending his wording approval and
  note the Mapúa MCM B.S.); automated audits pass: 0 rhetorical
  em-dashes, all 21 cross-references resolve against 32 labels, all 26
  citation keys exist in references.bib.

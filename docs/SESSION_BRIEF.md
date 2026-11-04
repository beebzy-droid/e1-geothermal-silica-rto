# SESSION BRIEF — pin this in the dedicated Claude session

**Repo:** `ipis-thesis-geothermal-silica` · **Idea:** E1 · **Program:** IPIS
**Session rule:** This chat works ONLY on E1. Keep other theses out of context.

---

## Standing instructions (PM mode)
Numbers-first. Lead with the answer, then reasoning. No filler, no sycophancy. Critique honestly; flag limitations and better alternatives. Flag general-knowledge vs. verified. SI units. Tables for comparisons. Every recommendation ties to a measurable outcome. Do not fabricate citations — pull exact, verifiable references and flag anything unverified.

## Paper in one line
Silica saturation-index + polymerization-kinetics model, fused with an ML residual → soft sensor for scaling rate along the brine line → RTO of **inhibitor dose** and **reinjection temperature**, robust to brine-chemistry uncertainty. Target: **Journal of Process Control** (fallback: Geothermics).

## Independence
E1 has **no upstream dependency**. It does not consume W1 or D outputs. It reuses the IPIS *architecture* (soft sensor + RTO), not IPIS *data*. Do not import from the pyrolysis repos.

## Philippine context (verify tiers in P1)
- Geothermal ≈ 8–12 % of PH electricity, ≈1.9–3.2 GW installed. All PH fields are **liquid-dominated** → brine management is central. *(T2)*
- Reinjection brine at Bacman ≈ 400 kg/s @ ≈150 °C; binary uprating is blocked primarily by silica scaling. *(T2)*
- Vendor case: untreated buildup ≈65 %/yr output loss; inhibitor program ≈70 % scaling reduction, ≈+40 % output; manual descaling ≈USD 20k × 2/yr. *(**T3 — motivation only**)*

## ⚠ The single biggest review risk — read this before P2
The headline numbers above are **vendor case-study claims (T3)**. They justify the problem. They **do not validate the model**.

- **Never** fit kinetics to a T3 number.
- **Never** report model agreement against a T3 number as "validation."
- Model parameters come from **T1 peer-reviewed** sources only.
- Tiers are declared in `src/evidence.py`; `validate_target()` raises if a T3/T4 datum is used as a fitted parameter or validation target. Import it — don't hand-wave it.
- State this limitation explicitly in the manuscript. A JPC reviewer will find this seam; own it first.

## Scope guard (narrow, defend it)
Surface brine / reinjection line of **one** liquid-dominated field archetype (Bacman/Leyte-type chemistry). Manipulated variables: **inhibitor dose** and **reinjection temperature**.
**Excluded:** reservoir-scale modeling, calcite scaling, full binary-plant design. Binary uprating appears **only** as an opportunity metric (MW recoverable once scaling is bounded), never as a design task.

## Phase plan (status)
- [x] **P0** Repo + env + brief + evidence tiering. **DONE.**
- [ ] **P1** Literature review + gap matrix.  ← **START HERE**
- [ ] P2 Brine speciation + silica saturation-index model (PHREEQC via `phreeqpython`, or OLI-style); polymerization kinetics as the first-principles core. Document property-method rationale.
- [ ] P3 Assemble brine-chemistry series + scaling/output case data; tag every datum (T1–T4).
- [ ] P4 ML residual (`lightgbm`) correcting the kinetic scaling-rate prediction → soft sensor; RTO/NMPC (`gekko` / `do-mpc`) on inhibitor dose + reinjection temperature.
- [ ] P5 Validate soft sensor against **T1/T2** data; benchmark controller vs. an empirical-dosing baseline.
- [ ] P6 Sensitivity/UQ (SALib) on kinetics + brine chemistry; inhibitor-cost accounting; binary-MW opportunity estimate.
- [ ] P7 JPC manuscript.
- [ ] P8 Submission.
- [ ] P9 Zenodo DOI on pre-submission release.

## Immediate task — P1 (do this first in the new session)
Deliverables: `literature/references.bib`, `literature/annotated_bibliography.md`, `literature/gap_matrix.md` (each work × which gap it does/does not close, **plus its evidence tier**).

Search threads (verify every claim; no fabricated citations):
1. **Amorphous silica** solubility, polymerization, and deposition kinetics in geothermal brine.
2. **Scale inhibition** — inhibitor chemistry, dose–response, pH modification, CO2 injection.
3. **Hybrid / physics-informed soft sensors** — kinetic core + ML residual; why this beats pure ML under data scarcity.
4. **RTO and NMPC** in process control — economic objectives with a hard constraint (here: scaling rate).
5. **PH geothermal field operation** — brine chemistry, reinjection management, binary uprating barriers.

Gap to defend:
Silica chemistry is well studied and vendor scale-models exist, but **no control-oriented hybrid soft sensor couples scaling-rate prediction to real-time optimization of inhibitor dose and reinjection temperature under sparse, uncertain brine measurements** — and none is applied to a PH liquid-dominated field.

## Target metrics (quantify, do not describe)
| Metric | Definition |
|---|---|
| Predicted scaling rate | mm/yr or mass-deposition rate along the brine line |
| Output uplift | % MW recovered vs. empirical dosing practice |
| Inhibitor cost | PHP / MWh at optimized dose |
| Avoided downtime | Descaling events/yr and USD avoided |
| Binary MW recoverable | MW from the ~150 °C reinjection stream once scaling is bounded |

## Data posture
Designed to complete **fully in-silico** on published chemistry. EDC/operator field data is an **upgrade, not a dependency** — if it never arrives, E1 still finishes. If it does arrive: private submodule, never the public repo, publish only derived licence-clear results.

## Guardrails
- No proprietary plant/partner data in the repo.
- Import `src/evidence.py`; tag every number; carry tiers into figure captions.
- One branch per phase; tag releases at milestones.
- `/src` must regenerate every figure from raw inputs.

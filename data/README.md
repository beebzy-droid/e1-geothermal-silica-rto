# Data provenance

No proprietary plant, partner, or company data is committed. E1 is designed to complete **fully in-silico**; field data is an upgrade, not a dependency.

## Evidence tiers — tag EVERY number you use

The load-bearing figures for this thesis come from mixed-quality sources. A JPC reviewer will attack the seam between them. Tag each datum in `src/evidence.py` and carry the tag into every table and figure caption.

| Tier | Meaning | Use |
|---|---|---|
| **T1** | Peer-reviewed measurement / primary source | Model parameters, kinetics, validation targets |
| **T2** | Operator or agency disclosure (EDC, DOE, NREL) | Field context, brine conditions, capacity figures |
| **T3** | Vendor / trade case study | **Motivation and benchmark ONLY.** Never a validation target, never a fitted parameter. |
| **T4** | General knowledge / assumption | Must be replaced or bounded by sensitivity analysis before P7 |

**Non-negotiable:** the headline motivating numbers (≈65 %/yr untreated output loss; ≈70 % scaling reduction and ≈+40 % output from an inhibitor program; ≈USD 20k per manual descaling event, twice yearly) are **T3 vendor case-study claims**. They justify the problem. They do **not** validate the model. Do not fit kinetics to them and do not report model agreement against them as validation — say so explicitly in the manuscript.

## Datasets

| Dataset | Source | Tier | Licence | Retrieved | Unlocks |
|---|---|---|---|---|---|
| Amorphous-silica solubility & polymerization kinetics | Peer-reviewed literature | T1 | (fill) | (fill) | First-principles core |
| Brine chemistry (SiO2, pH, T, ionic strength) — PH fields | Published EDC / Bacman / Leyte field studies; geothermal literature | T2 | (fill) | (fill) | Saturation model + soft-sensor inputs |
| Reinjection stream conditions (≈400 kg/s @ ≈150 °C, Bacman) | Operator/agency disclosure | T2 | (fill) | (fill) | Binary-opportunity metric |
| PH geothermal installed capacity (~1.9–3.2 GW; ~8–12 % of generation) | DOE / agency statistics | T2 | (fill) | (fill) | Impact scaling |
| Inhibitor-program outcomes (scaling reduction, output uplift, descaling cost) | Vendor case studies | **T3** | (fill) | (fill) | **Motivation + benchmark only — NOT validation** |
| Inhibitor chemistry / dose–response | Literature + vendor datasheets | T1/T3 | (fill) | (fill) | RTO manipulated variable |

Raw payloads under `data/raw/` (gitignored). Every row must have source, URL/citation, licence, retrieval date, and transform before P7.

## If field data becomes available
An EDC or operator partnership would upgrade P5 from "validated against published case data" to "validated against plant measurements" — a materially stronger claim. Treat it as optional upside. **Never commit partner data to this public repo**; keep it in a private submodule and publish only derived, licence-clear results.

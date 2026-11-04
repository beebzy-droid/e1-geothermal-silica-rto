# G7 Commitment — Uncertainty Treatment (binding design decision)

**Repo:** ipis-thesis-geothermal-silica · **Decided:** 2026-07-14 (P2) · **Binds:** P4–P7
**Rule:** this document may be amended only with a dated changelog entry and a stated reason. Silent drift into cosmetic UQ is the failure mode this file exists to prevent.

## Decision

The RTO layer of E1 is a **scenario-based robust real-time optimization** over a brine-chemistry uncertainty set, with **modifier adaptation** (Marchetti, Chachuat & Bonvin 2009) as the plant–model mismatch correction mechanism.

## The uncertainty set (T1-grounded, not synthetic)

The brine-chemistry scenario set is the **four-vertex endmember envelope of Sugiaman et al. (2004), Table 1** (Tiwi; primary PDF in `literature/`, transcribed into `src/brine_speciation.py::TIWI_ENDMEMBERS`, T1/VERIFIED):

| Vertex | Role | SiO₂ (mg/kg) | pH |
|---|---|---|---|
| A — meteoric recharge | dilution bound | 135 | 7.16 |
| B — Bariis upflow | **nominal archetype** | 638 | 5.60 |
| C — S. Kapipihan upflow | upflow variability | 648 | 5.75 |
| D — acid fluid | worst-case chemistry | 509 | 3.20 |

Scenarios are convex mixtures of the vertices plus flash-fraction perturbation (±5 % steam fraction around the design point). Measured at P2-gate: envelope spread in amorphous-silica saturation ratio at 150 °C = **0.87** (module-2 self-check #5) — the set is non-trivial by construction.

## The formulation (fixed structure, P4 fills parameters)

- **Decision variables:** inhibitor/acid dose `u_d`, reinjection temperature setpoint `u_T`.
- **Objective:** max E[net revenue] = power uplift − inhibitor cost (PHP/MWh accounting per brief O3), expectation over the scenario set.
- **Hard constraint, enforced per-scenario (robust, not on-average):** predicted scaling rate ≤ r_max **for every scenario vertex** — a scaling excursion on the worst-case brine is a plant event, not an averaging residual.
- **Mismatch correction:** first-order modifier adaptation on the scaling-rate constraint using soft-sensor innovations; fallback bias-update if gradient estimates are too noisy (decide at P5 with numbers, not preference).
- **Kinetic-parameter uncertainty** (Limitation A, the 100→150 °C extrapolation) enters as a parametric band on the module-3 rate constants, quantified in P6 via Sobol/SALib; the robust constraint uses the band edge, not the nominal.

## Acceptance criteria (P5/P6 gate — quantified, per brief)

1. Constraint satisfaction: 0 scaling-rate violations across all scenario vertices in closed-loop simulation (vs. the empirical-dosing baseline's violation count).
2. Economic cost of robustness: report Δ(net revenue) robust vs. nominal-only RTO — if the price of robustness is <2 % of uplift, robustness wins by default; if >10 %, justify or re-scope G7.
3. Modifier adaptation must recover ≥80 % of the optimality gap induced by a deliberate +25 % kinetic-rate-constant mismatch within 10 RTO iterations (in-silico test).

## Why this and not alternatives (pre-empting the reviewer)

- **Stochastic MPC / chance constraints:** rejected — requires distributions we cannot defend from sparse T1 data; a vertex envelope is honest about what is actually known.
- **Pure modifier adaptation without scenarios:** rejected — MA corrects at the operating point but gives no guarantee across brine excursions between chemistry measurements (the sparse-measurement reality is the point of G7).
- **Min-max robust NMPC:** held in reserve — if P5 shows scenario-robust RTO is too conservative, this is the named escalation path, not a new idea invented under review pressure.

## Changelog

- 2026-07-14 — v1.0 — initial commitment (P2). Envelope source: Sugiaman 2004 Table 1.

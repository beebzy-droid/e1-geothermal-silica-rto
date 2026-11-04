# Gap Matrix — E1 (ipis-thesis-geothermal-silica)

**Phase:** P1 · **Date:** 2026-07-14

## Gap dimensions

The defended gap decomposes into eight testable dimensions. A work "closes" a dimension only if it demonstrably delivers it, not merely discusses it.

| ID | Dimension |
|----|-----------|
| G1 | First-principles silica saturation / speciation model |
| G2 | Polymerization / deposition **kinetics** (rate, not just equilibrium potential) |
| G3 | Data-driven / ML prediction of scaling |
| G4 | **Hybrid** structure: physics core + ML correction |
| G5 | Online / real-time estimation from routine plant signals (**soft sensor**) |
| G6 | **Closed-loop optimization** of mitigation levers (inhibitor dose, reinjection T) with an economic objective and a scaling-rate constraint |
| G7 | Explicit handling of **sparse / uncertain** brine measurements |
| G8 | **Philippine** liquid-dominated field application |

Symbols: ● closes · ◐ partial · ○ does not address.

## Matrix

| Work | Tier | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | Gap left open |
|---|---|---|---|---|---|---|---|---|---|---|
| Weres, Yee & Tsao 1981 (+LBL-7033, SPE 1982) | T1 | ◐ | ● | ○ | ○ | ○ | ○ | ○ | ○ | Kinetics only; ≤100 °C; no estimation, no control |
| Rimstidt & Barnes 1980 | T1 | ○ | ● | ○ | ○ | ○ | ○ | ○ | ○ | Rate law only; dilute systems |
| Gunnarsson & Arnórsson 2000 | T1 | ● | ○ | ○ | ○ | ○ | ○ | ○ | ○ | Solubility only — SSI denominator |
| Rothbaum et al. 1979 | T1 | ◐ | ● | ○ | ○ | ○ | ○ | ○ | ○ | pH-dependent kinetics; no application layer |
| Bohlmann et al. 1980 | T1 | ○ | ● | ○ | ○ | ○ | ○ | ○ | ○ | Deposition kinetics; lab brines |
| van den Heuvel et al. 2018 | T1 | ◐ | ● | ○ | ○ | ○ | ○ | ○ | ○ | In-pipe scaling data; observational, no model-to-control |
| Scott et al. 2024 | T1 | ◐ | ● | ○ | ○ | ○ | ○ | ○ | ○ | Modern kinetics; lab scope |
| Dixit et al. 2016 (Bouillante) | T1 | ◐ | ● | ○ | ○ | ○ | ○ | ○ | ○ | Field-fitted kinetics; open-loop, non-PH |
| Møller, Greenberg & Weare 1998 | T1 | ● | ○ | ○ | ○ | ○ | ○ | ○ | ○ | Equilibrium potential only; no kinetics/control |
| OLI Systems (vendor platform) | T3 | ● | ◐ | ○ | ○ | ○ | ○ | ○ | ○ | Proprietary what-if prediction; no soft sensing/RTO |
| Polii & Abdurrachim 2013 | T2 | ◐ | ◐ | ○ | ○ | ○ | ○ | ○ | ○ | Open-loop pipe-deposition profile |
| Gallup 2002; Gallup & Barcelon 2005 | T1 | ○ | ○ | ○ | ○ | ○ | ◐ | ○ | ◐ | Dose–response data (incl. simulated PH brines); no model/optimizer — manual screening |
| Henley 1983 | T1 | ◐ | ◐ | ○ | ○ | ○ | ◐ | ○ | ○ | pH-mod rationale; pre-computational |
| Thermochem 2020 (Bacman pH-mod) | T3 | ◐ | ◐ | ○ | ○ | ○ | ◐ | ○ | ● | Static vendor design, not adaptive optimization; T3 |
| See 2008 (BacMan-II inhibitor test) | T2 | ○ | ○ | ○ | ○ | ○ | ◐ | ○ | ● | Single field trial; empirical dosing, no model |
| Siega et al. 2005 (Mahanagdong, calcite) | T2 | ○ | ○ | ○ | ○ | ○ | ◐ | ○ | ● | Calcite, not silica; empirical practice baseline |
| Kobayashi et al. 2024 (Mahanagdong SGW) | T2 | ○ | ○ | ○ | ○ | ○ | ◐ | ○ | ● | Documents the output-vs-scaling trade-off; managed manually |
| Okazaki et al. 2017 (fiber-optic sensor) | T1 | ○ | ○ | ○ | ○ | ◐ | ○ | ○ | ○ | Hard sensor, point measurement; no inference, no control |
| Juhri et al. 2024 (49th Stanford SGW) | T2 | ○ | ◐ | ● | ◐ | ◐ | ○ | ○ | ○ | Kinetics-informed **features**, not a hybrid residual; open-loop; 5 h horizon; Japan-trained; workshop tier |
| SSRG IJME 2024 (digital twin / IIoT) | T2 | ○ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | Monitoring + rule-level pH control; no hybrid model, no economic RTO, synthetic fluid |
| Buster et al. 2021 (GOOML) | T1 | ○ | ○ | ● | ○ | ◐ | ◐ | ○ | ○ | Steamfield ML optimization; scaling chemistry absent |
| Psichogios & Ungar 1992; Thompson & Kramer 1994 | T1 | ○ | ○ | ● | ● | ◐ | ○ | ◐ | ○ | Architecture exists — never applied to geothermal scaling |
| von Stosch et al. 2014 (review) | T1 | ○ | ○ | ● | ● | ◐ | ◐ | ◐ | ○ | Framework review; no scaling application |
| Kadlec et al. 2009; Jiang et al. 2021 (reviews) | T1 | ○ | ○ | ● | ○ | ● | ◐ | ◐ | ○ | Soft-sensor practice; pure data-driven emphasis |
| Karniadakis et al. 2021 (PIML review) | T1 | ○ | ○ | ● | ● | ○ | ○ | ◐ | ○ | Taxonomy; no process-control instantiation here |
| Ellis et al. 2014; Rawlings et al. 2012 (EMPC) | T1/T2 | ○ | ○ | ○ | ○ | ○ | ● | ◐ | ○ | Control theory; no scaling domain, no chemistry |
| Darby et al. 2011 (RTO practice) | T1 | ○ | ○ | ○ | ○ | ◐ | ● | ◐ | ○ | Industrial RTO; refinery-centric |
| Marchetti et al. 2009 (modifier adaptation) | T1 | ○ | ○ | ○ | ○ | ○ | ● | ● | ○ | Mismatch-robust RTO; never coupled to scaling soft sensor |
| **E1 (this thesis)** | — | **●** | **●** | **●** | **●** | **●** | **●** | **●** | **●** | — |

## Reading of the matrix

Column coverage is dense on the left and empty on the right. Counting ● per column across all prior work: G1 = 3, G2 = 6, G3 = 5, G4 = 3, G5 = 1, G6 = 3, G7 = 1, **G8 silica-specific model-based = 0** — and, decisively, **no single row has ● in more than two adjacent blocks.** The literature splits into three non-intersecting clusters:

1. **Chemistry cluster** (rows 1–11): saturation and kinetics are mature — G1/G2 are solved subproblems, which is exactly why they are E1's *inputs*, not its contribution.
2. **Practice cluster** (rows 12–18): inhibition and reinjection management at real fields — including three PH-specific rows — is empirical, static, and manually tuned. G6 never rises above ◐.
3. **Methods cluster** (rows 19–29): hybrid modeling, soft sensing, and economic RTO/EMPC are mature *in other domains*. None touches silica scaling; the closest ML work (2024) is open-loop, short-horizon, and uses kinetics as features rather than as a corrected first-principles core.

**Defended gap (one sentence).** Silica-scaling chemistry (cluster 1), field mitigation practice (cluster 2), and hybrid-soft-sensor/RTO methods (cluster 3) each exist in mature form, but no work couples a kinetics-cored, ML-corrected scaling-rate soft sensor to real-time economic optimization of inhibitor dose and reinjection temperature under sparse, uncertain brine measurements — and no model-based silica-scaling control of any kind has been demonstrated for a Philippine liquid-dominated field.

**Reviewer-anticipation notes.**
- The nearest ML neighbor is now fully characterized: Juhri et al. 2024, 49th Stanford SGW — **T2 workshop paper**, kinetics-as-features, open-loop, 5 h horizon, no uncertainty treatment. Differentiation is fourfold: architecture (G4), closed loop (G6), uncertainty (G7), and publication tier. Threat downgraded from "live" to "cite-and-differentiate."
- The Thermochem/Turboden Bacman pH-mod rows show industry already *acts* on both levers — this is an asset, not a threat: it proves the actuators exist and the optimization layer is the missing piece.
- G7 is the thinnest defended dimension (only modifier adaptation scores ●). The RTO formulation in P4 must make the uncertainty treatment explicit and non-cosmetic, or drop G7 from the novelty claim.

## Traceability

Search threads 1–5 from the session brief were each covered by ≥1 dedicated web query on 2026-07-14; verification statuses per work are recorded in `references.bib` (`note` field) and the annotated bibliography. Tier declarations to be mirrored in `src/evidence.py` at P2.

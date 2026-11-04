# Annotated Bibliography — E1 (ipis-thesis-geothermal-silica)

**Phase:** P1 · **Date:** 2026-07-14 · **Status:** first-pass systematic review (web-verified)

**Legend.**
Tiers per `src/evidence.py`: **T1** peer-reviewed · **T2** conference/institutional · **T3** vendor/press (motivation only) · **T4** unverified.
Verification: **[V]** bibliographic details confirmed at source this session · **[P]** provisional — existence certain, details to be resolved in Zotero before citing. **No [P] entry may be cited in the manuscript until resolved.**

Coverage tally: 41 entries — 23 T1, 12 T2, 3 T3, 3 software/tooling. 19 fully verified this session.

---

## Thread 1 — Amorphous silica solubility, polymerization, deposition kinetics

**Weres, Yee & Tsao (1981), *J. Colloid Interface Sci.* 84(2):379–402.** T1 [V]
The kinetic backbone of the field. Experimental polymerization of silicic acid in brine-like solutions, 23–100 °C, wide SiO₂/pH/NaCl ranges; homogeneous nucleation model (Lothe–Pound factor) plus molecular-deposition rate equations packaged in a predictive code for geothermal brines. **Use:** primary candidate for the first-principles kinetic core of the soft sensor (O2). **Limit:** ≤100 °C data; extrapolation to the 150 °C reinjection line must be flagged and carried into UQ (P6). Companion full report: LBL-7033 (1980, T2 [V]); engineering-format version: SPE J 22(1):9–16 (1982, T1 [V-existence]).

**Rimstidt & Barnes (1980), *Geochim. Cosmochim. Acta* 44:1683–1699.** T1 [P]
First-order silica–water reaction kinetics; the rate law used in the only located PH-specific deposition modeling (Tongonan injection wells, via method-of-characteristics models). **Use:** alternative/benchmark rate law to Weres et al.; parameter-sensitivity comparison belongs in P6. **Limit:** dilute-solution basis; deposition, not colloid-mediated fouling.

**Gunnarsson & Arnórsson (2000), *Geochim. Cosmochim. Acta* 64(13):2295–2307.** T1 [V]
Amorphous silica solubility 8–310 °C with a regressed temperature equation; the standard SSI (silica saturation index) denominator. **Use:** solubility correlation for the saturation-index model (O1). **Limit:** pure-water/P_sat basis — salinity and pH speciation corrections come from the electrolyte model layer (PHREEQC).

**Fournier & Rowe (1977), *Am. Mineral.* 62:1052–1056.** T1 [P]
Classic amorphous-silica solubility at elevated T/P. **Use:** cross-check on Gunnarsson & Arnórsson; historical anchor. **Limit:** superseded in precision; cite as lineage, not as the working correlation.

**Rothbaum et al. (1979), *Geothermics* 8(1):1–20.** T1 [V-existence]
Silica polymerisation and pH effects on scaling, 5–180 °C span (with Rothbaum & Rohde companion work). **Use:** T1 pH-dependence data for kinetic parameterization; overlaps the reinjection-line temperature window better than Weres et al. **Limit:** NZ fluid matrix; transferability to PH chemistry must be a declared assumption.

**Bohlmann, Mesmer & Berlinski (1980).** T1 [P]
Silica deposition kinetics from simulated geothermal brines; provides the interfacial saturation concentration treatment cited by later kinetic studies. **Use:** deposition-rate (as opposed to polymerization-rate) closure — the mm/yr target metric needs a deposition model, not just monomer decay. **Limit:** details unresolved; do not cite until Zotero-verified.

**van den Heuvel et al. (2018), *Geothermics* 76:231–241.** T1 [V]
In-pipeline scaling at Hellisheiði under well-constrained conditions; links fluid chemistry to actual wall-scale growth. **Use:** the best-quality T1 validation-shaped dataset located so far — scaling *in a pipe*, not a beaker. Priority acquisition for P3/P5. **Limit:** Icelandic chemistry; one flow geometry.

**Scott et al. (2024), *Geochim. Cosmochim. Acta* 371:78–94.** T1 [V]
Modern re-treatment of polymerization and nanocolloid nucleation/growth kinetics. **Use:** state-of-the-art kinetic parameterization to benchmark the 1980s rate laws against; citing this preempts the "your kinetics are 40 years old" review objection. **Limit:** lab solutions; needs mapping to line conditions.

**Dixit et al. (2016), *Chemical Geology*.** T1 [V-existence]
On-site polymerization kinetics of the Bouillante fluid (600 mg/L SiO₂; 25–90 °C; pH 5–8) with fitted kinetic parameters for an operating field. **Use:** template for exactly the field-fitted-kinetics workflow E1 applies to a PH archetype; direct methods precedent. **Limit:** seawater-derived fluid — chemistry far from PH andesitic brines.

---

## Thread 2 — Scale inhibition: inhibitor chemistry, dose–response, pH modification

**Gallup (2002), *Geothermics* 31(4):415–430.** T1 [P]
Screening of >25 organic inhibitor/dispersant formulations: only one achieved >50 % scale reduction (~1 ppm optimum), and **overdosing worsened deposition** (flocculation). **Use:** the single most important dose–response fact for the RTO — the inhibitor-effect model must be non-monotonic in dose, which makes optimization non-trivial and is a core defense of why RTO beats fixed empirical dosing. **Limit:** synthetic 0.15 M NaCl brine.

**Gallup & Barcelon (2005), *Geothermics* 34(6):756–771.** T1 [V-existence]
Follow-up using **simulated Philippine field brines** (Na–K–Ca–Cl, pH 7.0–8.4); organic inhibitors vs. strong acids and acid precursors. Acidification remained the benchmark (≈97 % inhibition in prior lab work). **Use:** the closest T1 dose–response source for PH-archetype chemistry — primary candidate for parameterizing the inhibitor-effect term. **Limit:** lab coil deposition, not line-scale.

**Henley (1983), *Geothermics* 12(4):307–321.** T1 [P]
Foundational treatment of pH and silica-scaling control in field development. **Use:** links pH-mod practice to polymerization kinetics; supports treating pH/acid dosing as the mechanistic pathway behind "inhibitor dose." **Limit:** pre-dates modern kinetics; cite for framing.

**Thermochem (2020), white paper.** T3 [V] — motivation only
Documents pH-mod design **for the Bacman binary bottoming cycle** and a successful dual-flash pH-mod pilot (Unit 9). **Use:** proves industrial practice targets exactly E1's two levers at exactly E1's field archetype. **Never** a parameter or validation source.

**Okazaki et al. (2017), *Sci. Rep.* 7, DOI 10.1038/s41598-017-03530-1.** T1 [V]
Fiber-optic sensor measuring silica scale formation in real time at Sumikawa (980 mg/L SiO₂, 93 °C); detected inhibitor and pH-mod effects within hours. **Use:** (a) evidence that direct scaling-rate measurement is possible but exotic — motivating soft sensing from routine signals; (b) a plausible future hard-sensor complement. **Limit:** point sensor, research-grade.

**Energies 17(19):4825 (2024), review of silica-scaling reduction technologies.** T1 [V-venue]
Market/technology overview incl. thermochemical prediction tooling and inhibitor practice. **Use:** RRL breadth and taxonomy of mitigation options; recent citation coverage. **Limit:** review, no new data.

**Brown (2011), Int. Workshop on Mineral Scaling, Manila.** T2 [V-existence]
Thermodynamics and kinetics of silica scaling, presented in Manila (PH-industry-facing). **Use:** bridges Thread 1 kinetics to PH practice; likely cites regional case data worth chasing. **Limit:** workshop paper.

---

## Thread 3 — Hybrid / physics-informed soft sensors

**Psichogios & Ungar (1992), *AIChE J.* 38(10):1499–1511.** T1 [P]
The original serial hybrid: neural network estimates unmeasured parameters inside a first-principles model; showed better generalization and lower data need than black-box NNs. **Use:** canonical justification for the hybrid structure under data scarcity — E1's central methodological premise. 

**Thompson & Kramer (1994), *AIChE J.* 40(8):1328–1340.** T1 [V]
Formalized parallel hybrid structures — data-driven **residual correction of a first-principles backbone** — and analyzed when prior knowledge helps. **Use:** this is E1's exact architecture (kinetic core + ML residual); the architectural citation. 

**von Stosch et al. (2014), *Comput. Chem. Eng.* 60:86–101.** T1 [V]
Definitive review of hybrid semi-parametric modeling: structures (serial/parallel), identification, and applications in monitoring, control, and optimization. Key caveat: hybrid ≠ automatically better; knowledge integration must be rational. **Use:** RRL spine for Chapter 2; frames the soft-sensor-to-optimization pipeline E1 instantiates. 

**Kadlec, Gabrys & Strandt (2009), *Comput. Chem. Eng.* 33(4):795–814.** T1 [V]
Standard review of data-driven soft sensors in process industry; catalogs the data pathologies (missing data, drift, outliers, collinearity) that sparse geothermal chemistry data will exhibit. **Use:** justifies preprocessing/validation design in P3–P5. **Limit:** pure data-driven scope — the contrast E1 argues against under scarcity.

**Jiang et al. (2021), *IEEE Sensors J.* 21(11):12868–12881.** T1 [V]
Review of soft sensors for monitoring, control, **and optimization** — the closed-loop framing. **Use:** positions soft sensors as controller inputs, the step most scaling literature never takes. 

**Karniadakis et al. (2021), *Nat. Rev. Phys.* 3:422–440.** T1 [P]
Physics-informed ML survey. **Use:** situates the residual-hybrid within the broader PIML taxonomy; JPC reviewers will expect the term handled precisely. **Limit:** PINN-centric; E1 is a hybrid-residual design, not a PINN — say so explicitly.

**Juhri et al. (2024), Proc. 49th Stanford Geothermal Workshop.** T2 [V]
**Closest ML prior art — venue resolved 2026-07-14** (pangea.stanford.edu/.../SGW/2024/Juhri.pdf; NEDO + JSPS–DIKTI funded). Supervised ML predicting silica-scale formation rate from geothermal-water physicochemistry + polymerization/adsorption kinetics *features*; trained on Japanese GPP plate-immersion experiments; %RRMSE ≈ 15 at a 5 h horizon. Their own stated future work is an AI *prediction* system — not control. **Use:** proves ML scaling-rate prediction exists and is open-loop, short-horizon, site-trained, and T2 — leaving the hybrid-residual + closed-loop-RTO + uncertainty gap fully open. Differentiate on four axes in the manuscript: architecture (features vs. corrected physics core), loop (open vs. closed), uncertainty (none vs. explicit), tier (workshop vs. journal target).

---

## Thread 4 — RTO / (N)MPC with economic objectives and hard constraints

**Ellis, Durand & Christofides (2014), *J. Process Control* 24(8):1156–1178.** T1 [V]
Tutorial review of economic MPC: stability, performance, constraint handling for nonlinear systems. **Use:** the target-journal anchor; E1's controller (maximize output minus inhibitor cost s.t. scaling-rate ≤ limit) is a textbook EMPC/RTO instance — cite to frame, then differentiate on the hybrid-sensor coupling and application domain. 

**Darby et al. (2011), *J. Process Control* 21(6):874–884.** T1 [P]
Industrial RTO practice: steady-state detection, model updating, the RTO/MPC hierarchy. **Use:** motivates the two-layer design choice (RTO on dose/reinjection-T setpoints vs. full NMPC) and its industrial realism for a plant like Bacman. 

**Marchetti, Chachuat & Bonvin (2009), *Ind. Eng. Chem. Res.* 48(13):6022–6033.** T1 [P]
Modifier adaptation: converging to plant optimality despite structural model mismatch. **Use:** directly relevant robustness mechanism — E1's kinetic core *will* be wrong for the specific field; MA (or its ideas) is one defensible answer alongside robust/stochastic formulations. 

**Rawlings, Angeli & Bates (2012), 51st IEEE CDC:3851–3861.** T2 [V]
Fundamentals of EMPC (dissipativity, average-performance guarantees). **Use:** theoretical grounding citation behind the tutorial review. 

---

## Thread 5 — PH geothermal field operation, brine chemistry, reinjection

**Fronda et al. (2020), Proc. World Geothermal Congress 2020+1.** T2 [V]
DOE country update: installed capacity, field inventory, development pipeline. **Use:** authoritative source for the ~1.9 GW installed / share-of-generation context claims (replaces the T2-tagged numbers in the brief with a citable source). **Limit:** conference; pair with DOE grid statistics for current-year figures.

**Sugiaman et al. (2004), *Geothermics* 33:57–86.** T1 [V]
Geochemical response to production at Tiwi — multi-year PH liquid-dominated brine chemistry evolution. **Use:** strongest located T1 candidate for the representative-brine composition and its variability envelope (O1 input; UQ ranges in P6). **Limit:** Tiwi ≠ Bacman; archetype framing must absorb this.

**See (2008), 29th PNOC-EDC Geothermal Conf.:143–149.** T2 [V-details]
**Silica inhibitor hot-injection field test at BacMan-II.** The single most on-point PH document located: real inhibitor trial at the exact field archetype. **Use:** qualitative validation shape + operating context for the dose lever; chase the PDF (EDC proceedings / UNU-GTP library). **Limit:** T2 and likely sparse quantitative reporting.

**Siega, Herras & Buñing (2005), WGC 2005.** T2 [V-details]
Calcite inhibition at Mahanagdong. **Use:** documents PH inhibitor-dosing operational practice (the "empirical baseline" E1 benchmarks against) — even though calcite itself is excluded from scope. 

**Kobayashi et al. (2024), 49th Stanford Geothermal Workshop.** T2 [P]
Mahanagdong reinjection management: terminating infield cold injection recovered thermal output **but triggered aggressive wellbore scaling** (11 MW loss episode documented). **Use:** live evidence that reinjection-temperature/routing decisions trade output against scaling — precisely the trade-off E1's optimizer formalizes. High rhetorical value in the Introduction.

**ThinkGeoEnergy (2019; 2021).** T3 [V] — motivation only
(a) EDC presentation report: Bacman reinjection ≈400 kg/s at ≈150 °C, binary uprating blocked primarily by silica; (b) EDC/Turboden 29 MW gross ORC brine-recovery plant at Palayan Bayan, with pH-mod for silica control. **Use:** the binary-MW opportunity metric (O5) now has a real project anchor — E1's opportunity estimate can be sanity-checked against a commercial design point (~25 MW net from this stream). **Never** fitted or used as validation (per `validate_target()`).

---

## Nearest-neighbor prior art (what already exists, and what it does not do)

**Møller, Greenberg & Weare (1998), *Transp. Porous Media*, DOI 10.1023/A:1006501927827.** T1 [V-DOI]
Pitzer-based equilibrium models predicting carbonate/silica scale to high T and ionic strength. **Does:** rigorous thermodynamic scale *potential*. **Does not:** kinetics, real-time estimation, or control.

**OLI Systems (2026, vendor blog + platform).** T3 [V] — motivation only
Vendor-grade electrolyte thermodynamics reproducing field silica/halite/Sb₂O₃ scaling observations. **Does:** what-if scale prediction. **Does not:** online soft sensing, closed-loop optimization; and it is proprietary — supporting the "OLI-style vs. open PHREEQC" implementation choice in P2.

**Polii & Abdurrachim (2013), Indonesia Int. Geothermal Convention.** T2 [P]
Silica-scaling prediction along a brine pipe from solubility + temperature correlations. **Does:** open-loop pipe deposition profile. **Does not:** data fusion, uncertainty, control.

**Buster et al. (2021), *Energies* 14(20) — GOOML.** T1 [V-venue]
ML framework for geothermal operational optimization (steamfield level). **Does:** ML + optimization in geothermal operations. **Does not:** scaling chemistry, first-principles core, or scaling-rate-constrained economics.

**SSRG IJME (2024), digital twin/AR for silica-scaling mitigation.** T2 [P]
PLC-controlled pH treatment of synthetic geofluid with DT/AR/IIoT monitoring. **Does:** real-time monitoring + rule-level pH control. **Does not:** hybrid kinetic-ML scaling-rate estimation, economic RTO, uncertainty handling.

---

## Software / methods tooling (Methodology citations)

PHREEQC v3 (Parkhurst & Appelo 2013, USGS TM 6-A43) [P] · GEKKO (Beal et al. 2018, *Processes* 6(8):106) [P] · do-mpc (Fiedler et al. 2023, *Control Eng. Pract.* 140:105676) [P] · SALib (Herman & Usher 2017, *JOSS* 2(9):97) [P] · LightGBM (Ke et al. 2017, NeurIPS 30) [P]. All standard; resolve DOIs in Zotero in one pass.

---

## Verification queue (blockers before manuscript citation)

| # | Item | Action |
|---|------|--------|
| 1 | ~~mlsilica2024 venue~~ | **RESOLVED 2026-07-14:** Juhri et al., Proc. 49th Stanford Geothermal Workshop (2024), T2. Remaining: transcribe full author list from the PDF. |
| 2 | Gallup 2002 / Gallup & Barcelon 2005 vol/pages/DOI | Zotero lookup. |
| 3 | Rimstidt & Barnes 1980; Fournier & Rowe 1977; Henley 1983; Bohlmann 1980 | Zotero DOI pass. |
| 4 | Psichogios & Ungar 1992; Karniadakis 2021; Darby 2011; Marchetti 2009 | Zotero DOI pass. |
| 5 | Kobayashi 2024 SGW author list/title | Pull PDF from Stanford URL. |
| 6 | See 2008 PDF | UNU-GTP / EDC proceedings retrieval; may need library request. |
| 7 | Energies 2024 review, Buster 2021, digital-twin 2024, Møller 1998 author lists | Complete records in Zotero. |
| 8 | Malate & O'Sullivan Tongonan silica-deposition injection-well modeling (identified via a science.gov index only) | Locate the primary paper before adding — NOT yet in references.bib because the exact record is unconfirmed. |

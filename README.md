# ipis-thesis-geothermal-silica

**Physics-Informed Soft Sensing and Real-Time Inhibitor Optimization for Silica Scaling Mitigation in Philippine Liquid-Dominated Geothermal Brine Systems**

Idea **E1** — strongest alternative to the pyrolysis line. Part of the IPIS research program.

## One-line contribution
A first-principles silica saturation-index and polymerization-kinetics model, fused with an ML residual, forms a soft sensor for scaling rate along the brine line; this drives a real-time optimizer for inhibitor dose and reinjection temperature that is robust to brine-chemistry uncertainty.

## Target journal
Journal of Process Control (fallback: Geothermics).

## Why this one
The soft-sensor + RTO architecture maps directly onto the IPIS stack, so E1 is a **lateral move, not a restart**. It is independent of W1/D — no upstream pin, no shared flowsheet.

## Status
- [x] P0 — Repository & environment setup
- [ ] P1 — Literature review & gap matrix
- [ ] P2 — Brine saturation + silica polymerization model (verified)
- [ ] P3 — Brine-chemistry dataset + scaling/output case series
- [ ] P4 — Physics-informed scaling-rate soft sensor + RTO/MPC
- [ ] P5 — Validation vs. published case data; empirical-dosing baseline
- [ ] P6 — Sensitivity/UQ + inhibitor-cost and binary-opportunity accounting
- [ ] P7 — Manuscript drafting (JPC)
- [ ] P8 — Submission
- [ ] P9 — Zenodo DOI preservation

## Environment
```bash
conda env create -f environment.yml
conda activate ipis-thesis-geothermal-silica
```

## Data posture (read before P3)
Designed to stand alone **in-silico** on published brine chemistry. Real EDC/field operating data is an *upgrade, not a dependency* — if it never arrives, the thesis still completes. See `data/README.md` for the evidence-tier rules.

## Scope guard
Surface brine / reinjection line only. **Excluded:** reservoir-scale modeling, calcite scaling, full binary-plant design (binary enters only as an opportunity metric).

## License
MIT (code). See `LICENSE`. Zenodo DOI minted at pre-submission release (P9).

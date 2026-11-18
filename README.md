# Real-time optimization of reinjection temperature and inhibitor dose for geothermal silica scaling control

Hybrid soft sensing and robust real-time optimization (RTO) for controlling
amorphous-silica scaling at the reinjection line of liquid-dominated
geothermal fields, demonstrated in silico on brine chemistry from Philippine
fields.

**Manuscript:** *Real-time optimization of reinjection temperature and
inhibitor dose for geothermal silica scaling control under uncertain kinetics
and sparse measurements.* Bien Don Busico, University of the Philippines
Diliman. Submitted to *Geothermics* (Elsevier), November 2026; under review.

This repository holds all code, transcribed primary data, result files,
figures and the submission package. Every number, table and figure in the
manuscript is regenerated from the committed result files by the scripts
here — nothing is typed by hand.

## What the study finds

- The classical amorphous-silica polymerization rate law (Rothbaum & Rohde,
  1979) differs from the independent 2024 laboratory dataset of Scott et al.
  by a factor of **six at the median**, and its temperature dependence is
  non-Arrhenius above about 90 °C.
- A daily feedback correction of the scaling constraint is safe **only when
  computed at the measured silica concentration**. Computed at the design-case
  brine composition it mistakes the optimizer's own safety margin for model
  error: under sixfold-faster kinetics the line then exceeds the scaling limit
  on roughly an order of magnitude more days per run.
- With the measured anchor, a **scalar** bias correction performs as well as
  Gaussian-process and gradient-boosted (machine-learned) corrections. The
  scheme needs no machine learning — only a daily silica grab sample and one
  scaling-rate measurement.
- A hybrid soft sensor estimates the scaling rate with about **51 % lower
  error** than its kinetic core, provided its correction is earned from the
  plant's own labels.

Exact figures, confidence intervals and the operating-point analysis are in
the manuscript under `submission/geot/`.

## Repository layout

| Path | Contents |
|------|----------|
| `src/` | Models, simulated plant, soft sensor, robust RTO, experiments, and the self-checking gate (`run_all_checks.py`) |
| `src/data/` | Re-keyed primary data tables (e.g. Rothbaum & Rohde 1979, Table II) |
| `results/` | All committed result files (CSV/JSON) the manuscript draws from |
| `figures/` | Generated figures — vector PDF + PNG |
| `manuscript/` | LaTeX sources, the number/figure build scripts, and the Word (`.docx`) builder |
| `submission/geot/` | *Geothermics* submission package (manuscript, figures, supplement, letters) |
| `submission/cace/` | Earlier *Computers & Chemical Engineering* package, kept as a record |
| `literature/` | `references.bib` |
| `docs/` | Design notes (uncertainty-quantification commitment) |
| `DATA_NOTICE.md` | Third-party data and how to obtain it |
| `LICENSE`, `LICENSE-DATA.md` | Licensing (see below) |

## Reproducing the results

Requirements: Python 3.13 with the pinned scientific stack (NumPy, SciPy,
pandas, LightGBM, SALib, Matplotlib) plus `phreeqpython`. A conda environment
named `e1` is assumed.

```bash
conda activate e1

# 1. Third-party dataset — NOT redistributed here (see DATA_NOTICE.md).
#    Download the Scott et al. (2024) supplementary Excel file from
#    doi:10.1016/j.gca.2024.02.017 and save it as:
#    literature/scott2024_supplementary_dataset.xlsx

# 2. Integrity gate — runs every module's self-checks.
python src/run_all_checks.py
#    expected tail: GATE OPEN — 16 modules, 111 checks

# 3. Regenerate the manuscript numbers, figures and submission files.
python manuscript/build_submission.py   # numbers, journal figures, LaTeX proof
python manuscript/build_docx.py          # Word manuscript, supplement, letters
```

All stochastic components are seeded, result files are byte-reproducible on
the pinned environment, and a provenance gate fails if any committed result no
longer matches the current code. The convention is that no commit is made
against a failing ("red") gate.

## Data availability

Code, transcribed primary data and all result files are in this repository.
The independent validation dataset is the supplementary material of Scott et
al. (2024), obtained from the article (doi:10.1016/j.gca.2024.02.017); it is
**not** redistributed here. See `DATA_NOTICE.md`.

## License

- Code (`src/`, `manuscript/*.py`): MIT, see `LICENSE`.
- Results, figures and transcribed data (`results/`, `figures/`,
  `src/data/`): CC BY 4.0, see `LICENSE-DATA.md`.
- Manuscript text and submission package (`manuscript/latex/`,
  `submission/`): all rights reserved while under review.
- Third-party files keep their own licenses (e.g. the CSL style,
  CC BY-SA 3.0). The Scott et al. (2024) dataset is not redistributed.

## Citation

Until the article is published, cite the repository:

> Busico, B.D. (2026). *Real-time optimization of reinjection temperature
> and inhibitor dose for geothermal silica scaling control: code and
> results.* https://github.com/beebzy-droid/e1-geothermal-silica-rto

## Author

Bien Don Busico — University of the Philippines Diliman, Quezon City 1101,
Philippines.

## Acknowledgement of tools

Analysis code and manuscript were developed with the assistance of a
generative-AI assistant under the author's direction; the author ran the gate
and all experiments and is responsible for the code and results. See the
manuscript's declaration for details.

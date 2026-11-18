# Licensing of non-code content

This repository carries three licensing regimes. When a file is not listed
below, the code license in `LICENSE` (MIT) applies.

| Path | License |
|------|---------|
| `src/` (code), `manuscript/*.py` | MIT (see `LICENSE`) |
| `results/` (result files, CSV/JSON) | CC BY 4.0 |
| `figures/` (generated figures) | CC BY 4.0 |
| `src/data/` (the author's re-keyed transcriptions) | CC BY 4.0, for the transcription and its checks only (see below) |
| `manuscript/latex/`, `manuscript/cover_letter.txt`, `submission/` | All rights reserved (see below) |
| `manuscript/elsevier-harvard.csl` | CC BY-SA 3.0, from the Citation Style Language project (its own header) |
| Third-party data cited in `DATA_NOTICE.md` | Not redistributed; obtain from the source |

## CC BY 4.0: results, figures, transcribed data

Copyright (c) 2026 Bien Don Busico. Licensed under the Creative Commons
Attribution 4.0 International License,
https://creativecommons.org/licenses/by/4.0/. You may share and adapt this
material for any purpose, provided you give appropriate credit, link to the
license and indicate any changes.

Suggested attribution: Busico, B.D. (2026). Real-time optimization of
reinjection temperature and inhibitor dose for geothermal silica scaling
control: code and results. https://github.com/beebzy-droid/e1-geothermal-silica-rto

The tables in `src/data/` are the author's re-keyed transcriptions of
numerical values reported in the cited primary literature (for example,
Rothbaum and Rohde, 1979, Table II). The license covers the transcription,
its checksums and its integrity checks. The underlying measurements belong
to their original authors and must be cited to them. No page images, PDFs or
other reproductions of the published articles are included in this
repository.

## All rights reserved: manuscript text

The manuscript sources and the submission package are under peer review at
*Geothermics* (Elsevier). Copyright (c) 2026 Bien Don Busico, all rights
reserved. They are published here so that every number in the manuscript can
be traced to the code and result files that produce it. You may read them
and run the build scripts on them; please do not redistribute or republish
the text. The license of these files will be updated to match the journal's
publishing agreement once a decision is made.

## Not redistributed

The supplementary dataset of Scott et al. (2024),
doi:10.1016/j.gca.2024.02.017, is used for validation but is not included.
See `DATA_NOTICE.md` for how to obtain it.

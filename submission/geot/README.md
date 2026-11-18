# Geothermics submission package (E1)

Built by `python manuscript/build_submission.py` (numbers, checks, journal
figures, LaTeX proof copy) and then `python manuscript/build_docx.py`
(Word files). Every number comes from `results/*.csv` through
`manuscript/make_numbers.py`, which refuses to run on stale results or on
prose claims the data no longer support.

## Upload map (Editorial Manager)

| File | Item type |
|---|---|
| `manuscript_GEOT.docx` | **Manuscript** (single column, line and page numbers, figures and tables embedded, editable equations) |
| `Figure_1.png` ... `Figure_7.png` | **Figure**, one file each, in order (line art at >= 1000 dpi; single-column figures >= 3543 px wide, full-page figures 7480 px) |
| `highlights.docx` | **Highlights** (5 bullets, each <= 85 characters) |
| `supplementary_material.docx` | **Supplementary material** (Table S1: Gaussian-process and hybrid corrections) |
| `cover_letter.docx` | **Cover letter** |
| `declaration_of_competing_interest.docx` | **Declaration of interest statement** (same wording as Elsevier's declarations tool, "nothing to declare"; generate it with declarations.elsevier.com instead if the system insists on the tool's own file) |

Paste into the form: `abstract.txt` (245 words), keywords below.
`proof/` holds the LaTeX proof copy for reading; it is not uploaded.

## Form fields

- Article type: full-length article.
- Title: Real-time optimization of reinjection temperature and inhibitor
  dose for geothermal silica scaling control under uncertain kinetics and
  sparse measurements
- Keywords (7): silica scaling; reinjection; scale inhibitor; real-time
  optimization; soft sensor; constraint adaptation; Philippines
- Research data (Option C): "The code, the transcribed primary data, all
  result files and the scripts that regenerate every table and figure are
  available at https://github.com/beebzy-droid/e1-geothermal-silica-rto.
  The independent validation dataset is the supplementary material of
  Scott et al. (2024), https://doi.org/10.1016/j.gca.2024.02.017, and is
  obtained from that article; it is not redistributed."
- Funding: none (statement is in the manuscript).
- Generative AI: declared in the manuscript, before the references.

## Checks run on this build

- Abstract 245 words (limit 250); highlights 72-82 characters (limit 85);
  7 keywords (limit 7).
- 36 references, all cited, all with volume and pages or article number
  where they exist; name particles (de, del, van den, von) consistent in
  text and list.
- Every number in the Word text matches the macro-expanded LaTeX source.
- Figures redrawn from committed result files (`src/paper_figures.py`),
  with integrity checks that the recomputed values reproduce the stored
  ones; no titles on the artwork (captions carry them).
- Rendered in LibreOffice, not Microsoft Word: open the manuscript once in
  Word and look at Eqs. (1)-(7) and Tables 1-2 before uploading.

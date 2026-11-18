# Manuscript sources (Geothermics)

- `main.tex`, `sections/*.tex`: the text. Experimental numbers are NOT
  typed here: they come from `numbers.tex` and the `tab_*_body.tex`
  files, which `../make_numbers.py` generates from `results/*.csv`.
- `supplementary.tex`: the supplementary material (Table S1).
- `highlights.tex`: the highlights, with the same macros.
- `../cover_letter.txt`: the cover letter, with the same macros.

Regenerate the numbers after any experiment rerun (pure Python, no TeX):

    python manuscript/make_numbers.py

It stops if `src/provenance.py` says the results are stale, or if a claim
made in the prose is no longer true in the data.

Build the submission (needs pdflatex + bibtex + elsarticle, poppler's
pdftoppm, pandoc >= 3, python-docx, and the Scott 2024 data file for two
of the journal figures):

    python manuscript/build_submission.py   # numbers, journal figures,
                                             # checks, LaTeX proof copy,
                                             # Figure_N.png
    python manuscript/build_docx.py          # Word manuscript, supplement,
                                             # highlights, letters

Output: `submission/geot/` (the proof copy is in `submission/geot/proof/`
and is not uploaded). The journal figures are drawn by
`src/paper_figures.py` from the committed result files; the gate modules
still write their own diagnostic figures.

Rule: never edit `numbers.tex`, the table bodies, or anything under
`submission/` by hand. The earlier C&CE package stays in
`submission/cace/` for the record.

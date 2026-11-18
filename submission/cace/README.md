# Computers & Chemical Engineering — submission package

Built by `python manuscript/build_submission.py` from `manuscript/latex/`
and `results/*.csv`. Do not edit the files here by hand: change the
sources and rebuild.

| File | What it is | Where it goes in Editorial Manager |
|---|---|---|
| `manuscript_CACE.docx` | Word manuscript, figures and tables embedded, editable equations; built by `python manuscript/build_docx.py` from the same LaTeX sources and `numbers.tex` as the PDF | **Manuscript** |
| `declaration_of_competing_interest.docx` | single-author "nothing to declare" statement | **Declaration of Interest Statement** |
| `highlights.docx` | 5 bullets, each ≤ 85 characters | **Highlights** |
| `cover_letter.pdf` | cover letter (text in `cover_letter.txt`) | **Cover Letter** |
| `Figure_1.pdf` … `Figure_7.pdf` | vector figures, in order of appearance | **Figure**, only if the system asks for separate figure files (they are already embedded in the Word manuscript) |
| `abstract.txt` | 248-word abstract, plain text | paste into the abstract field |
| `manuscript_CACE.tex` | single-file LaTeX source, reference list inlined | not uploaded with the Word route; keep for the revision stage |
| `manuscript_CACE.pdf` | compiled LaTeX copy, the reference rendering | not uploaded (EM builds its own) |

The Word file needs pandoc >= 3 and `pip install python-docx` to rebuild.
It was checked in LibreOffice, not in Microsoft Word: open it once in
Word and look at Eqs. (1)-(6) and Table 2 before uploading.

Form fields: Section/Category "Process dynamics, control and
monitoring"; data statement "Other" (text in the hand-over note); SSRN
preprint: No.

Keywords: soft sensor; hybrid modeling; real-time optimization;
constraint adaptation; plant-model mismatch; geothermal energy; silica
scaling.

Article type: Full Length Article.

Research data: Yes — https://github.com/beebzy-droid/e1-geothermal-silica-rto
(repository "other"; original data). Update the public snapshot BEFORE
submitting: it still holds the first-submission code and results.

Generative AI: the manuscript carries the required declaration (before
the references) and Appendix B describes AI-assisted software
development. If the form asks, answer yes and name the tool as the
manuscript does.

After EM builds its PDF, check: 7 figures, 2 tables, 6 numbered
equations, 30 references, no "??" and no empty boxes anywhere.

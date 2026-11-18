@echo off
REM The submission is built by scripts (numbers come from results/*.csv).
REM Run from the repo root; needs pdflatex + bibtex + elsarticle, pdftoppm,
REM pandoc and python-docx.
python manuscript\build_submission.py || exit /b 1
python manuscript\build_docx.py

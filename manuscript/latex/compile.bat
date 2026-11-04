@echo off
REM E1 manuscript build — run from manuscript\latex\
copy /Y ..\..\literature\references.bib references.bib
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
echo Done. Open main.pdf

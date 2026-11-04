# JPC submission package (Editorial Manager)

## Files in this folder
1. `manuscript_JPC.tex` - single-file manuscript, bibliography inlined
   in citation order (EM builds the PDF from this source).
2. `cover_letter.txt`
3. `highlights.txt` (5 bullets, each <= 85 characters)
4. `declaration_of_interests.txt`
5. `assemble_submission.bat` - copies the six gate-regenerated figures
   from the repo `figures\` folder next to the tex.

## Figures (upload as separate files; EM matches by filename)
fig_temperature_lever.png, fig_arrhenius_overprediction.png,
fig_scarcity_sweep.png, fig_sensitivity_sobol.png,
fig_kinetics_validation.png, fig_sensor_validation_scott.png
Use the copies from the repo `figures/` folder (gate-regenerated,
committed) - NOT any other copies.

## Editorial Manager steps
1. Article type: Research Paper.
2. Upload in order: cover letter, highlights, manuscript
   (`manuscript_JPC.tex`), the six figures, declaration.
3. Keywords (from the manuscript): soft sensor; hybrid modeling;
   real-time optimization; plant-model mismatch; geothermal energy;
   silica scaling; Philippines.
4. EM compiles the PDF - open it and check every figure renders and
   the reference list is complete (26 items) before approving.

## Recommended smoke test before EM
Upload `manuscript_JPC.tex` + the six figures to a blank Overleaf
project and compile once (needs the `elsarticle` class, available on
Overleaf by default). Fix nothing by hand in EM that you did not first
fix here and in the repo.

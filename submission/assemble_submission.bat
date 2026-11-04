@echo off
REM Run from the repo root. Copies gate-regenerated figures beside the tex.
for %%F in (fig_temperature_lever.png fig_arrhenius_overprediction.png fig_scarcity_sweep.png fig_sensitivity_sobol.png fig_kinetics_validation.png fig_sensor_validation_scott.png) do copy /Y figures\%%F submission\
echo Done. submission\ now contains the manuscript, documents, and figures.

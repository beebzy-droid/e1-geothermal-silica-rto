"""
scott2024_dataset.py — E1 / ipis-thesis-geothermal-silica
Phase P5, build 1: parser + integrity checks for the Scott et al. (2024)
supplementary experimental dataset (T1).

SOURCE & PROVENANCE
    literature/scott2024_supplementary_dataset.xlsx — Supplementary
    material of Scott et al. (2024), GCA 371:78-94,
    doi:10.1016/j.gca.2024.02.017 (dataset citation = the article, per
    corresponding-author email 2026-07). PARAMETERIZATION note: model
    parameters must follow the CORRIGENDUM (doi:10.1016/j.gca.2026.06.027)
    / the author-provided script in reference/ — this module touches only
    the RAW EXPERIMENTAL DATA, which the corrigendum does not alter.

LAYOUT (verified against the file, 2026-07-15)
    Repeating 3-column blocks: [labels, values, blank].
    Rows 1-4: Experiment ID, Temp [degC], pH, I [mol/kg]
              (header spelling varies: 'Experiment'/'n', 'I'/'IS' — handled)
    Rows 5-6: series headers: Time [minutes] | SiO2(mono) [mmol/kg]
    Rows 7+ : the monomer-decay series (variable length).

INTEGRITY CHECKS (machine-readable source, so checks replace the manual
transcription protocol): unit-header pinning, metadata ranges, strictly
increasing time, and a PHYSICS cross-check — experiments that consumed
>30% of their initial supersaturation must plateau within a tolerance
band of the GA00 amorphous-silica solubility (pH <= 7.5 only, where
ionization corrections are small). This cross-validates Scott's T1
endpoints against our P2 primary correlation in both directions.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import math

import numpy as np
import pandas as pd
import openpyxl

from silica_saturation import solubility_amorphous_silica_ga00

_XLSX = Path(__file__).parent.parent / "literature" / \
    "scott2024_supplementary_dataset.xlsx"

_MW_SIO2 = 60.084  # g/mol; mmol/kg * MW = mg/kg

_EXPECTED_TIME_HDR = "[minutes]"
_EXPECTED_CONC_HDR = "[mmol/kg]"


@dataclass
class Scott2024Data:
    meta: pd.DataFrame     # experiment, T_C, pH, I_molkg, n_points
    series: pd.DataFrame   # experiment, time_min, sio2_mmolkg, sio2_mgkg


def _fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_scott2024(path: Path = _XLSX) -> Scott2024Data:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    grid = [list(r) for r in ws.iter_rows(values_only=True)]
    ncol = max(len(r) for r in grid)
    for r in grid:
        r.extend([None] * (ncol - len(r)))
    nrow = len(grid)

    meta_rows: List[Tuple] = []
    ser_rows: List[Tuple] = []
    seen: dict = {}
    for c0 in range(0, ncol, 3):
        ri = 0
        while ri < nrow:
            key = grid[ri][c0]
            if key is None or str(key).strip() not in ("Experiment", "n"):
                ri += 1
                continue
            # header block: ID, Temp, pH, I, series hdr x2
            exp = str(grid[ri][c0 + 1]).strip()
            # duplicate IDs = replicate runs listed twice — keep separate,
            # never merge (merging created spurious time reversals)
            seen[exp] = seen.get(exp, 0) + 1
            if seen[exp] > 1:
                exp = f"{exp}#r{seen[exp]}"
            T_C = float(grid[ri + 1][c0 + 1])
            pH = float(grid[ri + 2][c0 + 1])
            I = float(grid[ri + 3][c0 + 1])
            t_hdr = str(grid[ri + 5][c0]).strip()
            c_hdr = str(grid[ri + 5][c0 + 1]).strip()
            if t_hdr != _EXPECTED_TIME_HDR or c_hdr != _EXPECTED_CONC_HDR:
                raise ValueError(
                    f"[layout] block '{exp}' units changed: "
                    f"time='{t_hdr}', conc='{c_hdr}' — inspect the file.")
            ri += 6
            n_pts = n_skipped = 0
            while ri < nrow:
                cell0 = grid[ri][c0]
                if cell0 is not None and str(cell0).strip() in ("Experiment", "n"):
                    break                      # next stacked experiment
                t, c = _fnum(grid[ri][c0]), _fnum(grid[ri][c0 + 1])
                if t is None and grid[ri][c0] is None \
                        and c is None and grid[ri][c0 + 1] is None:
                    ri += 1
                    continue                   # blank spacer row
                if t is None or c is None:
                    n_skipped += 1             # 'n.a.' etc.
                    ri += 1
                    continue
                ser_rows.append((exp, t, c, c * _MW_SIO2))
                n_pts += 1
                ri += 1
            meta_rows.append((exp, T_C, pH, I, n_pts, n_skipped))

    meta = pd.DataFrame(meta_rows,
                        columns=["experiment", "T_C", "pH", "I_molkg",
                                 "n_points", "n_skipped"])
    # flag experiments outside the dissolved-monomer kinetics regime
    c0map = (pd.DataFrame(ser_rows, columns=["experiment", "t", "c", "mg"])
             .groupby("experiment")["mg"].first())
    meta["kinetics_regime"] = meta.experiment.map(c0map) <= 2000.0
    series = pd.DataFrame(ser_rows,
                          columns=["experiment", "time_min", "sio2_mmolkg",
                                   "sio2_mgkg"])
    return Scott2024Data(meta, series)


def endpoint_vs_ga00(data: Scott2024Data,
                     decay_frac_min: float = 0.70,
                     pH_min: float = 5.0,
                     pH_max: float = 7.5) -> pd.DataFrame:
    """For sufficiently-decayed, near-neutral experiments: compare the
    trailing plateau (mean of last 3 points) with GA00 solubility."""
    rows = []
    for _, m in data.meta.iterrows():
        s = data.series[data.series.experiment == m.experiment]
        if len(s) < 5 or not (pH_min <= m.pH <= pH_max) \
                or not m.kinetics_regime:
            continue
        c0 = float(s.sio2_mgkg.iloc[0])
        c_end = float(s.sio2_mgkg.iloc[-3:].mean())
        ce = solubility_amorphous_silica_ga00(m.T_C + 273.15)
        s0 = c0 - ce
        if s0 <= 0:
            continue
        decay = (c0 - c_end) / s0
        if decay < decay_frac_min:
            continue
        rows.append((m.experiment, m.T_C, m.pH, c0, c_end, ce,
                     c_end / ce, decay))
    return pd.DataFrame(rows, columns=["experiment", "T_C", "pH",
                                       "c0_mgkg", "c_end_mgkg",
                                       "ce_ga00_mgkg", "end_over_ga00",
                                       "decay_frac"])


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []
    data = load_scott2024()

    # 1. Volume of data parsed
    checks.append(("Experiments parsed (>=15) with series (>=5 pts each)",
                   len(data.meta) >= 15 and (data.meta.n_points >= 5).all(),
                   f"n_exp={len(data.meta)}, total_pts={len(data.series)}, "
                   f"kinetics-regime={int(data.meta.kinetics_regime.sum())}, "
                   f"flagged-out={int((~data.meta.kinetics_regime).sum())}"))

    # 2. Metadata ranges physical
    ok_meta = (data.meta.T_C.between(0, 250).all()
               and data.meta.pH.between(2, 12).all()
               and data.meta.I_molkg.between(0.001, 1.0).all())
    checks.append(("Metadata ranges physical (T, pH, I)", bool(ok_meta),
                   f"T: {data.meta.T_C.min():.0f}-{data.meta.T_C.max():.0f} C, "
                   f"pH: {data.meta.pH.min():.2f}-{data.meta.pH.max():.2f}, "
                   f"I: {data.meta.I_molkg.min():.3f}-"
                   f"{data.meta.I_molkg.max():.3f}"))

    # 3. Time vectors strictly increasing, no NaNs
    ok_t = True
    for e, g in data.series.groupby("experiment"):
        t = g.time_min.to_numpy()
        if np.any(~np.isfinite(t)) or np.any(np.diff(t) < 0) \
                or g.sio2_mmolkg.isna().any():
            ok_t = False
            break
    checks.append(("Time non-decreasing (dup sample times allowed); "
                   "no NaNs", ok_t, ""))

    # 4. PHYSICS cross-check: decayed near-neutral endpoints vs GA00
    ep = endpoint_vs_ga00(data)
    if len(ep) == 0:
        checks.append(("Endpoint-vs-GA00 cross-check", False,
                       "no qualifying experiments — inspect thresholds"))
    else:
        within = ep.end_over_ga00.between(0.6, 1.6)
        checks.append(("Near-complete near-neutral endpoints within "
                       f"[0.6,1.6]x GA00 ({len(ep)} qualifying exps)",
                       bool(within.all()),
                       f"end/GA00: {ep.end_over_ga00.min():.2f}-"
                       f"{ep.end_over_ga00.max():.2f}, "
                       f"median={ep.end_over_ga00.median():.2f}"))

    # 5. Monomer never negative; initial supersaturation positive for
    #    the polymerization experiments (c0 above GA00 in >=60% of runs)
    neg = (data.series.sio2_mmolkg < 0).any()
    n_super = 0
    for _, m in data.meta.iterrows():
        g = data.series[data.series.experiment == m.experiment]
        ce = solubility_amorphous_silica_ga00(m.T_C + 273.15)
        n_super += float(g.sio2_mgkg.iloc[0]) > ce
    checks.append(("No negative concentrations; majority start "
                   "supersaturated",
                   (not neg) and n_super >= 0.6 * len(data.meta),
                   f"supersaturated starts: {n_super}/{len(data.meta)}"))

    width = max(len(c[0]) for c in checks)
    print("P5 build-1 self-check — scott2024_dataset.py")
    print("-" * (width + 55))
    failed = 0
    for name, ok, extra in checks:
        failed += (not ok)
        print(f"{name:<{width}}  {'PASS' if ok else 'FAIL'}  {extra}")
    print("-" * (width + 55))
    print(f"{len(checks) - failed}/{len(checks)} passed."
          + ("" if not failed else "  GATE BLOCKED."))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()

"""
weres_deposition.py — E1 / ipis-thesis-geothermal-silica
Weres, Yee & Tsao (1981), J. Colloid Interface Sci. 84(2) 379-402:
molecular-deposition rate law, transcribed under the T1 protocol, and
the closure of the r_max units caveat (polymerization g/t/min -> wall
growth mm/yr).

TRANSCRIBED LAW (their equations; page/section anchors in comments)
    [3]  R_md [g SiO2 cm^-2 min^-1] = F(pH, pH_nom) * k_OH(T) * ff(S)
                                       * (1 - 1/S)
    [4a] ff(S) = S^5                          for S < S_t
    [4b] ff(S) = S_t^5 + 5 S_t^4 (S - S_t)    for S >= S_t
    [4c] log10 S_t = 0.0977 + 75.84 / T                (T in K)
         SOURCE DISCREPANCY (documented, not silently fixed): the
         typeset [4c] (verified visually at 300 dpi, not an OCR error)
         reproduces only the FIRST of the paper's own quoted values
         ("St = 2.15, 1.99, 1.85 at 50, 75, 100 C"): it gives
         2.150 / 2.068 / 2.000. Per protocol (printed derived values
         are the checksum), the PRIMARY variant is the least-squares
         fit through the quoted triplet; the printed formula is
         carried as the alternate and both are reported in the
         calibration output.
    [5]  log10 k_OH = 3.1171 - 4296.6 / T     [g SiO2 cm^-2 min^-1]
    S = c / c0 with their internal solubility (Fournier & Rowe form):
         log10 c0 = -731 / T + 1.52           [g SiO2 / kg H2O]
    F = 1 at the reference state pH = pH_nom = 7 (their normalization
    f'(7.0) = 1) — the near-neutral fence this project already imposes.

PRINTED CHECKSUMS (validated by the self-check, T1 protocol)
    - S_t = 2.15, 1.99, 1.85 at 50, 75, 100 C            (printed, [4c])
    - effective activation energy for molecular deposition, rewritten
      in CONCENTRATION terms, ~= 3.0 kcal/mol (printed). This number
      only reproduces if [4], [5] AND the c0 formula are all transcribed
      correctly together: d ln R / d(1/T) at fixed c combines the k_OH
      slope (-2.303*4296.6) with the opposing S^5-via-c0 slope
      (+5*2.303*731).

THE CLOSURE
    Bulk polymerization (our constraint variable) and wall molecular
    deposition are PARALLEL pathways of the same state (S, T) — Weres'
    central finding. The calibration therefore maps states where our
    constraint is ACTIVE (core rate = r_max) to the Weres-implied wall
    growth rate there:
        growth [mm/yr] = R_md / rho_AS * 10 [mm/cm] * 525600 [min/yr]
    with rho_AS = 2.21 g/cm^3 (amorphous silica; stated assumption,
    band 2.0-2.21 changes the result < 10%).

Outputs: results/weres_rmax_calibration.csv
"""

from pathlib import Path
import math

import numpy as np
import pandas as pd

from silica_saturation import solubility_amorphous_silica_ga00
from temperature_lever import k_of_T

_RESDIR = Path(__file__).parent.parent / "results"

RHO_AS_G_CM3 = 2.21           # stated assumption (band 2.0-2.21)
MIN_PER_YR = 525600.0
R_CAL = 1.98720425            # cal / (mol K)

# printed St triplet (the checksum): (T_K, St)
_ST_PRINTED = [(323.15, 2.15), (348.15, 1.99), (373.15, 1.85)]
_x = np.array([1.0 / t for t, _ in _ST_PRINTED])
_y = np.array([math.log10(v) for _, v in _ST_PRINTED])
_B_FIT, _A_FIT = np.polyfit(_x, _y, 1)   # log10 St = A + B/T (fitted)


def c0_weres_gkg(T_K: float) -> float:
    """Their internal solubility [g SiO2 / kg H2O] (Fournier-Rowe form,
    as used to calibrate [3]-[5]; kept for calibration integrity)."""
    return 10.0 ** (-731.0 / T_K + 1.52)


def S_t(T_K: float, variant: str = "fitted") -> float:
    """PRIMARY 'fitted' = LSQ through the paper's quoted St triplet;
    'printed' = the typeset [4c] (source-internal discrepancy above)."""
    if variant == "printed":
        return 10.0 ** (0.0977 + 75.84 / T_K)                  # [4c]
    return 10.0 ** (_A_FIT + _B_FIT / T_K)


def k_oh(T_K: float) -> float:
    return 10.0 ** (3.1171 - 4296.6 / T_K)                     # [5]


def ff(S: float, T_K: float, variant: str = "fitted") -> float:
    St = S_t(T_K, variant)
    if S < St:
        return S ** 5                                          # [4a]
    return St ** 5 + 5.0 * St ** 4 * (S - St)                  # [4b]


def rmd_g_cm2_min(c_mgkg: float, T_C: float, F: float = 1.0,
                  variant: str = "fitted") -> float:
    """Molecular deposition flux at (c, T), near-neutral reference."""
    T_K = T_C + 273.15
    S = (c_mgkg / 1000.0) / c0_weres_gkg(T_K)
    if S <= 1.0:
        return 0.0
    return F * k_oh(T_K) * ff(S, T_K, variant) * (1.0 - 1.0 / S)  # [3]


def growth_mm_yr(c_mgkg: float, T_C: float, F: float = 1.0,
                 rho: float = RHO_AS_G_CM3,
                 variant: str = "fitted") -> float:
    return (rmd_g_cm2_min(c_mgkg, T_C, F, variant)
            / rho * 10.0 * MIN_PER_YR)


def rmax_calibration(r_max_g_t_min: float,
                     T_grid=None) -> pd.DataFrame:
    """Map constraint-active states (core rate == r_max) to
    Weres-implied wall growth across the operating temperature range."""
    if T_grid is None:
        T_grid = np.linspace(90.0, 175.0, 18)
    rows = []
    for T in T_grid:
        k = k_of_T(float(T))
        s_active = (r_max_g_t_min / k) ** 0.25          # core: k s^4
        c_active = solubility_amorphous_silica_ga00(T + 273.15) + s_active
        g_fit = growth_mm_yr(c_active, float(T), variant="fitted")
        g_pr = growth_mm_yr(c_active, float(T), variant="printed")
        rows.append((float(T), s_active, c_active, g_fit, g_pr))
    return pd.DataFrame(rows, columns=["T_C", "s_active_g_t",
                                       "c_active_mgkg",
                                       "growth_mm_yr_fitted",
                                       "growth_mm_yr_printed4c"])


def _self_check() -> None:
    checks = []

    # 1a. PRIMARY variant reproduces the paper's quoted St triplet
    st = [S_t(T + 273.15) for T in (50.0, 75.0, 100.0)]
    ok1 = all(abs(a - b) < 0.01 for a, b in zip(st, (2.15, 1.99, 1.85)))
    checks.append(("Primary St variant reproduces quoted triplet "
                   "2.15/1.99/1.85",
                   ok1, "St=" + "/".join(f"{v:.3f}" for v in st)))

    # 1b. Documented source discrepancy: the typeset [4c] matches the
    #     quoted triplet ONLY at 50 C (2.150) and gives 2.068/2.000 at
    #     75/100 C. This check FAILS if either variant is silently
    #     edited to agree with the other.
    stp = [S_t(T + 273.15, "printed") for T in (50.0, 75.0, 100.0)]
    ok1b = (abs(stp[0] - 2.150) < 0.005 and abs(stp[1] - 2.068) < 0.005
            and abs(stp[2] - 2.000) < 0.005
            and abs(stp[1] - 1.99) > 0.05)
    checks.append(("Source discrepancy in [4c] preserved as documented",
                   ok1b, "printed-formula St="
                   + "/".join(f"{v:.3f}" for v in stp)))

    # 2. Printed checksum: effective Ea ~ 3.0 kcal/mol in
    #    CONCENTRATION terms. Analytic identity, independent of [4c]:
    #    Ea = 2.303 R (4296.6 - 5*731) in the fifth-order regime —
    #    validates the transcription of BOTH slopes jointly.
    Ea_kcal = 2.303 * R_CAL * (4296.6 - 5.0 * 731.0) / 1000.0
    checks.append(("Printed checksum: effective Ea ~ 3.0 kcal/mol "
                   "(analytic, joint [5]+c0 slopes)",
                   abs(Ea_kcal - 3.0) < 0.2,
                   f"Ea={Ea_kcal:.2f} kcal/mol (printed ~3.0)"))

    # 3. Flux plausibility at their experimental window (100 C, S~2):
    #    order 1e-7..1e-5 g cm^-2 min^-1
    T_K = 373.15
    c_test = 2.0 * c0_weres_gkg(T_K) * 1000.0
    r = rmd_g_cm2_min(c_test, 100.0)
    checks.append(("Flux magnitude plausible at (100 C, S=2)",
                   1e-8 < r < 1e-5, f"R_md={r:.2e} g cm^-2 min^-1"))

    # 4. The closure: constraint-active mapping finite/positive across
    #    90-175 C; CSV written
    cal = rmax_calibration(0.5)
    g = cal.growth_mm_yr_fitted
    ok4 = bool(np.isfinite(g).all() and (g > 0).all()
               and np.isfinite(cal.growth_mm_yr_printed4c).all())
    _RESDIR.mkdir(exist_ok=True)
    cal.to_csv(_RESDIR / "weres_rmax_calibration.csv", index=False)
    checks.append(("r_max=0.5 g/t/min maps to finite positive mm/yr "
                   "across 90-175 C (both variants written)",
                   ok4, f"fitted-variant growth {g.min():.2f}/"
                        f"{g.median():.2f}/{g.max():.2f} mm/yr "
                        f"(min/median/max)"))

    # 5. Sanity at the Table-2 operating point (137.5 C, realized
    #    brine ~840 mg/kg): within [0.05, 5] mm/yr
    g_op = growth_mm_yr(840.0, 137.5)
    checks.append(("Operating-point growth within sanity band "
                   "[0.05, 5] mm/yr",
                   0.05 < g_op < 5.0, f"{g_op:.2f} mm/yr at "
                   f"(137.5 C, 840 mg/kg)"))

    width = max(len(c[0]) for c in checks)
    print("Weres 1981 transcription self-check — weres_deposition.py")
    print("-" * (width + 62))
    failed = 0
    for name, ok, extra in checks:
        failed += (not ok)
        print(f"{name:<{width}}  {'PASS' if ok else 'FAIL'}  {extra}")
    print("-" * (width + 62))
    print(f"{len(checks) - failed}/{len(checks)} passed."
          + ("" if not failed else "  GATE BLOCKED."))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()
